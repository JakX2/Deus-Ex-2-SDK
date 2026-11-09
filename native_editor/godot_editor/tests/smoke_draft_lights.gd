extends SceneTree
## DX2Ed v0.57 private Point/Spot light authoring and safe draft round-trip.
## Synthetic preview nodes only; no native DX2 Light/GameSys/lightmap writer.

const Editor = preload("res://main.gd")
const DraftLight = preload("res://draft_light_authoring.gd")
const LIGHT_NODE := "DX2Ed_LightPreview_EDITOR_ONLY"


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.57 private draft lights: " + message)
    quit(1)


func _write_document(path: String, payload: String) -> bool:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(payload)
    file.flush()
    file.close()
    return true


func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    var fake_scene := Node3D.new()
    fake_scene.name = "SyntheticLightDraftScene"
    editor.world_root.add_child(fake_scene)
    editor.scene_root = fake_scene
    editor.current_folder = ProjectSettings.globalize_path("user://v057_private_light_authoring")
    editor.camera_target = Vector3(3.0, 1.0, -2.0)

    var invalid := DraftLight.default_spec("Point")
    invalid["range"] = 0.1
    if not DraftLight.validate(invalid, "Point").is_empty():
        _fail("Light validator accepted an out-of-range point light")
        return
    invalid = DraftLight.default_spec("Spot")
    invalid["color"][0] = -0.1
    if not DraftLight.validate(invalid, "Spot").is_empty():
        _fail("Light validator accepted a negative color channel")
        return
    if not DraftLight.default_spec("Directional").is_empty():
        _fail("Unsupported light type was accepted")
        return

    editor.draft_light_kind_control.select(0)
    editor._add_draft_light()
    var point_name := "DraftProp_1"
    var point: MeshInstance3D = editor.draft_prop_copies.get(point_name, null)
    if not is_instance_valid(point) or not editor.draft_light_specs.has(point_name):
        _fail("Add draft Point did not create an editable private marker")
        return
    var point_light := point.get_node_or_null(LIGHT_NODE) as OmniLight3D
    if not is_instance_valid(point_light):
        _fail("Point draft did not create an OmniLight3D preview child")
        return
    if not editor.draft_light_panel.visible or editor.draft_light_angle_row.visible:
        _fail("Point light Inspector visibility or spot-only controls are incorrect")
        return

    editor._draft_light_value_changed(Color(0.18, 0.42, 1.0, 1.0), "color")
    editor._draft_light_value_changed(2.5, "energy")
    editor._draft_light_value_changed(12.0, "range")
    editor._draft_light_value_changed(true, "shadows")
    if (not point_light.light_color.is_equal_approx(Color(0.18, 0.42, 1.0, 1.0))
        or not is_equal_approx(point_light.light_energy, 2.5)
        or not is_equal_approx(point_light.omni_range, 12.0)
        or not point_light.shadow_enabled):
        _fail("Point Inspector did not apply color, energy, range or shadow settings")
        return
    editor._draft_light_value_changed(3.0, "energy")
    editor._undo_edit()
    point = editor.draft_prop_copies.get(point_name, null)
    point_light = point.get_node_or_null(LIGHT_NODE) as OmniLight3D
    if not is_equal_approx(point_light.light_energy, 2.5):
        _fail("Undo did not restore the previous point light energy")
        return
    editor._redo_edit()
    point = editor.draft_prop_copies.get(point_name, null)
    point_light = point.get_node_or_null(LIGHT_NODE) as OmniLight3D
    if not is_equal_approx(point_light.light_energy, 3.0):
        _fail("Redo did not restore the new point light energy")
        return

    editor.draft_light_kind_control.select(1)
    editor._add_draft_light()
    var spot_name := "DraftProp_2"
    var spot: MeshInstance3D = editor.draft_prop_copies.get(spot_name, null)
    if not is_instance_valid(spot) or not editor.draft_light_specs.has(spot_name):
        _fail("Add draft Spot did not create a private marker")
        return
    var spot_light := spot.get_node_or_null(LIGHT_NODE) as SpotLight3D
    if not is_instance_valid(spot_light):
        _fail("Spot draft did not create a SpotLight3D preview child")
        return
    if not editor.draft_light_panel.visible or not editor.draft_light_angle_row.visible:
        _fail("Spot light Inspector did not expose its cone-angle control")
        return
    editor._draft_light_value_changed(55.0, "spot_angle")
    editor._draft_light_value_changed(false, "enabled")
    if (not is_equal_approx(spot_light.spot_angle, 55.0)
        or spot_light.visible):
        _fail("Spot cone angle or enabled toggle did not reach the Godot light node")
        return
    editor._draft_light_value_changed(true, "enabled")

    editor._select_mesh_only(point)
    editor._add_selection_mesh(spot)
    editor.group_name_edit.text = "LightRig"
    editor._group_selected()
    if (not editor.draft_groups.has("LightRig")
        or editor._selection_transform_targets().size() != 1):
        _fail("Point and Spot lights could not join an editor-private parent group")
        return

    editor.category_filter.select(3)
    editor._refresh_hierarchy()
    if not editor.hierarchy_items.has(point_name) or not editor.hierarchy_items.has(spot_name):
        _fail("Lights category did not list the private Point and Spot drafts")
        return
    editor.category_filter.select(0)
    editor._refresh_hierarchy()

    editor._save_prop_draft()
    var draft_path := editor._draft_file_path()
    if draft_path.is_empty() or not FileAccess.file_exists(draft_path):
        _fail("Private light draft did not save")
        return
    var saved_json := FileAccess.get_file_as_string(draft_path)
    var saved_doc: Variant = JSON.parse_string(saved_json)
    if (typeof(saved_doc) != TYPE_DICTIONARY
        or saved_doc.get("copies", []).size() != 2
        or saved_doc["copies"][0].get("light", {}).is_empty()
        or saved_doc["copies"][1].get("light", {}).is_empty()
        or saved_doc.get("groups", []).size() != 1):
        _fail("Private JSON did not persist both light specifications and their group")
        return
    var saved_group_transform: Transform3D = editor.draft_groups["LightRig"].global_transform
    var saved_point_spec: Dictionary = editor.draft_light_specs[point_name].duplicate(true)
    var saved_spot_spec: Dictionary = editor.draft_light_specs[spot_name].duplicate(true)

    editor._ungroup_selected()
    if editor.draft_groups.has("LightRig"):
        _fail("Ungroup did not remove the private light group")
        return
    editor._load_prop_draft(true)
    if (not editor.draft_groups.has("LightRig")
        or not editor.draft_groups["LightRig"].global_transform.is_equal_approx(saved_group_transform)
        or editor.draft_light_specs.get(point_name, {}) != saved_point_spec
        or editor.draft_light_specs.get(spot_name, {}) != saved_spot_spec):
        _fail("Private Save/reopen did not restore the Point/Spot specs and group transform")
        return
    point = editor.draft_prop_copies.get(point_name, null)
    spot = editor.draft_prop_copies.get(spot_name, null)
    point_light = point.get_node_or_null(LIGHT_NODE) as OmniLight3D
    spot_light = spot.get_node_or_null(LIGHT_NODE) as SpotLight3D
    if (not is_instance_valid(point_light) or not is_instance_valid(spot_light)
        or not is_equal_approx(point_light.omni_range, 12.0)
        or not is_equal_approx(spot_light.spot_angle, 55.0)
        or not point_light.shadow_enabled):
        _fail("Reopened private light specs were not applied to the real Godot light nodes")
        return

    # A malformed light must be refused before the current scene is mutated.
    var stable_group_transform: Transform3D = editor.draft_groups["LightRig"].global_transform
    var bad_doc: Dictionary = JSON.parse_string(saved_json)
    for entry in bad_doc["copies"]:
        if entry.get("from_actor", "") == "Light::Point":
            entry["light"]["energy"] = 999.0
    if not _write_document(draft_path, JSON.stringify(bad_doc)):
        _fail("Could not write malicious light-energy fixture")
        return
    editor._load_prop_draft(true)
    if (not editor.draft_groups.has("LightRig")
        or not editor.draft_groups["LightRig"].global_transform.is_equal_approx(stable_group_transform)
        or editor.draft_light_specs.get(point_name, {}) != saved_point_spec):
        _fail("Out-of-range light metadata mutated the live editor before rejection")
        return
    bad_doc = JSON.parse_string(saved_json)
    for entry in bad_doc["copies"]:
        if entry.get("from_actor", "") == "Light::Spot":
            entry["light"]["color"][0] = -0.25
    if not _write_document(draft_path, JSON.stringify(bad_doc)):
        _fail("Could not write malicious light-color fixture")
        return
    editor._load_prop_draft(true)
    if editor.draft_light_specs.get(spot_name, {}) != saved_spot_spec:
        _fail("Negative light color mutated the live editor before rejection")
        return
    if not _write_document(draft_path, saved_json):
        _fail("Could not restore the valid private light document")
        return

    editor._duplicate_selected_prop()
    if editor.draft_light_specs.size() != 4 or editor.draft_groups.size() != 2:
        _fail("Duplicating the selected light group did not duplicate its light specs and parent")
        return
    editor._undo_edit()
    if editor.draft_light_specs.size() != 2 or editor.draft_groups.size() != 1:
        _fail("Undo did not remove the duplicated light group")
        return
    editor._redo_edit()
    if editor.draft_light_specs.size() != 4 or editor.draft_groups.size() != 2:
        _fail("Redo did not restore the duplicated light group")
        return
    editor._reset_selected_prop()
    if editor.draft_light_specs.size() != 2 or editor.draft_groups.size() != 1:
        _fail("Reset did not remove only the duplicated private light group")
        return

    for suffix in ["", ".bak", ".pending"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    editor.queue_free()
    print("DX2Ed v0.57 private Point/Spot lights, Inspector, shadow budget, transforms, hierarchy, Undo/Redo, group duplication, private JSON reopen and malicious preflight PASS")
    quit(0)
