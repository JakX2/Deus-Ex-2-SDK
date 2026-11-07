extends SceneTree
## Invented original identity/cache bytes only: tests Godot UI security gates.
## Does not run Python native writer or distribute any original DX2 assets.
const NativeScalarPanelScript = preload("res://native_scalar_panel.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(reason: String) -> void:
    push_error("v0.14 native scalar UI smoke: " + reason)
    quit(1)


func _inventory(sha: String, cache_sha: String, map_name: String) -> Dictionary:
    return {
        "bridge_schema": NativeScalarPanelScript.BRIDGE_SCHEMA,
        "action": "list",
        "schema": NativeScalarPanelScript.SDK_SCHEMA,
        "status": "original_staticmeshactor_list",
        "source_map": map_name,
        "source_sha256": sha,
        "actors_sha256": cache_sha,
        "source_original_modified": false,
        "runtime_game_verified": false,
        "native_gamesys_or_script_writer_enabled": false,
        "native_new_actor_creation_enabled": false,
        "source_actor_cache_verified": true,
        "read_only": true,
        "actors": [
            {"actor":"StaticMeshActor__1","export":1,
             "actor_class":"StaticMeshActor"},
        ],
        "shown_count": 1,
    }


func _fields(sha: String, cache_sha: String, map_name: String) -> Dictionary:
    return {
        "bridge_schema": NativeScalarPanelScript.BRIDGE_SCHEMA,
        "action": "fields",
        "schema": NativeScalarPanelScript.SDK_SCHEMA,
        "status": "original_scalar_field_inventory",
        "source_map": map_name,
        "source_sha256": sha,
        "actors_sha256": cache_sha,
        "source_original_modified": false,
        "runtime_game_verified": false,
        "native_gamesys_or_script_writer_enabled": false,
        "read_only": true,
        "original_map": map_name,
        "original_map_sha256": sha,
        "actor_name": "StaticMeshActor__1",
        "export": 1,
        "fields": [
            {"property":"FixtureFlag","type":"int32","source_value":98765},
            {"property":"FixtureFloat","type":"float32","source_value":12.5},
        ],
    }


func _run() -> void:
    var original_folder := ProjectSettings.globalize_path("user://scalar_v014_original")
    var private_folder := ProjectSettings.globalize_path("user://scalar_v014_private")
    if (DirAccess.make_dir_recursive_absolute(original_folder) != OK
        or DirAccess.make_dir_recursive_absolute(private_folder) != OK):
        _fail("Unable to create invented original and private-output locations")
        return
    var source := original_folder.path_join("M1_SyntheticScalar.gmp")
    var cache := original_folder.path_join("actors.json")
    var target := private_folder.path_join("M1_SyntheticScalar.gmp")
    var manifest := target.get_basename() + ".dx2sdk-scalar.json"
    if FileAccess.file_exists(target):
        DirAccess.remove_absolute(target)
    if FileAccess.file_exists(manifest):
        DirAccess.remove_absolute(manifest)
    var file := FileAccess.open(source, FileAccess.WRITE)
    if file == null:
        _fail("Cannot create private original identity bytes")
        return
    file.store_buffer(PackedByteArray([2, 3, 5, 7, 11]))
    file.close()
    file = FileAccess.open(cache, FileAccess.WRITE)
    if file == null:
        _fail("Cannot create private actor cache identity bytes")
        return
    file.store_string("invented original actor cache content only")
    file.close()
    var sha := FileAccess.get_sha256(source).to_lower()
    var cache_sha := FileAccess.get_sha256(cache).to_lower()
    var bridge := ProjectSettings.globalize_path(
        "res://backend/dx2_sdk_scalar_worker.py")
    var panel := NativeScalarPanelScript.new()
    get_root().add_child(panel)
    if not panel.configure_original(source, cache, sha, bridge):
        _fail("Original source/cache identity could not arm read-only list")
        return
    var inventory := _inventory(sha, cache_sha, source.get_file())
    if not panel.accept_actor_inventory(inventory):
        _fail("Valid source actor inventory was rejected")
        return
    if panel.original_actors.size() != 1 or not panel.save_button.disabled:
        _fail("Unselected actor enabled native scalar writing")
        return
    var forged := inventory.duplicate(true)
    forged["native_new_actor_creation_enabled"] = true
    if panel.accept_actor_inventory(forged):
        _fail("Invented native actor-spawner claim was accepted")
        return
    forged = inventory.duplicate(true)
    forged["actors_sha256"] = "0".repeat(64)
    if panel.accept_actor_inventory(forged):
        _fail("Foreign source actor cache identity accepted")
        return
    forged = inventory.duplicate(true)
    forged["actors"].append(forged["actors"][0].duplicate(true))
    forged["shown_count"] = 2
    if panel.accept_actor_inventory(forged):
        _fail("Duplicate native actor export was accepted")
        return
    # Selection normally starts an asynchronous Python source worker. Tests
    # deliberately avoid launching native subprocesses: fields come from a
    # fabricated data binding with exact expected schema and source hashes.
    panel.chosen_actor_index = 0
    var fields := _fields(sha, cache_sha, source.get_file())
    if not panel.accept_original_fields(fields):
        _fail("Valid explicit int32/float32 field inventory was rejected")
        return
    if panel.original_fields.size() != 2:
        _fail("Two typed source scalar fields were not preserved")
        return
    forged = fields.duplicate(true)
    forged["fields"][0]["property"] = "Location"
    if panel.accept_original_fields(forged):
        _fail("Original Location reserved geometry/transform field accepted")
        return
    forged = fields.duplicate(true)
    forged["fields"][0]["type"] = "script"
    if panel.accept_original_fields(forged):
        _fail("Unsupported native script field type accepted")
        return
    forged = fields.duplicate(true)
    forged["fields"][0]["source_value"] = 2147483648
    if panel.accept_original_fields(forged):
        _fail("Int32 original source overflow accepted")
        return
    forged = fields.duplicate(true)
    forged["fields"][0]["property"] = "FixtureFloat"
    if panel.accept_original_fields(forged):
        _fail("Duplicate original numeric tag name accepted")
        return
    forged = fields.duplicate(true)
    forged["actors_sha256"] = "0".repeat(64)
    if panel.accept_original_fields(forged):
        _fail("Stale original private actor cache proof accepted")
        return
    if panel.original_fields.size() != 2:
        _fail("Forged numeric field inventory mutated valid original selection")
        return
    panel._pick_field(0)
    if panel.edit_request(target) != {}:
        _fail("Unchanged original int32 generated an output patch")
        return
    panel.field_value.value = 123456
    var request := panel.edit_request(target)
    if (request.get("actor") != "StaticMeshActor__1"
        or request.get("export") != 1
        or request.get("property") != "FixtureFlag"
        or request.get("type") != "int32"
        or request.get("expected") != 98765
        or request.get("replacement") != 123456
        or request.get("output") != target):
        _fail("Original int32 scalar request lost authentic source identity")
        return
    if panel.edit_request(source) != {}:
        _fail("Original map path allowed as output")
        return
    if panel.edit_request(private_folder.path_join("Wrong.gmp")) != {}:
        _fail("Different native map basename allowed")
        return
    panel.field_value.value = 2147483647.0
    if panel.edit_request(target).is_empty():
        _fail("Maximum safe int32 replacement was rejected")
        return
    panel.field_value.value = -2147483648.0
    if panel.edit_request(target).is_empty():
        _fail("Minimum safe int32 replacement was rejected")
        return
    panel._pick_field(1)
    panel.field_value.value = 15.75
    var float_edit := panel.edit_request(target)
    if (float_edit.get("type") != "float32"
        or float_edit.get("expected") != 12.5
        or float_edit.get("replacement") != 15.75):
        _fail("Original float32 scalar identity or replacement changed")
        return
    if FileAccess.file_exists(target):
        _fail("Godot staging UI unexpectedly created a native GMP")
        return
    file = FileAccess.open(manifest, FileAccess.WRITE)
    file.store_string("private previous scalar manifest")
    file.close()
    if panel.edit_request(target) != {}:
        _fail("Existing independent scalar manifest could be overwritten")
        return
    DirAccess.remove_absolute(manifest)
    file = FileAccess.open(cache, FileAccess.WRITE)
    file.store_string("invented altered actor cache bytes")
    file.close()
    if panel.edit_request(target) != {}:
        _fail("Modified original actors.json did not invalidate scalar editor")
        return
    panel.reset_context()
    if (not panel.original_actors.is_empty()
        or not panel.original_fields.is_empty()
        or panel.chosen_actor_index != -1
        or panel.chosen_field_index != -1
        or not panel.scan_button.disabled
        or not panel.save_button.disabled):
        _fail("Native scalar controls were active after source reset")
        return
    panel.queue_free()
    DirAccess.remove_absolute(source)
    DirAccess.remove_absolute(cache)
    print("DX2Ed v0.14 invented native int32/float32 GUI source-and-cache SHA PASS")
    quit(0)
