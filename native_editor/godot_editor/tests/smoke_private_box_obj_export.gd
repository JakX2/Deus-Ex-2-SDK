extends SceneTree
## DX2Ed v0.95 actual Godot 4.3-to-Python independent OBJ interchange.
## All geometry and the fake original game-file sentinel are invented.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")
const Bridge = preload("res://private_box_obj_bridge.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.95 private OBJ Inspector: " + message)
    quit(1)


func _run() -> void:
    var root := ProjectSettings.globalize_path(
        "user://v095_synthetic_private_obj")
    if DirAccess.make_dir_recursive_absolute(root) != OK:
        _fail("Cannot create private synthetic test directory")
        return
    var dest := root.path_join("DraftProp_95.obj")
    var original_path := root.path_join("mock_original.gmp")
    if FileAccess.file_exists(dest):
        DirAccess.remove_absolute(dest)
    if FileAccess.file_exists(original_path):
        DirAccess.remove_absolute(original_path)
    var fake_original := FileAccess.open(original_path, FileAccess.WRITE)
    if fake_original == null:
        _fail("Cannot create synthetic original-map sentinel")
        return
    fake_original.store_string("UNMODIFIED_SYNTHETIC_DX2_SOURCE")
    fake_original.close()
    var original_sha := FileAccess.get_sha256(original_path)

    var box: Dictionary = Brush.default_spec("Box")
    box["clip_plane"] = {
        "normal": [1.0, 0.0, 0.0],
        "distance": 0.0, "keep_positive": false}
    var spec_before := box.duplicate(true)
    if Bridge.export_clipped_box(
            Brush.default_spec("Box"), root.path_join("uncut.obj"))["ok"]:
        _fail("Uncut private Box unexpectedly exported as clipped convex")
        return
    var invalid := Bridge.export_clipped_box(box, root.path_join("bad.gmp"))
    if bool(invalid.get("ok", true)):
        _fail("Bridge accepted a native GMP extension as an OBJ output")
        return
    var editor := Editor.new()
    get_root().add_child(editor)
    var node := editor._new_draft_copy(
        "Brush::Box", "DraftProp_95", Transform3D.IDENTITY)
    if (not is_instance_valid(node)
        or not editor._set_brush_spec("DraftProp_95", box)):
        _fail("Godot private Box was not created with its x=0 cut")
        return
    editor._select_mesh_only(node)
    if (editor.box_clip_export_obj_button == null
        or editor.box_clip_export_obj_button.disabled
        or editor.box_clip_obj_dialog == null
        or not editor.private_box_clip_panel.visible):
        _fail("Clipped private Box OBJ button/dialog unavailable")
        return
    var undo_count := editor.undo_stack.size()
    var original_spec: Dictionary = (
        editor.draft_brush_specs["DraftProp_95"].duplicate(true))
    # Exercise the actual Inspector signal and file-selection signal.
    editor.box_clip_export_obj_button.pressed.emit()
    if editor.box_clip_obj_export_owner != "DraftProp_95":
        _fail("Export dialog did not bind its source to selected private Box")
        return
    editor.box_clip_obj_dialog.hide()
    editor.box_clip_obj_dialog.file_selected.emit(dest)
    var exported: Dictionary = editor.box_clip_obj_last_result
    if (not bool(exported.get("ok", false))
        or int(exported.get("vertex_count", 0)) != 8
        or int(exported.get("face_count", 0)) != 6
        or int(exported.get("triangle_count", 0)) != 12
        or not FileAccess.file_exists(dest)
        or editor.undo_stack.size() != undo_count
        or editor.draft_brush_specs["DraftProp_95"] != original_spec
        or box != spec_before):
        _fail("Actual Inspector did not roundtrip private OBJ without editing history: "
            + str(exported.get("message", "")))
        return
    var obj := FileAccess.get_file_as_string(dest)
    if (obj.find("o DX2Ed_Private_Box") < 0
        or obj.find("g private_cut_cap_00") < 0
        or obj.find("f ") < 0
        or obj.find("vn ") < 0
        or obj.find("v ") < 0
        or FileAccess.get_sha256(dest) != str(exported["obj_sha256"])
        or FileAccess.get_sha256(original_path) != original_sha):
        _fail("OBJ group, triangle record, hash or source GMP sentinel changed")
        return
    # An identical second request must refuse overwrite, not silently
    # replace a user's OBJ, and may not change undo state or mock source.
    editor.box_clip_export_obj_button.pressed.emit()
    editor.box_clip_obj_dialog.hide()
    editor.box_clip_obj_dialog.file_selected.emit(dest)
    if (bool(editor.box_clip_obj_last_result.get("ok", true))
        or editor.undo_stack.size() != undo_count
        or FileAccess.get_sha256(dest) != str(exported["obj_sha256"])):
        _fail("Existing OBJ overwrite was not rejected safely")
        return
    # Original imported actor cannot invoke Box export. A selection switch
    # while the file dialog is open also invalidates the pending owner.
    editor.box_clip_export_obj_button.pressed.emit()
    editor.box_clip_obj_dialog.hide()
    var source := MeshInstance3D.new()
    source.name = "StaticMeshActor__95"
    source.mesh = BoxMesh.new()
    editor.world_root.add_child(source)
    editor.meshes_by_actor[str(source.name)] = source
    editor.actors_by_name[str(source.name)] = {
        "name": str(source.name), "class": "StaticMeshActor", "export": 95,
        "location": [0, 0, 0], "rotation": [0, 0, 0],
        "game_properties": []}
    editor._select_mesh_only(source)
    var denied_path := root.path_join("native_actor_should_not_export.obj")
    editor.box_clip_obj_dialog.file_selected.emit(denied_path)
    if (bool(editor.box_clip_obj_last_result.get("ok", true))
        or FileAccess.file_exists(denied_path)
        or editor.private_box_clip_panel.visible
        or FileAccess.get_sha256(original_path) != original_sha):
        _fail("Original actor acquired a source-private export destination")
        return
    # The temporary private Box JSON must have been deleted by the worker
    # bridge after both success and refusal.
    var temp_dir := ProjectSettings.globalize_path(
        "user://private_box_obj_stage")
    var temporary := DirAccess.get_files_at(temp_dir)
    for filename in temporary:
        if str(filename).begins_with("private_box_"):
            _fail("Private staged authoring JSON leaked after OBJ export")
            return
    editor.queue_free()
    DirAccess.remove_absolute(dest)
    DirAccess.remove_absolute(original_path)
    DirAccess.remove_absolute(root)
    print("DX2Ed v0.95 Godot Inspector private OBJ, Python worker, no overwrite PASS")
    quit(0)
