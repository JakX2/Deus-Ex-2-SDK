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
    # Explicitly constrain the editor to a narrower-than-default viewport.
    # A long, nonwrapping toolbar previously shoved Inspector outside it.
    viewer.size = Vector2(1280, 720)
    root.add_child(viewer)
    await process_frame
    var layout_base: Control = viewer.get_child(0)
    if layout_base.get_combined_minimum_size().x > viewer.size.x + 1.0:
        _fail("Toolbar minimum width should not overflow the 1280px window")
        return
    var inspector_panel: Control = viewer.inspector_title.get_parent().get_parent()
    if not inspector_panel is ScrollContainer:
        _fail("Inspector must have a vertical scroll container for long metadata")
        return
    if inspector_panel.size.x < 280.0 or inspector_panel.get_global_rect().end.x > viewer.get_global_rect().end.x + 1.0:
        _fail("Inspector panel is clipped offscreen in a 1280px window")
        return
    if viewer.inspector.custom_minimum_size.y < 180.0:
        _fail("Original source/material diagnostics need a readable minimum height")
        return

    # A rejected user-selected native actor must display the actual error,
    # never the first generic "Traceback" line from a Python exception.
    var rejected_json := '{"schema":"DX2Ed-experimental-native-prop-duplicate-v1","status":"refused","reason":"Source actor has active native/script state"}'
    if viewer._native_clone_error_reason(rejected_json) != "Source actor has active native/script state":
        _fail("Native clone writer JSON refusal did not show original source-state reason")
        return
    if viewer._native_clone_error_reason("Traceback (most recent call last):\nValueError: source actor blocked") != "ValueError: source actor blocked":
        _fail("Native clone fallback should surface the last Python exception line")
        return

    # A direct .gmp import must discover the original retail System/ folder,
    # otherwise the read-only GameSys audit and light Boolean path stay hidden.
    var direct_root := ProjectSettings.globalize_path("user://dx2_system_discovery_smoke")
    var direct_system := direct_root.path_join("System")
    var direct_maps := direct_root.path_join("Content/DX2/Maps")
    if DirAccess.make_dir_recursive_absolute(direct_system) != OK or DirAccess.make_dir_recursive_absolute(direct_maps) != OK:
        _fail("Could not prepare direct-import System fixture")
        return
    for filename in ["Engine.d2u", "DX2Gamesys.d2u"]:
        var source_fixture := FileAccess.open(direct_system.path_join(filename), FileAccess.WRITE)
        if source_fixture == null:
            _fail("Could not create System source fixture")
            return
        source_fixture.store_string("synthetic original system source")
        source_fixture.close()
    var demo_gmp := direct_maps.path_join("M1_Test.gmp")
    if viewer._direct_map_system_folder(demo_gmp) != direct_system:
        _fail("Standard retail map location should discover sibling System folder")
        return
    var isolated_dir := direct_root.path_join("Research")
    DirAccess.make_dir_recursive_absolute(isolated_dir)
    if viewer._direct_map_system_folder(isolated_dir.path_join("M1_Test.gmp")) != "":
        _fail("A non-standard map folder must not inherit an unrelated stale System")
        return
    viewer._select_direct_system_folder(direct_system)
    if viewer._direct_map_system_folder(isolated_dir.path_join("M1_Test.gmp")) != direct_system:
        _fail("Explicitly chosen valid DX2 System folder should support direct GMP")
        return
    var previous_direct_system: String = str(viewer.chosen_direct_system_path)
    viewer._select_direct_system_folder(isolated_dir)
    if viewer.chosen_direct_system_path != previous_direct_system:
        _fail("Invalid source folder must not replace verified DX2 System selection")
        return
    viewer.chosen_direct_system_path = ""
    for filename in ["Engine.d2u", "DX2Gamesys.d2u"]:
        DirAccess.remove_absolute(direct_system.path_join(filename))
    DirAccess.remove_absolute(direct_system)
    DirAccess.remove_absolute(direct_maps)
    DirAccess.remove_absolute(direct_root.path_join("Content/DX2"))
    DirAccess.remove_absolute(direct_root.path_join("Content"))
    DirAccess.remove_absolute(isolated_dir)
    DirAccess.remove_absolute(direct_root)

    # Automatic roll correction is reversible at import and never a GMP edit.
    if not viewer.preview_auto_roll:
        _fail("Auto Roll preview should be enabled for new imports")
        return
    viewer._set_auto_roll_preview(false)
    if viewer.preview_auto_roll:
        _fail("Auto Roll preview OFF must be selectable")
        return
    viewer._set_auto_roll_preview(true)
    if not viewer.preview_auto_roll:
        _fail("Auto Roll preview ON must be selectable again")
        return
    var shown: String = viewer._mesh_geometry_material_summary({
        "class": "StaticMeshActor", "mesh": "GEN_TRIM5-16ft",
        "auto_roll_preview": {"applied": true, "mode": "invert_roll_sign", "heuristic_only": true}
    })
    if not shown.contains("Auto Roll: inverted source roll"):
        _fail("Auto Roll candidate must be identifiable in the Inspector")
        return

    # Original AI layer is only a discoverable candidate marker.
    var ai_fixture := {"name":"D_527__0", "class":"D_527", "export":5,
        "location":[1,2,3],
        "game_properties":[{"id":82,"value":"AI"},
            {"id":41,"value":"generic_male"},
            {"id":1659,"value":"WTO_guard"}],
        "trigger_script_serialized":{"items":[432,424],"interpretation":"index"}}
    if not viewer._actor_on_original_ai_layer(ai_fixture):
        _fail("Original source AI layer should be discoverable")
        return
    if viewer._actor_on_original_ai_layer({"game_properties":[{"id":82,"value":"Staticmeshes"}]}):
        _fail("Other editor layers must not be treated as AI/NPC")
        return
    viewer.category_filter.select(9)
    if not viewer._category_visible("Gameplay / other", ai_fixture):
        _fail("AI actor filter must admit source-marked AI candidate")
        return
    viewer.category_filter.select(0)
    viewer.gameplay_catalog = {
        "script_definitions": [
            {"id":"TestLight", "title":"Test Only", "format":"1FFE2FST",
             "archive_member":"Defs/TestLight.tsd",
             "actions":["kTAT_LinkedPropertySet"],
             "conditions":["kTCT_ReceivePropagateMsgLink"]}
        ]
    }
    viewer._refresh_gameplay_script_list()
    if (viewer.gameplay_visible.size() != 1
        or viewer.gameplay_list.item_count != 1
        or not viewer.gameplay_details.text.contains("kTAT_LinkedPropertySet")
        or not viewer.gameplay_details.text.contains("Not bound to a specific map actor")):
        _fail("Read-only original TriggerScript browser list/details")
        return
    viewer.selected_actor = ai_fixture
    viewer._refresh_inspector_panel()
    if (not viewer.inspector_summary.text.contains("Original SkeletalTag (41): generic_male")
        or not viewer.inspector_summary.text.contains("Original MaterialSkin (1659): WTO_guard")
        or not viewer.inspector_summary.text.contains("inherited class defaults")):
        _fail("Original AI actor render fields must be visible without guessed inherited defaults")
        return
    viewer.focus_selected()
    var expected_ai_focus: Vector3 = Vector3(1.0, 3.0, 2.0) * float(viewer.NATIVE_CLONE_UNREAL_METRES)
    if viewer.camera_target.distance_to(expected_ai_focus) > 0.0001:
        _fail("Original AI-layer candidates without meshes must be focusable from source XYZ")
        return
    # v12 translucent guides visualize exact source AI-layer origins.
    # They are NOT rigged NPC models and cannot be native-spawned.
    var original_ai_properties: Variant = ai_fixture["game_properties"].duplicate(true)
    viewer.actors = [ai_fixture, {"name":"Decoration__0","class":"StaticMeshActor",
        "location":[3,4,5],"game_properties":[{"id":82,"value":"Staticmeshes"}]}]
    viewer._rebuild_ai_proxies()
    if (viewer.ai_proxies.size() != 1 or viewer.ai_proxies_toggle.disabled
        or viewer.ai_proxies_root.get_parent() != viewer.world_root):
        _fail("AI origin overlay should use exact source property-82 AI candidates")
        return
    var ai_capsule: MeshInstance3D = viewer.ai_proxies["D_527__0"]
    var source_ai_position: Vector3 = Vector3(1,3,2) * float(viewer.NATIVE_CLONE_UNREAL_METRES)
    if (not ai_capsule.get_meta("editor_only", false)
        or ai_capsule.get_meta("npc_body_decoded", true)
        or ai_capsule.global_position.distance_to(source_ai_position) > 0.000001
        or viewer.all_mesh_instances.has(ai_capsule)):
        _fail("AI origin capsule must be source-positioned and excluded from native meshes")
        return
    viewer.ai_proxies_toggle.button_pressed = true
    viewer._set_ai_proxies_visible(true)
    var ai_click: Vector2 = viewer.camera.unproject_position(source_ai_position)
    if (viewer._pick_ai_proxy_marker(ai_click) != "D_527__0"
        or not viewer.ai_proxies_count.text.contains("NOT bodies")):
        _fail("AI origin marker must be pickable and explicitly marked as a proxy")
        return
    viewer._set_ai_proxies_visible(false)
    if viewer._pick_ai_proxy_marker(ai_click) != "":
        _fail("Hidden AI origin overlays must never intercept scene picking")
        return
    viewer._clear_ai_proxies()
    viewer.ai_proxies_toggle.set_pressed_no_signal(false)
    if (not viewer.ai_proxies.is_empty()
        or ai_fixture["game_properties"] != original_ai_properties
        or not viewer.property_overrides.is_empty()
        or not viewer.draft_prop_copies.is_empty()):
        _fail("Clearing AI origin guides must not alter source actors/GMP drafts")
        return
    viewer.actors.clear()
    viewer.asset_kind_filter.select(7)
    if (not viewer._asset_kind_matches("skeletalmesh")
        or viewer._asset_kind_matches("staticmesh")):
        _fail("Skeletal mesh resources must be explicitly filterable in Assets")
        return
    viewer.asset_kind_filter.select(8)
    if not viewer._asset_kind_matches("skeletalanim"):
        _fail("Skeletal animations must be separately filterable in Assets")
        return
    viewer.asset_kind_filter.select(0)
    viewer.skeletal_inventory = {
        "schema":"DX2Ed-original-skeletal-ski-inventory-v1",
        "read_only":true,"npc_spawn_enabled":false,"geometry_decoded":false,
        "records":[{"name":"generic_male","version":"v5","pro_present":true,
            "animation_sets":["wto"],"position":[0,0,0],"scale":[1,1,1]}]
    }
    if (not viewer._skeletal_source_description("generic_male").contains("wto")
        or not viewer._skeletal_source_description("generic_male").contains(
            "Actor-to-skeleton mapping NOT verified.")):
        _fail("Loaded original SKI metadata must expose source animation sets without NPC claims")
        return
    viewer.skeletal_inventory.clear()
    viewer._inspect_selected_actor_scripts()
    if (not viewer.gameplay_details.text.contains("432")
        or not viewer.gameplay_details.text.contains("NOT verified TS_")):
        _fail("Actor raw script indices must remain explicitly unbound")
        return
    viewer.selected_actor = {}
    viewer.gameplay_catalog.clear()
    viewer._refresh_gameplay_script_list()

    # First-party source-backed environment actors are not interchangeable.
    # DX2 ZoneProperties own sound schema strings, while Emitter is a particle
    # class and Light carries LightColor/LightShape GameSys structs.
    var light_fixture := {
        "name":"Light__7","class":"Light","export":21,"location":[40,20,300],
        "game_properties":[
            {"id":116,"value":{"LightBrightness":24,"LightHue":150}},
            {"id":118,"value":{"LightRadius":48}},
            {"id":1586,"value":0.1}]
    }
    var zone_fixture := {
        "name":"ZoneProperties__3","class":"ZoneProperties","export":22,
        "location":[64,80,200],"game_properties":[
            {"id":1287,"value":"SeattleWTOTerminal"},
            {"id":1286,"value":"HubWTO_SmallRooms"},
            {"id":1467,"value":"HubWTO_RandomInAdj"}]
    }
    var second_zone_fixture := {
        "name":"ZoneProperties__4","class":"ZoneProperties","export":24,
        "location":[80,80,200],"game_properties":[
            {"id":1287,"value":"SeattleWTOTerminal"},
            {"id":1286,"value":"HubWTO_LargeRooms"},
            {"id":1467,"value":"HubWTO_FlybyInside"}]
    }
    var particle_fixture := {
        "name":"Emitter__0","class":"Emitter","export":23,
        "location":[0,0,64],"game_properties":[]
    }
    viewer.actors = [light_fixture, zone_fixture, particle_fixture, second_zone_fixture]
    viewer.actors_by_name["Light__7"] = light_fixture
    viewer._rebuild_environment_light_markers()
    if viewer.environment_light_markers.size() != 1:
        _fail("Read-only Light source marker should exist for original positioned Light")
        return
    var original_light_position: Vector3 = Vector3(40,300,20) * float(viewer.NATIVE_CLONE_UNREAL_METRES)
    var original_light_marker: MeshInstance3D = viewer.environment_light_markers["Light__7"]
    if (not is_instance_valid(original_light_marker)
        or original_light_marker.get_parent() != viewer.environment_light_markers_root
        or not original_light_marker.get_meta("editor_only", false)
        or original_light_marker.global_position.distance_to(original_light_position) > 0.00001
        or viewer.all_mesh_instances.has(original_light_marker)):
        _fail("Source light handle must be positioned from Unreal XYZ and excluded from native meshes")
        return
    # v11 whole-map semi-lit scene: source light positions, property-derived
    # approximate illumination, no shadows and no native state changes.
    viewer.semi_lit_toggle.disabled = not viewer._semi_lit_has_valid_source_lights()
    if viewer.semi_lit_toggle.disabled:
        _fail("Synthetic source Light should permit semi-lit preview")
        return
    var original_props_for_semi_lit: Variant = light_fixture["game_properties"].duplicate(true)
    viewer._set_semi_lit_enabled(true)
    if (not viewer.semi_lit_enabled or viewer.semi_lit_nodes.size() != 1
        or viewer.semi_lit_root.get_parent() != viewer.world_root
        or abs(viewer.semi_lit_key_light.light_energy - 0.18) > 0.001
        or abs(viewer.semi_lit_world_environment.ambient_light_energy - 0.38) > 0.001):
        _fail("Semi-lit must lower flat ambient/key light and create one source light")
        return
    var mapped_light: OmniLight3D = viewer.semi_lit_nodes["Light__7"]
    if (not is_instance_valid(mapped_light)
        or mapped_light.get_parent() != viewer.semi_lit_root
        or not mapped_light.get_meta("editor_only", false)
        or mapped_light.get_meta("source_actor") != "Light__7"
        or mapped_light.shadow_enabled
        or mapped_light.global_position.distance_to(original_light_position) > 0.00001
        or abs(mapped_light.omni_range - 5.76) > 0.001
        or abs(mapped_light.light_energy - 0.375) > 0.001
        or light_fixture["game_properties"] != original_props_for_semi_lit
        or not viewer.property_overrides.is_empty()
        or not viewer.draft_prop_copies.is_empty()):
        _fail("Semi-lit light must respect source values, no shadows, no GMP drafts")
        return
    viewer._set_semi_lit_enabled(false)
    if (viewer.semi_lit_enabled or not viewer.semi_lit_nodes.is_empty()
        or abs(viewer.semi_lit_key_light.light_energy - 1.6) > 0.001
        or abs(viewer.semi_lit_world_environment.ambient_light_energy - 1.1) > 0.001):
        _fail("Semi-lit OFF must restore baseline lights and clear source proxies")
        return
    # v13: Seattle Hub reproduction: exactly 41 eligible source lights,
    # plus an explicitly OFF and an invalid source actor.
    # The v11 32-light limit must now be configurable without a native edit.
    var lighting_original_properties: Variant = light_fixture["game_properties"].duplicate(true)
    var source_light_markers: Array[MeshInstance3D] = []
    var fixture_marker_mesh := SphereMesh.new()
    fixture_marker_mesh.radius = 0.08
    fixture_marker_mesh.height = 0.16
    for i in range(40):
        var additional_actor: Dictionary = light_fixture.duplicate(true)
        var additional_name := "Light__v13_fixture_" + str(i)
        additional_actor["name"] = additional_name
        additional_actor["location"] = [-10000 - i * 10, 20, 300]
        viewer.actors.append(additional_actor)
        var additional_marker := MeshInstance3D.new()
        additional_marker.name = "DX2Ed_source_marker_" + additional_name
        additional_marker.mesh = fixture_marker_mesh
        additional_marker.set_meta("editor_only", true)
        viewer.environment_light_markers_root.add_child(additional_marker)
        additional_marker.global_position = (Vector3(-10000 - i * 10, 300, 20)
            * float(viewer.NATIVE_CLONE_UNREAL_METRES))
        viewer.environment_light_markers[additional_name] = additional_marker
        source_light_markers.append(additional_marker)
    var explicitly_off_light: Dictionary = light_fixture.duplicate(true)
    explicitly_off_light["name"] = "Light__v13_OFF"
    explicitly_off_light["game_properties"].append({"id":1487,"value":false})
    viewer.actors.append(explicitly_off_light)
    viewer.actors.append({
        "name":"Light__v13_INVALID","class":"Light","location":[1,2,3],
        "game_properties":[{"id":116,"value":{"LightBrightness":24,"LightHue":150}},
                           {"id":118,"value":{"LightRadius":"not a number"}}]
    })
    viewer.lighting_preset_select.select(1)
    viewer._select_lighting_preset(1)
    if (not viewer.semi_lit_enabled or viewer.semi_lit_nodes.size() != 32
        or viewer.semi_lit_last_source_stats.get("total") != 43
        or viewer.semi_lit_last_source_stats.get("eligible") != 41
        or viewer.semi_lit_last_source_stats.get("capped") != 9
        or viewer.semi_lit_last_source_stats.get("explicit_off") != 1
        or viewer.semi_lit_last_source_stats.get("missing_data") != 1
        or not viewer.lighting_diagnostics.text.contains("Excluded by chosen limit: 9")
        or abs(viewer.lighting_ambient_control.value - 0.38) > 0.001
        or viewer.lighting_source_list.item_count != 43
        or not viewer.lighting_source_list.get_item_text(0).begins_with("ACTIVE")
        or not viewer.lighting_source_list.get_item_text(32).begins_with("LIMITED")
        or not viewer.lighting_source_list.get_item_text(41).begins_with("OFF")
        or not viewer.lighting_source_list.get_item_text(42).begins_with("INVALID")):
        _fail("Default semi-lit 32/41 diagnostics mismatch: "
            + JSON.stringify(viewer.semi_lit_last_source_stats)
            + " ambient_control=" + str(viewer.lighting_ambient_control.value))
        return
    viewer.lighting_limit_select.select(4) # All source lights, bounded by 256
    viewer.lighting_ambient_control.set_value_no_signal(0.65)
    viewer.lighting_radius_control.set_value_no_signal(1.5)
    viewer.lighting_energy_control.set_value_no_signal(1.25)
    viewer._lighting_manual_change()
    if (viewer.lighting_preset_select.selected != 4
        or viewer.semi_lit_light_limit != 0
        or viewer._semi_lit_active_budget() != 256
        or viewer.semi_lit_nodes.size() != 41
        or viewer.semi_lit_last_source_stats.get("capped") != 0
        or not viewer.lighting_source_list.get_item_text(32).begins_with("ACTIVE")
        or abs(viewer.semi_lit_world_environment.ambient_light_energy - 0.65) > 0.001
        or not viewer.semi_lit_nodes.has("Light__7")
        or abs(viewer.semi_lit_nodes["Light__7"].omni_range - 8.64) > 0.001
        or abs(viewer.semi_lit_nodes["Light__7"].light_energy - 0.46875) > 0.001
        or light_fixture["game_properties"] != lighting_original_properties
        or not viewer.draft_prop_copies.is_empty()
        or not viewer.property_overrides.is_empty()):
        _fail("All valid source lights, tone, radius and energy must only update Godot preview")
        return
    viewer.lighting_preset_select.select(3)
    viewer._select_lighting_preset(3)
    if (viewer.semi_lit_nodes.size() != 32
        or not viewer.semi_lit_nodes.has("Light__7")
        or abs(viewer.semi_lit_world_environment.ambient_light_energy - 0.15) > 0.001
        or abs(viewer.semi_lit_nodes["Light__7"].omni_range - 4.896) > 0.001):
        _fail("Dark preset should restore a bounded 32-source preview")
        return
    viewer.lighting_preset_select.select(0)
    viewer._select_lighting_preset(0)
    if (viewer.semi_lit_enabled or not viewer.semi_lit_nodes.is_empty()
        or abs(viewer.semi_lit_world_environment.ambient_light_energy - 1.1) > 0.001
        or abs(viewer.semi_lit_key_light.light_energy - 1.6) > 0.001):
        _fail("Editor preset must remove all source lights and restore legacy editor tone")
        return
    for i in range(40):
        var name := "Light__v13_fixture_" + str(i)
        viewer.environment_light_markers.erase(name)
        source_light_markers[i].free()
    viewer.actors.resize(4)
    # Restore default v11 preview values before older v10/v11 integration tests.
    viewer.lighting_preset_select.select(1)
    viewer._select_lighting_preset(1)
    viewer.lighting_preset_select.select(0)
    viewer._select_lighting_preset(0)
    if (not viewer.semi_lit_nodes.is_empty()
        or light_fixture["game_properties"] != lighting_original_properties):
        _fail("V13 diagnostics cleanup must preserve original actor and scene data")
        return
    viewer._refresh_environment_entities()
    if viewer.environment_list.item_count != 4 or viewer.environment_visible.size() != 4:
        _fail("Environment must list real lights, ambient zones and particle emitters separately")
        return
    viewer.environment_filter.text = "HubWTO_SmallRooms"
    viewer._refresh_environment_entities()
    if (viewer.environment_visible.size() != 1
        or str(viewer.environment_visible[0]["class"]) != "ZoneProperties"):
        _fail("Environment search must include original ambient sound schema values")
        return
    viewer.environment_filter.text = ""
    viewer._refresh_environment_entities()
    viewer._environment_entity_selected(0)
    if (not viewer.environment_details.text.contains("LightColor (GameSys 116)")
        or not viewer.environment_details.text.contains("LightShape (GameSys 118)")
        or str(viewer.selected_actor.get("name", "")) != "Light__7"):
        _fail("Native light actor inspector should display first-party DX2 property names")
        return
    viewer.focus_selected()
    if (not viewer.environment_light_radius.visible
        or viewer.environment_light_radius.mesh == null
        or viewer.environment_light_radius.mesh.surface_get_primitive_type(0) != Mesh.PRIMITIVE_LINES
        or not viewer.gizmo_root.visible
        or viewer.gizmo_handles.size() != 3):
        _fail("Selecting original Light must show Unity-style radius wire sphere and three-axis gizmo")
        return
    var marker_pixels: Vector2 = viewer.camera.unproject_position(original_light_marker.global_position)
    if viewer._pick_environment_light_marker(marker_pixels) != "Light__7":
        _fail("Source Light should be selectable by clicking its projected screen marker")
        return
    viewer._set_environment_light_markers_visible(false)
    if (viewer._pick_environment_light_marker(marker_pixels) != ""
        or viewer.environment_light_radius.visible
        or viewer.gizmo_root.visible):
        _fail("Hidden Light markers must not be viewport-pickable or show edit gizmos")
        return
    viewer._set_environment_light_markers_visible(true)
    # v10 preview color/range/energy are isolated editor-only values.
    # They must neither mutate original GameSys fields nor stage a GMP edit.
    if (viewer.environment_light_color_control.disabled
        or not viewer.environment_light_radius_control.editable
        or not viewer.environment_light_energy_control.editable
        or viewer.environment_light_live_toggle.disabled):
        _fail("Selected source Light should enable v10 visual inspector controls")
        return
    viewer.environment_light_live_toggle.button_pressed = true
    viewer._sync_environment_light_live_node()
    if (not is_instance_valid(viewer.environment_light_live_node)
        or not viewer.environment_light_live_node.get_meta("editor_only", false)
        or viewer.environment_light_live_node.get_parent() != viewer.world_root
        or str(viewer.environment_light_live_node.get_meta("source_actor", "")) != "Light__7"):
        _fail("Live source light must be an editor-only Godot OmniLight3D")
        return
    var original_game_properties: Variant = light_fixture["game_properties"].duplicate(true)
    viewer._set_environment_light_visual_setting("color", Color(0.2, 0.4, 0.9))
    viewer._set_environment_light_visual_setting("range", 9.5)
    viewer._set_environment_light_visual_setting("energy", 1.35)
    if (not viewer.environment_light_live_node.light_color.is_equal_approx(Color(0.2, 0.4, 0.9))
        or abs(viewer.environment_light_live_node.omni_range - 9.5) > 0.001
        or abs(viewer.environment_light_live_node.light_energy - 1.35) > 0.001
        or not viewer.environment_light_visual_settings.has("Light__7")
        or viewer.environment_light_visual_reset_button.disabled
        or light_fixture["game_properties"] != original_game_properties
        or not viewer.draft_prop_copies.is_empty()
        or not viewer.property_overrides.is_empty()):
        _fail("Preview edits must change only Godot visuals, not source GameSys/drafts")
        return
    viewer._set_environment_light_visual_setting("range", -100.0)
    if abs(viewer.environment_light_live_node.omni_range - 0.5) > 0.001:
        _fail("Preview radius must stay within its visual-only safety range")
        return
    viewer._set_environment_light_visual_setting("range", 9.5)
    # The map-wide renderer must reuse v10 selected Light preview settings
    # rather than changing authoritative GameSys property dictionaries.
    viewer._set_semi_lit_enabled(true)
    if (viewer.semi_lit_nodes.size() != 1
        or not viewer.semi_lit_nodes["Light__7"].light_color.is_equal_approx(Color(0.2, 0.4, 0.9))
        or abs(viewer.semi_lit_nodes["Light__7"].omni_range - 9.5) > 0.001
        or abs(viewer.semi_lit_nodes["Light__7"].light_energy - 1.35) > 0.001
        or is_instance_valid(viewer.environment_light_live_node)
        or light_fixture["game_properties"] != original_game_properties):
        _fail("Semi-lit must respect v10 color/range/energy overrides, without double lighting")
        return
    var preview_offset := original_light_position + Vector3(2.0, 0.0, 0.0)
    viewer._set_environment_light_preview_position(light_fixture, preview_offset)
    if (not viewer.environment_light_positions.has("Light__7")
        or original_light_marker.global_position.distance_to(preview_offset) > 0.00001
        or viewer.environment_light_radius.global_position.distance_to(preview_offset) > 0.00001
        or viewer.gizmo_root.global_position.distance_to(preview_offset) > 0.00001
        or viewer.environment_light_reset_button.disabled
        or light_fixture["location"] != [40,20,300]
        or not viewer.draft_prop_copies.is_empty()
        or not viewer.property_overrides.is_empty()):
        _fail("Dragging a light proxy must move gizmo + radius only, never source actor or GMP drafts")
        return
    if (viewer.semi_lit_nodes["Light__7"].global_position.distance_to(preview_offset) > 0.00001):
        _fail("Semi-lit light must follow editor-only moved marker")
        return
    viewer._set_semi_lit_enabled(false)
    viewer._sync_environment_light_live_node()
    if (not is_instance_valid(viewer.environment_light_live_node)
        or viewer.environment_light_live_node.global_position.distance_to(preview_offset) > 0.00001):
        _fail("Moving visual light marker must move its live preview without GMP edits")
        return
    viewer._reset_selected_environment_light_position()
    if (not viewer.environment_light_positions.is_empty()
        or original_light_marker.global_position.distance_to(original_light_position) > 0.00001
        or not viewer.environment_light_reset_button.disabled):
        _fail("Light visual position reset must restore original actor coordinates without GMP changes")
        return
    viewer._reset_selected_environment_light_visual_settings()
    if (not viewer.environment_light_visual_settings.is_empty()
        or not viewer.environment_light_visual_reset_button.disabled
        or abs(viewer.environment_light_live_node.omni_range - 5.76) > 0.001
        or abs(viewer.environment_light_live_node.light_energy - 0.375) > 0.001
        or light_fixture["game_properties"] != original_game_properties):
        _fail("Visual appearance reset must restore source-derived preview only")
        return
    viewer._preview_selected_light_at_target()
    if viewer.environment_light_previews.size() != 1:
        _fail("Source Light should create one visual-only Godot preview without native actor")
        return
    var light_preview: OmniLight3D = viewer.environment_light_previews[0]
    if (not is_instance_valid(light_preview)
        or not light_preview.get_meta("editor_only", false)
        or str(light_preview.get_meta("source_actor", "")) != "Light__7"
        or light_preview.get_parent() != viewer.world_root
        or light_preview.global_position.distance_to(viewer.camera_target) > 0.00001
        or not viewer.draft_prop_copies.is_empty()
        or not viewer.property_overrides.is_empty()
        or viewer.environment_light_clear_button.disabled):
        _fail("Editor-only Light preview must stay out of imported GLB and GMP draft state")
        return
    viewer._clear_environment_light_previews()
    if (not viewer.environment_light_previews.is_empty()
        or not viewer.environment_light_clear_button.disabled):
        _fail("Light preview clear should be reversible and remove editor-only lights")
        return
    var light_focus: Vector3 = Vector3(40,300,20) * float(viewer.NATIVE_CLONE_UNREAL_METRES)
    if viewer.camera_target.distance_to(light_focus) > 0.0001:
        _fail("Native light entity without rendered mesh should focus source XYZ")
        return
    viewer._environment_entity_selected(1)
    if (is_instance_valid(viewer.environment_light_live_node)
        or viewer.environment_light_radius_control.editable
        or not viewer.environment_light_visual_reset_button.disabled):
        _fail("Changing selection to sound zone must clear live light and lock light controls")
        return
    if (not viewer.environment_details.text.contains("HubWTO_RandomInAdj")
        or not viewer.environment_details.text.contains("StreamSchema1 (GameSys 1287)")
        or not viewer.environment_details.text.contains("NonStreamSchema1 (GameSys 1467)")):
        _fail("Original ZoneProperties should expose exact source sound schema strings")
        return
    var sound_plan: Dictionary = viewer._environment_sound_plan()
    if (viewer.environment_sound_field.disabled
        or viewer.environment_sound_schema.disabled
        or viewer.environment_sound_button.disabled
        or sound_plan.is_empty()
        or not int(sound_plan.get("property_id", -1)) in [1286,1467]
        or sound_plan.get("expect") == sound_plan.get("replace")
        or sound_plan.get("actor") != "ZoneProperties__3"):
        _fail("Experimental sound zone Save As should only select original cross-verified schema values")
        return
    viewer._environment_entity_selected(2)
    if not viewer._environment_sound_plan().is_empty() or not viewer.environment_sound_button.disabled:
        _fail("Particle emitters must never allow native sound schema editing")
        return
    if not viewer.environment_details.text.to_lower().contains("not sound"):
        _fail("Particle Emitter must never be mislabeled as an audio sound entity")
        return
    if not viewer.draft_prop_copies.is_empty() or not viewer.property_overrides.is_empty():
        _fail("Read-only Environment browser must not stage map edits")
        return
    viewer._clear_environment_light_markers()
    viewer.actors = []
    viewer.selected_actor = {}
    viewer.actors_by_name.erase("Light__7")
    viewer._refresh_environment_entities()

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
    # An anomalous source BSP (Seattle Needle BSP_218) can be hidden for
    # viewport comparison, but neither its geometry nor native draft changes.
    var suspect_bsp := MeshInstance3D.new()
    suspect_bsp.name = "BSP_218"
    suspect_bsp.mesh = BoxMesh.new()
    viewer.world_root.add_child(suspect_bsp)
    viewer.all_mesh_instances.append(suspect_bsp)
    viewer._select_mesh_only(suspect_bsp)
    if viewer.bsp_hide_preview_button.disabled:
        _fail("Selected original BSP should enable the temporary hide control")
        return
    viewer._toggle_bsp_preview_visibility()
    if (suspect_bsp.visible or viewer.bsp_hidden_preview.size() != 1
        or viewer.bsp_hide_preview_button.disabled
        or not viewer.bsp_hide_preview_button.text.begins_with("Restore hidden BSP")
        or not viewer.property_overrides.is_empty()
        or not viewer.draft_prop_copies.is_empty()):
        _fail("BSP preview hide must only affect reversible viewport visibility")
        return
    viewer._toggle_bsp_preview_visibility()
    if not suspect_bsp.visible or not viewer.bsp_hidden_preview.is_empty():
        _fail("BSP preview restore must return original visibility")
        return
    viewer._clear_selection()
    viewer.all_mesh_instances.erase(suspect_bsp)
    suspect_bsp.free()

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
    var material_summary: String = viewer._mesh_geometry_material_summary({
        "name": "TestActor", "class": "StaticMeshActor", "mesh": "FixtureMesh",
        "render_skin": {
            "selected": "Tan Stones", "status": "matched",
            "materials": [{"name": "SyntheticTan", "resolution": "missing_diffuse_texture"}]
        }
    })
    if (not material_summary.contains("Geometry: static mesh") or
        not material_summary.contains("Source materials: SyntheticTan") or
        not material_summary.contains("Skin: Tan Stones")):
        _fail("Inspector must show actor geometry and source material/skin at top")
        return
    if viewer._mesh_geometry_material_summary({}).find("none selected") < 0:
        _fail("Inspector should have a clear unselected state")
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
    # HSplitContainer has only two content panes. A previous third direct
    # child caused the Inspector to vanish at common screen resolutions.
    var inner_split: Node = inspector_panel.get_parent()
    if not inner_split is HSplitContainer or inner_split.get_child_count() != 2:
        _fail("Inspector and Scene must share a nested two-child HSplitContainer")
        return
    var outer_split: Node = inner_split.get_parent()
    if not outer_split is HSplitContainer or outer_split.get_child_count() != 2:
        _fail("Outer split must show Hierarchy and Scene/Inspector group")
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
    var audit_actor: Dictionary = viewer.actors_by_name["StaticMeshActor__1"]
    audit_actor["placement_diagnostic"] = {
        "status": "observed", "needs_review": true,
        "mesh_pivot_to_center_m": 3.2,
        "ibd_vertex_bounds_max_delta_ue": 0.0,
        "gmp_vertex_bounds_max_delta_ue": 20.0,
        "warnings": ["gmp_vertex_bounds_disagree"]
    }
    viewer._refresh_inspector_panel()
    if not viewer.placement_inspector.visible or not viewer.placement_inspector.text.contains("gmp_vertex_bounds_disagree"):
        _fail("Placement Inspector should display original GMP/IBD bounds evidence")
        return
    audit_actor["placement_diagnostic"]["preview_major_axis_endpoints_godot_m"] = [
        [-27.737, 7.773, 14.170], [-22.860, 7.773, 14.170]]
    audit_actor["placement_diagnostic"]["preview_world_aabb_min_m"] = [-27.737, 7.620, 14.018]
    audit_actor["placement_diagnostic"]["preview_world_aabb_max_m"] = [-22.860, 7.925, 14.323]
    audit_actor["placement_diagnostic"]["roll_direction_aabb_ambiguous"] = true
    viewer._refresh_inspector_panel()
    if (not viewer.placement_inspector.text.contains("World mesh endpoints:")
        or not viewer.placement_inspector.text.contains("Roll warning:")):
        _fail("Trim actor placement panel must explain transformed endpoints and roll ambiguity")
        return
    viewer.category_filter.select(8)
    viewer._refresh_actor_list()
    if viewer.visible_actors.size() != 1 or str(viewer.visible_actors[0].get("name", "")) != "StaticMeshActor__1":
        _fail("Review mesh placement filter must show only flagged source actors")
        return
    viewer.category_filter.select(0)
    viewer._refresh_actor_list()
    viewer.select_actor(audit_actor)
    # Catalog UI includes resources not already placed in the scene.
    viewer.asset_catalog = {"schema":"DX2Ed-asset-catalog-v1", "assets":[
        {"name":"SyntheticStair","kind":"staticmesh","bundle":"fictional.ibd","resource_index":1,"bytes":128},
        {"name":"UnusedMesh","kind":"staticmesh","bundle":"fictional.ibd","resource_index":2,"bytes":64},
        {"name":"OriginalDemoCube","kind":"staticmesh","bundle":"fixture.ibd","resource_index":3,"bytes":256}]}
    viewer._refresh_asset_list()
    if viewer.asset_list.item_count != 3:
        _fail("T3Ed-like asset browser should list both placed and unplaced resources")
        return
    viewer._asset_selected(1)
    if not viewer.asset_details.text.contains("UnusedMesh"):
        _fail("Asset Browser should show source provenance and resource metadata")
        return
    if (viewer._placed_instances_for_asset("UnusedMesh").size() != 0
        or not viewer._native_asset_source_for("UnusedMesh").is_empty()
        or not viewer.native_asset_place_button.disabled):
        _fail("Unplaced IBD mesh cannot be misrepresented as a native placeable actor")
        return
    viewer._asset_selected(0)
    if viewer._placed_instances_for_asset("SyntheticStair").size() != 0:
        _fail("Fixture source name does not match scene; unexpected match")
        return
    viewer._asset_selected(2)
    var linked_source: Dictionary = viewer._native_asset_source_for("OriginalDemoCube")
    if (str(linked_source.get("name", "")) != "StaticMeshActor__1"
        or int(linked_source.get("export", -1)) != 1
        or viewer.native_asset_place_button.disabled
        or not viewer.asset_details.text.contains("Native reuse source: StaticMeshActor__1")):
        _fail("Asset native placement must choose existing original actor by matching IBD mesh")
        return
    var base_pose: Transform3D = viewer.original_mesh_transforms["StaticMeshActor__1"]
    var camera_pose: Transform3D = viewer._native_asset_target_pose(
        "StaticMeshActor__1", base_pose.origin + Vector3(0.75, 0.0, 0.0))
    if (camera_pose.origin.distance_to(base_pose.origin + Vector3(0.75, 0.0, 0.0)) > 0.00001
        or not camera_pose.basis.is_equal_approx(base_pose.basis)):
        _fail("Asset native placement must retain original actor rotation and valid camera placement")
        return
    var far_pose: Transform3D = viewer._native_asset_target_pose(
        "StaticMeshActor__1", base_pose.origin + Vector3(1000, 0, 0))
    if (far_pose.origin.distance_to(base_pose.origin + Vector3(1, 0, 0)) > 0.00001
        or not far_pose.basis.is_equal_approx(base_pose.basis)):
        _fail("Out-of-range native placement must keep source basis and stay within supported translation")
        return
    var none_pose: Transform3D = viewer._native_asset_target_pose("StaticMeshActor__1", base_pose.origin)
    if none_pose.origin == base_pose.origin:
        _fail("Native placement cannot create a zero-delta clone at source location")
        return
    var original: MeshInstance3D = viewer.selected_mesh
    if not is_instance_valid(original):
        _fail("demo actor has no mesh")
        return
    # Source-only diagnostic for WTO frame visibility: do NOT edit original
    # GLB material resources, any game files, or the draft transform history.
    var other_geom: MeshInstance3D = viewer.meshes_by_actor["StaticMeshActor__2"]
    var other_was_visible := other_geom.visible
    var previous_override: Material = original.material_override
    var original_pos: Vector3 = original.global_position
    viewer._toggle_geometry_isolation()
    if (viewer.geometry_isolation_visibility.is_empty()
        or not original.visible or other_geom.visible
        or viewer.geometry_isolation_button.text != "Restore visibility"):
        _fail("Isolate selected must hide another mesh without modifying source geometry")
        return
    viewer._toggle_geometry_all_faces()
    if (not is_instance_valid(viewer.geometry_all_faces_target)
        or not original.material_override is StandardMaterial3D
        or original.material_override.cull_mode != BaseMaterial3D.CULL_DISABLED
        or viewer.geometry_all_faces_button.text != "Restore materials"):
        _fail("Inspect both faces must apply per-instance reversible no-cull preview")
        return
    if other_geom.material_override != null:
        _fail("Inspect both faces must not modify the other actor material")
        return
    viewer._toggle_geometry_all_faces()
    viewer._toggle_geometry_isolation()
    if (original.material_override != previous_override or
        other_geom.visible != other_was_visible or
        not viewer.geometry_isolation_visibility.is_empty() or
        is_instance_valid(viewer.geometry_all_faces_target) or
        original.global_position != original_pos):
        _fail("Restoring geometry diagnostics must preserve materials, visibility and pose")
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
    # Preview duplication can become ONE native actor only after a pure
    # translation; no mutations to the original pose or unrelated drafts.
    if not viewer._native_clone_draft_plan().is_empty():
        _fail("An unmoved duplicate must not be writable as a native actor")
        return
    viewer._move_selected_prop(Vector3.RIGHT)
    var native_plan: Dictionary = viewer._native_clone_draft_plan()
    if native_plan.is_empty():
        _fail("Moved original StaticMeshActor preview should pass native clone gate")
        return
    if (native_plan.get("actor") != "StaticMeshActor__1"
        or int(native_plan.get("export", -1)) != int(viewer.actors_by_name["StaticMeshActor__1"]["export"])
        or abs(float(native_plan["delta"][0]) - 0.25 / viewer.NATIVE_CLONE_UNREAL_METRES) > 0.01
        or abs(float(native_plan["delta"][1])) > 0.01
        or abs(float(native_plan["delta"][2])) > 0.01):
        _fail("Native clone must use the original export and transform Godot X to Unreal X")
        return
    # Multi Duplicate must collect 2 different original sources using
    # the same original-transform gate and UE/Godot axis conversion.
    var synthetic_copy = viewer._new_draft_copy(
        "StaticMeshActor__2", "DraftProp_998",
        viewer.original_mesh_transforms["StaticMeshActor__2"])
    if not is_instance_valid(synthetic_copy):
        _fail("Could not create second synthetic preview duplicate")
        return
    synthetic_copy.global_position += Vector3(0.0, 0.0, 0.5)
    var multiple: Array = viewer._native_multi_clone_draft_plan()
    if (multiple.size() != 2 or multiple[0]["actor"] != "StaticMeshActor__1"
        or multiple[1]["actor"] != "StaticMeshActor__2"
        or abs(float(multiple[1]["delta"][1]) - 0.5 / viewer.NATIVE_CLONE_UNREAL_METRES) > 0.01):
        _fail("Multi Duplicate plan must retain both unique source actors and UE Y translation")
        return
    synthetic_copy.rotate_y(0.25)
    if not viewer._native_multi_clone_draft_plan().is_empty():
        _fail("Multi Duplicate must reject an unverified rotated prop")
        return
    viewer.all_mesh_instances.erase(synthetic_copy)
    viewer.draft_prop_copies.erase("DraftProp_998")
    viewer.draft_prop_sources.erase("DraftProp_998")
    synthetic_copy.free()
    if not viewer._native_multi_clone_draft_plan().is_empty():
        _fail("Multi Duplicate must reject a single copy")
        return
    viewer._move_selected_prop(Vector3.UP)
    native_plan = viewer._native_clone_draft_plan()
    if (native_plan.is_empty()
        or abs(float(native_plan["delta"][2]) - 0.25 / viewer.NATIVE_CLONE_UNREAL_METRES) > 0.01):
        _fail("Native clone must translate Godot Y to Unreal Z")
        return
    viewer.property_overrides["StaticMeshActor__1"] = {"1": 2}
    if not viewer._native_clone_draft_plan().is_empty():
        _fail("Native clone may not silently ignore unrelated draft property edits")
        return
    viewer.property_overrides.clear()
    preview.scale *= 1.1
    if not viewer._native_clone_draft_plan().is_empty():
        _fail("Native clone may not serialize unverified rotation/scale changes")
        return
    preview.scale /= 1.1
    viewer._rotate_selected_prop(15.0)
    if not viewer._native_clone_draft_plan().is_empty():
        _fail("Native clone must reject preview rotation")
        return
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

    # Place a mesh that does not have a map actor. This is a draft visual
    # only, with no invented Gamesys export, collision or gameplay identity.
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    viewer.asset_catalog = {"schema":"DX2Ed-asset-catalog-v1", "assets":[
        {"name":"UnusedMesh","kind":"staticmesh","bundle":"synthetic.ibd",
         "resource_index":14,"bytes":64}]}
    viewer.asset_mesh_resources["UnusedMesh"] = BoxMesh.new()
    viewer.selected_asset = viewer.asset_catalog["assets"][0]
    viewer._place_selected_asset()
    if viewer.draft_prop_copies.size() != 1 or viewer.selected_mesh == null:
        _fail("Unplaced IBD asset should create one editable draft mesh")
        return
    var placed_name := str(viewer.selected_mesh.name)
    if viewer.draft_prop_sources.get(placed_name, "") != "AssetMesh::UnusedMesh":
        _fail("Asset draft must record resource lineage, not an invented actor")
        return
    viewer._move_selected_prop(Vector3.UP)
    viewer._undo_edit()  # Undo move
    viewer._undo_edit()  # Undo placement
    if not viewer.draft_prop_copies.is_empty():
        _fail("Undo should remove a preview placed from the asset browser")
        return
    viewer._redo_edit()
    if viewer.draft_prop_copies.size() != 1:
        _fail("Redo should reinstate an IBD asset preview")
        return
    viewer._save_prop_draft()
    var asset_draft: Variant = JSON.parse_string(FileAccess.get_file_as_string(viewer._draft_file_path()))
    if asset_draft.get("copies", []).size() != 1 or str(asset_draft["copies"][0]["from_actor"]) != "AssetMesh::UnusedMesh":
        _fail("Asset preview identity must survive draft serialization")
        return
    viewer._reset_selected_prop()
    viewer._load_prop_draft()
    if viewer.draft_prop_copies.size() != 1:
        _fail("Asset preview should be reconstructed by loading a draft")
        return
    viewer._restore_all_edits()
    if not viewer.draft_prop_copies.is_empty():
        _fail("Restore All should delete asset previews")
        return

    # T3Ed-like Gamesys class palette: class declaration is not a native
    # spawner. A placed template must retain its original actor provenance.
    var original_template: Dictionary = viewer.actors_by_name["StaticMeshActor__1"]
    var source_export := int(original_template.get("export", -1))
    viewer.archetype_catalog = {"schema":"DX2Ed-archetype-catalog-v1",
        "classes":[
            {"qualified":"DX2Game.StaticMeshActor","class":"StaticMeshActor",
             "base":"Actor","source":"system_declaration",
             "observed_actors":2,"template_actor":"StaticMeshActor__1",
             "template_export":source_export,"template_mesh":"TestMesh",
             "property_signatures":[]},
            {"qualified":"DX2Game.Unspawnable","class":"Unspawnable",
             "base":"Actor","source":"system_declaration",
             "observed_actors":0,"template_actor":null,
             "template_export":null,"template_mesh":null,
             "property_signatures":[]}
        ]}
    viewer._refresh_archetype_list()
    if viewer.archetype_list.item_count != 2:
        _fail("Class palette should include both observed and declared-only Gamesys classes")
        return
    viewer._archetype_selected(0)
    if not viewer.archetype_details.text.contains("Parent: Actor"):
        _fail("Class palette must show declared parent")
        return
    viewer._place_archetype_template()
    if viewer.draft_prop_copies.size() != 1:
        _fail("Placed class template must create one draft visual")
        return
    var template_name := str(viewer.selected_mesh.name)
    var provenance: Dictionary = viewer.draft_template_provenance.get(template_name, {})
    if provenance.get("qualified") != "DX2Game.StaticMeshActor" or provenance.get("source_export") != source_export:
        _fail("Template placement lost source class or export identity")
        return
    viewer._undo_edit()
    if not viewer.draft_prop_copies.is_empty() or not viewer.draft_template_provenance.is_empty():
        _fail("Undo must remove template mesh and its metadata")
        return
    viewer._redo_edit()
    if viewer.draft_template_provenance.get(template_name, {}).get("qualified") != "DX2Game.StaticMeshActor":
        _fail("Redo must restore template metadata")
        return
    viewer._save_prop_draft()
    var class_draft: Variant = JSON.parse_string(FileAccess.get_file_as_string(viewer._draft_file_path()))
    if class_draft.get("copies", []).size() != 1 or class_draft["copies"][0]["class_template"]["source_export"] != source_export:
        _fail("Template provenance did not survive JSON sidecar")
        return
    viewer._reset_selected_prop()
    viewer._load_prop_draft()
    if viewer.draft_prop_copies.size() != 1 or viewer.draft_template_provenance.get(template_name, {}).get("qualified") != "DX2Game.StaticMeshActor":
        _fail("Loading class template draft did not restore original class metadata")
        return
    if viewer._valid_template_provenance({"qualified":"DX2Game.Unspawnable",
        "source_actor":"StaticMeshActor__1","source_export":source_export}, "StaticMeshActor__1"):
        _fail("Invalid class-prototype pairing must be rejected")
        return
    viewer._restore_all_edits()
    viewer._archetype_selected(1)
    viewer._place_archetype_template()
    if not viewer.draft_prop_copies.is_empty():
        _fail("A declared class without a rendered example cannot be invented")
        return

    # T3Ed-style parameterized brushes: independent SDK source geometry.
    var builder = load("res://brush_geometry.gd")
    if builder == null:
        _fail("Brush geometry script could not load")
        return
    for kind in ["Box", "Wall", "Floor", "Stairs"]:
        var params: Dictionary = builder.default_spec(kind)
        if builder.validate(params).is_empty() or builder.build_mesh(params) == null:
            _fail("Brush construction failed for " + kind)
            return
    if not builder.validate({"kind":"Box","size":[2.0,0.0,2.0],"steps":1}).is_empty():
        _fail("Zero-size brushes must not be accepted")
        return
    if not builder.validate({"kind":"Stairs","size":[2.0,2.0,4.0],"steps":1000}).is_empty():
        _fail("Unbounded stair geometry must be rejected")
        return
    if not builder.validate({"kind":"Box","size":[2.0,"oops",2.0],"steps":1}).is_empty():
        _fail("Malformed dimensions must be rejected")
        return

    viewer.brush_kind_control.select(3)
    viewer._update_brush_form(3)
    viewer._place_preview_brush()
    if viewer.draft_prop_copies.size() != 1 or viewer.selected_mesh == null:
        _fail("Brush tab failed to create a preview stair")
        return
    var brush_name := str(viewer.selected_mesh.name)
    if viewer.draft_brush_specs.get(brush_name, {}).get("kind") != "Stairs":
        _fail("Stair brush lacks its original parameters")
        return
    var first_bounds: AABB = viewer.selected_mesh.get_aabb()
    viewer._change_brush_dimension(8.0, 2)
    if abs(float(viewer.draft_brush_specs[brush_name]["size"][2]) - 8.0) > 0.001:
        _fail("Brush dimensions did not change through the Inspector")
        return
    if abs(viewer.selected_mesh.get_aabb().size.z - first_bounds.size.z) < 0.001:
        _fail("Resize did not regenerate stair geometry")
        return
    viewer._change_brush_steps(12)
    if int(viewer.draft_brush_specs[brush_name]["steps"]) != 12:
        _fail("Inspector step count was not applied")
        return
    viewer._undo_edit()
    if int(viewer.draft_brush_specs[brush_name]["steps"]) != 8:
        _fail("Undo should restore the previous stair count")
        return
    viewer._redo_edit()
    if int(viewer.draft_brush_specs[brush_name]["steps"]) != 12:
        _fail("Redo should restore the updated stair geometry")
        return
    viewer._save_prop_draft()
    var brush_saved: Variant = JSON.parse_string(FileAccess.get_file_as_string(viewer._draft_file_path()))
    if brush_saved.get("copies", []).size() != 1 or int(brush_saved["copies"][0]["brush"]["steps"]) != 12:
        _fail("Saved draft must preserve brush parameters")
        return
    viewer._reset_selected_prop()
    viewer._load_prop_draft()
    if not viewer.draft_brush_specs.has(brush_name) or int(viewer.draft_brush_specs[brush_name]["steps"]) != 12:
        _fail("Load draft must rebuild the original parametric stair")
        return
    viewer._select_mesh_only(viewer.draft_prop_copies[brush_name])
    viewer._duplicate_selected_prop()
    if viewer.draft_brush_specs.size() != 2:
        _fail("Duplicating a brush must preserve its parametric definition")
        return
    viewer._restore_all_edits()
    if not viewer.draft_brush_specs.is_empty() or not viewer.draft_prop_copies.is_empty():
        _fail("Restore All must discard every preview brush")
        return

    if not diagnosis.contains("Exported skin: Tan Stones") or not diagnosis.contains("Skin material: SyntheticTan | missing_diffuse_texture"):
        _fail("skin diagnostics should show exact missing texture status")
        return

    # A separate original GameSys source sidecar enriches the Inspector.
    # Its values NEVER become draft edits, GameSys native writes or spawn actions.
    if viewer.source_gamesys_panel == null or viewer.source_archetype_list == null:
        _fail("Source GameSys inspector and recovered archetype tab must exist")
        return
    viewer._clear_selection()
    viewer.current_source_map_name = "M1_Fixture.gmp"
    viewer.source_gamesys_sha256 = "a".repeat(64)
    var original_gamesys_fixture := {
        "schema": "DX2Ed-gamesys-inspector-sidecar-v1",
        "read_only": true,
        "native_game_editing_enabled": false,
        "source_map": "M1_Fixture.gmp",
        "source_sha256": "a".repeat(64),
        "actors": {str(source_export): {
            "name": "StaticMeshActor__1",
            "export": source_export,
            "properties": [{
                "id": 92, "name": "TriggerScripts",
                "declared_type": "array<name>", "declared_in": "Engine.Actor",
                "source_value": {"items": [71, 72], "interpretation": "index"},
                "encoding": "array", "encoded_id": 67108956,
                "payload_offset": 432, "payload_bytes": 3,
                "source_payload_sha256": "deadbeef"
            }]
        }},
        "archetypes": [{
            "class": "D_1179", "display_name": "BotBasicVuln",
            "parent": "D_1198", "source_ancestry": ["D_1179", "D_1198"],
            "inheritance_complete": true, "recovered_dx2_layout": true,
            "local_property_count": 1,
            "local_defaults": [{
                "property_id": 959, "source_declared_name": "VulnerabilityArray",
                "source_declared_type": "array<struct>", "element_count": 29,
                "elements": [{"element_index": 1,
                    "typed_fields": [{"name": "Vulnerability", "value": 1.0}]}]
            }]
        }]
    }
    var gamesys_smoke_path := ProjectSettings.globalize_path("user://gamesys_sidecar_smoke.json")
    var gamesys_smoke_file := FileAccess.open(gamesys_smoke_path, FileAccess.WRITE)
    if gamesys_smoke_file == null:
        _fail("Unable to write private GameSys smoke fixture")
        return
    gamesys_smoke_file.store_string(JSON.stringify(original_gamesys_fixture))
    gamesys_smoke_file.close()
    viewer._load_source_gamesys_catalog(gamesys_smoke_path)
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    if not viewer.source_gamesys_panel.visible or viewer.source_gamesys_list.item_count != 1:
        _fail("Verified GameSys actor fields did not reach the read-only Inspector")
        return
    viewer._source_gamesys_selected(0)
    if not viewer.source_gamesys_details.text.contains("array<name>") or not viewer.source_gamesys_details.text.contains("Payload offset: 0x1b0"):
        _fail("GameSys Inspector did not show type and original native byte offset")
        return
    if viewer.source_archetype_list.item_count != 1:
        _fail("Verified original DX2 archetype did not reach source browser")
        return
    viewer._source_archetype_selected(0)
    if not viewer.source_archetype_details.text.contains("BotBasicVuln") or not viewer.source_archetype_details.text.contains("Vulnerability"):
        _fail("Recovered grouped vulnerability fields are missing from GameSys tab")
        return
    if viewer._capture_edit_state()["property_edits"] != {}:
        _fail("Reading native GameSys fields must never create draft property edits")
        return
    # The only conditional GameSys writer affordance is a source-verified
    # authored Boolean #1487. Scripts, other types and runtime bits stay locked.
    if viewer.source_gamesys_light_button == null or viewer.source_gamesys_light_button.visible:
        _fail("Non-Boolean GameSys source may not offer native light Save As")
        return
    var light_record := {
        "id": 1487, "name": "bLightOn",
        "declared_type": "bool", "declared_in": "Engine.Actor",
        "source_value": true, "encoding": "bool",
        "encoded_id": (128 << 16) | 1487,
        "payload_offset": 470, "payload_bytes": 1,
        "source_payload_sha256": "aa".repeat(32)
    }
    original_gamesys_fixture["actors"][str(source_export)]["properties"].append(light_record)
    var new_file := FileAccess.open(gamesys_smoke_path, FileAccess.WRITE)
    new_file.store_string(JSON.stringify(original_gamesys_fixture))
    new_file.close()
    viewer._load_source_gamesys_catalog(gamesys_smoke_path)
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    viewer._source_gamesys_selected(1)
    var light_context: Dictionary = viewer._selected_source_light_bool_context()
    if (not viewer.source_gamesys_light_button.visible
        or int(light_context.get("property_id", -1)) != 1487
        or light_context.get("expected") != true
        or str(light_context.get("actor", "")) != "StaticMeshActor__1"
        or viewer._capture_edit_state()["property_edits"] != {}):
        _fail("Verified authored bLightOn must allow only an isolated test; no draft edits")
        return
    viewer._source_gamesys_selected(0)
    if viewer.source_gamesys_light_button.visible:
        _fail("Switching from bLightOn to TriggerScripts must hide the light writer")
        return
    viewer._source_gamesys_selected(1)
    original_gamesys_fixture["actors"][str(source_export)]["properties"][1]["encoded_id"] |= (0x4000 << 16)
    var runtime_file := FileAccess.open(gamesys_smoke_path, FileAccess.WRITE)
    runtime_file.store_string(JSON.stringify(original_gamesys_fixture))
    runtime_file.close()
    viewer._load_source_gamesys_catalog(gamesys_smoke_path)
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    viewer._source_gamesys_selected(1)
    if viewer.source_gamesys_light_button.visible or not viewer._selected_source_light_bool_context().is_empty():
        _fail("Runtime-flagged bLightOn must never expose native Save As")
        return
    original_gamesys_fixture["actors"][str(source_export)]["properties"][1]["encoded_id"] = (128 << 16) | 1487
    original_gamesys_fixture["actors"][str(source_export)]["properties"][1]["encoding"] = "byte"
    var byte_file := FileAccess.open(gamesys_smoke_path, FileAccess.WRITE)
    byte_file.store_string(JSON.stringify(original_gamesys_fixture))
    byte_file.close()
    viewer._load_source_gamesys_catalog(gamesys_smoke_path)
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    viewer._source_gamesys_selected(1)
    if viewer.source_gamesys_light_button.visible:
        _fail("One-byte non-Boolean GameSys fields must not offer bLightOn editing")
        return
    original_gamesys_fixture["actors"][str(source_export)]["properties"][1]["encoding"] = "bool"
    original_gamesys_fixture["actors"][str(source_export)]["properties"][1]["source_value"] = 1
    var int_file := FileAccess.open(gamesys_smoke_path, FileAccess.WRITE)
    int_file.store_string(JSON.stringify(original_gamesys_fixture))
    int_file.close()
    viewer._load_source_gamesys_catalog(gamesys_smoke_path)
    viewer.select_actor(viewer.actors_by_name["StaticMeshActor__1"])
    viewer._source_gamesys_selected(1)
    if viewer.source_gamesys_light_button.visible:
        _fail("Non-Boolean source values must never be coerced into light edits")
        return
    viewer.source_gamesys_sha256 = "b".repeat(64)
    viewer._load_source_gamesys_catalog(gamesys_smoke_path)
    if not viewer.source_gamesys_catalog.is_empty() or viewer.source_gamesys_panel.visible:
        _fail("Mismatched source SHA must hide stale GameSys Inspector data")
        return
    DirAccess.remove_absolute(gamesys_smoke_path)

    print("DX2Ed triangle picking smoke: PASS (faces, transforms, sparse AABB, actor schema)")
    quit(0)
