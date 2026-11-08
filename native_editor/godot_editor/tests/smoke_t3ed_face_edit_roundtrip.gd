extends SceneTree
## DX2Ed v0.35: actual Godot editor T3Ed-style box/face authoring smoke.
## Invented source mesh and private draft only. NO original GMP, native CSG
## brushes, portal/BSP, collision or gameplay package writes.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")
const Guides = preload("res://orthographic_authoring_guides.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.35 draft face authoring: " + message)
    quit(1)


func _run() -> void:
    var box := Brush.default_spec("Box")
    var enlarged := Brush.face_resize(box, 1, 0.5)
    var shrunk := Brush.face_resize(box, 1, -0.5)
    var left := Brush.face_resize(box, 0, 0.5)
    if (enlarged.is_empty() or shrunk.is_empty() or left.is_empty()
        or not is_equal_approx(float(enlarged["spec"]["size"][0]), 2.5)
        or not is_equal_approx(float(shrunk["spec"]["size"][0]), 1.5)
        or not enlarged["center_offset_local"].is_equal_approx(Vector3(0.25, 0, 0))
        or not shrunk["center_offset_local"].is_equal_approx(Vector3(-0.25, 0, 0))
        or not left["center_offset_local"].is_equal_approx(Vector3(-0.25, 0, 0))):
        _fail("Pure face math failed to anchor the opposite local face")
        return
    for invalid in [
        Brush.face_resize(Brush.default_spec("Ramp"), 1, 0.5),
        Brush.face_resize(Brush.default_spec("Stairs"), 1, 0.5),
        Brush.face_resize(box, -1, 0.5),
        Brush.face_resize(box, 6, 0.5),
        Brush.face_resize(box, 1, INF),
        Brush.face_resize(box, 1, 0.0),
        Brush.face_resize(box, 1, -1.99),
        Brush.face_resize(box, 1, 255.0),
        Brush.face_resize({"kind":"Box", "size":[2,2,INF], "steps":1}, 1, 0.5),
    ]:
        if not invalid.is_empty():
            _fail("Invalid native or unbounded draft face operation accepted")
            return

    var editor := Editor.new()
    get_root().add_child(editor)
    if (editor.brush_face_controls == null
        or editor.brush_face_selector == null
        or editor.brush_face_selector.item_count != 6
        or editor.brush_face_outward_button == null
        or editor.brush_face_inward_button == null):
        _fail("Actual editor does not expose six-face In/Out brush inspector")
        return

    # The real authoring project has a decoded/rendered source mesh and a
    # separate editor-only brush copy. Source file is wholly invented.
    var original_file := ProjectSettings.globalize_path(
        "user://v035_invented_read_only_source.gmp")
    var payload := PackedByteArray([68, 88, 50, 69, 100, 103, 101, 53])
    var fake_file := FileAccess.open(original_file, FileAccess.WRITE)
    if fake_file == null:
        _fail("Synthetic source file not available")
        return
    fake_file.store_buffer(payload)
    fake_file.close()
    var source_sha := FileAccess.get_sha256(original_file)

    var fake_scene := Node3D.new()
    fake_scene.name = "InventedImportedScene"
    editor.world_root.add_child(fake_scene)
    editor.scene_root = fake_scene
    editor.current_folder = ProjectSettings.globalize_path(
        "user://v035_private_fully_synthetic_map_cache")

    var original := MeshInstance3D.new()
    original.name = "StaticMeshActor__901"
    original.mesh = BoxMesh.new()
    fake_scene.add_child(original)
    original.global_position = Vector3(-3.0, 0.0, 2.0)
    var original_identity := str(original.name)
    editor.meshes_by_actor[original_identity] = original
    editor.actors_by_name[original_identity] = {
        "name": original_identity, "class": "StaticMeshActor",
        "export": 901, "location": [0, 0, 0],
        "rotation": [0, 0, 0], "game_properties": []}
    editor.original_mesh_transforms[original_identity] = original.global_transform
    editor.all_mesh_instances.append(original)

    var world := Transform3D(
        Basis(Vector3.UP, PI / 2.0),
        Vector3(3.0, 0.0, 5.0))
    var draft := editor._new_draft_copy("Brush::Box", "DraftProp_1", world)
    if not is_instance_valid(draft):
        _fail("Could not construct original DX2Ed draft box")
        return
    editor.next_prop_copy_id = 2
    editor._select_mesh_only(draft)
    if not editor.brush_face_controls.visible:
        _fail("Draft Box face controls hidden from actual inspector")
        return
    editor._grid_spacing_changed(0.5)
    editor.brush_face_selector.select(1) # Local +X face.
    var opposite_before := draft.global_position - draft.global_basis.x
    editor._change_brush_face(1.0)
    if (editor.undo_stack.size() != 1
        or not is_equal_approx(float(editor.draft_brush_specs["DraftProp_1"]["size"][0]), 2.5)):
        _fail("Real editor did not resize draft brush and record Undo")
        return
    draft = editor.draft_prop_copies["DraftProp_1"]
    var opposite_after := draft.global_position - draft.global_basis.x * 1.25
    if not opposite_before.is_equal_approx(opposite_after):
        _fail("Face drag moved opposite plane on a rotated draft brush")
        return

    editor._undo_edit()
    if (not editor.draft_prop_copies.has("DraftProp_1")
        or float(editor.draft_brush_specs["DraftProp_1"]["size"][0]) != 2.0):
        _fail("Face resize Undo did not recover original Box geometry")
        return
    editor._redo_edit()
    if (not editor.draft_prop_copies.has("DraftProp_1")
        or not is_equal_approx(float(editor.draft_brush_specs["DraftProp_1"]["size"][0]), 2.5)):
        _fail("Face resize Redo did not reapply draft geometry")
        return

    # Make the actual authored project more than a single brush: retain a
    # moved imported actor preview, a rotated resized brush, and the ortho UI.
    editor._select_mesh_only(original)
    editor._move_selected_prop(Vector3.UP)
    if not original.global_position.is_equal_approx(Vector3(-3, 0.5, 2)):
        _fail("Original actor preview move cannot join brush project")
        return
    editor._set_editor_view_mode(Guides.SIDE)
    editor._grid_spacing_changed(0.5)
    editor._toggle_ortho_grid(false)
    # Multi-selection should survive the real private draft Save/Load,
    # including a source preview and editor-only face-resized brush.
    editor._toggle_selection_mesh(editor.draft_prop_copies["DraftProp_1"])
    if editor.selected_meshes.size() != 2:
        _fail("Combined original actor/draft multi-selection unavailable")
        return
    var draft_path := editor._draft_file_path()
    if draft_path.is_empty():
        _fail("Private draft output path unavailable")
        return
    for suffix in ["", ".pending", ".bak"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    editor._save_prop_draft()
    if not FileAccess.file_exists(draft_path):
        _fail("Real editor Save draft did not produce private JSON")
        return
    var saved: Variant = JSON.parse_string(FileAccess.get_file_as_string(draft_path))
    if (typeof(saved) != TYPE_DICTIONARY
        or saved.get("schema") != "DX2Ed-prop-draft-v1"
        or saved["moved"].size() != 1 or saved["copies"].size() != 1
        or saved["copies"][0]["from_actor"] != "Brush::Box"
        or float(saved["copies"][0]["brush"]["size"][0]) != 2.5
        or saved["workspace"]["view_mode"] != Guides.SIDE
        or saved["workspace"]["grid_enabled"] != false
        or saved["selection"].size() != 2
        or not saved["selection"].has(original_identity)
        or not saved["selection"].has("DraftProp_1")):
        _fail("Saved project lost native-source previews, brush dimensions or view")
        return

    # Change all three independently, then reopen using the REAL loader.
    original.global_position = Vector3(90, 90, 90)
    editor._set_brush_spec("DraftProp_1", Brush.default_spec("Box"))
    editor._set_editor_view_mode(Guides.PERSPECTIVE)
    editor._toggle_ortho_grid(true)
    editor._load_prop_draft()
    if (not original.global_position.is_equal_approx(Vector3(-3, 0.5, 2))
        or not editor.draft_prop_copies.has("DraftProp_1")
        or not is_equal_approx(float(editor.draft_brush_specs["DraftProp_1"]["size"][0]), 2.5)
        or editor.editor_view_mode != Guides.SIDE
        or editor.ortho_grid_enabled
        or not is_equal_approx(editor.ortho_grid_step, 0.5)
        or editor.selected_meshes.size() != 2
        or not editor.selected_meshes.has(original_identity)
        or not editor.selected_meshes.has("DraftProp_1")):
        _fail("Real editor project reopen failed to reconstruct full authored state")
        return
    var reloaded: MeshInstance3D = editor.draft_prop_copies["DraftProp_1"]
    if not (reloaded.global_position - reloaded.global_basis.x * 1.25
            ).is_equal_approx(opposite_before):
        _fail("Reopened resized brush shifted its original opposite face")
        return
    if FileAccess.get_sha256(original_file) != source_sha:
        _fail("Original invented source bytes changed during preview authoring")
        return

    for suffix in ["", ".pending", ".bak"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    DirAccess.remove_absolute(original_file)
    editor.queue_free()
    print("DX2Ed v0.35 T3Ed-style face resize + full private scene save/reopen PASS")
    quit(0)
