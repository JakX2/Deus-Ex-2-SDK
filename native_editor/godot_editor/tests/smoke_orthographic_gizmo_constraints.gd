extends SceneTree
## DX2Ed v0.54 active-pane orthographic gizmo and private transform round-trip smoke.
## Invented editor-only Polygon brush; no retail map, native BSP or source writer.
const Guides = preload("res://orthographic_authoring_guides.gd")
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.54 orthographic gizmo: " + message)
    quit(1)


func _local_mouse(editor, screen: Vector2) -> Vector2:
    return screen * editor.view_container.size / Vector2(editor.world_view.size)


func _check_gizmo(editor, mode: String, tool: String) -> bool:
    var expected := Guides.gizmo_axes(mode, tool)
    var actual: Array[Vector3] = []
    var plane_count := 0
    for handle in editor.gizmo_handles:
        if not is_instance_valid(handle) or handle.layers != Guides.INTERACTION_LAYER_MASK:
            return false
        if handle.has_meta("axis"):
            var axis: Vector3 = handle.get_meta("axis")
            actual.append(axis)
        elif handle.has_meta("plane_axes"):
            plane_count += 1
    if actual.size() != expected.size():
        return false
    for axis in expected:
        if not actual.has(axis):
            return false
    var expected_planes := 1 if tool == "move" and mode != Guides.PERSPECTIVE else 0
    return plane_count == expected_planes


func _run() -> void:
    if (Guides.INTERACTION_LAYER_MASK == 0
        or (Guides.INTERACTION_LAYER_MASK & Guides.grid_layer_mask("top")) != 0
        or (Guides.INTERACTION_LAYER_MASK & Guides.grid_layer_mask("front")) != 0
        or (Guides.INTERACTION_LAYER_MASK & Guides.grid_layer_mask("side")) != 0):
        _fail("Interaction cull layer overlaps a planar grid layer")
        return

    var pivot := Vector3(0.25, 2.0, 0.25)
    var snapped_plane: Variant = Guides.plane_drag_delta(
        pivot, pivot, Vector3(2.6, 2.0, -1.4),
        [Vector3.RIGHT, Vector3.BACK], 1.0, true)
    if snapped_plane == null or not (pivot + snapped_plane).is_equal_approx(Vector3(3, 2, -1)):
        _fail("Top-plane world-grid snap did not align the resulting pivot")
        return
    var free_plane: Variant = Guides.plane_drag_delta(
        pivot, pivot, Vector3(2.6, 2.0, -1.4),
        [Vector3.RIGHT, Vector3.BACK], 1.0, false)
    if free_plane == null or not free_plane.is_equal_approx(Vector3(2.35, 0, -1.65)):
        _fail("Unsnapped plane translation changed an unconstrained component")
        return
    var snapped_axis: Variant = Guides.axis_drag_delta(
        pivot, 2.2, Vector3.RIGHT, 1.0, true)
    if snapped_axis == null or not (pivot + snapped_axis).is_equal_approx(Vector3(2, 2, 0.25)):
        _fail("Axis world-grid snap did not align the resulting pivot")
        return
    if (Guides.plane_drag_delta(pivot, pivot, pivot, [Vector3.RIGHT, Vector3(1, 0, 0.01)], 1.0, true) != null
        or Guides.plane_drag_delta(pivot, pivot, pivot, [Vector3.RIGHT], 1.0, true) != null
        or Guides.plane_drag_delta(pivot, pivot, pivot, [Vector3.RIGHT, Vector3.BACK], INF, true) != null
        or Guides.axis_drag_delta(pivot, 1.0, Vector3.ZERO, 1.0, false) != null):
        _fail("Malformed plane/axis drag input was accepted")
        return

    var editor := Editor.new()
    get_root().add_child(editor)
    var fake_scene := Node3D.new()
    editor.world_root.add_child(fake_scene)
    editor.scene_root = fake_scene
    editor.current_folder = ProjectSettings.globalize_path("user://v054_orthographic_gizmo")
    var draft := editor._new_draft_copy(
        "Brush::Polygon", "DraftProp_54", Transform3D.IDENTITY)
    if not is_instance_valid(draft):
        _fail("Could not construct the synthetic editor-only Polygon brush")
        return
    if not editor._set_brush_spec("DraftProp_54", Brush.default_spec("Polygon")):
        _fail("Synthetic Polygon brush failed normal authoring preflight")
        return
    editor._select_mesh_only(draft)
    if not editor.gizmo_root.visible or editor._selection_nodes().size() != 1:
        _fail("Selected private Polygon did not expose its transform gizmo")
        return

    for view_id in Guides.VIEW_IDS:
        editor._activate_view(view_id, false, false, true)
        var mode := Guides.mode_for_view_id(view_id)
        for tool in ["move", "rotate", "scale"]:
            editor._set_editor_tool(tool)
            if not _check_gizmo(editor, mode, tool):
                _fail("Incorrect constrained gizmo axes/plane handle: " + view_id + "/" + tool)
                return
        for candidate_view in Guides.VIEW_IDS:
            var expected_mask := Guides.viewport_cull_mask(candidate_view, view_id)
            if editor.cameras_by_view[candidate_view].cull_mask != expected_mask:
                _fail("Interactive overlay leaked into an inactive pane: " + view_id)
                return

    editor._activate_view("top", false, false, true)
    editor._set_editor_tool("move")
    editor.view_container.size = Vector2(400, 360)
    editor.world_view.size = Vector2i(400, 360)
    editor.camera_target = Vector3.ZERO
    editor.orbit_distance = 25.0
    editor._update_camera()
    editor._update_gizmo_pose()
    var plane_handle: MeshInstance3D = null
    for handle in editor.gizmo_handles:
        if handle.has_meta("plane_axes"):
            plane_handle = handle
            break
    if not is_instance_valid(plane_handle):
        _fail("Top view did not create the two-axis plane handle")
        return
    var start_mouse := _local_mouse(
        editor, editor.camera.unproject_position(plane_handle.global_position))
    editor.undo_stack.clear()
    editor.redo_stack.clear()
    if not editor._begin_gizmo_drag_at(start_mouse) or not editor.gizmo_plane_drag_active:
        _fail("Top-view plane handle did not begin an actual viewport drag")
        return
    var end_world := editor.gizmo_drag_plane_start + Vector3(2.0, 0.0, 0.0)
    var end_mouse := _local_mouse(editor, editor.camera.unproject_position(end_world))
    editor._apply_gizmo_drag_at(end_mouse)
    var moved: MeshInstance3D = editor.draft_prop_copies["DraftProp_54"]
    if not moved.global_position.is_equal_approx(Vector3(2.0, 0.0, 0.0)):
        _fail("Orthographic plane drag did not move the Polygon on the intended XZ plane")
        return
    editor._finish_gizmo_drag()
    if editor.undo_stack.size() != 1:
        _fail("One plane drag did not commit exactly one Undo transaction")
        return
    editor._undo_edit()
    var undone: MeshInstance3D = editor.draft_prop_copies["DraftProp_54"]
    if not undone.global_position.is_equal_approx(Vector3.ZERO):
        _fail("Undo did not restore the Polygon's original transform")
        return
    editor._redo_edit()
    var redone: MeshInstance3D = editor.draft_prop_copies["DraftProp_54"]
    if not redone.global_position.is_equal_approx(Vector3(2.0, 0.0, 0.0)):
        _fail("Redo did not restore the orthographic plane drag")
        return

    editor._save_prop_draft()
    var draft_path := editor._draft_file_path()
    if draft_path.is_empty() or not FileAccess.file_exists(draft_path):
        _fail("Private draft save did not persist the transformed Polygon")
        return
    var saved_transform: Transform3D = editor.draft_prop_copies["DraftProp_54"].global_transform
    editor.draft_prop_copies["DraftProp_54"].global_position = Vector3(99, 99, 99)
    editor._load_prop_draft(true)
    var reopened: MeshInstance3D = editor.draft_prop_copies.get("DraftProp_54", null)
    if (not is_instance_valid(reopened)
        or not reopened.global_transform.is_equal_approx(saved_transform)):
        _fail("Private Save/reopen did not preserve the orthographic gizmo transform")
        return
    for suffix in ["", ".bak", ".pending"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    editor.queue_free()
    print("DX2Ed v0.54 active-pane orthographic gizmos, plane drag, grid snap, Undo/Redo and private Save/reopen PASS")
    quit(0)
