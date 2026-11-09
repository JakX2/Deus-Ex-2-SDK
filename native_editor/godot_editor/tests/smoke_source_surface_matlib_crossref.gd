extends SceneTree
## Synthetic Godot 4.3 tests for source MOPP render-section → MatLib name correlation.
const Panel = preload("res://source_surface_matlib_crossref.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed source-surface MatLib cross-reference smoke: " + message)
    quit(1)

func _write_json(path: String, value: Dictionary) -> void:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        _fail("Could not write synthetic catalog.")
        return
    file.store_string(JSON.stringify(value, "  "))
    file.close()

func _stage(index: int, name: String, texture: Dictionary = {}) -> Dictionary:
    var record := {"index": index, "name": name, "resolved": not texture.is_empty()}
    if not texture.is_empty():
        record["texture"] = texture
    return record

func _material(name: String, bundle: String, preview_path: String, preview_sha: String) -> Dictionary:
    var texture := {
        "name": "TexFixture", "format": "BGRA8", "width": 4, "height": 4,
        "usage_code": 0, "usage": "diffuse", "detail": 0,
        "source_bundle": bundle, "preview_path": preview_path,
        "preview_sha256": preview_sha, "preview_omitted_reason": ""
    }
    var stages: Array = [_stage(0, "TexFixture", texture)]
    for index in range(1, 9):
        stages.append(_stage(index, ""))
    return {
        "name": name, "source_bundle": bundle, "source": "synthetic fixture",
        "version": 1, "flags": 3, "stage_mask": 1, "category_id": 7,
        "colors": [], "params": [], "stages": stages
    }

func _catalog(materials: Array, duplicate_count: int = 0) -> Dictionary:
    return {
        "schema": "DX2Ed-MatLib-catalog-v1",
        "read_only": true, "native_writer_enabled": false,
        "source_bytes_modified": false, "asset_payloads_included": false,
        "preview_files_included": true, "catalog_id": "a".repeat(64),
        "source_files": [{"path": "fixture.ibd", "sha256": SHA, "bytes": 64}],
        "source_bundles": ["fixture.ibd"],
        "material_count": materials.size(), "texture_count": 1, "preview_count": 1,
        "stage_reference_count": materials.size(), "unresolved_stage_count": 0,
        "duplicate_names": {"textures": 0, "materials": duplicate_count},
        "skipped_textures": [], "materials": materials, "textures": []
    }

func _evidence(name: String = "MatA") -> Dictionary:
    return {
        "schema": "DX2Ed-read-only-source-render-material-evidence-v1",
        "source_map": "Fixture.gmp", "source_sha256": SHA,
        "original_level_triangle_id": 17, "source_block_id": 2,
        "render_block_ordinal": 1, "render_section_ordinal": 3,
        "render_material_name": name, "source_section_triangle_count": 4,
        "selection_is_ray_hit": true,
        "render_material_is_physics_material": false,
        "native_map_written": false, "native_material_index_verified": false,
        "shader_semantics_verified": false
    }

func _run() -> void:
    var root_path := ProjectSettings.globalize_path("user://dx2ed_source_surface_matlib_crossref_smoke")
    var preview_dir := root_path.path_join("previews")
    if DirAccess.make_dir_recursive_absolute(preview_dir) != OK and not DirAccess.dir_exists_absolute(preview_dir):
        _fail("Could not create isolated preview directory.")
        return
    var image := Image.create(4, 4, false, Image.FORMAT_RGBA8)
    image.fill(Color(0.2, 0.7, 0.9, 1.0))
    var png_path := preview_dir.path_join("fixture.png")
    if image.save_png(png_path) != OK:
        _fail("Could not create synthetic thumbnail.")
        return
    var preview_sha := FileAccess.get_sha256(png_path)
    var catalog_path := root_path.path_join("catalog.json")
    var panel := Panel.new()
    root.add_child(panel)
    panel.initialize()
    if panel.visible:
        _fail("Cross-reference panel should start hidden.")
        return
    var catalog := _catalog([_material("MatA", "fixture.ibd", "previews/fixture.png", preview_sha)])
    _write_json(catalog_path, catalog)
    if not panel.set_catalog(catalog_path, catalog) or not panel.set_source_evidence(_evidence()):
        _fail("Valid synthetic catalog or source evidence was rejected.")
        return
    if (not panel.visible or panel.match_kind != "exact"
        or not panel.match_label.text.contains("EXACT STRING MATCH")
        or panel.candidate_list.item_count != 1
        or not panel.details_label.text.contains("Slot 0: TexFixture [resolved]")
        or not panel.details_label.text.contains("Native material index: NOT VERIFIED.")
        or panel.preview_rect.texture == null):
        _fail("Exact-name candidate, raw slots or hash-verified preview did not appear.")
        return
    var casefold_catalog := _catalog([_material("mata", "casefold.ibd", "previews/fixture.png", preview_sha)])
    _write_json(catalog_path, casefold_catalog)
    if not panel.set_catalog(catalog_path, casefold_catalog) or not panel.set_source_evidence(_evidence("MatA")):
        _fail("Case-fold catalog or source evidence was rejected.")
        return
    if panel.match_kind != "casefold" or not panel.match_label.text.contains("CASE-INSENSITIVE MATCH ONLY"):
        _fail("Case-insensitive candidate was not clearly distinguished.")
        return
    var ambiguous := _catalog([
        _material("MatA", "bundle-a.ibd", "previews/fixture.png", preview_sha),
        _material("MatA", "bundle-b.ibd", "previews/fixture.png", preview_sha)
    ])
    _write_json(catalog_path, ambiguous)
    if not panel.set_catalog(catalog_path, ambiguous) or not panel.set_source_evidence(_evidence()):
        _fail("Ambiguous catalog or source evidence was rejected.")
        return
    if panel.match_kind != "exact" or panel.candidate_list.item_count != 2 or not panel.match_label.text.contains("AMBIGUOUS"):
        _fail("Multiple exact-name candidates were not marked ambiguous.")
        return
    panel._candidate_selected(1)
    if not panel.details_label.text.contains("bundle-b.ibd"):
        _fail("Candidate selection did not inspect the chosen source bundle.")
        return
    var duplicates := _catalog([_material("MatA", "fixture.ibd", "previews/fixture.png", preview_sha)], 2)
    _write_json(catalog_path, duplicates)
    if not panel.set_catalog(catalog_path, duplicates) or not panel.set_source_evidence(_evidence()):
        _fail("Duplicate-name catalog or evidence was rejected.")
        return
    if not panel.match_label.text.contains("duplicate MatLib name collisions overall"):
        _fail("Catalog-wide duplicate-name caveat was not shown.")
        return
    if not panel.set_source_evidence(_evidence("NotInCatalog")):
        _fail("Valid unmatched source evidence was rejected.")
        return
    if panel.match_kind != "none" or not panel.match_label.text.contains("NO MATCH IN IMPORTED CATALOG"):
        _fail("Missing catalog match was not reported honestly.")
        return
    var invalid_evidence := _evidence()
    invalid_evidence["render_material_is_physics_material"] = true
    if panel.set_source_evidence(invalid_evidence):
        _fail("Unverified render material was accepted as a physics material.")
        return
    if panel.visible or not panel.source_evidence.is_empty():
        _fail("Rejected source evidence left stale cross-reference data visible.")
        return
    var hostile := _catalog([_material("MatA", "fixture.ibd", "../outside.png", preview_sha)])
    _write_json(catalog_path, hostile)
    if panel.set_catalog(catalog_path, hostile):
        _fail("Path-traversing preview path passed catalog preflight.")
        return
    print("DX2Ed source-surface MatLib exact/casefold/ambiguous/no-match and preview safety smoke: PASS")
    quit(0)
