extends SceneTree
## v0.28 T3Ed-style orthographic editor workflow smoke, invented 3D nodes.
## Tests the REAL Godot editor toolbar/camera and pure guide math.
## No retail maps, native actors, source GMP writes, BSP/zone serialization.
const Guides = preload("res://orthographic_authoring_guides.gd")
const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.28 orthographic editor guides: " + message)
    quit(1)


func _run() -> void:
    var root := Node3D.new()
    get_root().add_child(root)
    var cam := Camera3D.new()
    root.add_child(cam)
    var target := Vector3(7.4, 2.6, -12.1)
    var original_mode := Guides.PERSPECTIVE
    if (not Guides.apply_camera(cam, original_mode, target, 25.0, 0.7, 0.3)
        or cam.projection != Camera3D.PROJECTION_PERSPECTIVE):
        _fail("Original perspective camera projection unavailable")
        return
    var all_modes := [Guides.TOP, Guides.FRONT, Guides.SIDE]
    var normals := [Vector3.UP, Vector3.BACK, Vector3.RIGHT]
    for index in range(all_modes.size()):
        var mode: String = all_modes[index]
        if not Guides.apply_camera(cam, mode, target, 25.0, 0.7, 0.3):
            _fail("Orthographic camera refused valid authoring mode")
            return
        if (cam.projection != Camera3D.PROJECTION_ORTHOGONAL
            or not is_equal_approx(cam.size, 40.0)
            or not cam.global_position.is_equal_approx(target + normals[index] * 25.0)
            or not cam.global_basis.z.is_equal_approx(normals[index])):
            _fail("Fixed source-independent camera axes/projection incorrect: " + mode)
            return
        var segments := Guides.grid_segments(
            mode, Vector3(1.2, 2.4, 3.6), 1.0, 2)
        if segments.size() != 10:
            _fail("Grid did not emit bounded parallel lines")
            return
        for line in segments:
            if line.size() != 2:
                _fail("Invalid grid endpoint count")
                return
            for point in line:
                if (mode == Guides.TOP and not is_equal_approx(point.y, 2.0)
                    or mode == Guides.FRONT and not is_equal_approx(point.z, 4.0)
                    or mode == Guides.SIDE and not is_equal_approx(point.x, 1.0)):
                    _fail("Grid escaped chosen orthographic plane")
                    return
        var mesh := Guides.grid_mesh(mode, target, 1.0, 2)
        if mesh.get_surface_count() != 1:
            _fail("Orthographic line mesh was not constructed")
            return
    if (Guides.apply_camera(cam, "Unsafe", target, 25.0, 0.7, 0.3)
        or Guides.grid_segments(Guides.PERSPECTIVE, target, 1.0).size() != 0
        or not Guides.grid_segments(Guides.TOP, target, 1.0, 1000).is_empty()
        or not Guides.grid_segments(Guides.TOP, target, 0.0, 2).is_empty()
        or not Guides.grid_segments(Guides.TOP, Vector3(INF, 0, 0), 1.0).is_empty()):
        _fail("Unbounded/invalid grid or invalid view did not fail closed")
        return
    var editor := Editor.new()
    get_root().add_child(editor)
    if (editor.editor_view_mode_select == null
        or editor.editor_view_mode_select.item_count != 4
        or editor.ortho_grid_node == null
        or editor.camera == null):
        _fail("Real DX2Ed toolbar/camera did not include T3Ed-style views")
        return
    editor._set_editor_view_mode(Guides.TOP)
    if (editor.camera.projection != Camera3D.PROJECTION_ORTHOGONAL
        or not editor.ortho_grid_node.visible
        or editor.ortho_grid_node.mesh.get_surface_count() != 1):
        _fail("Real editor could not activate top orthographic grid")
        return
    editor._grid_spacing_changed(2.0)
    if (not is_equal_approx(editor.ortho_grid_step, 2.0)
        or not is_equal_approx(editor.prop_edit_step.value, 2.0)):
        _fail("Grid step did not synchronize preview Ctrl snap increment")
        return
    editor._toggle_ortho_grid(false)
    if editor.ortho_grid_node.visible:
        _fail("Grid visibility toggle did not hide overlay")
        return
    editor._set_editor_view_mode(Guides.SIDE)
    if editor.camera.projection != Camera3D.PROJECTION_ORTHOGONAL:
        _fail("Side orthographic authoring mode not reachable")
        return
    editor._toggle_ortho_grid(true)
    editor._set_editor_view_mode(Guides.PERSPECTIVE)
    if (editor.camera.projection != Camera3D.PROJECTION_PERSPECTIVE
        or editor.ortho_grid_node.visible
        or editor.editor_view_mode_select.selected != 0):
        _fail("Perspective restore leaked grid or toolbar state")
        return
    editor.queue_free()
    root.queue_free()
    print("DX2Ed v0.28 T3Ed-style orthographic viewport/grid smoke PASS")
    quit(0)
