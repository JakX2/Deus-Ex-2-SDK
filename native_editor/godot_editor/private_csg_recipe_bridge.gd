extends RefCounted
## P103: explicit private CSG recipe NEW-file save / verified reopen.
## No native DX2 .gmp/.ibd or original BSP actor can be read or written.
const CSG = preload("res://private_csg_preview_bridge.gd")
const PythonRuntime = preload("res://python_runtime.gd")
const WORKER = "res://backend/dx2_private_csg_recipe_worker.py"
const MAX_RESULT_CHARS = 1024 * 1024


static func _destination(path: String, must_exist: bool) -> bool:
    if (path.is_empty() or not path.is_absolute_path()
        or not path.to_lower().ends_with(".dx2csg.json")
        or DirAccess.dir_exists_absolute(path)):
        return false
    if must_exist:
        return FileAccess.file_exists(path)
    return not FileAccess.file_exists(path)


static func _run(args: PackedStringArray) -> Dictionary:
    var worker := ProjectSettings.globalize_path(WORKER)
    if not FileAccess.file_exists(worker):
        return {"ok": false, "message": "Private CSG recipe worker missing."}
    var command := PackedStringArray([worker])
    command.append_array(args)
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), command, output, true)
    if code == -1:
        output.clear()
        var fallback := PackedStringArray(["-3"])
        fallback.append_array(command)
        code = OS.execute("py", fallback, output, true)
    var combined := "\n".join(output).strip_edges()
    if code != 0:
        return {"ok": false, "message": (
            "Private CSG recipe refused: " + combined.substr(0, 260))}
    if combined.is_empty() or combined.length() > MAX_RESULT_CHARS:
        return {"ok": false, "message": "Private CSG recipe worker output invalid."}
    var parsed: Variant = JSON.parse_string(combined)
    if typeof(parsed) != TYPE_DICTIONARY:
        return {"ok": false, "message": "Private recipe returned malformed JSON."}
    if (str(parsed.get("schema", "")) != "DX2Ed-private-CSG-recipe-v1"
        or parsed.get("read_only_source", true) != true):
        return {"ok": false, "message": "Private recipe source scope invalid."}
    return {"ok": true, "record": parsed}


static func save_recipe(
        path: String, operation: String,
        name_a: String, name_b: String,
        spec_a: Variant, spec_b: Variant,
        pose_a: Transform3D, pose_b: Transform3D) -> Dictionary:
    if not _destination(path, false):
        return {"ok": false, "message": (
            "Choose an unused local .dx2csg.json file for the recipe.")}
    if operation not in ["intersection", "subtraction"]:
        return {"ok": false, "message": "Only private CSG recipe operations supported."}
    var a := CSG._private_box(spec_a)
    var b := CSG._private_box(spec_b)
    var ta := CSG._rigid_record(pose_a)
    var tb := CSG._rigid_record(pose_b)
    if (a.is_empty() or b.is_empty() or ta.is_empty() or tb.is_empty()):
        return {"ok": false, "message": "Private CSG Box or transform invalid."}
    var folder := ProjectSettings.globalize_path(
        "user://private_csg_recipe_stage")
    if DirAccess.make_dir_recursive_absolute(folder) != OK:
        return {"ok": false, "message": "Private recipe staging directory unavailable."}
    var prefix := ("recipe_" + str(OS.get_process_id())
        + "_" + str(Time.get_ticks_usec()) + "_")
    var rows := [a, b, ta, tb]
    var paths: Array[String] = []
    for i in range(rows.size()):
        var stage: String = folder.path_join(prefix + str(i) + ".json")
        if not CSG._stage_private_json(stage, rows[i]):
            for used in paths:
                DirAccess.remove_absolute(used)
            return {"ok": false, "message": "Private recipe staging refused."}
        paths.append(stage)
    var args := PackedStringArray([
        "save", operation, name_a, name_b,
    ])
    for stage in paths:
        args.append(stage)
    args.append(path)
    var result := _run(args)
    for used in paths:
        DirAccess.remove_absolute(used)
    if not bool(result.get("ok", false)):
        return result
    var record: Dictionary = result["record"]
    if (str(record.get("operation", "")) != operation
        or str(record.get("source_private_a", "")) != name_a
        or str(record.get("source_private_b", "")) != name_b
        or record.get("original_game_files_modified", true) != false
        or record.get("retail_game_runtime_verified", true) != false
        or not FileAccess.file_exists(path)):
        return {"ok": false, "message": "Private recipe save verification refused."}
    return {"ok": true, "record": record, "path": path}


static func load_recipe(path: String) -> Dictionary:
    if not _destination(path, true):
        return {"ok": false, "message": "Select an existing private .dx2csg.json."}
    var result := _run(PackedStringArray(["load", path]))
    if not bool(result.get("ok", false)):
        return result
    var record: Dictionary = result["record"]
    if (not record.has("result")
        or typeof(record["result"]) != TYPE_DICTIONARY
        or str(record.get("operation", "")) not in [
            "intersection", "subtraction",
        ]):
        return {"ok": false, "message": "Private recipe replay result invalid."}
    var verified: Dictionary = record["result"]
    if (verified.get("original_gmp_or_ibd_modified", true) != false
        or verified.get("retail_game_runtime_verified", true) != false):
        return {"ok": false, "message": "Private recipe cannot load native data."}
    return {
        "ok": true, "operation": str(record["operation"]),
        "source_private_a": str(record["source_private_a"]),
        "source_private_b": str(record["source_private_b"]),
        "computed_result_sha256": str(record["computed_result_sha256"]),
        "report": verified, "path": path,
    }
