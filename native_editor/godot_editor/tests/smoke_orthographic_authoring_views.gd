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
    # Private draft workspace metadata is strict, bounded, and source-independent.
    var workspace := {"view_mode": Guides.SIDE, "grid_step": 2.0, "grid_enabled": false}
    var checked: Variant = editor._validated_draft_workspace(workspace)
    if checked == null or checked["view_mode"] != Guides.SIDE or checked["grid_step"] != 2.0 or checked["grid_enabled"] != false:
        _fail("Valid private workspace metadata was rejected")
        return
    for bad in [
        {"view_mode": "Unsafe", "grid_step": 2.0, "grid_enabled": true},
        {"view_mode": Guides.TOP, "grid_step": 0.0, "grid_enabled": true},
        {"view_mode": Guides.TOP, "grid_step": INF, "grid_enabled": true},
        {"view_mode": Guides.TOP, "grid_step": 65.0, "grid_enabled": true},
        {"view_mode": Guides.TOP, "grid_step": 1.0, "grid_enabled": 1},
        {"view_mode": Guides.TOP, "grid_step": 1.0},
        {"view_mode": Guides.TOP, "grid_step": 1.0, "grid_enabled": true, "native_writer": true}
    ]:
        if editor._validated_draft_workspace(bad) != null:
            _fail("Invalid private workspace metadata was accepted")
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
    # JSON draft records contain String values; Node.name is a StringName.
    # Exercise the persisted representation, not the in-memory node type.
    var actor_id: String = str(invented.name)
    var valid_move := [{"actor": actor_id}]
    var valid_copy := [{"name": "DraftProp_1", "from_actor": actor_id}]
    var preflight_cases := [
        {"label": "valid original move and draft copy", "moved": valid_move, "copies": valid_copy, "accept": true},
        {"label": "duplicate original move", "moved": valid_move + valid_move, "copies": [], "accept": false},
        {"label": "missing original actor", "moved": [{"actor": "missing"}], "copies": [], "accept": false},
        {"label": "duplicate draft copy", "moved": [], "copies": valid_copy + valid_copy, "accept": false},
        {"label": "zero draft copy identifier", "moved": [], "copies": [{"name": "DraftProp_0", "from_actor": actor_id}], "accept": false},
        {"label": "missing draft source", "moved": [], "copies": [{"name": "DraftProp_2", "from_actor": "missing"}], "accept": false},
    ]
    for case in preflight_cases:
        var verdict: String = editor._draft_record_preflight(case["moved"], case["copies"])
        if verdict.is_empty() != case["accept"]:
            _fail("Private draft preflight " + case["label"] + ": " + verdict)
            return
    var selected_copy_rows := [{"name": "DraftProp_9", "from_actor": actor_id}]
    var restored_selection: Variant = editor._validated_draft_selection(
        [actor_id, "DraftProp_9"], selected_copy_rows)
    if restored_selection == null or restored_selection.size() != 2:
        _fail("Private project selection failed to resolve original actor and draft copy")
        return
    for invalid_selection in [
        [actor_id, actor_id], ["missing"], ["DraftProp_10"], [42], "not an array"
    ]:
        if editor._validated_draft_selection(invalid_selection, selected_copy_rows) != null:
            _fail("Invalid private project selection was accepted")
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
    # Real private project write path: stage, replace, retain previous version,
    # and fail closed on an interrupted .pending file without touching the draft.
    var draft_dir := ProjectSettings.globalize_path("user://prop_drafts")
    if DirAccess.make_dir_recursive_absolute(draft_dir) != OK:
        _fail("Could not create isolated private draft smoke directory")
        return
    var draft_path := draft_dir.path_join("synthetic_transaction_smoke.json")
    for suffix in ["", ".bak", ".pending"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    if not editor._write_private_draft_transaction(draft_path, "draft-1"):
        _fail("Initial private draft transactional save failed")
        return
    if not editor._write_private_draft_transaction(draft_path, "draft-2"):
        _fail("Second private draft transactional save failed")
        return
    var current := FileAccess.get_file_as_string(draft_path)
    var previous := FileAccess.get_file_as_string(draft_path + ".bak")
    if current != "draft-2" or previous != "draft-1":
        _fail("Private draft replacement or previous-version recovery failed")
        return
    var interrupted := FileAccess.open(draft_path + ".pending", FileAccess.WRITE)
    if interrupted == null:
        _fail("Could not create synthetic interrupted draft")
        return
    interrupted.store_string("unfinished")
    interrupted.close()
    if editor._write_private_draft_transaction(draft_path, "draft-3") or FileAccess.get_file_as_string(draft_path) != current:
        _fail("Interrupted private draft save overwrote existing document")
        return
    for suffix in ["", ".bak", ".pending"]:
        DirAccess.remove_absolute(draft_path + suffix)
    editor.queue_free()
    root.queue_free()
    print("DX2Ed v0.28 T3Ed-style orthographic viewport/grid smoke PASS")
    quit(0)
