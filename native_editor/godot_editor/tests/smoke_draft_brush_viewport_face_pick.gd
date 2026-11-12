extends SceneTree
## DX2Ed v0.37 viewport face selection, synthetic Godot brush data ONLY.
## No owner original map, native GMP/BSP/collision writer or game runtime.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")
const CapPicker = preload("res://private_box_cap_picker.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.37 draft viewport face picking: " + message)
    quit(1)


func _run() -> void:
    var box := Brush.default_spec("Box")
    var pose := Transform3D(Basis(Vector3.UP, PI * 0.5), Vector3(3.0, 1.0, -2.0))
    var rays := [
        {"start": Vector3(-5,0,0), "toward": Vector3.RIGHT, "face": 0},
        {"start": Vector3(5,0,0), "toward": Vector3.LEFT, "face": 1},
        {"start": Vector3(0,-5,0), "toward": Vector3.UP, "face": 2},
        {"start": Vector3(0,5,0), "toward": Vector3.DOWN, "face": 3},
        {"start": Vector3(0,0,-5), "toward": Vector3.BACK, "face": 4},
        {"start": Vector3(0,0,5), "toward": Vector3.FORWARD, "face": 5},
    ]
    for case in rays:
        var ray_origin: Vector3 = pose * case["start"]
        var ray_direction: Vector3 = pose.basis * case["toward"]
        var hit := Brush.pick_draft_face(box, pose, ray_origin, ray_direction)
        if (hit.is_empty() or int(hit["face_index"]) != case["face"]
            or str(hit["label"]) != str(Brush.FACE_LABELS[case["face"]])):
            _fail("Rotated cuboid ray picked incorrect face " + str(case["face"]))
            return
    var from_inside := Brush.pick_draft_face(
        box, pose, pose * Vector3.ZERO, pose.basis * Vector3.RIGHT)
    if from_inside.is_empty() or from_inside["face_index"] != 1:
        _fail("Ray beginning inside preview box did not select exit face")
        return
    var miss := Brush.pick_draft_face(
        box, pose, pose * Vector3(5, 5, 0), pose.basis * Vector3.LEFT)
    var singular := Transform3D(Basis().scaled(Vector3(0,1,1)), Vector3.ZERO)
    var bad_cases := [
        Brush.pick_draft_face(Brush.default_spec("Ramp"), pose,
            pose * Vector3(5,0,0), pose.basis * Vector3.LEFT),
        Brush.pick_draft_face(box, singular, Vector3(5,0,0), Vector3.LEFT),
        Brush.pick_draft_face(box, pose, Vector3(INF,0,0), Vector3.LEFT),
        Brush.pick_draft_face(box, pose, Vector3.ZERO, Vector3.ZERO),
        Brush.pick_draft_face(box, pose, Vector3.ZERO, Vector3(INF,0,0)),
    ]
    if not miss.is_empty():
        _fail("Off-face ray erroneously selected a box")
        return
    for hit in bad_cases:
        if not hit.is_empty():
            _fail("Invalid, unsupported or nonfinite face ray accepted")
            return

    # The face highlight is exactly four local edges, bounded to a single
    # authored face; no original BSP geometry enters the preview.
    var line_vertices := Brush.face_outline_edges(box, 1)
    if line_vertices.size() != 8:
        _fail("Selected face highlight did not create exactly four edges")
        return
    for point in line_vertices:
        if not is_equal_approx(point.x, 1.0075):
            _fail("Selected face outline escaped +X draft face")
            return
    if not Brush.face_outline_edges(Brush.default_spec("Ramp"), 1).is_empty():
        _fail("Unsupported/native face acquired a preview highlight")
        return

    # v0.86: nearest-face ray selection on real closed, private capped meshes.
    # The first Box cap is local x=0, with no native source geometry.
    var half_box: Dictionary = Brush.default_spec("Box")
    var x_cut := {
        "normal": [1.0,0.0,0.0], "distance": 0.0,
        "keep_positive": false}
    half_box["clip_plane"] = x_cut
    var cap_world_origin := pose * Vector3(5.0, 0.23, 0.36)
    var cap_world_ray := pose.basis * Vector3.LEFT
    var cap_hit := CapPicker.pick_cap(
        half_box, pose, cap_world_origin, cap_world_ray)
    if (cap_hit.is_empty() or cap_hit["plane_index"] != 0
        or not cap_hit["world_point"].is_equal_approx(
            pose * Vector3(0.0, 0.23, 0.36))):
        _fail("v0.86 rotated authored Box cap ray did not select its plane")
        return
    var cap_lines := CapPicker.cap_outline_edges(half_box, 0)
    if (cap_lines.size() != 8
        or CapPicker.cap_outline_mesh(half_box, 0).get_surface_count() != 1):
        _fail("v0.86 original four-edge cap has no editor-only perimeter")
        return
    for vertex in cap_lines:
        if absf(vertex.x - 0.0075) > 0.0001:
            _fail("v0.86 cap outline offset escaped authored local plane")
            return
    var two_caps: Dictionary = Brush.default_spec("Box")
    two_caps["clip_planes"] = [
        x_cut, {
        "normal": [0.0,1.0,0.0], "distance": 0.0,
        "keep_positive": false}]
    var hit_x := CapPicker.pick_cap(two_caps, pose,
        pose * Vector3(5.0,-0.31,0.23), pose.basis * Vector3.LEFT)
    var hit_y := CapPicker.pick_cap(two_caps, pose,
        pose * Vector3(-0.32,5.0,0.23), pose.basis * Vector3.DOWN)
    if (hit_x.is_empty() or hit_x["plane_index"] != 0
        or hit_y.is_empty() or hit_y["plane_index"] != 1
        or CapPicker.cap_outline_edges(two_caps, 0).size() != 8
        or CapPicker.cap_outline_edges(two_caps, 1).size() != 8):
        _fail("v0.86 two capped planes lost individual ray/outline identities")
        return
    var invalid_caps := [
        CapPicker.pick_cap(box, pose, cap_world_origin, cap_world_ray),
        CapPicker.pick_cap(half_box, singular,
            Vector3(5,0,0), Vector3.LEFT),
        CapPicker.pick_cap(half_box, pose, Vector3(INF,0,0), Vector3.LEFT),
        CapPicker.pick_cap(half_box, pose, cap_world_origin, Vector3.ZERO),
        CapPicker.pick_cap(half_box, pose,
            pose * Vector3(-5.0,-0.32,0.24), pose.basis * Vector3.RIGHT),
        CapPicker.pick_cap(two_caps, pose,
            pose * Vector3(5.0,0.8,0.2), pose.basis * Vector3.LEFT),
    ]
    for invalid in invalid_caps:
        if not invalid.is_empty():
            _fail("v0.86 hidden, off-target or untrusted source acquired cap selection")
            return
    if (not CapPicker.cap_outline_edges(box, 0).is_empty()
        or not CapPicker.cap_outline_edges(two_caps, 2).is_empty()
        or not CapPicker.cap_outline_edges(two_caps, -1).is_empty()):
        _fail("v0.86 uncut/nonexistent cap acquired editor outline")
        return

    var editor := Editor.new()
    get_root().add_child(editor)
    var draft := editor._new_draft_copy("Brush::Box", "DraftProp_17", pose)
    if not is_instance_valid(draft):
        _fail("Could not make real DX2Ed editor-only Brush::Box instance")
        return
    editor._select_mesh_only(draft)
    if (editor.brush_face_selector == null or editor.brush_face_selector.item_count != 6
        or editor.brush_face_hint == null or not editor.brush_face_hint.visible):
        _fail("Actual Godot Inspector missing clickable face controls/hint")
        return
    var selected := editor._pick_selected_draft_face_ray(
        pose * Vector3(5, 0, 0), pose.basis * Vector3.LEFT)
    if not selected or editor.brush_face_selector.selected != 1:
        _fail("Viewport face picking did not choose local +X Inspector face")
        return
    if (not is_instance_valid(editor.brush_face_outline)
        or editor.brush_face_outline.get_parent() != draft
        or editor.brush_face_outline.mesh.get_surface_count() != 1
        or editor.all_mesh_instances.has(editor.brush_face_outline)):
        _fail("Picked face wireframe leaked into original actor/mesh hierarchy")
        return
    var back_before := draft.global_position - draft.global_basis.x
    editor._grid_spacing_changed(0.5)
    editor._change_brush_face(1.0)
    if (not is_equal_approx(float(editor.draft_brush_specs["DraftProp_17"]["size"][0]), 2.5)
        or not (draft.global_position - draft.global_basis.x * 1.25
                ).is_equal_approx(back_before)):
        _fail("Picking +X and resizing moved opposite world plane")
        return
    var resized_outline := Brush.face_outline_edges(
        editor.draft_brush_specs["DraftProp_17"], 1)
    if resized_outline.size() != 8 or not is_equal_approx(
            resized_outline[0].x, 1.2575):
        _fail("Draft face highlight failed to track resized face")
        return
    editor._undo_edit()
    if not is_equal_approx(float(editor.draft_brush_specs["DraftProp_17"]["size"][0]), 2.0):
        _fail("Direct-picked face resizing failed Undo")
        return
    editor._redo_edit()
    if not is_equal_approx(float(editor.draft_brush_specs["DraftProp_17"]["size"][0]), 2.5):
        _fail("Direct-picked face resizing failed Redo")
        return

    # A failed hit must NOT change chosen face, geometry or selection.
    var selected_after := editor.brush_face_selector.selected
    if editor._pick_selected_draft_face_ray(
            pose * Vector3(5, 5, 0), pose.basis * Vector3.LEFT):
        _fail("Ray missed box but editor accepted it")
        return
    if editor.brush_face_selector.selected != selected_after:
        _fail("Missed click changed selected Inspector face")
        return
    # v0.86 actual selection gesture: choose authored clipped cap, not its
    # former cuboid face, without recording an edit or touching original GMP.
    if not editor._set_brush_spec("DraftProp_17", half_box):
        _fail("v0.86 editor refused valid private half-cube")
        return
    editor._select_mesh_only(draft)
    var history_at_cap_pick := editor.undo_stack.size()
    if (editor.brush_face_controls.visible
        or not editor.private_box_clip_panel.visible
        or not editor._can_pick_selected_draft_face()
        or not editor._pick_selected_draft_face_ray(
            cap_world_origin, cap_world_ray)
        or editor.box_clip_plane_selector.selected != 0):
        _fail("v0.86 Alt+Shift cap selection unavailable on selected private Box")
        return
    if (not is_instance_valid(editor.brush_face_outline)
        or editor.brush_face_outline.get_parent() != draft
        or editor.brush_face_outline.mesh.get_surface_count() != 1
        or editor.all_mesh_instances.has(editor.brush_face_outline)
        or editor.undo_stack.size() != history_at_cap_pick):
        _fail("v0.86 cap outline leaked or cap selection mutated Undo")
        return
    if not editor._set_brush_spec("DraftProp_17", two_caps):
        _fail("v0.86 editor refused valid private quarter-cube")
        return
    editor._select_mesh_only(draft)
    if (not editor._pick_selected_draft_face_ray(
            pose * Vector3(-0.32,5.0,0.23), pose.basis * Vector3.DOWN)
        or editor.box_clip_plane_selector.selected != 1
        or not is_instance_valid(editor.brush_face_outline)
        or editor.brush_face_outline.mesh.get_surface_count() != 1):
        _fail("v0.86 viewport did not switch selected cap and active outline")
        return
    var selected_cap_before := editor.box_clip_plane_selector.selected
    if (editor._pick_selected_draft_face_ray(
            pose * Vector3(-5.0,-0.3,0.2), pose.basis * Vector3.RIGHT)
        or editor.box_clip_plane_selector.selected != selected_cap_before
        or editor.undo_stack.size() != history_at_cap_pick):
        _fail("v0.86 visible original Box face changed selected cap or history")
        return
    # Never permit this gesture on original imported actors, even when the
    # corresponding display mesh is a cuboid.
    var imported := MeshInstance3D.new()
    imported.name = "StaticMeshActor__918"
    imported.mesh = BoxMesh.new()
    editor.world_root.add_child(imported)
    editor.meshes_by_actor[str(imported.name)] = imported
    editor.actors_by_name[str(imported.name)] = {
        "name": str(imported.name), "class": "StaticMeshActor", "export": 918,
        "location": [0,0,0], "rotation": [0,0,0], "game_properties": []}
    editor._select_mesh_only(imported)
    if is_instance_valid(editor.brush_face_outline):
        _fail("Original actor selection kept an editor-only brush face outline")
        return
    if editor._can_pick_selected_draft_face() or editor._pick_selected_draft_face_ray(
            Vector3(5,0,0), Vector3.LEFT):
        _fail("Imported original mesh wrongly acquired draft face editor")
        return
    editor.queue_free()
    print("DX2Ed v0.86 Godot cuboid and closed private cap viewport picking PASS")
    quit(0)
