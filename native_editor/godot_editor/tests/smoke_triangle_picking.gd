extends SceneTree
## Read-only, asset-free DX2Ed picking smoke test.
## Run from repo root with:
## godot --headless --path native_editor/godot_editor --script res://tests/smoke_triangle_picking.gd

func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed triangle picking smoke: " + message)
    quit(1)


func _run() -> void:
    var script = load("res://main.gd")
    if script == null:
        _fail("main.gd failed to parse or load")
        return
    var viewer = script.new()
    if viewer == null:
        _fail("main.gd failed to instantiate")
        return
    root.add_child(viewer)

    # Editor categories are class hints, not a substitute for decoded physics.
    if viewer._actor_category({"class":"StaticMeshActor"}) != "Static mesh":
        _fail("static-mesh category classification")
        return
    if viewer._actor_category({"class":"DefaultPhysicsVolume"}) != "Volume / trigger":
        _fail("volumes should not be called physics props")
        return
    if viewer._actor_category({"class":"D_Character"}) != "Gameplay / other":
        _fail("unverified gameplay actors should remain unclassified")
        return
    viewer._set_editor_tool("rotate")
    if viewer.editor_tool != "rotate" or viewer.gizmo_handles.size() != 3:
        _fail("rotation gizmo should have three axis handles")
        return
    viewer._set_editor_tool("scale")
    if viewer.editor_tool != "scale":
        _fail("scale gizmo mode")
        return
    viewer._set_editor_tool("move")
    viewer._set_fly_mode(true)
    if not viewer.fly_looking:
        _fail("RMB fly mode failed to engage")
        return
    viewer._set_fly_mode(false)
    if viewer.fly_looking:
        _fail("RMB fly mode failed to disengage")
        return

    # A normal triangle mesh should be selectable by its real surface.
    var solid := MeshInstance3D.new()
    solid.name = "TestSolid"
    var cube := BoxMesh.new()
    cube.size = Vector3(2.0, 2.0, 2.0)
    solid.mesh = cube
    root.add_child(solid)
    var ray_origin := Vector3(0.0, 0.0, 5.0)
    var ray_dir := Vector3(0.0, 0.0, -1.0)
    var hit: Dictionary = viewer._ray_mesh_triangles(solid, ray_origin, ray_dir)
    if hit.is_empty() or abs(float(hit.get("distance", -1.0)) - 4.0) > 0.001:
        _fail("solid box front face should be 4 Godot units away")
        return

    # Ensure transformed instances are handled in local coordinates.
    solid.scale = Vector3(1.2, 1.5, 0.5)
    solid.rotation_degrees = Vector3(0.0, 35.0, 0.0)
    hit = viewer._ray_mesh_triangles(solid, ray_origin, ray_dir)
    if hit.is_empty() or float(hit["distance"]) <= 0.0:
        _fail("rotated and non-uniformly scaled box should be hittable")
        return

    # A ray can intersect an AABB without intersecting either of its triangles.
    # This is the original selection problem with sprawling BSP bounds.
    var arrays := []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = PackedVector3Array([
        Vector3(-10.0, -1.0, 0.0), Vector3(-8.0, -1.0, 0.0), Vector3(-10.0, 1.0, 0.0),
        Vector3(8.0, -1.0, 0.0), Vector3(10.0, -1.0, 0.0), Vector3(10.0, 1.0, 0.0)
    ])
    var sparse_mesh := ArrayMesh.new()
    sparse_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
    var sparse := MeshInstance3D.new()
    sparse.mesh = sparse_mesh
    root.add_child(sparse)
    if viewer._ray_aabb(ray_origin, ray_dir, viewer._mesh_world_aabb(sparse)) < 0.0:
        _fail("fixture error: central ray must intersect sparse mesh AABB")
        return
    if not viewer._ray_mesh_triangles(sparse, ray_origin, ray_dir).is_empty():
        _fail("AABB-only false positive: central ray does not intersect triangles")
        return

    # Retail Actor Explorer JSON uses a string mesh and separate mesh_bounds.
    var diagnosis: String = viewer._format_actor_diagnostic({
        "name": "TestActor", "class": "StaticMeshActor", "export": 7,
        "mesh": "FixtureMesh", "mesh_bounds": [[-1, -1, -1], [1, 1, 1]],
        "location": [10, 20, 30], "rotation": [0, 16384, 0],
        "render_skin": {"requested": "Tan Stones", "selected": "Tan Stones",
            "status": "matched", "materials": [
                {"name": "SyntheticTan", "resolution": "missing_diffuse_texture"}]}
    })
    if not diagnosis.contains("Mesh resource: FixtureMesh") or not diagnosis.contains("10, 20, 30"):
        _fail("Actor Explorer schema did not reach diagnostic")
        return

    # Exercise preview prop editing against the original synthetic two-cube GLB.
    viewer.load_glb(ProjectSettings.globalize_path("res://demo/scene.glb"))
    if not viewer.actors_by_name.has("StaticMeshActor__1"):
        _fail("demo actor metadata not linked")
        return
    # A small Gamesys fixture proves typed property overrides remain separate
    # from original map metadata and round-trip through undo and sidecars.
    var typed_actor: Dictionary = viewer.actors_by_name["StaticMeshActor__1"]
    typed_actor["game_properties"] = [
        {"id": 1301, "name": "Visible", "type": "bool", "value": true},
        {"id": 1302, "name": "Counter", "type": "int", "value": 5},
        {"id": 1303, "name": "Radius", "type": "float", "value": 1.5},
        {"id": 1304, "name": "Caption", "type": "string", "value": "Original"},
        {"id": 1305, "name": "Complex", "type": "struct", "value": {"A": 7}},
        {"id": 43, "name": "MeshReference", "type": "int", "value": 9}
    ]
    viewer.select_actor(typed_actor)
    if viewer._find_editable_property(typed_actor, 1301).is_empty():
        _fail("Boolean actor field should be editable")
        return
    if not viewer._find_editable_property(typed_actor, 1305).is_empty() or not viewer._find_editable_property(typed_actor, 43).is_empty():
        _fail("Structs and mesh references must be locked")
        return
    viewer._actor_property_changed(11.0, str(typed_actor["name"]), 1302)
    if viewer.property_overrides.get("StaticMeshActor__1", {}).get("1302") != 11:
        _fail("Typed integer property was not recorded in sidecar overrides")
        return
    if typed_actor["game_properties"][1]["value"] != 5:
        _fail("Edited property mutated original source data")
        return
    viewer._undo_edit()
    if not viewer.property_overrides.is_empty():
        _fail("Undo did not restore original actor property")
        return
    viewer._redo_edit()
    if viewer.property_overrides.get("StaticMeshActor__1", {}).get("1302") != 11:
        _fail("Redo did not restore changed actor property")
        return
    viewer._actor_property_changed(false, "StaticMeshActor__1", 1301)
    viewer._actor_property_changed("Edited", "StaticMeshActor__1", 1304)
    viewer.property_filter.text = "Caption"
    viewer.property_editor_last_key = ""
    viewer._refresh_actor_property_editor()
    if viewer.property_editor_rows.get_child_count() != 1:
        _fail("Inspector property filter should display only matching scalar rows")
        return
    viewer._reset_actor_property_edits()
    if not viewer.property_overrides.is_empty():
        _fail("Reset values should remove only edited actor scalar overrides")
        return
    viewer._undo_edit()
    if viewer.property_overrides.get("StaticMeshActor__1", {}).get("1304") != "Edited":
        _fail("Reset values should be undoable")
        return
    viewer.property_filter.text = ""
    viewer.property_editor_last_key = ""
    viewer._refresh_actor_property_editor()
    viewer._save_prop_draft()
    var typed_draft: Variant = JSON.parse_string(FileAccess.get_file_as_string(viewer._draft_file_path()))
    if typeof(typed_draft) != TYPE_DICTIONARY or typed_draft.get("property_edits", []).size() != 3:
        _fail("Saved sidecar must contain only three typed property overrides")
        return
    if viewer._validate_property_edits([{"actor":"StaticMeshActor__1","export":7,
        "id":43,"type":"int","value":12}]) != null:
        _fail("Unsafe object reference override must fail validation")
        return
    viewer._restore_all_edits()
    if not viewer.property_overrides.is_empty():
        _fail("Restore All must also clear actor property edits")
        return
    viewer._load_prop_draft()
    if not viewer.property_overrides.is_empty():
        _fail("Restore All must persist an empty property sidecar")
        return
    viewer._undo_edit()
    # Restore All is one undo step; its pre-reset scalar state is restored.
    if viewer.property_overrides.get("StaticMeshActor__1", {}).get("1304") != "Edited":
        _fail("Restore All property changes must be undoable")
        return
    viewer._restore_all_edits()

    # Logical actors lack a rendered mesh, but typed fields must remain
    # editable and their inspector selection must survive an undo.
    var logic: Dictionary = {"name": "LogicOnly__100", "class": "Trigger",
        "export": 42, "game_properties": [
            {"id": 1601, "name": "Threshold", "type": "float", "value": 2.0}]}
    viewer.actors_by_name["LogicOnly__100"] = logic
    viewer.select_actor(logic)
    viewer._actor_property_changed(3.5, "LogicOnly__100", 1601)
    viewer._undo_edit()
    if str(viewer.selected_actor.get("name", "")) != "LogicOnly__100":
        _fail("Undo should preserve selected non-rendered actor")
        return
    viewer._redo_edit()
    if viewer.property_overrides.get("LogicOnly__100", {}).get("1601") != 3.5:
        _fail("Logical-only actor fields should participate in undo/redo")
        return
    viewer._restore_all_edits()

    # Unity-like workspace: actor Hierarchy links to the Inspector.
    if viewer.hierarchy_tree == null or viewer.inspector_title == null:
        _fail("Hierarchy / Inspector panes were not constructed")
        return
    if not viewer.hierarchy_items.has("StaticMeshActor__1") or not viewer.hierarchy_items.has("StaticMeshActor__2"):
        _fail("Hierarchy missing the two synthetic scene actors")
        return
    viewer.hierarchy_tree.deselect_all()
    viewer.hierarchy_items["StaticMeshActor__2"].select(0)
    viewer._apply_hierarchy_selection()
    if viewer.selected_mesh == null or str(viewer.selected_mesh.name) != "StaticMeshActor__2":
        _fail("Hierarchy selection did not choose the rendered actor")
        return
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    # Catalog UI includes resources not already placed in the scene.
    viewer.asset_catalog = {"schema":"DX2Ed-asset-catalog-v1", "assets":[
        {"name":"SyntheticStair","kind":"staticmesh","bundle":"fictional.ibd","resource_index":1,"bytes":128},
        {"name":"UnusedMesh","kind":"staticmesh","bundle":"fictional.ibd","resource_index":2,"bytes":64}]}
    viewer._refresh_asset_list()
    if viewer.asset_list.item_count != 2:
        _fail("T3Ed-like asset browser should list both placed and unplaced resources")
        return
    viewer._asset_selected(1)
    if not viewer.asset_details.text.contains("UnusedMesh"):
        _fail("Asset Browser should show source provenance and resource metadata")
        return
    if viewer._placed_instances_for_asset("UnusedMesh").size() != 0:
        _fail("An unplaced resource must not be confused with an actor")
        return
    viewer._asset_selected(0)
    if viewer._placed_instances_for_asset("SyntheticStair").size() != 0:
        _fail("Fixture uses only TestMesh name; unexpected match")
        return
    var original: MeshInstance3D = viewer.selected_mesh
    if not is_instance_valid(original):
        _fail("demo actor has no mesh")
        return
    var before := original.global_position
    # Source rotator 16384 = 90 degrees. Axis remapping must match exporter.
    var converted: Basis = viewer._ue_rotator_basis([0, 16384, 0])
    if (converted * Vector3.RIGHT).distance_to(Vector3.BACK) > 0.001:
        _fail("Unreal Yaw 90 should map Godot X to +Z")
        return
    if not viewer.rotation_lab_panel.visible or viewer.rotation_lab_modes.item_count != 6:
        _fail("Rotation Lab must expose six reversible hypotheses for a placed actor")
        return
    var original_basis := original.global_transform.basis
    viewer.rotation_lab_modes.select(2)  # Extra +90 deg yaw
    viewer._preview_rotation_hypothesis()
    if original.global_transform.basis == original_basis:
        _fail("Rotation Lab preview should change the rendered basis")
        return
    viewer._undo_edit()
    if original.global_transform.basis != original_basis:
        _fail("Rotation Lab orientation preview must undo cleanly")
        return
    var lab_report: String = viewer._rotation_evidence_text()
    if not lab_report.contains("GMP rotator") or not lab_report.contains("Original export"):
        _fail("Rotation evidence must include original source and alternative hypotheses")
        return
    if not viewer.inspector_transform_section.visible:
        _fail("Editable static mesh must expose Inspector transforms")
        return
    viewer._inspector_transform_changed(before.x + 1.0, "Position", 0)
    if abs(original.global_position.x - before.x - 1.0) > 0.001:
        _fail("Inspector X field failed to edit world position")
        return
    viewer._undo_edit()
    if original.global_position.distance_to(before) > 0.001:
        _fail("Inspector edits must support Ctrl+Z")
        return
    viewer._move_selected_prop(Vector3.RIGHT)
    if abs(original.global_position.x - before.x - 0.25) > 0.001:
        _fail("preview move must use default 0.25-metre step")
        return
    viewer._undo_edit()
    if original.global_position.distance_to(before) > 0.001:
        _fail("Ctrl+Z should undo the first move")
        return
    viewer._redo_edit()
    if abs(original.global_position.x - before.x - 0.25) > 0.001:
        _fail("Ctrl+Y should redo the first move")
        return
    viewer._reset_selected_prop()
    if original.global_position.distance_to(before) > 0.001:
        _fail("reset prop did not restore original transform")
        return
    # Multi-select both synthetic actors, use the shared pivot and move together.
    var second: MeshInstance3D = viewer.meshes_by_actor["StaticMeshActor__2"]
    var initial_second := second.global_position
    viewer._toggle_selection_mesh(second)
    if viewer._selection_nodes().size() != 2:
        _fail("Ctrl-toggle should make a two-object selection")
        return
    var original_spacing := second.global_position.distance_to(original.global_position)
    viewer._move_selected_prop(Vector3.UP)
    if abs(original.global_position.y - before.y - 0.25) > 0.001 or abs(second.global_position.y - initial_second.y - 0.25) > 0.001:
        _fail("group move did not translate both props")
        return
    viewer._rotate_selected_prop(90.0)
    if abs(original.global_position.distance_to(second.global_position) - original_spacing) > 0.001:
        _fail("group rotation should preserve spacing")
        return
    viewer._save_prop_draft()
    viewer._reset_selected_prop()
    if original.global_position.distance_to(before) > 0.001 or second.global_position.distance_to(initial_second) > 0.001:
        _fail("group reset did not restore both originals")
        return
    viewer._load_prop_draft()
    if abs(second.global_position.y - initial_second.y - 0.25) > 0.001:
        _fail("group draft did not restore transforms")
        return
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    viewer._toggle_selection_mesh(second)
    viewer._reset_selected_prop()
    # Ctrl-click again removes only the chosen member, leaving the first.
    viewer._toggle_selection_mesh(second)
    if viewer._selection_nodes().size() != 1 or viewer.selected_mesh != original:
        _fail("Ctrl-toggle should deselect only the second prop")
        return

    viewer._duplicate_selected_prop()
    if viewer.draft_prop_copies.size() != 1:
        _fail("duplicate did not produce a preview prop")
        return
    viewer._undo_edit()
    if viewer.draft_prop_copies.size() != 0:
        _fail("Undo should remove the duplicated preview prop")
        return
    viewer._redo_edit()
    if viewer.draft_prop_copies.size() != 1:
        _fail("Redo should recreate the duplicate under its original name")
        return
    var preview: MeshInstance3D = viewer.selected_mesh
    viewer._move_selected_prop(Vector3.UP)
    viewer._rotate_selected_prop(15.0)
    viewer._save_prop_draft()
    if not FileAccess.file_exists(viewer._draft_file_path()):
        _fail("draft sidecar was not saved")
        return
    viewer._reset_selected_prop()
    if viewer.draft_prop_copies.size() != 0:
        _fail("delete copy left a preview prop behind")
        return
    viewer._load_prop_draft()
    if viewer.draft_prop_copies.size() != 1:
        _fail("draft sidecar did not restore duplicate")
        return
    if viewer.draft_prop_copies.values()[0].global_position.y < 0.1:
        _fail("draft sidecar did not restore edited transform")
        return

    # Restore All must clear live edits AND the saved draft. It remains undoable.
    viewer._restore_all_edits()
    if viewer.draft_prop_copies.size() != 0:
        _fail("Restore All must remove every preview copy")
        return
    if original.global_position.distance_to(before) > 0.001:
        _fail("Restore All must restore the original imported pose")
        return
    var empty_draft: Variant = JSON.parse_string(FileAccess.get_file_as_string(viewer._draft_file_path()))
    if typeof(empty_draft) != TYPE_DICTIONARY or not empty_draft["moved"].is_empty() or not empty_draft["copies"].is_empty():
        _fail("Restore All should persist an empty sidecar draft")
        return
    viewer._undo_edit()
    if viewer.draft_prop_copies.size() != 1:
        _fail("Restore All should be undoable for the current session")
        return
    viewer._redo_edit()
    if viewer.draft_prop_copies.size() != 0:
        _fail("Restore All should be redoable")
        return
    # A complete gizmo drag is a single history entry, not one per motion.
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    var before_drag := original.global_position
    var history_count: int = viewer.undo_stack.size()
    viewer.gizmo_undo_before = viewer._capture_edit_state()
    viewer.gizmo_drag_active = true
    original.global_position += Vector3(0.5, 0.0, 0.0)
    original.global_position += Vector3(0.5, 0.0, 0.0)
    viewer._finish_gizmo_drag()
    if viewer.undo_stack.size() != history_count + 1:
        _fail("One drag should create exactly one undo entry")
        return
    viewer._undo_edit()
    if original.global_position.distance_to(before_drag) > 0.001:
        _fail("Undo should revert the entire gizmo gesture")
        return
    viewer._redo_edit()
    if abs(original.global_position.x - before_drag.x - 1.0) > 0.001:
        _fail("Redo should restore the entire gizmo gesture")
        return

    # A fresh edit after undo clears redo history.
    viewer._undo_edit()
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    viewer._move_selected_prop(Vector3.RIGHT)
    if not viewer.redo_stack.is_empty():
        _fail("New edits should clear redo history")
        return

    if not diagnosis.contains("Exported skin: Tan Stones") or not diagnosis.contains("Skin material: SyntheticTan | missing_diffuse_texture"):
        _fail("skin diagnostics should show exact missing texture status")
        return

    print("DX2Ed triangle picking smoke: PASS (faces, transforms, sparse AABB, actor schema)")
    quit(0)
