extends SceneTree
## DX2Ed v0.91: strictly validated private three-face vertex chamfer.
## Uses invented Godot Box geometry; no licensed source files.
const Brush = preload("res://brush_geometry.gd")
const Bevel = preload("res://private_box_cap_corner_bevel.gd")
const MultiClip = preload("res://private_box_multiclip.gd")
const SingleClip = preload("res://private_box_clip.gd")
const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.91 private cap corner: " + message)
    quit(1)


func _run() -> void:
    var box: Dictionary = Brush.default_spec("Box")
    var half: Dictionary = box.duplicate(true)
    half["clip_plane"] = {
        "normal": [1.0,0.0,0.0], "distance": 0.0,
        "keep_positive": false}
    var corners: Array = Bevel.cap_corner_vertices(half, 0)
    if corners.size() != 4:
        _fail("Simple x=0 clipped Box did not expose four real 3-face corners")
        return
    var wanted := -1
    for i in range(corners.size()):
        var corner: Dictionary = corners[i]
        var point: Vector3 = corner["point"]
        if absf(point.x) > 0.0001 or absf(point.y) > 1.0001 or absf(point.z) > 1.0001:
            _fail("Selected private corner escaped source-independent Box cap")
            return
        var cap: Vector3 = corner["cap_outward"]
        var one: Vector3 = corner["adjacent_a"]
        var two: Vector3 = corner["adjacent_b"]
        if (cap.distance_to(Vector3.RIGHT) > 0.0001
            or absf(cap.dot(one.cross(two))) < 0.99):
            _fail("Three incident outward faces were not genuine trihedral")
            return
        if point.y > 0.95 and point.z > 0.95:
            wanted = i
    if wanted == -1:
        _fail("Could not locate upper-front private cap corner")
        return
    var cut: Dictionary = Bevel.bevel_cap_corner(half, 0, wanted, 0.1)
    if (cut.is_empty() or not cut.has("clip_planes")
        or cut["clip_planes"].size() != 2
        or cut["clip_planes"][0] != half["clip_plane"]):
        _fail("Selected corner failed to append one validated cut")
        return
    var added: Dictionary = cut["clip_planes"][1]
    var added_normal := Vector3(
        added["normal"][0], added["normal"][1], added["normal"][2])
    var expected := Vector3(1.0, 1.0, 1.0).normalized()
    var expected_distance := 2.0 / sqrt(3.0) - 0.1
    if (added_normal.distance_to(expected) > 0.0001
        or absf(float(added["distance"]) - expected_distance) > 0.0001
        or bool(added["keep_positive"])):
        _fail("Corner cut was not the inward trihedral bisector")
        return
    var mesh: Mesh = Brush.build_mesh(cut)
    if mesh == null:
        _fail("Valid trihedral corner cut had no Godot mesh")
        return
    var vertices: PackedVector3Array = (
        mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX])
    var volume := MultiClip._signed_volume(vertices)
    var lost_edge := 0.1 * sqrt(3.0)
    var expected_volume := 4.0 - pow(lost_edge, 3.0) / 6.0
    if (not SingleClip._valid_closed_soup(vertices, 8.0)
        or absf(volume - expected_volume) > 0.001):
        _fail("Trihedral corner clipping was not manifold or conserved volume")
        return
    var invalid: Array = [
        Bevel.bevel_cap_corner(box, 0, 0, 0.1),
        Bevel.bevel_cap_corner(half, -1, 0, 0.1),
        Bevel.bevel_cap_corner(half, 1, 0, 0.1),
        Bevel.bevel_cap_corner(half, 0, -1, 0.1),
        Bevel.bevel_cap_corner(half, 0, 99, 0.1),
        Bevel.bevel_cap_corner(half, 0, wanted, 0.01),
        Bevel.bevel_cap_corner(half, 0, wanted, 0.41),
        Bevel.bevel_cap_corner(half, 0, wanted, INF),
    ]
    for candidate in invalid:
        if not candidate.is_empty():
            _fail("Nonexistent corner or invalid bevel depth was accepted")
            return
    if (not Bevel.cap_corner_vertices(box, 0).is_empty()
        or not Bevel.cap_corner_vertices(half, 1).is_empty()
        or not Bevel.cap_corner_vertices(half, -1).is_empty()):
        _fail("Uncut or absent cap exposed selectable three-face corners")
        return
    var eight: Dictionary = box.duplicate(true)
    var eight_planes: Array = []
    for sx in [-1.0, 1.0]:
        for sy in [-1.0, 1.0]:
            for sz in [-1.0, 1.0]:
                eight_planes.append({
                    "normal": [sx/sqrt(3.0),sy/sqrt(3.0),sz/sqrt(3.0)],
                    "distance": 1.4, "keep_positive": false})
    eight["clip_planes"] = eight_planes
    if (Brush.validate(eight).is_empty()
        or not Bevel.bevel_cap_corner(eight, 0, 0, 0.1).is_empty()):
        _fail("A ninth private plane was accepted by corner bevel")
        return

    var editor := Editor.new()
    get_root().add_child(editor)
    var draft := editor._new_draft_copy(
        "Brush::Box", "DraftProp_91", Transform3D.IDENTITY)
    if (not is_instance_valid(draft)
        or not editor._set_brush_spec("DraftProp_91", half)):
        _fail("Actual Godot editor refused invented private clipped Box")
        return
    editor._select_mesh_only(draft)
    if (editor.box_cap_corner_selector == null
        or editor.box_cap_corner_selector.item_count != 4
        or editor.box_cap_corner_selector.disabled
        or editor.box_cap_corner_bevel_button == null
        or editor.box_cap_corner_bevel_button.disabled
        or editor.box_cap_corner_depth == null
        or not is_instance_valid(editor.box_cap_corner_highlight)
        or editor.box_cap_corner_highlight.get_parent() != draft
        or editor.all_mesh_instances.has(editor.box_cap_corner_highlight)):
        _fail("Real Godot corner selector or private highlight was not isolated")
        return
    editor.box_cap_corner_selector.select(wanted)
    editor._refresh_private_box_corner_highlight()
    var marker: MeshInstance3D = editor.box_cap_corner_highlight
    if (not is_instance_valid(marker)
        or not marker.has_meta("editor_only")
        or marker.position.distance_to(
            (corners[wanted]["point"] as Vector3)
            + Vector3.RIGHT * 0.025) > 0.0001):
        _fail("Selected private corner magenta marker was misplaced")
        return
    var before: Dictionary = (
        editor.draft_brush_specs["DraftProp_91"].duplicate(true))
    var history := editor.undo_stack.size()
    editor.box_cap_corner_depth.value = 0.10
    editor.box_cap_corner_bevel_button.pressed.emit()
    var after: Dictionary = (
        editor.draft_brush_specs["DraftProp_91"].duplicate(true))
    if (editor.undo_stack.size() != history + 1
        or not after.has("clip_planes")
        or after["clip_planes"].size() != 2
        or after["clip_planes"][0] != half["clip_plane"]
        or editor.box_clip_plane_selector.selected != 1
        or editor.draft_prop_copies["DraftProp_91"].mesh == null):
        _fail("Inspector corner bevel did not append a second private plane "
            + "or record exactly one Undo: " + editor.status_label.text)
        return
    # Validated Godot normals are renormalized during _set_brush_spec:
    # a few float32 ULPs of difference are not a changed halfspace.
    var ui_plane: Dictionary = after["clip_planes"][1]
    var generated_plane: Dictionary = cut["clip_planes"][1]
    var ui_normal := Vector3(
        ui_plane["normal"][0], ui_plane["normal"][1], ui_plane["normal"][2])
    var generated_normal := Vector3(
        generated_plane["normal"][0],
        generated_plane["normal"][1], generated_plane["normal"][2])
    if (ui_normal.distance_to(generated_normal) > 0.00001
        or absf(float(ui_plane["distance"])
            - float(generated_plane["distance"])) > 0.00001
        or bool(ui_plane["keep_positive"]) !=
            bool(generated_plane["keep_positive"])):
        _fail("Inspector corner bevel changed the validated halfspace")
        return
    editor._undo_edit()
    if editor.draft_brush_specs["DraftProp_91"] != before:
        _fail("Corner bevel Undo lost the original private Box cut")
        return
    editor._redo_edit()
    var redone: Dictionary = editor.draft_brush_specs["DraftProp_91"]
    if (not redone.has("clip_planes") or redone["clip_planes"].size() != 2
        or redone["clip_planes"][0] != before["clip_plane"]):
        _fail("Corner bevel Redo lost the original or new clipping plane")
        return
    var redo_plane: Dictionary = redone["clip_planes"][1]
    var redo_normal := Vector3(
        redo_plane["normal"][0], redo_plane["normal"][1],
        redo_plane["normal"][2])
    if (redo_normal.distance_to(ui_normal) > 0.00001
        or absf(float(redo_plane["distance"])
            - float(ui_plane["distance"])) > 0.00001):
        _fail("Corner bevel Redo did not restore the accepted halfspace")
        return
    draft = editor.draft_prop_copies["DraftProp_91"]
    if (not is_instance_valid(draft)
        or not editor._set_brush_spec("DraftProp_91", eight)):
        _fail("Could not place an eight-plane private Box in Godot")
        return
    editor._select_mesh_only(draft)
    if not editor.box_cap_corner_bevel_button.disabled:
        _fail("Private corner Bevel button not disabled at eight-cut limit")
        return
    # Switching to an original imported actor must remove all private
    # corner controls and highlight, never mutate game geometry.
    var original := MeshInstance3D.new()
    original.name = "StaticMeshActor__91"
    original.mesh = BoxMesh.new()
    editor.world_root.add_child(original)
    editor.meshes_by_actor[str(original.name)] = original
    editor.actors_by_name[str(original.name)] = {
        "name": str(original.name), "class": "StaticMeshActor", "export": 91,
        "location": [0,0,0], "rotation": [0,0,0], "game_properties": []}
    editor._select_mesh_only(original)
    if (editor.private_box_clip_panel.visible
        or is_instance_valid(editor.box_cap_corner_highlight)
        or not editor._selected_private_box_name().is_empty()):
        _fail("Imported original actor exposed source-private corner editing")
        return
    editor.queue_free()
    print("DX2Ed v0.91 private 3-face corner bevel, closed mesh and Inspector Undo PASS")
    quit(0)
