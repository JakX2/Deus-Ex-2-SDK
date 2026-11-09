extends SceneTree
## Synthetic UI and provenance smoke for the read-only MatLib browser.
## All textures are generated here; no original retail data is included.

const Browser = preload("res://matlib_browser.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.45 MatLib stage-mask audit: " + message)
    quit(1)


func _write_json(path: String, value: Dictionary) -> void:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        _fail("Could not write synthetic catalog.")
        return
    file.store_string(JSON.stringify(value))
    file.close()


func _run() -> void:
    var root_path := ProjectSettings.globalize_path(
        "user://dx2ed_material_cache/matlib_browser_smoke")
    var preview_dir := root_path.path_join("previews")
    if DirAccess.make_dir_recursive_absolute(preview_dir) != OK:
        _fail("Could not create synthetic preview directory.")
        return
    var image := Image.create(4, 4, false, Image.FORMAT_RGBA8)
    image.fill(Color(0.2, 0.7, 0.9, 1.0))
    var png_path := preview_dir.path_join("diffuse.png")
    if image.save_png(png_path) != OK:
        _fail("Could not write synthetic PNG preview.")
        return
    var preview_sha := FileAccess.get_sha256(png_path).to_lower()
    var normal_image := Image.create(4, 4, false, Image.FORMAT_RGBA8)
    normal_image.fill(Color(0.45, 0.8, 0.45, 1.0))
    var normal_png_path := preview_dir.path_join("normal.png")
    if normal_image.save_png(normal_png_path) != OK:
        _fail("Could not write synthetic normal-usage PNG preview.")
        return
    var normal_preview_sha := FileAccess.get_sha256(normal_png_path).to_lower()

    var source_path := root_path.path_join("synthetic.ibd")
    var source_file := FileAccess.open(source_path, FileAccess.WRITE)
    if source_file == null:
        _fail("Could not create synthetic source identity sentinel.")
        return
    source_file.store_buffer(PackedByteArray([68, 88, 50, 73, 66, 68]))
    source_file.close()
    var source_sha := FileAccess.get_sha256(source_path).to_lower()

    var stages: Array = []
    for index in range(9):
        if index == 0:
            stages.append({
                "index": index,
                "name": "T_SYNTH_DIFFUSE",
                "resolved": true,
                "texture": {
                    "name": "T_SYNTH_DIFFUSE",
                    "format": "BGRA8",
                    "width": 4,
                    "height": 4,
                    "usage_code": 0,
                    "usage": "diffuse",
                    "source_bundle": "synthetic.ibd",
                    "preview_path": "previews/diffuse.png",
                    "preview_sha256": preview_sha
                }
            })
        elif index == 1:
            stages.append({"index": index, "name": "T_MISSING", "resolved": false})
        elif index == 2:
            stages.append({
                "index": index,
                "name": "T_SYNTH_NORMAL",
                "resolved": true,
                "texture": {
                    "name": "T_SYNTH_NORMAL",
                    "format": "BGRA8",
                    "width": 4,
                    "height": 4,
                    "usage_code": 1,
                    "usage": "normal",
                    "source_bundle": "synthetic.ibd",
                    "preview_path": "previews/normal.png",
                    "preview_sha256": normal_preview_sha
                }
            })
        else:
            stages.append({"index": index, "name": "", "resolved": false})

    var material := {
        "name": "M_SYNTH_METAL",
        "source_bundle": "synthetic.ibd",
        "source": "synthetic fixture",
        "version": 1,
        "flags": 3,
        "stage_mask": 7,
        "category_id": 7,
        "colors": [],
        "params": [],
        "stages": stages
    }
    var mismatch_stages: Array = []
    for index in range(9):
        if index == 0 or index == 2:
            mismatch_stages.append(stages[index].duplicate(true))
        else:
            mismatch_stages.append({"index": index, "name": "", "resolved": false})
    var mismatch_material: Dictionary = material.duplicate(true)
    mismatch_material["name"] = "M_SYNTH_MISMATCH"
    mismatch_material["stage_mask"] = 0x201
    mismatch_material["stages"] = mismatch_stages

    var catalog := {
        "schema": "DX2Ed-MatLib-catalog-v1",
        "read_only": true,
        "native_writer_enabled": false,
        "source_bytes_modified": false,
        "catalog_id": "a".repeat(64),
        "source_files": [{"path": source_path, "sha256": source_sha, "bytes": 6}],
        "materials": [material, mismatch_material],
        "material_count": 2,
        "texture_count": 2,
        "preview_count": 2,
        "unresolved_stage_count": 1
    }
    var catalog_path := root_path.path_join("catalog.json")
    _write_json(catalog_path, catalog)

    var browser := Browser.new()
    root.add_child(browser)
    if not browser.load_catalog(catalog_path):
        _fail("Valid source-backed synthetic catalog was rejected.")
        return
    if browser.materials.size() != 2:
        _fail("Material records were not loaded.")
        return

    browser.search_box.text = "metal"
    browser._refresh_list()
    if browser.visible_materials.size() != 1:
        _fail("Material search did not filter by name.")
        return
    browser.filter_selector.select(1)
    browser._refresh_list()
    if browser.visible_materials.size() != 1:
        _fail("Resolved diffuse filter did not retain the material.")
        return
    browser.material_list.select(0)
    browser._material_selected(0)
    if browser.apply_button.disabled or browser.selected_diffuse_assignment().is_empty():
        _fail("Resolved slot-0 preview candidate did not enable the private Polygon preview action.")
        return
    if browser.stage_grid.get_child_count() != 9:
        _fail("Browser did not display all nine MatLib slots.")
        return
    if browser._preview_texture(browser.selected_material["stages"][0]) == null:
        _fail("Verified source texture thumbnail did not load.")
        return
    if browser._preview_texture(browser.selected_material["stages"][2]) == null:
        _fail("Verified second-stage usage preview did not load.")
        return
    if not browser.stage_audit_label.text.contains("Raw stage_mask: 0x00000007 (uninterpreted)"):
        _fail("Raw stage mask was not presented explicitly as uninterpreted.")
        return
    if not browser.stage_audit_label.text.contains("3 named, 2 resolved, 1 unresolved, 6 empty"):
        _fail("Nine-slot raw reference/resolution counts are incorrect.")
        return
    if not browser.details_label.text.contains("diffuse shader semantics are unverified"):
        _fail("Slot-0 preview candidate was presented as verified shader semantics.")
        return
    if not browser.details_label.text.contains("Named-slot mask (derived): 0x007"):
        _fail("Per-material named-slot mask was not derived from non-empty slot names.")
        return
    if not browser.details_label.text.contains("Low-nine XOR: 0x000 (exact match; candidate only)"):
        _fail("Per-material raw mask/slot comparison was not reported as a candidate only.")
        return

    var worker_path := ProjectSettings.globalize_path("res://backend/dx2_matlib_catalog.py")
    var help_output: Array = []
    if browser._execute_python_worker(
        worker_path, PackedStringArray(["--help"]), help_output) != 0:
        _fail("Launcher-verified Python did not invoke the MatLib worker script.")
        return
    if not str(help_output).contains("--audit-catalog"):
        _fail("MatLib worker help did not expose the read-only audit mode.")
        return
    if not browser._run_catalog_stage_mask_audit():
        _fail("Catalog-wide stage-mask / slot audit failed.")
        return
    if (not browser.catalog_audit_label.text.contains("Materials: 2")
        or not browser.catalog_audit_label.text.contains("exact low-nine matches: 1")
        or not browser.catalog_audit_label.text.contains("mismatches: 1")
        or not browser.catalog_audit_label.text.contains("Records with high bits set: 1")):
        _fail("Catalog-wide stage-mask audit did not report exact, mismatch and high-bit controls.")
        return

    browser.filter_selector.select(5)
    browser._refresh_list()
    if browser.visible_materials.size() != 1:
        _fail("Parser usage-code 1 filter did not find the synthetic normal-usage resource.")
        return
    browser.filter_selector.select(10)
    browser._refresh_list()
    if not browser.visible_materials.is_empty():
        _fail("Parser usage-code 6 filter fabricated an environment resource match.")
        return

    var hostile: Dictionary = catalog.duplicate(true)
    hostile["materials"][0]["stages"][0]["texture"]["preview_path"] = "../outside.png"
    var hostile_path := root_path.path_join("hostile.json")
    _write_json(hostile_path, hostile)
    if browser.load_catalog(hostile_path):
        _fail("Path-traversing thumbnail reference passed catalog validation.")
        return
    if browser.materials.size() != 2:
        _fail("Rejected catalog destroyed the last valid browser state.")
        return

    var tampered: Dictionary = catalog.duplicate(true)
    tampered["materials"][0]["stages"][0]["texture"]["preview_sha256"] = "0".repeat(64)
    var tampered_path := root_path.path_join("tampered.json")
    _write_json(tampered_path, tampered)
    if not browser.load_catalog(tampered_path):
        _fail("Structurally valid tampered catalog should load metadata.")
        return
    if browser._preview_texture(browser.materials[0]["stages"][0]) != null:
        _fail("Modified thumbnail bytes passed SHA-256 verification.")
        return

    print("DX2Ed v0.45 MatLib stage-mask / slot correspondence audit smoke: PASS")
    quit(0)
