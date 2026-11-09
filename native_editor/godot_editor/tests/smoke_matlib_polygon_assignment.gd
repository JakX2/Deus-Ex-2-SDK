extends SceneTree
## End-to-end source-backed diffuse assignment to multiple private Polygon surfaces.
## All IBD identity bytes and texture pixels are invented synthetic fixtures.

const Editor = preload("res://main.gd")
const MatLibBrowser = preload("res://matlib_browser.gd")
const CustomPolygon = preload("res://custom_polygon_geometry.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.43 MatLib batch-to-Polygon assignment: " + message)
    quit(1)


func _write_json(path: String, value: Dictionary) -> void:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        _fail("Could not write synthetic JSON fixture.")
        return
    file.store_string(JSON.stringify(value, "  "))
    file.close()


func _run() -> void:
    var root_path := ProjectSettings.globalize_path(
        "user://dx2ed_material_cache/smoke_assignment")
    var preview_dir := root_path.path_join("previews")
    if (DirAccess.make_dir_recursive_absolute(preview_dir) != OK
        and not DirAccess.dir_exists_absolute(preview_dir)):
        _fail("Could not create isolated preview cache.")
        return

    var source_path := root_path.path_join("synthetic.ibd")
    var source_bytes := PackedByteArray([68, 88, 50, 77, 97, 116, 76, 105, 98, 42])
    var source_file := FileAccess.open(source_path, FileAccess.WRITE)
    if source_file == null:
        _fail("Could not create invented source sentinel.")
        return
    source_file.store_buffer(source_bytes)
    source_file.close()
    var source_sha := FileAccess.get_sha256(source_path).to_lower()

    var image := Image.create(8, 8, false, Image.FORMAT_RGBA8)
    image.fill(Color(0.2, 0.7, 0.9, 1.0))
    var preview_path := preview_dir.path_join("diffuse.png")
    if image.save_png(preview_path) != OK:
        _fail("Could not create synthetic diffuse thumbnail.")
        return
    var preview_sha := FileAccess.get_sha256(preview_path).to_lower()

    var stages: Array = []
    for index in range(9):
        if index == 0:
            stages.append({
                "index": 0,
                "name": "T_SYNTH_DIFFUSE",
                "resolved": true,
                "texture": {
                    "name": "T_SYNTH_DIFFUSE",
                    "format": "BGRA8",
                    "width": 8,
                    "height": 8,
                    "usage": "diffuse",
                    "detail": 0,
                    "source_bundle": "synthetic.ibd",
                    "preview_path": "previews/diffuse.png",
                    "preview_sha256": preview_sha
                }
            })
        elif index == 1:
            stages.append({"index": 1, "name": "T_SYNTH_MISSING", "resolved": false})
        else:
            stages.append({"index": index, "name": "", "resolved": false})

    var material := {
        "name": "M_SYNTH_METAL",
        "source_bundle": "synthetic.ibd",
        "source": "synthetic fixture",
        "version": 1,
        "flags": 3,
        "stage_mask": 1,
        "category_id": 7,
        "colors": [],
        "params": [],
        "stages": stages
    }
    var catalog := {
        "schema": "DX2Ed-MatLib-catalog-v1",
        "read_only": true,
        "native_writer_enabled": false,
        "source_bytes_modified": false,
        "asset_payloads_included": false,
        "catalog_id": "b".repeat(64),
        "source_files": [{
            "path": source_path,
            "sha256": source_sha,
            "bytes": source_bytes.size()
        }],
        "materials": [material],
        "material_count": 1,
        "texture_count": 1,
        "preview_count": 1,
        "unresolved_stage_count": 1
    }
    var catalog_path := root_path.path_join("catalog.json")
    _write_json(catalog_path, catalog)
    if not FileAccess.file_exists(catalog_path):
        _fail("Synthetic MatLib catalog was not written.")
        return

    var editor := Editor.new()
    root.add_child(editor)
    var fake_scene := Node3D.new()
    editor.world_root.add_child(fake_scene)
    editor.scene_root = fake_scene
    editor.current_folder = ProjectSettings.globalize_path(
        "user://dx2ed_matlib_polygon_assignment_map")
    var draft := editor._new_draft_copy(
        "Brush::Polygon", "DraftProp_42", Transform3D.IDENTITY)
    var second_draft := editor._new_draft_copy(
        "Brush::Polygon", "DraftProp_43", Transform3D(Basis.IDENTITY, Vector3(3.0, 0.0, 0.0)))
    var box_draft := editor._new_draft_copy(
        "Brush::Box", "DraftProp_44", Transform3D.IDENTITY)
    if (not is_instance_valid(draft) or not is_instance_valid(second_draft)
        or not is_instance_valid(box_draft)):
        _fail("Could not create the two Polygon targets and mixed-selection Box fixture.")
        return
    editor._clear_selection()
    editor._add_selection_mesh(draft)
    editor._add_selection_mesh(second_draft)
    editor._refresh_selection_inspector()

    var browser = editor.matlib_browser
    if browser == null or not browser.load_catalog(catalog_path):
        _fail("Actual Materials workspace rejected the synthetic catalog.")
        return
    browser.search_box.text = "M_SYNTH_METAL"
    browser._refresh_list()
    if browser.visible_materials.size() != 1:
        _fail("Materials workspace search did not find the synthetic material.")
        return
    browser.material_list.select(0)
    browser._material_selected(0)
    if browser.selected_diffuse_assignment().is_empty():
        _fail("Resolved diffuse did not produce a source-pinned assignment.")
        return

    browser.target_slot_selector.select(2)
    var history_before := editor.undo_stack.size()
    browser._request_apply_selected_material()
    var spec_a: Dictionary = editor.draft_brush_specs["DraftProp_42"]
    var spec_b: Dictionary = editor.draft_brush_specs["DraftProp_43"]
    var assignment_a: Dictionary = spec_a["surface_style"]["sides"]["source_material"]
    var assignment_b: Dictionary = spec_b["surface_style"]["sides"]["source_material"]
    var mesh_a := editor.draft_prop_copies["DraftProp_42"].mesh as ArrayMesh
    var mesh_b := editor.draft_prop_copies["DraftProp_43"].mesh as ArrayMesh
    var side_material_a := mesh_a.surface_get_material(2) as StandardMaterial3D
    var side_material_b := mesh_b.surface_get_material(2) as StandardMaterial3D
    if (editor.undo_stack.size() != history_before + 1
        or assignment_a.is_empty() or assignment_b != assignment_a
        or assignment_a["catalog_id"] != "b".repeat(64)
        or assignment_a["catalog_sha256"] != FileAccess.get_sha256(catalog_path).to_lower()
        or assignment_a["preview_sha256"] != preview_sha
        or side_material_a == null or side_material_b == null
        or side_material_a.albedo_texture == null or side_material_b.albedo_texture == null
        or side_material_a.albedo_texture.get_image().get_width() != 8
        or side_material_b.albedo_texture.get_image().get_width() != 8
        or mesh_a.surface_get_material(0) == side_material_a
        or mesh_a.surface_get_material(1) == side_material_a
        or mesh_b.surface_get_material(0) == side_material_b
        or mesh_b.surface_get_material(1) == side_material_b):
        _fail("Diffuse was not assigned to both selected Polygon side slots as one undoable batch.")
        return

    # A mixed selection must reject the whole operation without changing either Polygon.
    editor._clear_selection()
    editor._add_selection_mesh(draft)
    editor._add_selection_mesh(box_draft)
    var mixed_history_before := editor.undo_stack.size()
    browser._request_apply_selected_material()
    if (editor.undo_stack.size() != mixed_history_before
        or editor.draft_brush_specs["DraftProp_42"]["surface_style"]["sides"]["source_material"] != assignment_a
        or editor.draft_brush_specs["DraftProp_43"]["surface_style"]["sides"]["source_material"] != assignment_b
        or not editor.draft_brush_specs["DraftProp_44"].get("surface_style", {}).is_empty()):
        _fail("Mixed Polygon/Box selection was not refused atomically.")
        return
    editor._clear_selection()
    editor._add_selection_mesh(draft)
    editor._add_selection_mesh(second_draft)
    editor._refresh_selection_inspector()

    editor._undo_edit()
    if (not editor.draft_brush_specs["DraftProp_42"]["surface_style"]["sides"]["source_material"].is_empty()
        or not editor.draft_brush_specs["DraftProp_43"]["surface_style"]["sides"]["source_material"].is_empty()):
        _fail("Batch Undo did not restore both procedural side slots.")
        return
    editor._redo_edit()
    if (editor.draft_brush_specs["DraftProp_42"]["surface_style"]["sides"]["source_material"].is_empty()
        or editor.draft_brush_specs["DraftProp_43"]["surface_style"]["sides"]["source_material"].is_empty()):
        _fail("Batch Redo did not restore both source identities.")
        return

    var draft_path := editor._draft_file_path()
    if draft_path.is_empty():
        _fail("Private project path was unavailable.")
        return
    for suffix in ["", ".bak", ".pending"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    editor._save_prop_draft()
    if not FileAccess.file_exists(draft_path):
        _fail("Private JSON Save did not persist the material assignment.")
        return
    var saved: Variant = JSON.parse_string(FileAccess.get_file_as_string(draft_path))
    if typeof(saved) != TYPE_DICTIONARY or saved.get("copies", []).size() != 3:
        _fail("Private JSON Save did not persist both Polygon targets and the Box fixture.")
        return
    var saved_by_name: Dictionary = {}
    for saved_copy in saved["copies"]:
        saved_by_name[str(saved_copy.get("name", ""))] = saved_copy
    if (not saved_by_name.has("DraftProp_42") or not saved_by_name.has("DraftProp_43")
        or saved_by_name["DraftProp_42"]["brush"]["surface_style"]["sides"]["source_material"]["preview_sha256"] != preview_sha
        or saved_by_name["DraftProp_43"]["brush"]["surface_style"]["sides"]["source_material"]["preview_sha256"] != preview_sha):
        _fail("Saved project omitted one or both source material/thumbnail identities.")
        return

    editor._select_mesh_only(draft)
    editor._clear_polygon_surface_source_material()
    if not editor.draft_brush_specs["DraftProp_42"]["surface_style"]["sides"]["source_material"].is_empty():
        _fail("Clear source diffuse did not remove the selected slot assignment.")
        return
    var saved_assignment: Dictionary = saved_by_name["DraftProp_42"]["brush"]["surface_style"]["sides"]["source_material"]
    var saved_assignment_b: Dictionary = saved_by_name["DraftProp_43"]["brush"]["surface_style"]["sides"]["source_material"]
    if CustomPolygon.validate_source_material_assignment(saved_assignment).is_empty():
        _fail("Serialized source assignment failed structural preflight: " + JSON.stringify(saved_assignment))
        return
    if MatLibBrowser.load_assignment_texture(saved_assignment) == null:
        _fail("Serialized source assignment could not re-verify its catalog/thumbnail.")
        return
    editor._load_prop_draft()
    if (not editor.draft_brush_specs.has("DraftProp_42")
        or not editor.draft_brush_specs.has("DraftProp_43")
        or editor.draft_brush_specs["DraftProp_42"]["surface_style"]["sides"]["source_material"].is_empty()
        or editor.draft_brush_specs["DraftProp_43"]["surface_style"]["sides"]["source_material"].is_empty()
        or editor._selection_nodes().size() != 2):
        _fail("Private project reopen did not restore both source assignments and the multi-selection: " + editor.status_label.text)
        return
    var reopened_mesh := editor.draft_prop_copies["DraftProp_42"].mesh as ArrayMesh
    var reopened_material := reopened_mesh.surface_get_material(2) as StandardMaterial3D
    var reopened_mesh_b := editor.draft_prop_copies["DraftProp_43"].mesh as ArrayMesh
    var reopened_material_b := reopened_mesh_b.surface_get_material(2) as StandardMaterial3D
    if (reopened_material == null or reopened_material.albedo_texture == null
        or reopened_material.albedo_texture.get_image().get_width() != 8
        or reopened_material_b == null or reopened_material_b.albedo_texture == null
        or reopened_material_b.albedo_texture.get_image().get_width() != 8):
        _fail("Private project reopen did not re-verify and restore both diffuse preview textures.")
        return

    # A changed thumbnail must not silently keep rendering as the source texture.
    var changed_image := Image.create(8, 8, false, Image.FORMAT_RGBA8)
    changed_image.fill(Color(0.9, 0.1, 0.2, 1.0))
    if changed_image.save_png(preview_path) != OK:
        _fail("Could not write the tampered preview fixture.")
        return
    if MatLibBrowser.load_assignment_texture(assignment) != null:
        _fail("Tampered source thumbnail passed its recorded SHA-256.")
        return
    editor.polygon_source_texture_cache.clear()
    editor._set_brush_spec(
        "DraftProp_42", editor.draft_brush_specs["DraftProp_42"])
    var fallback_mesh := editor.draft_prop_copies["DraftProp_42"].mesh as ArrayMesh
    var fallback_material := fallback_mesh.surface_get_material(2) as StandardMaterial3D
    if (fallback_material == null or fallback_material.albedo_texture == null
        or fallback_material.albedo_texture.get_image().get_width() != 64):
        _fail("Changed thumbnail did not fall back to the procedural checker.")
        return

    # Malformed provenance is rejected before the existing editor scene is cleared.
    var malformed: Variant = JSON.parse_string(FileAccess.get_file_as_string(draft_path))
    var malformed_target_found := false
    for malformed_copy in malformed.get("copies", []):
        if str(malformed_copy.get("name", "")) == "DraftProp_42":
            malformed_copy["brush"]["surface_style"]["sides"]["source_material"].erase("preview_sha256")
            malformed_target_found = true
    if not malformed_target_found:
        _fail("Could not find the first Polygon in the saved document for malformed-preflight coverage.")
        return
    _write_json(draft_path, malformed)
    var retained_node: MeshInstance3D = editor.draft_prop_copies["DraftProp_42"]
    var retained_assignment: Dictionary = editor.draft_brush_specs["DraftProp_42"]["surface_style"]["sides"]["source_material"].duplicate(true)
    editor._load_prop_draft()
    if (editor.draft_prop_copies.get("DraftProp_42", null) != retained_node
        or editor.draft_brush_specs["DraftProp_42"]["surface_style"]["sides"]["source_material"] != retained_assignment):
        _fail("Malformed assignment preflight cleared or changed the existing editor scene.")
        return
    if FileAccess.get_sha256(source_path).to_lower() != source_sha:
        _fail("Synthetic source IBD sentinel changed during preview authoring.")
        return

    print("DX2Ed v0.43 source-backed MatLib diffuse batch to private Polygon surfaces PASS")
    quit(0)
