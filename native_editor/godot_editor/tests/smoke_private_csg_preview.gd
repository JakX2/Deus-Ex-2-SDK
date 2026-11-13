extends SceneTree
## P102: actual toolbar -> isolated Python worker -> non-native Godot shell.
## Original GMP sentinel is synthetic; no retail source is imported.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")
const Bridge = preload("res://private_csg_preview_bridge.gd")
const Viewer = preload("res://private_csg_preview_mesh.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("P102 source-private CSG viewport: " + message)
    quit(1)


func _run() -> void:
    var scratch := ProjectSettings.globalize_path("user://p102_csg_test")
    if DirAccess.make_dir_recursive_absolute(scratch) != OK:
        _fail("Could not create isolated test fixture")
        return
    var sentinel := scratch.path_join("original.gmp")
    if FileAccess.file_exists(sentinel):
        DirAccess.remove_absolute(sentinel)
    var input := FileAccess.open(sentinel, FileAccess.WRITE)
    if input == null:
        _fail("Cannot write synthetic GMP sentinel")
        return
    input.store_string("SYNTHETIC_DX2_ORIGINAL_DO_NOT_EDIT")
    input.close()
    var sentinel_sha := FileAccess.get_sha256(sentinel)
    var spec := Brush.default_spec("Box")
    spec["clip_plane"] = {
        "normal": [1.0, 0.0, 0.0],
        "distance": 0.0, "keep_positive": false,
    }
    var moved := Transform3D.IDENTITY
    moved.origin = Vector3(0.5, 0.0, 0.0)
    var tested: Dictionary = Bridge.preview_pair(
        spec, spec, Transform3D.IDENTITY, moved, "subtraction")
    if not bool(tested.get("ok", false)):
        _fail("Python CSG subtraction bridge failed: " + str(tested.get("message", "")))
        return
    var visual: Dictionary = Viewer.build_preview(tested["report"], "subtraction")
    if (not bool(visual.get("ok", false))
        or int(visual.get("pieces", -1)) != 1
        or int(visual.get("triangles", -1)) != 12
        or not is_equal_approx(float(visual.get("volume_m3", 0)), 2.0)):
        _fail("Python-to-Godot CSG shell generation failed: "
            + str(visual) + " | report piece count="
            + str(tested["report"].get("piece_count", "?"))
            + " report remaining m3="
            + str(tested["report"].get("remaining_volume_m3", "?")))
        return
    (visual["root"] as Node3D).free()
    for denied in [
        [Brush.default_spec("Box"), spec],
        [spec, {"kind": "StaticMeshActor"}],
    ]:
        var invalid: Dictionary = Bridge.preview_pair(
            denied[0], denied[1], Transform3D.IDENTITY, moved,
            "subtraction")
        if bool(invalid.get("ok", true)):
            _fail("CSG accepted uncut or native actor source")
            return
    var bad: Dictionary = Bridge.preview_pair(
        spec, spec, Transform3D.IDENTITY, moved, "native-bsp")
    if bool(bad.get("ok", true)):
        _fail("Unsupported native CSG operation accepted")
        return
    var editor := Editor.new()
    get_root().add_child(editor)
    var first: MeshInstance3D = editor._new_draft_copy(
        "Brush::Box", "DraftProp_102", Transform3D.IDENTITY)
    var second: MeshInstance3D = editor._new_draft_copy(
        "Brush::Box", "DraftProp_103", moved)
    if (not is_instance_valid(first) or not is_instance_valid(second)
        or not editor._set_brush_spec("DraftProp_102", spec)
        or not editor._set_brush_spec("DraftProp_103", spec)):
        _fail("Could not build two synthetic source-private Box drafts")
        return
    editor._select_mesh_only(first)
    editor._toggle_selection_mesh(second)
    var undo_before := editor.undo_stack.size()
    if (editor.private_csg_subtraction_button == null
        or editor.private_csg_intersection_button == null
        or editor.private_csg_clear_button == null
        or editor._private_csg_selected_pair().is_empty()):
        _fail("Private CSG toolbar or deterministic two-Box selection missing")
        return
    editor.private_csg_subtraction_button.pressed.emit()
    var result: Dictionary = editor.private_csg_preview_last_result
    if (not bool(result.get("ok", false))
        or str(result.get("source_a", "")) != "DraftProp_102"
        or str(result.get("source_b", "")) != "DraftProp_103"
        or int(result.get("piece_count", 0)) != 1
        or not is_equal_approx(float(result.get("volume_m3", 0)), 2.)
        or not is_instance_valid(editor.private_csg_preview_root)
        or editor.private_csg_preview_root.get_child_count() != 1
        or editor.undo_stack.size() != undo_before
        or FileAccess.get_sha256(sentinel) != sentinel_sha):
        _fail("Toolbar A-minus-B scene render/volume/safety failed: "
            + str(result))
        return
    var piece: MeshInstance3D = editor.private_csg_preview_root.get_child(0)
    if (piece.mesh == null or piece.mesh.get_surface_count() != 1
        or piece.mesh.surface_get_array_len(0) != 36
        or editor.draft_prop_copies.size() != 2
        or editor.actors_by_name.has(str(piece.name))
        or not bool(piece.get_meta("dx2sdk_private_csg_preview_only", false))):
        _fail("CSG mesh leaked into native actor or draft editing state")
        return
    editor.private_csg_intersection_button.pressed.emit()
    result = editor.private_csg_preview_last_result
    if (not bool(result.get("ok", false))
        or str(result.get("operation", "")) != "intersection"
        or int(result.get("piece_count", -1)) != 1
        or not is_equal_approx(float(result.get("volume_m3", 0)), 2.)
        or editor.undo_stack.size() != undo_before):
        _fail("Toolbar intersection result or read-only Undo mismatch")
        return
    editor.private_csg_clear_button.pressed.emit()
    if is_instance_valid(editor.private_csg_preview_root):
        _fail("Clear preview did not remove only ephemeral geometry")
        return
    # Rebuild and edit source metadata: stale result must disappear.
    editor.private_csg_subtraction_button.pressed.emit()
    var changed: Dictionary = spec.duplicate(true)
    changed["clip_plane"]["distance"] = 0.25
    if (not editor._set_brush_spec("DraftProp_103", changed)
        or is_instance_valid(editor.private_csg_preview_root)):
        _fail("Private brush geometry changed without invalidating stale CSG")
        return
    # Selecting an original actor never supplies valid private provenance.
    var original_node := MeshInstance3D.new()
    original_node.name = "StaticMeshActor__102"
    original_node.mesh = BoxMesh.new()
    editor.world_root.add_child(original_node)
    editor.meshes_by_actor[str(original_node.name)] = original_node
    editor.actors_by_name[str(original_node.name)] = {
        "name": str(original_node.name), "class": "StaticMeshActor",
        "export": 102, "game_properties": []
    }
    editor._select_mesh_only(first)
    editor._toggle_selection_mesh(original_node)
    editor.private_csg_subtraction_button.pressed.emit()
    if (bool(editor.private_csg_preview_last_result.get("ok", true))
        or is_instance_valid(editor.private_csg_preview_root)
        or FileAccess.get_sha256(sentinel) != sentinel_sha):
        _fail("Native original actor bypassed private CSG provenance gate")
        return
    var stage_dir := ProjectSettings.globalize_path("user://private_csg_preview_stage")
    for filename in DirAccess.get_files_at(stage_dir):
        if str(filename).begins_with("csg_"):
            _fail("Private CSG staging JSON not cleaned")
            return
    editor.queue_free()
    DirAccess.remove_absolute(sentinel)
    DirAccess.remove_absolute(scratch)
    print("DX2Ed P102 private CSG toolbar/mesh/Undo/GMP-sentinel PASS")
    quit(0)
