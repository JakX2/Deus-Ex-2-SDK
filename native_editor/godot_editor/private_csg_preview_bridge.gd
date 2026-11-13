extends RefCounted
## P102: source-private CSG to Godot render shell, no native BSP write.
## Only two already-authored clipped Box specs and two proper rigid world
## preview transforms reach the Python worker. All JSON stages are ephemeral.
const Brush = preload("res://brush_geometry.gd")
const PythonRuntime = preload("res://python_runtime.gd")
const Worker = "res://backend/dx2_private_csg_preview_worker.py"
const MAX_STDOUT_BYTES = 1024 * 1024


static func _private_box(raw: Variant) -> Dictionary:
    if typeof(raw) != TYPE_DICTIONARY:
        return {}
    var spec: Dictionary = Brush.validate(raw)
    if (spec.is_empty() or str(spec.get("kind", "")) != "Box"
        or (not spec.has("clip_plane") and not spec.has("clip_planes"))
        or Brush.build_mesh(spec) == null):
        return {}
    return spec


static func _rigid_record(pose: Transform3D) -> Dictionary:
    # Basis columns in Godot are serialized as rows to match Python.
    var basis: Basis = pose.basis
    var origin := pose.origin
    var coordinates := [
        basis.x.x, basis.y.x, basis.z.x,
        basis.x.y, basis.y.y, basis.z.y,
        basis.x.z, basis.y.z, basis.z.z,
        origin.x, origin.y, origin.z,
    ]
    for value in coordinates:
        if not is_finite(float(value)):
            return {}
    return {
        "basis": [
            [basis.x.x, basis.y.x, basis.z.x],
            [basis.x.y, basis.y.y, basis.z.y],
            [basis.x.z, basis.y.z, basis.z.z],
        ],
        "origin": [origin.x, origin.y, origin.z],
    }


static func _stage_private_json(path: String, record: Dictionary) -> bool:
    if FileAccess.file_exists(path):
        return false
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(JSON.stringify(record))
    file.flush()
    file.close()
    return true


static func preview_pair(
        raw_a: Variant, raw_b: Variant,
        pose_a: Transform3D, pose_b: Transform3D,
        operation: String) -> Dictionary:
    if operation not in ["intersection", "subtraction"]:
        return {"ok": false, "message": "Unsupported private CSG operation."}
    var spec_a := _private_box(raw_a)
    var spec_b := _private_box(raw_b)
    var transform_a := _rigid_record(pose_a)
    var transform_b := _rigid_record(pose_b)
    if (spec_a.is_empty() or spec_b.is_empty()
        or transform_a.is_empty() or transform_b.is_empty()):
        return {"ok": false, "message": (
            "Only two valid editor-created clipped Boxes with finite "
            + "rigid preview placements are accepted.")}
    var worker_path := ProjectSettings.globalize_path(Worker)
    if not FileAccess.file_exists(worker_path):
        return {"ok": false, "message": "Private CSG Python preview worker missing."}
    var folder := ProjectSettings.globalize_path(
        "user://private_csg_preview_stage")
    if DirAccess.make_dir_recursive_absolute(folder) != OK:
        return {"ok": false, "message": "Private CSG preview staging unavailable."}
    var prefix := (
        "csg_" + str(OS.get_process_id()) + "_"
        + str(Time.get_ticks_usec()) + "_")
    var stages: Array[String] = []
    var records := [spec_a, spec_b, transform_a, transform_b]
    var staged := true
    for i in range(records.size()):
        var stage: String = folder.path_join(prefix + str(i) + ".json")
        if FileAccess.file_exists(stage) or not _stage_private_json(stage, records[i]):
            staged = false
            break
        stages.append(stage)
    if not staged:
        for stage in stages:
            DirAccess.remove_absolute(stage)
        return {"ok": false, "message": "Unable to stage private CSG preview."}
    var arguments := PackedStringArray([worker_path, operation])
    for path in stages:
        arguments.append(path)
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), arguments, output, true)
    if code == -1:
        output.clear()
        var fallback := PackedStringArray(["-3"])
        fallback.append_array(arguments)
        code = OS.execute("py", fallback, output, true)
    for stage in stages:
        DirAccess.remove_absolute(stage)
    var combined := "\n".join(output).strip_edges()
    if code != 0:
        return {"ok": false, "message": (
            "Private CSG preview refused: " + combined.substr(0, 240))}
    if combined.length() > MAX_STDOUT_BYTES or combined.is_empty():
        return {"ok": false, "message": "Private CSG worker report oversized or empty."}
    var parsed: Variant = JSON.parse_string(combined)
    if typeof(parsed) != TYPE_DICTIONARY:
        return {"ok": false, "message": "Private CSG returned malformed JSON."}
    if (str(parsed.get("operation", "")) != (
            "a-minus-b" if operation == "subtraction" else "")
        and operation == "subtraction"):
        return {"ok": false, "message": "Private CSG operation mismatch."}
    if (parsed.get("original_gmp_or_ibd_modified", true) != false
        or parsed.get("retail_game_runtime_verified", true) != false
        or parsed.get("native_collision_generated",
            parsed.get("native_havok_or_mopp_cooker_enabled", true)) != false):
        return {"ok": false, "message": "Private CSG worker violated read-only scope."}
    if (operation == "intersection"
        and str(parsed.get("schema", "")) !=
        "DX2SDK-private-convex-CSG-intersection-preview-v1"):
        return {"ok": false, "message": "Unexpected intersection schema."}
    if (operation == "subtraction"
        and str(parsed.get("schema", "")) !=
        "DX2SDK-source-private-convex-CSG-difference-decomposition-v1"):
        return {"ok": false, "message": "Unexpected subtraction schema."}
    return {"ok": true, "report": parsed, "operation": operation}
