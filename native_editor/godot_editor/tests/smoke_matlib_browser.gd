extends SceneTree
## Synthetic UI and provenance smoke for the read-only MatLib browser.
## All textures are generated here; no original retail data is included.

const Browser = preload("res://matlib_browser.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.41 MatLib browser: " + message)
    quit(1)


func _write_json(path: String, value: Dictionary) -> void:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        _fail("Could not write synthetic catalog.")
        return
    file.store_string(JSON.stringify(value))
    file.close()


func _run() -> void:
    var root_path := ProjectSettings.globalize_path("user://dx2ed_matlib_browser_smoke")
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
                    "usage": "diffuse",
                    "source_bundle": "synthetic.ibd",
                    "preview_path": "previews/diffuse.png",
                    "preview_sha256": preview_sha
                }
            })
        elif index == 1:
            stages.append({"index": index, "name": "T_MISSING", "resolved": false})
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
        "source_files": [{"path": "synthetic.ibd", "sha256": "a".repeat(64), "bytes": 128}],
        "materials": [material],
        "material_count": 1,
        "texture_count": 1,
        "preview_count": 1,
        "unresolved_stage_count": 1
    }
    var catalog_path := root_path.path_join("catalog.json")
    _write_json(catalog_path, catalog)

    var browser := Browser.new()
    root.add_child(browser)
    if not browser.load_catalog(catalog_path):
        _fail("Valid source-backed synthetic catalog was rejected.")
        return
    if browser.materials.size() != 1:
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
    if browser.stage_grid.get_child_count() != 9:
        _fail("Browser did not display all nine stage slots.")
        return
    if browser._preview_texture(browser.selected_material["stages"][0]) == null:
        _fail("Verified source texture thumbnail did not load.")
        return

    var hostile: Dictionary = catalog.duplicate(true)
    hostile["materials"][0]["stages"][0]["texture"]["preview_path"] = "../outside.png"
    var hostile_path := root_path.path_join("hostile.json")
    _write_json(hostile_path, hostile)
    if browser.load_catalog(hostile_path):
        _fail("Path-traversing thumbnail reference passed catalog validation.")
        return
    if browser.materials.size() != 1:
        _fail("Rejected catalog destroyed the last valid browser state.")
        return

    var tampered: Dictionary = catalog.duplicate(true)
    tampered["materials"][0]["stages"][0]["texture"]["preview_sha256"] = "0".repeat(64)
    var tampered_path := root_path.path_join("tampered.json")
    _write_json(tampered_path, tampered)
    if not browser.load_catalog(tampered_path):
        _fail("Structurally valid tampered catalog should load metadata.")
        return
    if browser._preview_texture(browser.selected_material.get("stages", stages)[0]) != null:
        _fail("Modified thumbnail bytes passed SHA-256 verification.")
        return

    print("DX2Ed v0.41 source-backed MatLib browser smoke: PASS")
    quit(0)
