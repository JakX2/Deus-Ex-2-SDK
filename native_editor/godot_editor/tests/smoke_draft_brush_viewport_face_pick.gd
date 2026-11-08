extends SceneTree
## DX2Ed v0.37 viewport face selection, synthetic Godot brush data ONLY.
## No owner original map, native GMP/BSP/collision writer or game runtime.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")


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
    var back_before := draft.global_position - draft.global_basis.x
    editor._grid_spacing_changed(0.5)
    editor._change_brush_face(1.0)
    if (not is_equal_approx(float(editor.draft_brush_specs["DraftProp_17"]["size"][0]), 2.5)
        or not (draft.global_position - draft.global_basis.x * 1.25
                ).is_equal_approx(back_before)):
        _fail("Picking +X and resizing moved opposite world plane")
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
    if editor._can_pick_selected_draft_face() or editor._pick_selected_draft_face_ray(
            Vector3(5,0,0), Vector3.LEFT):
        _fail("Imported original mesh wrongly acquired draft face editor")
        return
    editor.queue_free()
    print("DX2Ed v0.37 real Godot viewport draft face picking smoke PASS")
    quit(0)
