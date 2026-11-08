extends SceneTree
## DX2Ed v0.38 custom polygon extrusion and real-editor authoring smoke.
## Uses invented assets and an isolated user:// draft. No retail DX2 GMP.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")
const Polygon = preload("res://custom_polygon_geometry.gd")
const Guides = preload("res://orthographic_authoring_guides.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.38 custom polygon geometry: " + message)
    quit(1)


func _run() -> void:
    var spec := Brush.default_spec("Polygon")
    if (spec.is_empty() or Brush.validate(spec).is_empty()
        or spec["outline"].size() != 6):
        _fail("Polygon brush missing from validated palette")
        return
    var mesh := Brush.build_mesh(spec)
    if (mesh == null or mesh.get_surface_count() != 1
        or mesh.surface_get_array_len(0) != 60):
        _fail("L-shaped concave 6-corner polygon did not create a closed mesh")
        return
    var points: PackedVector3Array = mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    var bounds := AABB(Vector3(-2.0,-1.0,-2.0), Vector3(4.0,2.0,4.0))
    for point in points:
        if not bounds.has_point(point):
            _fail("Polygon extruded outside configured X/Y/Z dimensions")
            return
    var mirrored: Dictionary = spec.duplicate(true)
    mirrored["outline"].reverse()
    var reverse_mesh := Brush.build_mesh(mirrored)
    if reverse_mesh == null or reverse_mesh.surface_get_array_len(0) != 60:
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
    if not Polygon.with_moved_vertex(spec["outline"],2,0,0.75).size() == 6:
        _fail("Vertex editing failed for concave polygon")
        return
    if (not Polygon.with_moved_vertex(spec["outline"],2,0,4.0).is_empty()
        or not Polygon.with_inserted_vertex(spec["outline"],-1).is_empty()
        or not Polygon.with_deleted_vertex(spec["outline"],10).is_empty()):
        _fail("Custom polygon dimension/index safeguards failed")
        return

    var editor := Editor.new()
    get_root().add_child(editor)
    var source := ProjectSettings.globalize_path("user://v038_owner_invented_source.gmp")
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
        "user://v038_private_custom_polygon_cache")
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
            editor.draft_brush_specs["DraftProp_38"]["outline"][2][0]),0.75)
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
            editor.draft_brush_specs["DraftProp_38"]["outline"][2][0]),0.75)):
        _fail("Invalid polygon draft destroyed live edited geometry")
        return
    if FileAccess.get_sha256(source) != source_hash:
        _fail("Invented original source bytes were modified")
        return
    for suffix in ["",".bak",".pending"]:
        if FileAccess.file_exists(path+suffix):
            DirAccess.remove_absolute(path+suffix)
    DirAccess.remove_absolute(source)
    editor.queue_free()
    print("DX2Ed v0.38 custom polygon/concave geometry real Godot authoring PASS")
    quit(0)
