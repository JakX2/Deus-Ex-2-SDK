extends SceneTree
## DX2Ed v0.90: source-private Box cap-edge chamfer and real Godot UI.
const Brush = preload("res://brush_geometry.gd")
const Bevel = preload("res://private_box_cap_edge_bevel.gd")
const CapPicker = preload("res://private_box_cap_picker.gd")
const SingleClip = preload("res://private_box_clip.gd")
const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.90 private edge bevel: " + message)
    quit(1)


func _run() -> void:
    var box: Dictionary = Brush.default_spec("Box")
    var half: Dictionary = box.duplicate(true)
    half["clip_plane"] = {
        "normal": [1.0,0.0,0.0],
        "distance": 0.0, "keep_positive": false}
    var edges := Bevel.cap_boundary_edges(half, 0)
    if edges.size() != 4:
        _fail("Single private x-cut did not expose exactly four true cap edges")
        return
    var edge_index := -1
    for i in range(edges.size()):
        var edge: Dictionary = edges[i]
        if (absf(float(edge["length"]) - 2.0) > 0.0001
            or not edge["midpoint"].is_finite()):
            _fail("Cap edge was not a genuine 2m perimeter segment")
            return
        if edge["midpoint"].y > 0.95:
            edge_index = i
    if edge_index < 0:
        _fail("Could not select the source-independent top cap edge")
        return
    var bevel: Dictionary = Bevel.bevel_cap_edge(half, 0, edge_index, 0.1)
    if (bevel.is_empty() or not bevel.has("clip_planes")
        or bevel["clip_planes"].size() != 2
        or bevel["clip_planes"][0] != half["clip_plane"]):
        _fail("Bevel did not append exactly one plane preserving the old cut")
        return
    var new_plane: Dictionary = bevel["clip_planes"][1]
    var normal := Vector3(
        new_plane["normal"][0], new_plane["normal"][1],
        new_plane["normal"][2])
    if (normal.distance_to(Vector3(1.0,1.0,0.0).normalized()) > 0.0001
        or absf(float(new_plane["distance"])
            - (1.0 / sqrt(2.0) - 0.1)) > 0.0001
        or bool(new_plane["keep_positive"])):
        _fail("Bevel bisector or signed inward depth did not match top edge")
        return
    var bevel_mesh: Mesh = Brush.build_mesh(bevel)
    if bevel_mesh == null:
        _fail("Accepted chamfer did not produce a private mesh")
        return
    var triangles: PackedVector3Array = (
        bevel_mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX])
    if (not SingleClip._valid_closed_soup(triangles, 8.0)
        or CapPicker._cap_index(
            triangles[0],triangles[1],triangles[2],
            bevel["clip_planes"]) < -1):
        _fail("Accepted chamfer preview failed manifold closure")
        return
    var refused := [
        Bevel.bevel_cap_edge(box, 0, 0, 0.1),
        Bevel.bevel_cap_edge(half, -1, 0, 0.1),
        Bevel.bevel_cap_edge(half, 0, -1, 0.1),
        Bevel.bevel_cap_edge(half, 0, 8, 0.1),
        Bevel.bevel_cap_edge(half, 0, 0, 0.01),
        Bevel.bevel_cap_edge(half, 0, 0, 0.51),
        Bevel.bevel_cap_edge(half, 0, 0, INF),
    ]
    for candidate in refused:
        if not candidate.is_empty():
            _fail("Untrusted, invalid or undersized cap bevel was accepted")
            return
    if (not Bevel.cap_boundary_edges(box, 0).is_empty()
        or not Bevel.cap_boundary_edges(half, -1).is_empty()
        or not Bevel.cap_boundary_edges(half, 1).is_empty()):
        _fail("Uncut or absent cap exposed selectable boundary edges")
        return
    var eight: Dictionary = box.duplicate(true)
    var eight_planes := []
    for sx in [-1.0, 1.0]:
        for sy in [-1.0, 1.0]:
            for sz in [-1.0, 1.0]:
                eight_planes.append({
                    "normal": [sx/sqrt(3.0),sy/sqrt(3.0),sz/sqrt(3.0)],
                    "distance": 1.4, "keep_positive": false})
    eight["clip_planes"] = eight_planes
    if (Brush.validate(eight).is_empty()
        or not Bevel.bevel_cap_edge(eight, 0, 0, 0.1).is_empty()):
        _fail("Eight-plane cap accepted a ninth bevel plane")
        return
    var editor := Editor.new()
    get_root().add_child(editor)
    var draft := editor._new_draft_copy(
        "Brush::Box", "DraftProp_90", Transform3D.IDENTITY)
    if (not is_instance_valid(draft)
        or not editor._set_brush_spec("DraftProp_90", half)):
        _fail("Actual Godot editor refused invented private x-cut Box")
        return
    editor._select_mesh_only(draft)
    if (editor.box_cap_edge_selector == null
        or editor.box_cap_edge_selector.item_count != 4
        or editor.box_cap_edge_bevel_button == null
        or editor.box_cap_edge_bevel_button.disabled
        or editor.box_cap_edge_depth == null
        or not is_instance_valid(editor.box_cap_edge_highlight)
        or editor.box_cap_edge_highlight.get_parent() != draft
        or editor.all_mesh_instances.has(editor.box_cap_edge_highlight)):
        _fail("Real editor private cap edge selector/highlight was not isolated")
        return
    var before: Dictionary = editor.draft_brush_specs["DraftProp_90"].duplicate(true)
    var history := editor.undo_stack.size()
    editor.box_cap_edge_selector.select(edge_index)
    editor._refresh_private_box_edge_highlight()
    editor.box_cap_edge_depth.value = 0.1
    editor.box_cap_edge_bevel_button.pressed.emit()
    var after: Dictionary = editor.draft_brush_specs["DraftProp_90"].duplicate(true)
    if (editor.undo_stack.size() != history + 1
        or after != bevel
        or editor.box_clip_plane_selector.selected != 1
        or editor.draft_prop_copies["DraftProp_90"].mesh == null):
        _fail("Real Inspector Bevel edge did not append validated plane in one Undo")
        return
    editor._undo_edit()
    if editor.draft_brush_specs["DraftProp_90"] != before:
        _fail("Private cap bevel Undo failed to restore original clipped Box")
        return
    editor._redo_edit()
    if editor.draft_brush_specs["DraftProp_90"] != after:
        _fail("Private cap bevel Redo failed to restore new cutting plane")
        return
    # Once the active selection is an imported actor, all private controls
    # and the temporary highlighted edge must be gone.
    var source := MeshInstance3D.new()
    source.name = "StaticMeshActor__90"
    source.mesh = BoxMesh.new()
    editor.world_root.add_child(source)
    editor.meshes_by_actor[str(source.name)] = source
    editor.actors_by_name[str(source.name)] = {
        "name": str(source.name), "class": "StaticMeshActor", "export": 90,
        "location": [0,0,0], "rotation": [0,0,0], "game_properties": []}
    editor._select_mesh_only(source)
    if (editor.private_box_clip_panel.visible
        or is_instance_valid(editor.box_cap_edge_highlight)
        or not editor._selected_private_box_name().is_empty()):
        _fail("Original game actor acquired editable private cap edge controls")
        return
    editor.queue_free()
    print("DX2Ed v0.90 private capped Box edge chamfer and Inspector Undo/Redo PASS")
    quit(0)
