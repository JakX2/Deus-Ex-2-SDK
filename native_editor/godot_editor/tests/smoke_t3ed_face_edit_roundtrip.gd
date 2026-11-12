extends SceneTree
## DX2Ed v0.35: actual Godot editor T3Ed-style box/face authoring smoke.
## Invented source mesh and private draft only. NO original GMP, native CSG
## brushes, portal/BSP, collision or gameplay package writes.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")
const PrivateBoxClip = preload("res://private_box_clip.gd")
const MultiClip = preload("res://private_box_multiclip.gd")
const Guides = preload("res://orthographic_authoring_guides.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.35 draft face authoring: " + message)
    quit(1)


func _run() -> void:
    var box := Brush.default_spec("Box")
    var enlarged := Brush.face_resize(box, 1, 0.5)
    var shrunk := Brush.face_resize(box, 1, -0.5)
    var left := Brush.face_resize(box, 0, 0.5)
    if (enlarged.is_empty() or shrunk.is_empty() or left.is_empty()
        or not is_equal_approx(float(enlarged["spec"]["size"][0]), 2.5)
        or not is_equal_approx(float(shrunk["spec"]["size"][0]), 1.5)
        or not enlarged["center_offset_local"].is_equal_approx(Vector3(0.25, 0, 0))
        or not shrunk["center_offset_local"].is_equal_approx(Vector3(-0.25, 0, 0))
        or not left["center_offset_local"].is_equal_approx(Vector3(-0.25, 0, 0))):
        _fail("Pure face math failed to anchor the opposite local face")
        return
    for invalid in [
        Brush.face_resize(Brush.default_spec("Ramp"), 1, 0.5),
        Brush.face_resize(Brush.default_spec("Stairs"), 1, 0.5),
        Brush.face_resize(box, -1, 0.5),
        Brush.face_resize(box, 6, 0.5),
        Brush.face_resize(box, 1, INF),
        Brush.face_resize(box, 1, 0.0),
        Brush.face_resize(box, 1, -1.99),
        Brush.face_resize(box, 1, 255.0),
        Brush.face_resize({"kind":"Box", "size":[2,2,INF], "steps":1}, 1, 0.5),
    ]:
        if not invalid.is_empty():
            _fail("Invalid native or unbounded draft face operation accepted")
            return

    # v0.80: genuine 3D half-space caps on source-isolated draft boxes,
    # with a geometric manifold and signed-volume check. No DX2 CSG.
    var cube := Brush.default_spec("Box")
    var axis_cut: Dictionary = cube.duplicate(true)
    axis_cut["clip_plane"] = {
        "normal": [1.0, 0.0, 0.0], "distance": 0.0,
        "keep_positive": false}
    var half_mesh: ArrayMesh = Brush.build_mesh(axis_cut)
    if (Brush.validate(axis_cut).is_empty() or half_mesh == null
        or half_mesh.get_surface_count() != 1):
        _fail("Private 3D Box half-plane did not build capped convex mesh")
        return
    var half_points: PackedVector3Array = half_mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    if not PrivateBoxClip._valid_closed_soup(half_points, 8.0):
        _fail("Private Box 3D half-mesh is not closed and outward oriented")
        return
    var half_volume := 0.0
    for i in range(0, half_points.size(), 3):
        half_volume += half_points[i].dot(
            half_points[i+1].cross(half_points[i+2])) / 6.0
    if not is_equal_approx(half_volume, 4.0):
        _fail("Source-only 3D half-box has the wrong enclosed volume")
        return
    var opposite: Dictionary = axis_cut.duplicate(true)
    opposite["clip_plane"]["keep_positive"] = true
    var other_mesh: ArrayMesh = Brush.build_mesh(opposite)
    if other_mesh == null:
        _fail("Opposite 3D Box clip side refused valid half cube")
        return
    var diagonal: Dictionary = axis_cut.duplicate(true)
    var inv_root3 := 1.0/sqrt(3.0)
    diagonal["clip_plane"]["normal"] = [inv_root3, inv_root3, inv_root3]
    var diagonal_mesh: ArrayMesh = Brush.build_mesh(diagonal)
    if diagonal_mesh == null:
        _fail("3D diagonal plane could not cap a convex hexagonal cut")
        return
    var diagonal_points: PackedVector3Array = (
        diagonal_mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX])
    if not PrivateBoxClip._valid_closed_soup(diagonal_points, 8.0):
        _fail("Oblique 3D Box cap is not closed and consistently oriented")
        return
    var diag_volume := 0.0
    for i in range(0, diagonal_points.size(), 3):
        diag_volume += diagonal_points[i].dot(
            diagonal_points[i+1].cross(diagonal_points[i+2])) / 6.0
    if absf(diag_volume-4.0) > 0.0005:
        _fail("Oblique center plane does not split symmetric cube volume")
        return
    for invalid_clip in [
        {"normal":[2,0,0], "distance":0.0, "keep_positive":false},
        {"normal":[1,0,0], "distance":1.0, "keep_positive":false},
        {"normal":[1,0,0], "distance":0.99, "keep_positive":false},
        {"normal":[1,0,0], "distance":0.0, "keep_positive":1},
        {"normal":[INF,0,0], "distance":0.0, "keep_positive":false},
        {"normal":[1,0,0], "distance":NAN, "keep_positive":false},
        {"normal":[1,0,0], "distance":257.0, "keep_positive":false},
        {"normal":[1,0], "distance":0.0, "keep_positive":false},
    ]:
        var bad: Dictionary = cube.duplicate(true)
        bad["clip_plane"] = invalid_clip
        if not Brush.validate(bad).is_empty() or Brush.build_mesh(bad) != null:
            _fail("Invalid, tangent, nonunit or nonfinite 3D plane accepted")
            return
    var other_kind := Brush.default_spec("Floor")
    other_kind["clip_plane"] = axis_cut["clip_plane"]
    if not Brush.validate(other_kind).is_empty():
        _fail("Untrusted private clip attached to non-Box brush kind")
        return
    if (not Brush.face_resize(axis_cut, 0, 0.5).is_empty()
        or not Brush.pick_draft_face(
            axis_cut, Transform3D.IDENTITY,
            Vector3(-5,0,0), Vector3.RIGHT).is_empty()):
        _fail("Clipped 3D Box still allowed misleading original cuboid face edit")
        return

    # v0.81: source-independent sequential convex Box clipping, not game
    # CSG. Three orthogonal cuts yield exactly one original octant.
    var planes := [
        {"normal":[1.0,0.0,0.0], "distance":0.0, "keep_positive":false},
        {"normal":[0.0,1.0,0.0], "distance":0.0, "keep_positive":false},
        {"normal":[0.0,0.0,1.0], "distance":0.0, "keep_positive":false},
    ]
    var source_size := Vector3(2,2,2)
    var expected_volumes := [4.0,2.0,1.0]
    for count in range(1,4):
        var current := planes.slice(0,count)
        var checked: Array = MultiClip.validate_planes(current,source_size)
        var multi_spec: Dictionary = cube.duplicate(true)
        multi_spec["clip_planes"] = current
        var generated: ArrayMesh = Brush.build_mesh(multi_spec)
        if (checked.size() != count or Brush.validate(multi_spec).is_empty()
            or generated == null or generated.get_surface_count() != 1):
            _fail("v0.81 sequential convex Box clip refused a valid orthogonal cut")
            return
        var vertices: PackedVector3Array = generated.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
        if not PrivateBoxClip._valid_closed_soup(vertices,8.0):
            _fail("v0.81 sequential Box cut generated an open triangle soup")
            return
        var volume := MultiClip._signed_volume(vertices)
        if absf(volume-float(expected_volumes[count-1])) > 0.0005:
            _fail("v0.81 sequential orthogonal cuts lost enclosed-volume conservation")
            return
        for point in vertices:
            if (count >= 1 and point.x > 0.0001
                or count >= 2 and point.y > 0.0001
                or count >= 3 and point.z > 0.0001):
                _fail("v0.81 convex clipping retained source point beyond halfspace")
                return
    var fourth: Dictionary = {
        "normal":[sqrt(0.5),0.0,sqrt(0.5)],
        "distance":-0.8, "keep_positive":false}
    var four_planes: Array = planes.duplicate(true)
    four_planes.append(fourth)
    var four_spec: Dictionary = cube.duplicate(true)
    four_spec["clip_planes"] = four_planes
    var four_mesh: ArrayMesh = Brush.build_mesh(four_spec)
    if four_mesh == null or four_mesh.get_surface_count() != 1:
        _fail("v0.81 fourth angled clipping plane refused valid convex Box")
        return
    var four_vertices: PackedVector3Array = four_mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    var four_volume := MultiClip._signed_volume(four_vertices)
    if (not PrivateBoxClip._valid_closed_soup(four_vertices,8.0)
        or four_volume <= 0.0 or four_volume >= 1.0):
        _fail("v0.81 fourth oblique plane did not generate a closed reduced volume")
        return
    var invalid_multi := cube.duplicate(true)
    invalid_multi["clip_planes"] = []
    if not Brush.validate(invalid_multi).is_empty():
        _fail("Empty private 3D clip stack passed source-only validation")
        return
    invalid_multi["clip_planes"] = four_planes + [fourth]
    if not Brush.validate(invalid_multi).is_empty():
        _fail("Unbounded fifth private 3D plane passed source-only validation")
        return
    invalid_multi["clip_planes"] = four_planes
    invalid_multi["clip_plane"] = planes[0]
    if not Brush.validate(invalid_multi).is_empty():
        _fail("Ambiguous single and multi 3D plane keys passed validation")
        return
    invalid_multi = Brush.default_spec("Floor")
    invalid_multi["clip_planes"] = planes
    if not Brush.validate(invalid_multi).is_empty():
        _fail("Private 3D multi-plane metadata accepted on non-Box kind")
        return
    invalid_multi = cube.duplicate(true)
    invalid_multi["clip_planes"] = [planes[0],planes[0]]
    if Brush.build_mesh(invalid_multi) != null:
        _fail("Geometrically redundant second plane did not fail closed")
        return
    invalid_multi = cube.duplicate(true)
    invalid_multi["clip_planes"] = [planes[0],
        {"normal":[-1.0,0.0,0.0], "distance":0.01, "keep_positive":false}]
    if Brush.build_mesh(invalid_multi) != null:
        _fail("Near-empty overlapping private 3D cut stack did not fail closed")
        return

    var editor := Editor.new()
    get_root().add_child(editor)
    if (editor.brush_face_controls == null
        or editor.brush_face_selector == null
        or editor.brush_face_selector.item_count != 6
        or editor.brush_face_outward_button == null
        or editor.brush_face_inward_button == null):
        _fail("Actual editor does not expose six-face In/Out brush inspector")
        return

    # The real authoring project has a decoded/rendered source mesh and a
    # separate editor-only brush copy. Source file is wholly invented.
    var original_file := ProjectSettings.globalize_path(
        "user://v035_invented_read_only_source.gmp")
    var payload := PackedByteArray([68, 88, 50, 69, 100, 103, 101, 53])
    var fake_file := FileAccess.open(original_file, FileAccess.WRITE)
    if fake_file == null:
        _fail("Synthetic source file not available")
        return
    fake_file.store_buffer(payload)
    fake_file.close()
    var source_sha := FileAccess.get_sha256(original_file)

    var fake_scene := Node3D.new()
    fake_scene.name = "InventedImportedScene"
    editor.world_root.add_child(fake_scene)
    editor.scene_root = fake_scene
    editor.current_folder = ProjectSettings.globalize_path(
        "user://v035_private_fully_synthetic_map_cache")

    var original := MeshInstance3D.new()
    original.name = "StaticMeshActor__901"
    original.mesh = BoxMesh.new()
    fake_scene.add_child(original)
    original.global_position = Vector3(-3.0, 0.0, 2.0)
    var original_identity := str(original.name)
    editor.meshes_by_actor[original_identity] = original
    editor.actors_by_name[original_identity] = {
        "name": original_identity, "class": "StaticMeshActor",
        "export": 901, "location": [0, 0, 0],
        "rotation": [0, 0, 0], "game_properties": []}
    editor.original_mesh_transforms[original_identity] = original.global_transform
    editor.all_mesh_instances.append(original)

    var world := Transform3D(
        Basis(Vector3.UP, PI / 2.0),
        Vector3(3.0, 0.0, 5.0))
    var draft := editor._new_draft_copy("Brush::Box", "DraftProp_1", world)
    if not is_instance_valid(draft):
        _fail("Could not construct original DX2Ed draft box")
        return
    editor.next_prop_copy_id = 2
    editor._select_mesh_only(draft)
    if not editor.brush_face_controls.visible:
        _fail("Draft Box face controls hidden from actual inspector")
        return
    editor._grid_spacing_changed(0.5)
    editor.brush_face_selector.select(1) # Local +X face.
    var opposite_before := draft.global_position - draft.global_basis.x
    editor._change_brush_face(1.0)
    if (editor.undo_stack.size() != 1
        or not is_equal_approx(float(editor.draft_brush_specs["DraftProp_1"]["size"][0]), 2.5)):
        _fail("Real editor did not resize draft brush and record Undo")
        return
    draft = editor.draft_prop_copies["DraftProp_1"]
    var opposite_after := draft.global_position - draft.global_basis.x * 1.25
    if not opposite_before.is_equal_approx(opposite_after):
        _fail("Face drag moved opposite plane on a rotated draft brush")
        return

    editor._undo_edit()
    if (not editor.draft_prop_copies.has("DraftProp_1")
        or float(editor.draft_brush_specs["DraftProp_1"]["size"][0]) != 2.0):
        _fail("Face resize Undo did not recover original Box geometry")
        return
    editor._redo_edit()
    if (not editor.draft_prop_copies.has("DraftProp_1")
        or not is_equal_approx(float(editor.draft_brush_specs["DraftProp_1"]["size"][0]), 2.5)):
        _fail("Face resize Redo did not reapply draft geometry")
        return

    # Make the actual authored project more than a single brush: retain a
    # moved imported actor preview, a rotated resized brush, and the ortho UI.
    editor._select_mesh_only(original)
    editor._move_selected_prop(Vector3.UP)
    if not original.global_position.is_equal_approx(Vector3(-3, 0.5, 2)):
        _fail("Original actor preview move cannot join brush project")
        return
    editor._set_editor_view_mode(Guides.SIDE)
    editor._grid_spacing_changed(0.5)
    editor._toggle_ortho_grid(false)
    # Multi-selection should survive the real private draft Save/Load,
    # including a source preview and editor-only face-resized brush.
    editor._toggle_selection_mesh(editor.draft_prop_copies["DraftProp_1"])
    if editor.selected_meshes.size() != 2:
        _fail("Combined original actor/draft multi-selection unavailable")
        return
    var draft_path := editor._draft_file_path()
    if draft_path.is_empty():
        _fail("Private draft output path unavailable")
        return
    for suffix in ["", ".pending", ".bak"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    editor._save_prop_draft()
    if not FileAccess.file_exists(draft_path):
        _fail("Real editor Save draft did not produce private JSON")
        return
    var saved: Variant = JSON.parse_string(FileAccess.get_file_as_string(draft_path))
    if (typeof(saved) != TYPE_DICTIONARY
        or saved.get("schema") != "DX2Ed-prop-draft-v1"
        or saved["moved"].size() != 1 or saved["copies"].size() != 1
        or saved["copies"][0]["from_actor"] != "Brush::Box"
        or float(saved["copies"][0]["brush"]["size"][0]) != 2.5
        or saved["workspace"]["view_mode"] != Guides.SIDE
        or saved["workspace"]["grid_enabled"] != false
        or saved["selection"].size() != 2
        or not saved["selection"].has(original_identity)
        or not saved["selection"].has("DraftProp_1")):
        _fail("Saved project lost native-source previews, brush dimensions or view")
        return

    # Change all three independently, then reopen using the REAL loader.
    original.global_position = Vector3(90, 90, 90)
    editor._set_brush_spec("DraftProp_1", Brush.default_spec("Box"))
    editor._set_editor_view_mode(Guides.PERSPECTIVE)
    editor._toggle_ortho_grid(true)
    editor._load_prop_draft()
    if (not original.global_position.is_equal_approx(Vector3(-3, 0.5, 2))
        or not editor.draft_prop_copies.has("DraftProp_1")
        or not is_equal_approx(float(editor.draft_brush_specs["DraftProp_1"]["size"][0]), 2.5)
        or editor.editor_view_mode != Guides.SIDE
        or editor.ortho_grid_enabled
        or not is_equal_approx(editor.ortho_grid_step, 0.5)
        or editor.selected_meshes.size() != 2
        or not editor.selected_meshes.has(original_identity)
        or not editor.selected_meshes.has("DraftProp_1")):
        _fail("Real editor project reopen failed to reconstruct full authored state")
        return
    var reloaded: MeshInstance3D = editor.draft_prop_copies["DraftProp_1"]
    if not (reloaded.global_position - reloaded.global_basis.x * 1.25
            ).is_equal_approx(opposite_before):
        _fail("Reopened resized brush shifted its original opposite face")
        return
    # Use the actual Inspector, private draft state, history and project
    # reload. Original scene preview actor and retail-style source file stay
    # separate from the editor-only capped mesh.
    editor._select_mesh_only(editor.draft_prop_copies["DraftProp_1"])
    if (editor.private_box_clip_panel == null
        or not editor.private_box_clip_panel.visible
        or editor.box_clip_yaw == null or editor.box_clip_elevation == null
        or editor.box_clip_keep_side == null or editor.box_clip_distance == null
        or editor.box_clip_reset_button == null):
        _fail("Real Godot Box Inspector has no v0.80 private 3D clip controls")
        return
    var prior_box: Dictionary = editor.draft_brush_specs["DraftProp_1"].duplicate(true)
    var prior_history := editor.undo_stack.size()
    editor.box_clip_yaw.value = 45.0
    editor.box_clip_elevation.value = 30.0
    editor.box_clip_distance.value = 0.0
    editor.box_clip_keep_side.select(0)
    editor._apply_private_box_clip()
    var clipped_spec: Dictionary = editor.draft_brush_specs["DraftProp_1"].duplicate(true)
    var clipped_node: MeshInstance3D = editor.draft_prop_copies["DraftProp_1"]
    if (not clipped_spec.has("clip_plane")
        or editor.undo_stack.size() != prior_history + 1
        or clipped_node.mesh == null or clipped_node.mesh.get_surface_count() != 1
        or not editor.private_box_clip_panel.visible
        or editor.brush_face_controls.visible
        or not editor.box_clip_reset_button.disabled == false):
        _fail("Real Inspector Box clip did not create one capped preview and Undo step")
        return
    var clipped_points: PackedVector3Array = (
        clipped_node.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX])
    if not PrivateBoxClip._valid_closed_soup(clipped_points, 2.5*2.0*2.0):
        _fail("Actual editor-generated 3D box lacks closed manifold")
        return
    var no_op_history := editor.undo_stack.size()
    editor._apply_private_box_clip()
    if (editor.undo_stack.size() != no_op_history
        or editor.draft_brush_specs["DraftProp_1"] != clipped_spec):
        _fail("Repeating identical private 3D clipping polluted history")
        return
    editor._undo_edit()
    if editor.draft_brush_specs["DraftProp_1"] != prior_box:
        _fail("3D Box Clip undo did not reconstruct uncut private box")
        return
    editor._redo_edit()
    if not editor.draft_brush_specs["DraftProp_1"].has("clip_plane"):
        _fail("3D Box Clip redo did not regenerate capped private mesh")
        return
    editor._save_prop_draft()
    var clip_doc: Variant = JSON.parse_string(FileAccess.get_file_as_string(draft_path))
    if (typeof(clip_doc) != TYPE_DICTIONARY
        or clip_doc["copies"].size() != 1
        or not clip_doc["copies"][0]["brush"].has("clip_plane")
        or clip_doc["copies"][0]["from_actor"] != "Brush::Box"):
        _fail("3D Box Clip plane was dropped from private project document")
        return
    editor._set_brush_spec("DraftProp_1", Brush.default_spec("Box"))
    editor._load_prop_draft()
    if (not editor.draft_brush_specs.has("DraftProp_1")
        or not editor.draft_brush_specs["DraftProp_1"].has("clip_plane")
        or editor.draft_prop_copies["DraftProp_1"].mesh == null):
        _fail("Real 3D Box Clip private project reopen lost clipping plane or cap")
        return
    editor._select_mesh_only(editor.draft_prop_copies["DraftProp_1"])
    editor._reset_private_box_clip()
    if (editor.draft_brush_specs["DraftProp_1"].has("clip_plane")
        or not editor.brush_face_controls.visible):
        _fail("Reset-to-Box did not restore original six-face preview")
        return
    editor._undo_edit()
    if not editor.draft_brush_specs["DraftProp_1"].has("clip_plane"):
        _fail("Reset-to-Box Undo lost the original clipped Box")
        return
    editor._redo_edit()
    if editor.draft_brush_specs["DraftProp_1"].has("clip_plane"):
        _fail("Reset-to-Box Redo did not restore the uncut draft")
        return
    # v0.81 actual editor buttons: cumulative cuts preserve all earlier
    # planes, each append/removal is a single history transaction.
    editor._set_brush_spec("DraftProp_1", Brush.default_spec("Box"))
    editor._select_mesh_only(editor.draft_prop_copies["DraftProp_1"])
    var history_before_stack := editor.undo_stack.size()
    if (editor.box_clip_add_plane_button == null
        or editor.box_clip_remove_last_button == null
        or editor.box_clip_plane_count_label == null
        or not editor.private_box_clip_panel.visible):
        _fail("v0.81 real Box Inspector missing Add / Remove / plane count controls")
        return
    editor.box_clip_yaw.value = 0.0
    editor.box_clip_elevation.value = 0.0
    editor.box_clip_distance.value = 0.0
    editor.box_clip_keep_side.select(0)
    editor._apply_private_box_clip()
    if (editor.undo_stack.size() != history_before_stack+1
        or not editor.draft_brush_specs["DraftProp_1"].has("clip_plane")):
        _fail("v0.81 real Box Inspector failed initial single plane")
        return
    var single_before_redundant: Dictionary = editor.draft_brush_specs["DraftProp_1"].duplicate(true)
    var redundant_history := editor.undo_stack.size()
    editor._append_private_box_plane()
    if (editor.undo_stack.size() != redundant_history
        or editor.draft_brush_specs["DraftProp_1"] != single_before_redundant):
        _fail("v0.81 redundant added plane mutated history or draft")
        return
    editor.box_clip_yaw.value = 0.0
    editor.box_clip_elevation.value = 90.0
    editor.box_clip_distance.value = 0.0
    editor._append_private_box_plane()
    if (editor.undo_stack.size() != history_before_stack+2
        or not editor.draft_brush_specs["DraftProp_1"].has("clip_planes")
        or editor.draft_brush_specs["DraftProp_1"]["clip_planes"].size() != 2):
        _fail("v0.81 first cumulative plane was not preserved")
        return
    editor.box_clip_yaw.value = 90.0
    editor.box_clip_elevation.value = 0.0
    editor._append_private_box_plane()
    if (editor.undo_stack.size() != history_before_stack+3
        or editor.draft_brush_specs["DraftProp_1"]["clip_planes"].size() != 3):
        _fail("v0.81 third private cutting plane did not commit")
        return
    editor.box_clip_yaw.value = 45.0
    editor.box_clip_elevation.value = 0.0
    editor.box_clip_distance.value = -0.8
    editor._append_private_box_plane()
    var final_stack: Dictionary = editor.draft_brush_specs["DraftProp_1"].duplicate(true)
    if (not final_stack.has("clip_planes")
        or final_stack["clip_planes"].size() != 4
        or editor.undo_stack.size() != history_before_stack+4
        or editor.box_clip_plane_count_label.text != "Planes: 4 / 4"
        or not editor.box_clip_add_plane_button.disabled):
        _fail("v0.81 fourth capped plane or Inspector limit failed")
        return
    var final_mesh: Mesh = editor.draft_prop_copies["DraftProp_1"].mesh
    if final_mesh == null or final_mesh.get_surface_count() != 1:
        _fail("v0.81 four-plane clipped preview mesh is absent")
        return
    var final_vertices: PackedVector3Array = final_mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    if (not PrivateBoxClip._valid_closed_soup(final_vertices, 8.0)
        or MultiClip._signed_volume(final_vertices) >= 1.0):
        _fail("v0.81 real Godot four-plane clip did not create closed reduced convex solid")
        return
    editor._save_prop_draft()
    var stacked_doc: Variant = JSON.parse_string(
        FileAccess.get_file_as_string(draft_path))
    if (typeof(stacked_doc) != TYPE_DICTIONARY
        or not stacked_doc["copies"][0]["brush"].has("clip_planes")
        or stacked_doc["copies"][0]["brush"]["clip_planes"].size() != 4):
        _fail("v0.81 private JSON save lost four original local clipping planes")
        return
    editor._set_brush_spec("DraftProp_1", Brush.default_spec("Box"))
    editor._load_prop_draft()
    editor._select_mesh_only(editor.draft_prop_copies["DraftProp_1"])
    if (not editor.draft_brush_specs["DraftProp_1"].has("clip_planes")
        or editor.draft_brush_specs["DraftProp_1"]["clip_planes"].size() != 4
        or editor.draft_prop_copies["DraftProp_1"].mesh == null):
        _fail("v0.81 private draft reopen did not reconstruct four-plane convex Box")
        return
    editor._remove_last_private_box_plane()
    if (editor.draft_brush_specs["DraftProp_1"]["clip_planes"].size() != 3
        or editor.box_clip_add_plane_button.disabled):
        _fail("v0.81 Remove last did not retain earlier planes")
        return
    editor._undo_edit()
    if (not editor.draft_brush_specs["DraftProp_1"].has("clip_planes")
        or editor.draft_brush_specs["DraftProp_1"]["clip_planes"].size() != 4):
        _fail("v0.81 Remove last Undo lost original four-plane clip")
        return
    editor._redo_edit()
    if editor.draft_brush_specs["DraftProp_1"]["clip_planes"].size() != 3:
        _fail("v0.81 Remove last Redo lost the original three planes")
        return
    editor._remove_last_private_box_plane()
    editor._remove_last_private_box_plane()
    if (not editor.draft_brush_specs["DraftProp_1"].has("clip_plane")
        or editor.draft_brush_specs["DraftProp_1"].has("clip_planes")):
        _fail("v0.81 removing planes did not restore legacy single-plane draft")
        return
    editor._reset_private_box_clip()
    if (editor.draft_brush_specs["DraftProp_1"].has("clip_plane")
        or editor.draft_brush_specs["DraftProp_1"].has("clip_planes")
        or not editor.brush_face_controls.visible):
        _fail("v0.81 Reset to Box did not clear cumulative clipping metadata")
        return
    if FileAccess.get_sha256(original_file) != source_sha:
        _fail("Original invented source bytes changed during preview authoring")
        return

    for suffix in ["", ".pending", ".bak"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    DirAccess.remove_absolute(original_file)
    editor.queue_free()
    print("DX2Ed v0.81 4-plane closed convex Box, independent Undo, Reset and private Save/reopen PASS")
    quit(0)
