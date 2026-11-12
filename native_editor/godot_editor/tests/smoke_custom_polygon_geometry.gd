extends SceneTree
## DX2Ed v0.40 custom polygon viewport vertex editing and private round-trip smoke.
## Uses invented assets and an isolated user:// draft. No retail DX2 GMP.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")
const Polygon = preload("res://custom_polygon_geometry.gd")
const Guides = preload("res://orthographic_authoring_guides.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.40 custom polygon viewport vertex editing: " + message)
    quit(1)


func _run() -> void:
    var spec := Brush.default_spec("Polygon")
    if (spec.is_empty() or Brush.validate(spec).is_empty()
        or spec["outline"].size() != 6):
        _fail("Polygon brush missing from validated palette")
        return
    var legacy_spec: Dictionary = spec.duplicate(true)
    legacy_spec.erase("surface_style")
    var legacy_valid := Brush.validate(legacy_spec)
    if (legacy_valid.is_empty()
        or legacy_valid["surface_style"]["top"]["preset"] != "Concrete"):
        _fail("Legacy Polygon project without surface style did not receive defaults")
        return
    var mesh := Brush.build_mesh(spec)
    if (mesh == null or mesh.get_surface_count() != 3
        or mesh.surface_get_array_len(0) != 12
        or mesh.surface_get_array_len(1) != 12
        or mesh.surface_get_array_len(2) != 36):
        _fail("Concave polygon did not create separate top/bottom/side surfaces")
        return
    var bounds := AABB(Vector3(-2.0,-1.0,-2.0), Vector3(4.0,2.0,4.0))
    for surface_index in range(3):
        var arrays: Array = mesh.surface_get_arrays(surface_index)
        var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
        var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
        if uvs.size() != points.size() or uvs.is_empty():
            _fail("Polygon surface did not expose complete UV coordinates")
            return
        for point in points:
            if not bounds.has_point(point):
                _fail("Polygon extruded outside configured X/Y/Z dimensions")
                return
    var mirrored: Dictionary = spec.duplicate(true)
    mirrored["outline"].reverse()
    var reverse_mesh := Brush.build_mesh(mirrored)
    if (reverse_mesh == null or reverse_mesh.get_surface_count() != 3
        or reverse_mesh.surface_get_array_len(0) != 12
        or reverse_mesh.surface_get_array_len(1) != 12
        or reverse_mesh.surface_get_array_len(2) != 36):
        _fail("Clockwise custom polygon refused despite valid simple topology")
        return

    for bad in [
        [[-1,-1],[1,1],[-1,1],[1,-1]], # self crossing
        [[-1,-1],[1,-1],[1,-1],[-1,1]], # duplicate
        [[-1,-1],[1,-1],[1,1]], # valid triangle (control below)
        [[-1,-1],[INF,-1],[1,1]],
        [[-1,-1],[1,-1],[3,1]], # beyond bounded local coordinates
        [[-1,-1],[1,-1]], # not enough corners
        [[0,0],[0.01,0],[0,0.01]], # degenerate area
    ]:
        if bad.size() == 3 and bad[0] == [-1,-1] and bad[1] == [1,-1] and bad[2] == [1,1]:
            if Polygon.validate_outline(bad).is_empty():
                _fail("Simple triangle outline rejected")
                return
        elif not Polygon.validate_outline(bad).is_empty():
            _fail("Malformed source-only custom outline passed validation")
            return
    if Polygon.with_moved_vertex(spec["outline"],2,0,0.75).size() != 6:
        _fail("Vertex editing failed for concave polygon")
        return
    var invalid_style_spec: Dictionary = spec.duplicate(true)
    invalid_style_spec["surface_style"]["top"]["uv_scale"] = [0.001, 1.0]
    if not Brush.validate(invalid_style_spec).is_empty():
        _fail("Out-of-range private surface UV scale passed brush preflight")
        return
    invalid_style_spec = spec.duplicate(true)
    invalid_style_spec["surface_style"]["sides"]["preset"] = "UnverifiedShader"
    if not Brush.validate(invalid_style_spec).is_empty():
        _fail("Unknown private surface preset passed brush preflight")
        return
    if (not Polygon.with_moved_vertex(spec["outline"],2,0,4.0).is_empty()
        or not Polygon.with_inserted_vertex(spec["outline"],-1).is_empty()
        or not Polygon.with_deleted_vertex(spec["outline"],10).is_empty()):
        _fail("Custom polygon dimension/index safeguards failed")
        return

    # v0.78: bounded planar Brush Clip works on private editable footprints.
    var rectangle := [[-1.0,-1.0],[1.0,-1.0],[1.0,1.0],[-1.0,1.0]]
    var clip_left: Array = Polygon.clip_outline_axis(rectangle, 0, 0.0, false)
    var clip_right: Array = Polygon.clip_outline_axis(rectangle, 0, 0.0, true)
    var clip_top: Array = Polygon.clip_outline_axis(rectangle, 1, 0.25, true)
    if (clip_left.size() != 4 or clip_right.size() != 4
        or clip_top.size() != 4
        or Polygon.validate_outline(clip_left).is_empty()
        or Polygon.validate_outline(clip_right).is_empty()
        or Polygon.validate_outline(clip_top).is_empty()):
        _fail("Bounded local X/Z half-plane polygon clip did not retain valid rectangles")
        return
    for point in clip_left:
        if float(point[0]) > 0.00001:
            _fail("Left clip retained a source point outside its half-plane")
            return
    for point in clip_right:
        if float(point[0]) < -0.00001:
            _fail("Right clip retained a source point outside its half-plane")
            return
    for point in clip_top:
        if float(point[1]) < 0.24999:
            _fail("Top clip retained a source point outside its half-plane")
            return
    var clockwise: Array = rectangle.duplicate(true)
    clockwise.reverse()
    if Polygon.clip_outline_axis(clockwise, 0, 0.0, false).size() != 4:
        _fail("Clockwise source winding did not survive private brush clip")
        return
    var disconnected_u := [
        [-1.0,-1.0],[1.0,-1.0],[1.0,1.0],[0.6,1.0],
        [0.6,-0.6],[-0.6,-0.6],[-0.6,1.0],[-1.0,1.0]]
    for rejected in [
        Polygon.clip_outline_axis(rectangle, -1, 0.0, false),
        Polygon.clip_outline_axis(rectangle, 2, 0.0, false),
        Polygon.clip_outline_axis(rectangle, 0, INF, false),
        Polygon.clip_outline_axis(rectangle, 0, 1.1, false),
        Polygon.clip_outline_axis(rectangle, 0, 1.0, false),
        Polygon.clip_outline_axis(rectangle, 0, -1.0, false),
        Polygon.clip_outline_axis(disconnected_u, 1, 0.0, true),
        Polygon.clip_outline_axis([[-1,-1],[1,1],[-1,1],[1,-1]],0,0.0,false)
    ]:
        if not rejected.is_empty():
            _fail("Unsafe, disconnected, degenerate or unchanged Polygon clip was accepted")
            return

    var editor := Editor.new()
    get_root().add_child(editor)
    var source := ProjectSettings.globalize_path("user://v040_owner_invented_source.gmp")
    var content := PackedByteArray([68,88,50,69,100,103,101,111,56])
    var source_file := FileAccess.open(source,FileAccess.WRITE)
    if source_file == null:
        _fail("Cannot create isolated invented source sentinel")
        return
    source_file.store_buffer(content)
    source_file.close()
    var source_hash := FileAccess.get_sha256(source)
    var fake_scene := Node3D.new()
    editor.world_root.add_child(fake_scene)
    editor.scene_root = fake_scene
    editor.current_folder = ProjectSettings.globalize_path(
        "user://v040_private_custom_polygon_cache")
    var draft := editor._new_draft_copy(
        "Brush::Polygon", "DraftProp_38",
        Transform3D(Basis(Vector3.UP,0.37),Vector3(4,1,7)))
    if not is_instance_valid(draft):
        _fail("Could not create authored polygon in actual Godot editor")
        return
    editor.next_prop_copy_id = 39
    editor._select_mesh_only(draft)
    if (editor.polygon_inspector_panel == null
        or not editor.polygon_inspector_panel.visible
        or editor.polygon_vertex_selector.item_count != 6
        or editor.polygon_vertex_x == null or editor.polygon_vertex_z == null
        or editor.polygon_surface_selector == null
        or editor.polygon_surface_preset_selector == null
        or editor.polygon_surface_uv_controls.size() != 4
        or editor.brush_face_controls.visible):
        _fail("Actual Inspector missing custom polygon corner editing")
        return
    editor.polygon_vertex_selector.select(2)
    editor._polygon_corner_selected(2)
    editor._change_polygon_corner(0.75,0)
    if (editor.undo_stack.size() != 1
        or not is_equal_approx(
            float(editor.draft_brush_specs["DraftProp_38"]["outline"][2][0]),0.75)):
        _fail("Moving custom polygon corner did not edit mesh and enter Undo")
        return
    var after_move_mesh: Mesh = editor.draft_prop_copies["DraftProp_38"].mesh
    if after_move_mesh == mesh:
        _fail("Custom polygon vertex edit left original mesh unchanged")
        return

    # Apply a real per-surface material/UV change through the Inspector and
    # prove it is one undoable private-draft edit, not a global material override.
    var history_before_style := editor.undo_stack.size()
    editor.polygon_surface_selector.select(0)
    editor._polygon_surface_slot_selected(0)
    editor.polygon_surface_preset_selector.select(Polygon.SURFACE_PRESETS.find("Metal"))
    editor.polygon_surface_uv_controls[0].value = 2.0
    editor.polygon_surface_uv_controls[1].value = 3.0
    editor.polygon_surface_uv_controls[2].value = 0.25
    editor.polygon_surface_uv_controls[3].value = -0.5
    editor._apply_polygon_surface_style()
    var styled_spec: Dictionary = editor.draft_brush_specs["DraftProp_38"]
    var styled_mesh: Mesh = editor.draft_prop_copies["DraftProp_38"].mesh
    var top_material := styled_mesh.surface_get_material(0) as StandardMaterial3D
    if (editor.undo_stack.size() != history_before_style + 1
        or styled_mesh.get_surface_count() != 3
        or top_material == null or top_material.albedo_texture == null
        or styled_spec["surface_style"]["top"]["preset"] != "Metal"
        or not is_equal_approx(float(styled_spec["surface_style"]["top"]["uv_scale"][0]), 2.0)
        or not is_equal_approx(float(styled_spec["surface_style"]["top"]["uv_scale"][1]), 3.0)
        or not is_equal_approx(top_material.uv1_scale.x, 2.0)
        or not is_equal_approx(top_material.uv1_scale.y, 3.0)
        or not is_equal_approx(top_material.uv1_offset.x, 0.25)
        or not is_equal_approx(top_material.uv1_offset.y, -0.5)
        or styled_mesh.surface_get_material(1) == top_material
        or styled_mesh.surface_get_material(2) == top_material):
        _fail("Per-surface preview material/UV assignment did not reach three independent mesh surfaces")
        return
    editor._undo_edit()
    if editor.draft_brush_specs["DraftProp_38"]["surface_style"]["top"]["preset"] != "Concrete":
        _fail("Polygon surface material/UV Undo did not restore the prior style")
        return
    editor._redo_edit()
    if editor.draft_brush_specs["DraftProp_38"]["surface_style"]["top"]["preset"] != "Metal":
        _fail("Polygon surface material/UV Redo did not restore the applied style")
        return
    editor._insert_polygon_corner()
    if editor.draft_brush_specs["DraftProp_38"]["outline"].size() != 7:
        _fail("Insert corner was not applied to authored polygon")
        return
    editor._delete_polygon_corner()
    if editor.draft_brush_specs["DraftProp_38"]["outline"].size() != 6:
        _fail("Delete corner did not return to six original footprint points")
        return
    editor._undo_edit()
    if editor.draft_brush_specs["DraftProp_38"]["outline"].size() != 7:
        _fail("Polygon delete cannot be undone")
        return
    editor._redo_edit()
    if editor.draft_brush_specs["DraftProp_38"]["outline"].size() != 6:
        _fail("Polygon delete cannot be redone")
        return

    # Exercise the actual Godot editor path: visible handles, Top-view screen
    # picking, transformed top-plane ray drag, world snapping and one history
    # transaction. Overlay nodes must stay outside actor indexing.
    editor._set_editor_view_mode(Guides.TOP)
    editor._grid_spacing_changed(0.25)
    editor.view_container.stretch = false
    editor.view_container.size = Vector2(400, 360)
    editor.world_view.size = Vector2i(400, 360)
    editor._refresh_polygon_vertex_handles()
    if (editor.polygon_vertex_handles.size() != 6
        or not editor.polygon_vertex_handle_root.visible):
        _fail("Selected Polygon did not display six viewport corner handles")
        return
    var first_handle: MeshInstance3D = editor.polygon_vertex_handles[0]
    if (not first_handle.get_meta("editor_only", false)
        or editor.all_mesh_instances.has(first_handle)):
        _fail("Viewport corner overlay leaked into source actor mesh indexing")
        return
    var start_pixels: Vector2 = editor.camera.unproject_position(first_handle.global_position)
    var start_mouse: Vector2 = (
        start_pixels * editor.view_container.size / Vector2(editor.world_view.size))
    var drag_node: MeshInstance3D = editor.draft_prop_copies["DraftProp_38"]
    var drag_size := Vector3(
        float(editor.draft_brush_specs["DraftProp_38"]["size"][0]),
        float(editor.draft_brush_specs["DraftProp_38"]["size"][1]),
        float(editor.draft_brush_specs["DraftProp_38"]["size"][2]))
    var target_world := drag_node.to_global(Vector3(
        -0.75 * drag_size.x * 0.5,
        drag_size.y * 0.5 + 0.035,
        -0.75 * drag_size.z * 0.5))
    var target_pixels: Vector2 = editor.camera.unproject_position(target_world)
    var target_mouse: Vector2 = (
        target_pixels * editor.view_container.size / Vector2(editor.world_view.size))
    var original_drag_outline: Array = (
        editor.draft_brush_specs["DraftProp_38"]["outline"].duplicate(true))
    var original_drag_x := float(original_drag_outline[0][0])
    var original_drag_z := float(original_drag_outline[0][1])
    var history_before_drag := editor.undo_stack.size()
    editor._set_editor_view_mode(Guides.FRONT)
    if editor.polygon_vertex_outline_node.mesh == null:
        _fail("Hidden polygon overlay retained a null mesh resource")
        return
    if editor._begin_polygon_vertex_drag_at(start_mouse):
        _fail("Front (XY) view unexpectedly enabled XZ footprint vertex drag")
        return
    editor._set_editor_view_mode(Guides.TOP)
    if editor._pick_polygon_vertex_handle_at(start_mouse) != 0:
        _fail("Top-view screen-space handle picking missed the first corner")
        return
    if not editor._begin_polygon_vertex_drag_at(start_mouse):
        _fail("Could not begin direct viewport drag on the selected Polygon corner")
        return
    if editor.polygon_vertex_selector.selected != 0:
        _fail("Viewport handle click did not select the matching Inspector corner")
        return
    var outside_world := drag_node.to_global(Vector3(
        1.5 * drag_size.x * 0.5,
        drag_size.y * 0.5 + 0.035,
        -drag_size.z * 0.5))
    var outside_pixels: Vector2 = editor.camera.unproject_position(outside_world)
    var outside_mouse: Vector2 = (
        outside_pixels * editor.view_container.size / Vector2(editor.world_view.size))
    editor._apply_polygon_vertex_drag_at(outside_mouse)
    var after_rejected_drag: Array = editor.draft_brush_specs["DraftProp_38"]["outline"]
    if (not is_equal_approx(float(after_rejected_drag[0][0]), original_drag_x)
        or not is_equal_approx(float(after_rejected_drag[0][1]), original_drag_z)):
        _fail("Out-of-bounds viewport drag replaced the last valid Polygon preview")
        return
    editor._apply_polygon_vertex_drag_at(target_mouse)
    editor._finish_polygon_vertex_drag()
    var dragged_outline: Array = editor.draft_brush_specs["DraftProp_38"]["outline"]
    if (is_equal_approx(float(dragged_outline[0][0]), original_drag_x)
        and is_equal_approx(float(dragged_outline[0][1]), original_drag_z)):
        _fail("Viewport corner drag did not move the authored footprint")
        return
    if editor.undo_stack.size() != history_before_drag + 1:
        _fail("One viewport drag did not commit exactly one Undo transaction")
        return
    var moved_node: MeshInstance3D = editor.draft_prop_copies["DraftProp_38"]
    var moved_size := Vector3(
        float(editor.draft_brush_specs["DraftProp_38"]["size"][0]),
        float(editor.draft_brush_specs["DraftProp_38"]["size"][1]),
        float(editor.draft_brush_specs["DraftProp_38"]["size"][2]))
    var moved_world := moved_node.to_global(Vector3(
        float(dragged_outline[0][0]) * moved_size.x * 0.5,
        moved_size.y * 0.5 + 0.035,
        float(dragged_outline[0][1]) * moved_size.z * 0.5))
    if (not is_equal_approx(snappedf(moved_world.x, 0.25), moved_world.x)
        or not is_equal_approx(snappedf(moved_world.z, 0.25), moved_world.z)):
        _fail("Viewport vertex drag did not preserve world X/Z grid snapping")
        return
    editor._undo_edit()
    var undone_outline: Array = editor.draft_brush_specs["DraftProp_38"]["outline"]
    if (not is_equal_approx(float(undone_outline[0][0]), original_drag_x)
        or not is_equal_approx(float(undone_outline[0][1]), original_drag_z)):
        _fail("Viewport vertex drag Undo did not restore the exact original corner")
        return
    editor._redo_edit()
    var redone_outline: Array = editor.draft_brush_specs["DraftProp_38"]["outline"]
    if (not is_equal_approx(float(redone_outline[0][0]), float(dragged_outline[0][0]))
        or not is_equal_approx(float(redone_outline[0][1]), float(dragged_outline[0][1]))):
        _fail("Viewport vertex drag Redo did not restore the snapped corner")
        return

    editor._set_editor_view_mode(Guides.TOP)
    editor._grid_spacing_changed(0.5)
    var path := editor._draft_file_path()
    if path.is_empty():
        _fail("Private geometry draft path missing")
        return
    for suffix in ["",".bak",".pending"]:
        if FileAccess.file_exists(path+suffix):
            DirAccess.remove_absolute(path+suffix)
    editor._save_prop_draft()
    if not FileAccess.file_exists(path):
        _fail("Private polygon draft Save failed")
        return
    var doc: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
    if (typeof(doc) != TYPE_DICTIONARY
        or doc.get("schema") != "DX2Ed-prop-draft-v1"
        or doc["copies"].size() != 1
        or doc["copies"][0]["brush"]["kind"] != "Polygon"
        or doc["copies"][0]["brush"]["outline"].size() != 6
        or doc["copies"][0]["brush"]["surface_style"]["top"]["preset"] != "Metal"
        or not is_equal_approx(float(doc["copies"][0]["brush"]["surface_style"]["top"]["uv_scale"][0]), 2.0)
        or not is_equal_approx(float(doc["copies"][0]["brush"]["surface_style"]["top"]["uv_offset"][1]), -0.5)
        or not is_equal_approx(float(doc["copies"][0]["brush"]["outline"][0][0]), float(redone_outline[0][0]))
        or not is_equal_approx(float(doc["copies"][0]["brush"]["outline"][0][1]), float(redone_outline[0][1]))
        or not is_equal_approx(float(doc["copies"][0]["brush"]["outline"][2][0]),0.75)
        or doc["workspace"]["view_mode"] != Guides.TOP
        or not doc["selection"].has("DraftProp_38")):
        _fail("Private project lost custom polygon vertices or workspace")
        return
    # Exercise actual editor project reopen after altering the whole mesh.
    editor._set_brush_spec("DraftProp_38",Brush.default_spec("Polygon"))
    editor._set_editor_view_mode(Guides.PERSPECTIVE)
    editor._load_prop_draft()
    if (not editor.draft_prop_copies.has("DraftProp_38")
        or not is_equal_approx(float(
            editor.draft_brush_specs["DraftProp_38"]["outline"][0][0]), float(redone_outline[0][0]))
        or not is_equal_approx(float(
            editor.draft_brush_specs["DraftProp_38"]["outline"][0][1]), float(redone_outline[0][1]))
        or not is_equal_approx(float(
            editor.draft_brush_specs["DraftProp_38"]["outline"][2][0]),0.75)
        or editor.draft_brush_specs["DraftProp_38"]["surface_style"]["top"]["preset"] != "Metal"
        or not is_equal_approx(float(
            editor.draft_brush_specs["DraftProp_38"]["surface_style"]["top"]["uv_scale"][0]), 2.0)
        or not editor.selected_meshes.has("DraftProp_38")
        or editor.editor_view_mode != Guides.TOP):
        _fail("Custom polygon geometry/project failed real editor reload")
        return

    # A malicious self-intersecting private project must be refused BEFORE
    # it clears the user's currently edited draft shape.
    var malicious: Dictionary = doc.duplicate(true)
    malicious["copies"][0]["brush"]["outline"] = [
        [-1,-1],[1,1],[-1,1],[1,-1]]
    var external := FileAccess.open(path,FileAccess.WRITE)
    external.store_string(JSON.stringify(malicious))
    external.close()
    editor._load_prop_draft()
    if (not editor.draft_prop_copies.has("DraftProp_38")
        or not is_equal_approx(float(
            editor.draft_brush_specs["DraftProp_38"]["outline"][0][0]), float(redone_outline[0][0]))
        or not is_equal_approx(float(
            editor.draft_brush_specs["DraftProp_38"]["outline"][2][0]),0.75)):
        _fail("Invalid polygon draft destroyed live edited geometry")
        return
    # Invalid material metadata is also rejected before the live draft is cleared.
    var malicious_style: Dictionary = doc.duplicate(true)
    malicious_style["copies"][0]["brush"]["surface_style"]["top"]["uv_offset"] = [0.0, 1000.0]
    external = FileAccess.open(path, FileAccess.WRITE)
    external.store_string(JSON.stringify(malicious_style))
    external.close()
    editor._load_prop_draft()
    if (not editor.draft_prop_copies.has("DraftProp_38")
        or editor.draft_brush_specs["DraftProp_38"]["surface_style"]["top"]["preset"] != "Metal"
        or not is_equal_approx(float(
            editor.draft_brush_specs["DraftProp_38"]["surface_style"]["top"]["uv_scale"][0]), 2.0)):
        _fail("Invalid private surface UV metadata destroyed the current valid preview")
        return
    # Exercise the real Inspector controls and actual private save/reopen.
    if (editor.polygon_clip_axis_selector == null
        or editor.polygon_clip_position == null
        or editor.polygon_clip_keep_selector == null
        or editor.polygon_clip_button == null
        or not editor.polygon_inspector_panel.visible):
        _fail("Actual T3Ed-inspired Polygon Clip Inspector controls are absent")
        return
    var before_clip: Array = editor.draft_brush_specs["DraftProp_38"]["outline"].duplicate(true)
    var history_before_clip := editor.undo_stack.size()
    editor.polygon_clip_axis_selector.select(0)
    editor.polygon_clip_position.value = 0.0
    editor.polygon_clip_keep_selector.select(0)
    editor._clip_selected_polygon_footprint()
    var clipped: Array = editor.draft_brush_specs["DraftProp_38"]["outline"].duplicate(true)
    var clipped_mesh: Mesh = editor.draft_prop_copies["DraftProp_38"].mesh
    if (clipped == before_clip or clipped.is_empty()
        or editor.undo_stack.size() != history_before_clip + 1
        or clipped_mesh == null or clipped_mesh.get_surface_count() != 3
        or Polygon.validate_outline(clipped).is_empty()
        or editor.draft_brush_specs["DraftProp_38"]["surface_style"]["top"]["preset"] != "Metal"):
        _fail("Real private Polygon Clip did not create one undoable three-surface draft")
        return
    for point in clipped:
        if float(point[0]) > 0.00001:
            _fail("Edited draft footprint escaped the selected local half-plane")
            return
    editor._undo_edit()
    if editor.draft_brush_specs["DraftProp_38"]["outline"] != before_clip:
        _fail("Undo did not restore the exact preclip private Polygon outline")
        return
    editor._redo_edit()
    if editor.draft_brush_specs["DraftProp_38"]["outline"] != clipped:
        _fail("Redo did not reinstate the clipped private Polygon outline")
        return
    var refused_history := editor.undo_stack.size()
    editor.polygon_clip_position.value = 1.0
    editor._clip_selected_polygon_footprint()
    if (editor.undo_stack.size() != refused_history
        or editor.draft_brush_specs["DraftProp_38"]["outline"] != clipped):
        _fail("A no-op clip corrupted current draft or added Undo history")
        return
    editor._save_prop_draft()
    var clipped_doc: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
    if (typeof(clipped_doc) != TYPE_DICTIONARY
        or clipped_doc["copies"].size() != 1
        or clipped_doc["copies"][0]["brush"]["outline"] != clipped):
        _fail("Clipped local footprint did not persist in private project JSON")
        return
    editor._set_brush_spec("DraftProp_38", Brush.default_spec("Polygon"))
    editor._load_prop_draft()
    if (not editor.draft_prop_copies.has("DraftProp_38")
        or editor.draft_brush_specs["DraftProp_38"]["outline"] != clipped
        or editor.draft_brush_specs["DraftProp_38"]["surface_style"]["top"]["preset"] != "Metal"
        or not editor.selected_meshes.has("DraftProp_38")):
        _fail("Clipped private footprint failed full editor Save/reopen")
        return
    if FileAccess.get_sha256(source) != source_hash:
        _fail("Invented original source bytes were modified")
        return
    for suffix in ["",".bak",".pending"]:
        if FileAccess.file_exists(path+suffix):
            DirAccess.remove_absolute(path+suffix)
    DirAccess.remove_absolute(source)
    editor.queue_free()
    print("DX2Ed v0.78 private Polygon Clip, Undo/Redo, material, Godot mesh and Save/reopen PASS")
    quit(0)
