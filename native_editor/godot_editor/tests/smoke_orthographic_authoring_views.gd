extends SceneTree
## v0.28 T3Ed-style orthographic editor workflow smoke, invented 3D nodes.
## Tests the REAL Godot editor toolbar/camera and pure guide math.
## No retail maps, native actors, source GMP writes, BSP/zone serialization.
const Guides = preload("res://orthographic_authoring_guides.gd")
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")


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
    # The actual preview-brush mesh builder, used by the editor and draft save.
    var cylinder_spec := Brush.default_spec("Cylinder")
    var cylinder := Brush.build_mesh(cylinder_spec)
    if (cylinder_spec.is_empty() or cylinder == null
        or cylinder.get_surface_count() != 1
        or cylinder.surface_get_array_len(0) != 288
        or Brush.validate({"kind": "Cylinder", "size": [0.0, 2.0, 2.0], "steps": 1}) != {}
        or Brush.validate({"kind": "Cylinder", "size": [2.0, 2.0, 2.0], "steps": 2}) != {}):
        _fail("Closed bounded cylinder draft mesh/validation regression")
        return
    # New draft palette must produce bounded closed meshes through the actual builder.
    var cone := Brush.build_mesh(Brush.default_spec("Cone"))
    var sphere := Brush.build_mesh(Brush.default_spec("Sphere"))
    if (cone == null or sphere == null
        or cone.get_surface_count() != 1 or sphere.get_surface_count() != 1
        or cone.surface_get_array_len(0) != 144
        or sphere.surface_get_array_len(0) != 1584
        or Brush.validate({"kind": "Cone", "size": [0.0, 2.0, 2.0], "steps": 1}) != {}
        or Brush.validate({"kind": "Sphere", "size": [2.0, INF, 2.0], "steps": 1}) != {}
        or Brush.validate({"kind": "Sphere", "size": [2.0, 2.0, 2.0], "steps": 2}) != {}):
        _fail("Cone/ellipsoid palette mesh or fail-closed validation regression")
        return
    # Ramp is a closed six-face triangular prism (8 triangles / 24 vertices).
    var ramp_spec := Brush.default_spec("Ramp")
    var ramp := Brush.build_mesh(ramp_spec)
    if (ramp == null or ramp.get_surface_count() != 1
        or ramp.surface_get_array_len(0) != 24
        or Brush.validate(ramp_spec).is_empty()
        or Brush.validate({"kind": "Ramp", "size": [3.0, 1.5, 4.0], "steps": 2}) != {}
        or Brush.validate({"kind": "Ramp", "size": [3.0, -1.0, 4.0], "steps": 1}) != {}):
        _fail("Ramp brush mesh or bounded validation regression")
        return
    var ramp_vertices: PackedVector3Array = ramp.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    var ramp_min := Vector3(INF, INF, INF)
    var ramp_max := Vector3(-INF, -INF, -INF)
    for vertex in ramp_vertices:
        ramp_min = ramp_min.min(vertex)
        ramp_max = ramp_max.max(vertex)
    if not ramp_min.is_equal_approx(Vector3(-1.5, -0.75, -2.0)) or not ramp_max.is_equal_approx(Vector3(1.5, 0.75, 2.0)):
        _fail("Ramp brush bounds regression")
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
    var snap_input := Vector3(1.26, -0.4, 0.6)
    if not Guides.snapped_preview_position(snap_input, 0.5).is_equal_approx(
            Vector3(1.5, -0.5, 0.5)):
        _fail("Grid snap did not align world coordinates")
        return
    var invented := MeshInstance3D.new()
    invented.name = "StaticMeshActor__777"
    invented.mesh = BoxMesh.new()
    editor.world_root.add_child(invented)
    invented.global_position = Vector3(1.1, 2.9, -0.9)
    editor.meshes_by_actor[invented.name] = invented
    editor.actors_by_name[invented.name] = {
        "name": invented.name, "class": "StaticMeshActor",
        "export": 777, "location": [0,0,0],
        "rotation": [0,0,0], "game_properties": [],
    }
    editor.original_mesh_transforms[invented.name] = invented.global_transform
    # Real editor private draft preflight: malformed identities must never
    # reach the destructive reset/reconstruction stage.
    var valid_move := [{"actor": invented.name}]
    var valid_copy := [{"name": "DraftProp_1", "from_actor": invented.name}]
    if (not editor._draft_record_preflight(valid_move, valid_copy).is_empty()
        or editor._draft_record_preflight(valid_move + valid_move, []).is_empty()
        or editor._draft_record_preflight([{"actor": "missing"}], []).is_empty()
        or editor._draft_record_preflight([], valid_copy + valid_copy).is_empty()
        or editor._draft_record_preflight([], [{"name": "DraftProp_0", "from_actor": invented.name}]).is_empty()
        or editor._draft_record_preflight([], [{"name": "DraftProp_2", "from_actor": "missing"}]).is_empty()):
        _fail("Private draft preflight accepted missing/duplicate records or rejected valid records")
        return
    editor.selected_meshes[invented.name] = invented
    editor.selected_mesh = invented
    var original_preview := invented.global_position
    editor._snap_selected_preview_to_grid()
    if (not invented.global_position.is_equal_approx(Vector3(2, 2, 0))
        or editor.undo_stack.size() != 1):
        _fail("Real editor did not create undoable preview grid snap")
        return
    editor._undo_edit()
    if not invented.global_position.is_equal_approx(original_preview):
        _fail("Preview grid snap Ctrl+Z did not restore actor position")
        return
    editor._redo_edit()
    if not invented.global_position.is_equal_approx(Vector3(2, 2, 0)):
        _fail("Preview grid snap Ctrl+Y did not replay snapped position")
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
