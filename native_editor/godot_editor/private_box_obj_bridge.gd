extends RefCounted
## Private editor-only bridge to the independently verified DX2SDK v0.93
## OBJ geometry exporter. This never invokes native game writers.

const Brush = preload("res://brush_geometry.gd")
const PythonRuntime = preload("res://python_runtime.gd")

static func export_clipped_box(raw: Variant, destination: String) -> Dictionary:
    if (typeof(raw) != TYPE_DICTIONARY or destination.is_empty()
        or destination.get_extension().to_lower() != "obj"
        or not destination.is_absolute_path()
        or FileAccess.file_exists(destination)
        or DirAccess.dir_exists_absolute(destination)):
        return {"ok": false, "message": (
            "Refused: choose a NEW absolute .obj preview path. "
            + "Existing files are never overwritten.")}
    var checked: Dictionary = Brush.validate(raw)
    if (checked.is_empty() or str(checked.get("kind", "")) != "Box"
        or (not checked.has("clip_plane")
            and not checked.has("clip_planes"))
        or Brush.build_mesh(checked) == null):
        return {"ok": false, "message": (
            "Refused: select a valid editor-authored clipped Box, not "
            + "an imported DX2 actor or original BSP surface.")}
    var worker := ProjectSettings.globalize_path(
        "res://backend/dx2_private_obj_export_worker.py")
    if not FileAccess.file_exists(worker):
        return {"ok": false, "message": (
            "Private Python OBJ bridge is missing from this editor build.")}
    var stage_dir := ProjectSettings.globalize_path(
        "user://private_box_obj_stage")
    if DirAccess.make_dir_recursive_absolute(stage_dir) != OK:
        return {"ok": false, "message": "Cannot create private OBJ staging folder."}
    # Only an ephemeral normalized private Box record is staged. The
    # original map, actor list, game cache and source paths are never sent
    # to Python. A unique name avoids reusing earlier interrupted exports.
    var stage := stage_dir.path_join(
        "private_box_" + str(OS.get_process_id()) + "_"
        + str(Time.get_ticks_usec()) + ".json")
    if FileAccess.file_exists(stage):
        return {"ok": false, "message": "Private OBJ staging name collision."}
    var file := FileAccess.open(stage, FileAccess.WRITE)
    if file == null:
        return {"ok": false, "message": "Private OBJ staging file unavailable."}
    file.store_string(JSON.stringify(checked))
    file.flush()
    file.close()
    var output: Array = []
    var args := PackedStringArray([worker, stage, destination])
    var exit_code := OS.execute(
        PythonRuntime.executable(), args, output, true)
    if exit_code == -1:
        # Existing Godot worker fallback for developer installations.
        output.clear()
        var fallback := PackedStringArray(["-3", worker, stage, destination])
        exit_code = OS.execute("py", fallback, output, true)
    # Clean stage whether Python accepted or rejected the candidate.
    DirAccess.remove_absolute(stage)
    if exit_code != 0:
        return {"ok": false, "message": (
            "Independent private OBJ export refused: "
            + "\n".join(output).strip_edges().substr(0, 340))}
    var parsed: Variant = JSON.parse_string("\n".join(output).strip_edges())
    if (typeof(parsed) != TYPE_DICTIONARY
        or parsed.get("status", "") != "new-source-private-OBJ-written"
        or str(parsed.get("output", "")) != destination
        or not FileAccess.file_exists(destination)
        or int(parsed.get("triangle_count", 0)) <= 0):
        return {"ok": false, "message": (
            "Python OBJ export returned an unverified result. "
            + "Do not treat any created file as native DX2 geometry.")}
    return {
        "ok": true, "path": destination,
        "triangle_count": int(parsed["triangle_count"]),
        "face_count": int(parsed["face_count"]),
        "vertex_count": int(parsed["vertex_count"]),
        "obj_sha256": str(parsed["obj_sha256"]),
        "message": "Exported editor-private Box preview OBJ. No native BSP, "
            + "collision or game file was written."
    }
