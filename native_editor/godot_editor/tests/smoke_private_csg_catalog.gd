extends SceneTree
## P104: real editor catalog toolbar and registered recipe re-verification.
## All game-looking assets are invented test sentinels; preview GLB is demo.
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")
const Recipe = preload("res://private_csg_recipe_bridge.gd")
const Catalog = preload("res://private_csg_recipe_catalog.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(reason: String) -> void:
    push_error("P104 private CSG object manager: " + reason)
    quit(1)


func _write(path: String, bytes: PackedByteArray) -> bool:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_buffer(bytes)
    file.close()
    return FileAccess.file_exists(path)


func _run() -> void:
    var scratch := ProjectSettings.globalize_path("user://p104_csg_catalog_fixture")
    if DirAccess.make_dir_recursive_absolute(scratch) != OK:
        _fail("Cannot create private fixture directory")
        return
    var glb := scratch.path_join("synthetic_preview.glb")
    var original := scratch.path_join("original_sentinel.gmp")
    var first_path := scratch.path_join("first.dx2csg.json")
    var cavity_path := scratch.path_join("six_piece_cavity.dx2csg.json")
    var index := Catalog.catalog_path(scratch)
    var other_index := Catalog.catalog_path(scratch.path_join("other_project"))
    for path in [glb, original, first_path, cavity_path,
                 index, index + ".bak", index + ".pending",
                 other_index, other_index + ".bak"]:
        if FileAccess.file_exists(path):
            DirAccess.remove_absolute(path)
    var demo := ProjectSettings.globalize_path("res://demo/scene.glb")
    if (not FileAccess.file_exists(demo)
        or not _write(glb, FileAccess.get_file_as_bytes(demo))
        or not _write(original, "IMMUTABLE_SYNTHETIC_ORIGINAL_GMP_P104".to_utf8_buffer())):
        _fail("Cannot prepare synthetic demo GLB and original GMP sentinel")
        return
    var original_sha := FileAccess.get_sha256(original)
    var half := Brush.default_spec("Box")
    half["clip_plane"] = {
        "normal": [1.0, 0.0, 0.0],
        "distance": 0.0, "keep_positive": false}
    var large := Brush.default_spec("Box")
    large["size"] = [4.0, 4.0, 4.0]
    large["clip_plane"] = {
        "normal": [1.0, 0.0, 0.0],
        "distance": 1.0, "keep_positive": false}
    var shifted := Transform3D.IDENTITY
    shifted.origin = Vector3(0.5, 0., 0.)
    var cavity_shift := Transform3D.IDENTITY
    cavity_shift.origin = Vector3(-0.5, 0., 0.)
    var first := Recipe.save_recipe(first_path, "intersection",
        "DraftProp_104", "DraftProp_105", half, half,
        Transform3D.IDENTITY, shifted)
    var second := Recipe.save_recipe(cavity_path, "subtraction",
        "DraftProp_106", "DraftProp_107", large, half,
        Transform3D.IDENTITY, cavity_shift)
    if (not bool(first.get("ok", false)) or not bool(second.get("ok", false))):
        _fail("Source-private recipe fixture save failed: "
            + str(first) + str(second))
        return
    var first_sha := FileAccess.get_sha256(first_path)
    var cavity_sha := FileAccess.get_sha256(cavity_path)
    var editor := Editor.new()
    get_root().add_child(editor)
    editor.load_glb(glb)
    if (editor.current_folder != scratch or editor.scene_root == null
        or editor.private_csg_catalog_add_button == null
        or editor.private_csg_catalog_selector == null
        or editor.private_csg_catalog_refresh_button == null
        or editor.private_csg_catalog_remove_button == null
        or editor.private_csg_catalog_add_dialog == null
        or editor.private_csg_catalog_entries.size() != 0):
        _fail("Private CSG object manager did not initialize with demo project")
        return
    var undo_before := editor.undo_stack.size()
    editor.private_csg_catalog_add_button.pressed.emit()
    editor.private_csg_catalog_add_dialog.hide()
    editor.private_csg_catalog_add_dialog.file_selected.emit(first_path)
    if (not bool(editor.private_csg_catalog_last_result.get("ok", false))
        or editor.private_csg_catalog_entries.size() != 1
        or not FileAccess.file_exists(index)
        or editor.private_csg_catalog_selector.selected != 0):
        _fail("Add CSG recipe toolbar action failed: "
            + str(editor.private_csg_catalog_last_result))
        return
    # Duplicates may not silently appear, even when reselected via dialog.
    editor.private_csg_catalog_add_button.pressed.emit()
    editor.private_csg_catalog_add_dialog.hide()
    editor.private_csg_catalog_add_dialog.file_selected.emit(first_path)
    if (bool(editor.private_csg_catalog_last_result.get("ok", true))
        or editor.private_csg_catalog_entries.size() != 1):
        _fail("Duplicate private CSG catalog registration accepted")
        return
    editor.private_csg_catalog_add_button.pressed.emit()
    editor.private_csg_catalog_add_dialog.hide()
    editor.private_csg_catalog_add_dialog.file_selected.emit(cavity_path)
    if (not bool(editor.private_csg_catalog_last_result.get("ok", false))
        or editor.private_csg_catalog_entries.size() != 2
        or editor.private_csg_catalog_selector.selected != 1):
        _fail("Second CSG recipe registration or selection failed")
        return
    editor.private_csg_catalog_refresh_button.pressed.emit()
    if (not bool(editor.private_csg_catalog_last_result.get("ok", false))
        or not is_instance_valid(editor.private_csg_preview_root)
        or editor.private_csg_preview_root.get_child_count() != 6
        or not bool(editor.private_csg_preview_last_result.get(
            "from_private_catalog", false))
        or not is_equal_approx(
            float(editor.private_csg_preview_last_result.get("volume_m3", 0)), 44.)
        or editor.undo_stack.size() != undo_before
        or FileAccess.get_sha256(original) != original_sha):
        _fail("Refreshed six-piece cavity catalog preview invalid")
        return
    var catalog_sha := FileAccess.get_sha256(index)
    # Loading the SAME private GLB must restore only pinned recipe references.
    editor.load_glb(glb)
    if (editor.private_csg_catalog_entries.size() != 2
        or is_instance_valid(editor.private_csg_preview_root)
        or FileAccess.get_sha256(index) != catalog_sha):
        _fail("Map cache reopened without restored private CSG catalog")
        return
    editor.private_csg_catalog_selector.select(0)
    editor.private_csg_catalog_refresh_button.pressed.emit()
    if (not bool(editor.private_csg_catalog_last_result.get("ok", false))
        or not is_instance_valid(editor.private_csg_preview_root)
        or editor.private_csg_preview_root.get_child_count() != 1
        or not is_equal_approx(
            float(editor.private_csg_preview_last_result.get("volume_m3", 0)), 2.)):
        _fail("Project reopening could not refresh first pinned recipe")
        return
    # Test the guard against changed bytes on an already-registered path.
    var original_first_bytes := FileAccess.get_file_as_bytes(first_path)
    var mutated: Variant = JSON.parse_string(FileAccess.get_file_as_string(first_path))
    if typeof(mutated) != TYPE_DICTIONARY:
        _fail("Fixture generated an invalid recipe")
        return
    mutated["piece_count"] = 42
    if not _write(first_path, JSON.stringify(mutated).to_utf8_buffer()):
        _fail("Could not create tampered private recipe test input")
        return
    editor.private_csg_catalog_refresh_button.pressed.emit()
    if (bool(editor.private_csg_catalog_last_result.get("ok", true))
        or not is_instance_valid(editor.private_csg_preview_root)
        or FileAccess.get_sha256(index) != catalog_sha
        or FileAccess.get_sha256(original) != original_sha):
        _fail("Changed registered recipe bypassed P104 pin verification")
        return
    _write(first_path, original_first_bytes)
    if FileAccess.get_sha256(first_path) != first_sha:
        _fail("Could not restore synthetic source-private recipe")
        return
    # A separate private cache has no registered recipes even if it shares
    # the same installed editor and original game-looking sentinel.
    var other := Catalog.load_catalog(scratch.path_join("other_project"))
    if (not bool(other.get("ok", false)) or not other["entries"].is_empty()
        or bool(Catalog.refresh_recipe(scratch.path_join("other_project"), 0)
            .get("ok", true))):
        _fail("CSG catalog leaked recipes between distinct private caches")
        return
    # Unlink NEVER deletes the actual recipe and cleans only the selected
    # catalog-backed overlay, preserving unrelated private files.
    editor.private_csg_catalog_selector.select(0)
    editor.private_csg_catalog_remove_button.pressed.emit()
    if (not bool(editor.private_csg_catalog_last_result.get("ok", false))
        or editor.private_csg_catalog_entries.size() != 1
        or is_instance_valid(editor.private_csg_preview_root)
        or FileAccess.get_sha256(first_path) != first_sha
        or FileAccess.get_sha256(cavity_path) != cavity_sha
        or FileAccess.get_sha256(original) != original_sha):
        _fail("Unlink deleted recipe data or left stale catalog overlay")
        return
    # Persisted index is strict about map identity and unsafe native flags.
    var saved_catalog := FileAccess.get_file_as_bytes(index)
    var spoof: Variant = JSON.parse_string(FileAccess.get_file_as_string(index))
    if typeof(spoof) != TYPE_DICTIONARY:
        _fail("Could not parse isolated index for safety test")
        return
    spoof["native_bsp_or_collision_writer_enabled"] = true
    if not _write(index, JSON.stringify(spoof).to_utf8_buffer()):
        _fail("Cannot stage altered private CSG catalog")
        return
    if bool(Catalog.load_catalog(scratch).get("ok", true)):
        _fail("Catalog accepted claimed native BSP/collision writer capability")
        return
    _write(index, saved_catalog)
    editor._reload_private_csg_catalog()
    if (editor.private_csg_catalog_entries.size() != 1
        or editor.private_csg_catalog_entries[0]["path"] != cavity_path
        or editor.undo_stack.size() != undo_before):
        _fail("Private CSG index did not survive verified rollback")
        return
    for stage_dir in ["user://private_csg_recipe_stage",
                      "user://private_csg_preview_stage"]:
        var absolute := ProjectSettings.globalize_path(stage_dir)
        for name in DirAccess.get_files_at(absolute):
            if (str(name).begins_with("recipe_") or str(name).begins_with("csg_")):
                _fail("Private CSG staging JSON leaked")
                return
    editor.queue_free()
    for path in [index, index + ".bak", index + ".pending", other_index,
                 other_index + ".bak", glb, first_path, cavity_path, original]:
        if FileAccess.file_exists(path):
            DirAccess.remove_absolute(path)
    DirAccess.remove_absolute(scratch)
    print("DX2Ed P104 private CSG catalog register/replay/rollback/unlink PASS")
    quit(0)
