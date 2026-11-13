extends RefCounted
## DX2Ed v0.97. Read-only audit of exactly the local OBJ generated from one
## source-private authored Box. Never opens or writes native GMP/IBD resources.
const Brush = preload("res://brush_geometry.gd")
const PythonRuntime = preload("res://python_runtime.gd")


static func audit_clipped_box(raw: Variant, obj_path: String) -> Dictionary:
    if (typeof(raw) != TYPE_DICTIONARY or obj_path.is_empty()
        or obj_path.get_extension().to_lower() != "obj"
        or not obj_path.is_absolute_path()
        or not FileAccess.file_exists(obj_path)
        or DirAccess.dir_exists_absolute(obj_path)):
        return {"ok": false, "message": (
            "Read-only audit refused: select an existing local .obj file.")}
    var checked: Dictionary = Brush.validate(raw)
    if (checked.is_empty() or str(checked.get("kind", "")) != "Box"
        or (not checked.has("clip_plane")
            and not checked.has("clip_planes"))
        or Brush.build_mesh(checked) == null):
        return {"ok": false, "message": (
            "Read-only audit requires an editor-authored, clipped private Box. "
            + "Original imported actors and source BSP are excluded.")}
    var worker := ProjectSettings.globalize_path(
        "res://backend/dx2_private_obj_audit_worker.py")
    if not FileAccess.file_exists(worker):
        return {"ok": false, "message": "Private Python OBJ audit worker missing."}
    var stage_dir := ProjectSettings.globalize_path(
        "user://private_box_obj_stage")
    if DirAccess.make_dir_recursive_absolute(stage_dir) != OK:
        return {"ok": false, "message": "Cannot create private OBJ audit staging."}
    # Stage only one normalized private brush. Do not stage original game
    # source paths, actor records, map caches or imported assets.
    var stage := stage_dir.path_join(
        "private_audit_" + str(OS.get_process_id()) + "_"
        + str(Time.get_ticks_usec()) + ".json")
    if FileAccess.file_exists(stage):
        return {"ok": false, "message": "Private OBJ audit staging collision."}
    var file := FileAccess.open(stage, FileAccess.WRITE)
    if file == null:
        return {"ok": false, "message": "Private OBJ audit staging unavailable."}
    file.store_string(JSON.stringify(checked))
    file.flush()
    file.close()
    var output: Array = []
    var args := PackedStringArray([worker, stage, obj_path])
    var exit_code := OS.execute(PythonRuntime.executable(), args, output, true)
    if exit_code == -1:
        output.clear()
        exit_code = OS.execute(
            "py", PackedStringArray(["-3", worker, stage, obj_path]),
            output, true)
    # No temporary private metadata remains after either outcome.
    DirAccess.remove_absolute(stage)
    if exit_code != 0:
        return {"ok": false, "message": (
            "Private OBJ verification refused: "
            + "\n".join(output).strip_edges().substr(0, 340))}
    var parsed: Variant = JSON.parse_string("\n".join(output).strip_edges())
    if (typeof(parsed) != TYPE_DICTIONARY
        or str(parsed.get("status", "")) != "exact-source-private-OBJ-roundtrip-verified"
        or parsed.get("exact_export_match", false) != true
        or parsed.get("original_game_files_modified", true) != false
        or parsed.get("native_world_model_writer_enabled", true) != false
        or parsed.get("native_collision_generated", true) != false
        or parsed.get("retail_game_runtime_verified", true) != false
        or int(parsed.get("triangle_count", 0)) <= 0
        or str(parsed.get("obj_sha256", "")) != FileAccess.get_sha256(obj_path)):
        return {"ok": false, "message": (
            "OBJ verification produced an untrusted or mismatched report. "
            + "No native game modification is inferred.")}
    return {
        "ok": true,
        "path": obj_path,
        "triangle_count": int(parsed["triangle_count"]),
        "face_count": int(parsed["face_count"]),
        "vertex_count": int(parsed["vertex_count"]),
        "obj_sha256": str(parsed["obj_sha256"]),
        "private_geometry_sha256": str(parsed["private_geometry_sha256"]),
        "message": "Exact source-private OBJ verified, read-only. No "
            + "original DX2 BSP, GMP/IBD, collision or game files changed."
    }
