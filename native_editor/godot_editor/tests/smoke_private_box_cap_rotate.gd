extends SceneTree
## DX2Ed v0.88: private capped Box centroid turns, synthetic assets only.
const Brush = preload("res://brush_geometry.gd")
const Pivot = preload("res://private_box_cap_rotate.gd")
const Picker = preload("res://private_box_cap_picker.gd")
const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.88 cap rotation: " + message)
    quit(1)


func _run() -> void:
    var box: Dictionary = Brush.default_spec("Box")
    var one: Dictionary = box.duplicate(true)
    var cut_x := {"normal": [1.0,0.0,0.0],
        "distance": 0.0, "keep_positive": false}
    var cut_y := {"normal": [0.0,1.0,0.0],
        "distance": 0.0, "keep_positive": false}
    one["clip_plane"] = cut_x
    var one_pivot := Pivot.cap_area_centroid(one, 0)
    if (one_pivot.is_empty()
        or one_pivot["center"].distance_to(Vector3.ZERO) > 0.0001
        or absf(float(one_pivot["area"]) - 4.0) > 0.0001):
        _fail("Single cap area-weighted center was not at its actual midpoint")
        return
    var turn := Pivot.rotated_about_cap(one, 0, Vector3.UP, 5.0)
    if (turn.is_empty() or turn.has("clip_planes")
        or not turn.has("clip_plane")
        or not is_equal_approx(
            float(turn["clip_plane"]["normal"][0]), cos(deg_to_rad(5.0)))
        or absf(float(turn["clip_plane"]["distance"])) > 0.0001):
        _fail("Single private cap rotation failed to retain a centered cut")
        return
    var two: Dictionary = box.duplicate(true)
    two["clip_planes"] = [cut_x, cut_y]
    var base_pivot := Pivot.cap_area_centroid(two, 0)
    if (base_pivot.is_empty()
        or base_pivot["center"].distance_to(
            Vector3(0.0,-0.5,0.0)) > 0.0001
        or absf(float(base_pivot["area"]) - 2.0) > 0.0001):
        _fail("Multi-plane cap was not area-weighted at the actual visible face")
        return
    # A local Z rotation has a NONZERO new distance because its chosen
    # cap was asymmetric after the Y cut. The old face center stays exactly
    # on the proposed plane, not just the same plane offset.
    var angled := Pivot.rotated_about_cap(two, 0, Vector3.BACK, 5.0)
    var expected_offset := -0.5 * sin(deg_to_rad(5.0))
    if (angled.is_empty() or angled["clip_planes"].size() != 2
        or angled["clip_planes"][1] != cut_y
        or absf(float(angled["clip_planes"][0]["distance"])
            - expected_offset) > 0.0001):
        _fail("Asymmetric cap rotation did not reanchor signed distance")
        return
    var angled_n := Vector3(
        angled["clip_planes"][0]["normal"][0],
        angled["clip_planes"][0]["normal"][1],
        angled["clip_planes"][0]["normal"][2])
    if absf(angled_n.dot(base_pivot["center"])
            - float(angled["clip_planes"][0]["distance"])) > 0.00001:
        _fail("Rotated private cap failed to pass through original face pivot")
        return
    var invalid := [
        Pivot.rotated_about_cap(box, 0, Vector3.UP, 5.0),
        Pivot.rotated_about_cap(two, -1, Vector3.UP, 5.0),
        Pivot.rotated_about_cap(two, 2, Vector3.UP, 5.0),
        Pivot.rotated_about_cap(two, 0, Vector3.ZERO, 5.0),
        Pivot.rotated_about_cap(two, 0, Vector3(INF,0,0), 5.0),
        Pivot.rotated_about_cap(two, 0, Vector3.RIGHT, 5.0),
        Pivot.rotated_about_cap(two, 0, Vector3.UP, 0.0),
        Pivot.rotated_about_cap(two, 0, Vector3.UP, 31.0)
    ]
    for attempt in invalid:
        if not attempt.is_empty():
            _fail("Invalid/no-op, uncut or out-of-range cap pivot was accepted")
            return
    var editor := Editor.new()
    get_root().add_child(editor)
    var draft := editor._new_draft_copy(
        "Brush::Box", "DraftProp_88", Transform3D.IDENTITY)
    if not is_instance_valid(draft):
        _fail("Actual Godot editor failed to create an authored private Box")
        return
    if not editor._set_brush_spec("DraftProp_88", two):
        _fail("Actual Godot editor refused valid synthetic two-cap geometry")
        return
    editor._select_mesh_only(draft)
    if (editor.box_clip_rotate_y_pos_button == null
        or editor.box_clip_rotate_y_neg_button == null
        or editor.box_clip_rotate_x_pos_button == null
        or editor.box_clip_rotate_x_neg_button == null
        or editor.box_clip_rotate_y_pos_button.disabled):
        _fail("Centroid rotation controls are absent or disabled on a capped Box")
        return
    editor.box_clip_plane_selector.select(0)
    editor._selected_private_box_plane_changed(0)
    var before: Dictionary = editor.draft_brush_specs["DraftProp_88"].duplicate(true)
    var history := editor.undo_stack.size()
    editor.box_clip_rotate_x_pos_button.pressed.emit()
    if (editor.undo_stack.size() != history
        or editor.draft_brush_specs["DraftProp_88"] != before):
        _fail("Parallel-axis no-op rotation mutated the draft or Undo history")
        return
    editor.box_clip_rotate_y_pos_button.pressed.emit()
    var rotated: Dictionary = editor.draft_brush_specs["DraftProp_88"].duplicate(true)
    if (editor.undo_stack.size() != history + 1
        or editor.box_clip_plane_selector.selected != 0
        or rotated["clip_planes"].size() != 2
        or rotated["clip_planes"][1] != before["clip_planes"][1]
        or not is_equal_approx(
            float(rotated["clip_planes"][0]["normal"][0]),
            cos(deg_to_rad(5.0)))
        or editor.draft_prop_copies["DraftProp_88"].mesh == null):
        _fail("Clicked Inspector Y+5 pivot did not preserve the other cut")
        return
    var mesh := editor.draft_prop_copies["DraftProp_88"].mesh
    var vertices: PackedVector3Array = (
        mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX])
    if vertices.size() == 0 or not Picker._checked_spec(rotated).has("clip_planes"):
        _fail("Pivot rotation lost its closed private geometry")
        return
    editor._undo_edit()
    if editor.draft_brush_specs["DraftProp_88"] != before:
        _fail("Single pivot turn Undo did not recover both original cut planes")
        return
    editor._redo_edit()
    if editor.draft_brush_specs["DraftProp_88"] != rotated:
        _fail("Single pivot turn Redo did not restore the changed plane")
        return
    # Undo recreates preview nodes. Reacquire and ensure original imported
    # actors cannot reveal these private editing controls.
    var imported := MeshInstance3D.new()
    imported.name = "StaticMeshActor__88"
    imported.mesh = BoxMesh.new()
    editor.world_root.add_child(imported)
    editor.meshes_by_actor[str(imported.name)] = imported
    editor.actors_by_name[str(imported.name)] = {
        "name": str(imported.name), "class": "StaticMeshActor", "export": 88,
        "location": [0,0,0], "rotation": [0,0,0], "game_properties": []}
    editor._select_mesh_only(imported)
    if editor.private_box_clip_panel.visible:
        _fail("Original StaticMeshActor displayed private cap rotation controls")
        return
    editor.queue_free()
    print("DX2Ed v0.88 private Box cap centroid pivot and Inspector Undo/Redo PASS")
    quit(0)
