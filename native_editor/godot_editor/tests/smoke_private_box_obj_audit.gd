extends SceneTree
## DX2Ed v0.97: actual Godot Inspector -> independent Python OBJ audit.
## Synthetic authoring and GMP sentinel only; never loads original game data.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")
const ExportBridge = preload("res://private_box_obj_bridge.gd")
const AuditBridge = preload("res://private_box_obj_audit_bridge.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.97 private OBJ round-trip audit: " + message)
    quit(1)


func _run() -> void:
    var root := ProjectSettings.globalize_path(
        "user://v097_synthetic_private_obj_audit")
    if DirAccess.make_dir_recursive_absolute(root) != OK:
        _fail("Cannot create private synthetic test directory")
        return
    var obj_path := root.path_join("DraftProp_97.obj")
    var bad_path := root.path_join("altered_private.obj")
    var sentinel := root.path_join("original_sentinel.gmp")
    for path in [obj_path, bad_path, sentinel]:
        if FileAccess.file_exists(path):
            DirAccess.remove_absolute(path)
    var fake := FileAccess.open(sentinel, FileAccess.WRITE)
    if fake == null:
        _fail("Cannot create synthetic original GMP sentinel")
        return
    fake.store_string("SYNTHETIC_NEVER_MODIFIED_GAME_FILE")
    fake.close()
    var source_sha := FileAccess.get_sha256(sentinel)
    var box: Dictionary = Brush.default_spec("Box")
    box["clip_plane"] = {
        "normal": [1.0, 0.0, 0.0],
        "distance": 0.0, "keep_positive": false}
    var exported: Dictionary = ExportBridge.export_clipped_box(box, obj_path)
    if (not bool(exported.get("ok", false))
        or not FileAccess.file_exists(obj_path)):
        _fail("Independent private OBJ fixture export failed: "
            + str(exported.get("message", "")))
        return
    var obj_sha := FileAccess.get_sha256(obj_path)
    if (bool(AuditBridge.audit_clipped_box(
            Brush.default_spec("Box"), obj_path).get("ok", true))
        or bool(AuditBridge.audit_clipped_box(
            box, sentinel).get("ok", true))):
        _fail("Private audit bridge accepted uncut Box or original GMP")
        return
    var editor := Editor.new()
    get_root().add_child(editor)
    var node := editor._new_draft_copy(
        "Brush::Box", "DraftProp_97", Transform3D.IDENTITY)
    if (not is_instance_valid(node)
        or not editor._set_brush_spec("DraftProp_97", box)):
        _fail("Authoring fixture failed to create private clipped Box")
        return
    editor._select_mesh_only(node)
    if (editor.box_clip_obj_audit_button == null
        or editor.box_clip_obj_audit_button.disabled
        or editor.box_clip_obj_audit_dialog == null
        or not editor.private_box_clip_panel.visible):
        _fail("Private OBJ audit Inspector button/dialog unavailable")
        return
    var initial_undo := editor.undo_stack.size()
    var initial_spec: Dictionary = (
        editor.draft_brush_specs["DraftProp_97"].duplicate(true))
    editor.box_clip_obj_audit_button.pressed.emit()
    if (editor.box_clip_obj_audit_owner != "DraftProp_97"
        or editor.box_clip_obj_audit_spec != initial_spec):
        _fail("OBJ audit did not bind exact selected private brush spec")
        return
    editor.box_clip_obj_audit_dialog.hide()
    editor.box_clip_obj_audit_dialog.file_selected.emit(obj_path)
    var audit: Dictionary = editor.box_clip_obj_audit_last_result
    if (not bool(audit.get("ok", false))
        or int(audit.get("vertex_count", 0)) != 8
        or int(audit.get("face_count", 0)) != 6
        or int(audit.get("triangle_count", 0)) != 12
        or str(audit.get("obj_sha256", "")) != obj_sha
        or editor.undo_stack.size() != initial_undo
        or editor.draft_brush_specs["DraftProp_97"] != initial_spec
        or FileAccess.get_sha256(obj_path) != obj_sha
        or FileAccess.get_sha256(sentinel) != source_sha):
        _fail("Inspector read-only round-trip audit failed: "
            + str(audit.get("message", "")))
        return
    # An edited OBJ is not canonical. The read-only verification must
    # refuse it, but neither overwrite it nor touch the original source.
    var altered := FileAccess.open(bad_path, FileAccess.WRITE)
    if altered == null:
        _fail("Cannot prepare synthetic malformed OBJ")
        return
    altered.store_string("o altered\nv 0 0 0\nf 1 1 1\n")
    altered.close()
    var bad_sha := FileAccess.get_sha256(bad_path)
    editor.box_clip_obj_audit_button.pressed.emit()
    editor.box_clip_obj_audit_dialog.hide()
    editor.box_clip_obj_audit_dialog.file_selected.emit(bad_path)
    if (bool(editor.box_clip_obj_audit_last_result.get("ok", true))
        or FileAccess.get_sha256(bad_path) != bad_sha
        or FileAccess.get_sha256(obj_path) != obj_sha
        or editor.undo_stack.size() != initial_undo):
        _fail("Tampered private OBJ was accepted or modified")
        return
    # Reject changed geometry between opening the dialog and choosing OBJ.
    editor.box_clip_obj_audit_button.pressed.emit()
    editor.box_clip_obj_audit_dialog.hide()
    var edited := box.duplicate(true)
    edited["clip_plane"]["distance"] = 0.25
    if not editor._set_brush_spec("DraftProp_97", edited):
        _fail("Synthetic brush change failed")
        return
    editor.box_clip_obj_audit_dialog.file_selected.emit(obj_path)
    if (bool(editor.box_clip_obj_audit_last_result.get("ok", true))
        or FileAccess.get_sha256(obj_path) != obj_sha):
        _fail("Changed private geometry bypassed pending dialog binding")
        return
    # Imported source actors cannot be used as private Box verification
    # provenance, even when an OBJ dialog was opened for a real private Box.
    editor._set_brush_spec("DraftProp_97", box)
    editor._select_mesh_only(node)
    editor.box_clip_obj_audit_button.pressed.emit()
    editor.box_clip_obj_audit_dialog.hide()
    var source := MeshInstance3D.new()
    source.name = "StaticMeshActor__97"
    source.mesh = BoxMesh.new()
    editor.world_root.add_child(source)
    editor.meshes_by_actor[str(source.name)] = source
    editor.actors_by_name[str(source.name)] = {
        "name": str(source.name), "class": "StaticMeshActor", "export": 97,
        "location": [0, 0, 0], "rotation": [0, 0, 0],
        "game_properties": []}
    editor._select_mesh_only(source)
    editor.box_clip_obj_audit_dialog.file_selected.emit(obj_path)
    if (bool(editor.box_clip_obj_audit_last_result.get("ok", true))
        or editor.private_box_clip_panel.visible
        or FileAccess.get_sha256(obj_path) != obj_sha
        or FileAccess.get_sha256(sentinel) != source_sha):
        _fail("Imported original actor could verify as a private Box")
        return
    # Every staged JSON is removed after success or rejection.
    var stage_dir := ProjectSettings.globalize_path(
        "user://private_box_obj_stage")
    for filename in DirAccess.get_files_at(stage_dir):
        if str(filename).begins_with("private_audit_"):
            _fail("Private OBJ audit staging JSON leaked")
            return
    editor.queue_free()
    for path in [obj_path, bad_path, sentinel]:
        DirAccess.remove_absolute(path)
    DirAccess.remove_absolute(root)
    print("DX2Ed v0.97 private OBJ audit Inspector, tamper refusal, GMP safety PASS")
    quit(0)
