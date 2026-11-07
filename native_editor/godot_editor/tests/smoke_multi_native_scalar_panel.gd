extends SceneTree
## DX2Ed v0.15 Godot native scalar batch state test: invented original SHA
## and actors.json identity only, no native GMP, retail game or writer run.
const BatchScalarScript = preload("res://multi_native_scalar_panel.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(reason: String) -> void:
    push_error("DX2Ed v0.15 native scalar batch UI smoke: " + reason)
    quit(1)


func _actors(sha: String, cache_sha: String, map_name: String) -> Dictionary:
    return {
        "bridge_schema": BatchScalarScript.BRIDGE_SCHEMA,
        "schema": BatchScalarScript.SDK_SCHEMA,
        "action": "list",
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
            {"actor":"StaticMeshActor__1","export":1,"actor_class":"StaticMeshActor"},
            {"actor":"StaticMeshActor__2","export":2,"actor_class":"StaticMeshActor"},
        ],
        "shown_count":2,
    }


func _fields(sha: String, cache_sha: String, map_name: String,
             actor: String, export: int, count: int = 2) -> Dictionary:
    var items: Array = []
    for i in range(count):
        items.append({
            "property": "FixtureNumeric" + str(i),
            "type": "int32" if i % 2 == 0 else "float32",
            "source_value": 98765 + i if i % 2 == 0 else 12.5 + i,
        })
    return {
        "bridge_schema": BatchScalarScript.BRIDGE_SCHEMA,
        "schema": BatchScalarScript.SDK_SCHEMA,
        "action": "fields",
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
        "actor_name": actor,
        "export": export,
        "fields": items,
    }


func _run() -> void:
    var original_folder := ProjectSettings.globalize_path("user://scalar_batch_v015_source")
    var private_folder := ProjectSettings.globalize_path("user://scalar_batch_v015_private")
    if (DirAccess.make_dir_recursive_absolute(original_folder) != OK
        or DirAccess.make_dir_recursive_absolute(private_folder) != OK):
        _fail("Cannot create synthetic original/cache private paths")
        return
    var map := original_folder.path_join("M1_BatchScalarSynthetic.gmp")
    var cache := original_folder.path_join("actors.json")
    var target := private_folder.path_join("M1_BatchScalarSynthetic.gmp")
    var manifest := target.get_basename() + ".dx2sdk-scalar.json"
    if FileAccess.file_exists(target):
        DirAccess.remove_absolute(target)
    if FileAccess.file_exists(manifest):
        DirAccess.remove_absolute(manifest)
    var f := FileAccess.open(map, FileAccess.WRITE)
    if f == null:
        _fail("Cannot build fake source identity bytes")
        return
    f.store_buffer(PackedByteArray([2, 3, 5, 7, 11]))
    f.close()
    f = FileAccess.open(cache, FileAccess.WRITE)
    f.store_string("invented source actor index")
    f.close()
    var sha := FileAccess.get_sha256(map).to_lower()
    var cache_sha := FileAccess.get_sha256(cache).to_lower()
    var bridge := ProjectSettings.globalize_path(
        "res://backend/dx2_sdk_multi_scalar_worker.py")
    var panel := BatchScalarScript.new()
    get_root().add_child(panel)
    if not panel.configure_original(map, cache, sha, bridge):
        _fail("Authentic invented source/cache identity rejected")
        return
    var originals := _actors(sha, cache_sha, map.get_file())
    if not panel.accept_actor_inventory(originals):
        _fail("Source-validated original actor list rejected")
        return
    if panel.original_actors.size() != 2 or not panel.batch_button.disabled:
        _fail("Read-only source list erroneously enabled batch writes")
        return
    panel.chosen_actor_index = 0
    var list1 := _fields(sha, cache_sha, map.get_file(), "StaticMeshActor__1",1)
    if not panel.accept_original_fields(list1):
        _fail("Original first actor numeric property list rejected")
        return
    panel._pick_field(0)
    if panel.stage_selected():
        _fail("Unchanged original int32 got staged")
        return
    panel.field_value.value = 123456
    if not panel.stage_selected() or panel.staged.size() != 1:
        _fail("First source-original int32 field was not staged")
        return
    if panel.batch_request(target) != {}:
        _fail("One staged numeric tag incorrectly qualified as batch")
        return
    panel._pick_field(1)
    panel.field_value.value = 15.75
    if not panel.stage_selected() or panel.staged.size() != 2:
        _fail("Second source float32 tag was not staged")
        return
    var two := panel.batch_request(target)
    if (two.get("rows", []).size() != 2
        or two["rows"][0]["actor"] != "StaticMeshActor__1"
        or two["rows"][0]["type"] != "int32"
        or two["rows"][1]["property"] != "FixtureNumeric1"
        or two["rows"][1]["type"] != "float32"
        or two.get("source_sha256") != sha
        or two.get("actors_sha256") != cache_sha):
        _fail("Original int32+float32 staging lost source actor/cache pins")
        return
    if panel.batch_request(map) != {}:
        _fail("Original source GMP allowed as native batch output")
        return
    if panel.batch_request(private_folder.path_join("Other.gmp")) != {}:
        _fail("Native output used different original GMP basename")
        return
    panel._pick_field(0)
    panel.field_value.value = 654321
    if not panel.stage_selected() or panel.staged.size() != 2:
        _fail("Updating already-staged original property increased field count")
        return
    if panel.staged[0]["replacement"] != 654321:
        _fail("Staged original numeric replacement was not updated")
        return
    panel.chosen_actor_index = 1
    var list2 := _fields(sha, cache_sha, map.get_file(), "StaticMeshActor__2",2)
    if not panel.accept_original_fields(list2):
        _fail("Second original actor property list rejected")
        return
    panel._pick_field(0)
    panel.field_value.value = 33
    if not panel.stage_selected() or panel.staged.size() != 3:
        _fail("Cross-actor original numeric edit lost staged source fields")
        return
    if panel.batch_request(target)["rows"][2]["actor"] != "StaticMeshActor__2":
        _fail("Original cross-actor export indexing was not preserved")
        return
    var forged := originals.duplicate(true)
    forged["actors_sha256"] = "0".repeat(64)
    if panel.accept_actor_inventory(forged):
        _fail("Forged source actors.json SHA accepted")
        return
    if panel.staged.size() != 3:
        _fail("Rejected source inventory silently cleared authenticated batch")
        return
    forged = list2.duplicate(true)
    forged["fields"][0]["property"] = "Location"
    if panel.accept_original_fields(forged):
        _fail("Forbidden Location transform/tag accepted in batch")
        return
    forged = list2.duplicate(true)
    forged["fields"][0]["type"] = "array"
    if panel.accept_original_fields(forged):
        _fail("Unsupported tagged array type accepted")
        return
    if panel.staged.size() != 3:
        _fail("Forged native field list altered staged original property edits")
        return
    panel.chosen_actor_index = 0
    var many := _fields(sha,cache_sha,map.get_file(),"StaticMeshActor__1",1,9)
    if not panel.accept_original_fields(many):
        _fail("Invented nine distinct source typed field inventory rejected")
        return
    for i in range(2,7):
        panel._pick_field(i)
        panel.field_value.value = 500 + i
        if not panel.stage_selected():
            _fail("Could not stage native numeric original field up to eight")
            return
    if panel.staged.size() != 8:
        _fail("Exact eight field staging limit not reached")
        return
    panel._pick_field(7)
    panel.field_value.value = 555
    if panel.stage_selected() or panel.staged.size() != 8:
        _fail("Ninth original numeric tag bypassed bounded batch limit")
        return
    if panel.batch_request(target).is_empty():
        _fail("Exactly eight authenticated original tags incorrectly rejected")
        return
    panel.pending = panel.batch_request(target)
    panel._clear()
    if not panel.pending.is_empty() or not panel.batch_button.disabled:
        _fail("Clear staged preserved native output authorization")
        return
    if not panel.accept_actor_inventory(originals):
        _fail("Fresh source actor inventory after clearing batch was refused")
        return
    panel.chosen_actor_index = 0
    if not panel.accept_original_fields(list1):
        _fail("Fresh original field inventory after clear rejected")
        return
    panel._pick_field(0)
    panel.field_value.value = 11
    panel.stage_selected()
    panel._pick_field(1)
    panel.field_value.value = 15.75
    panel.stage_selected()
    if panel.batch_request(target).is_empty():
        _fail("Two source fields failed after clear/reset")
        return
    f = FileAccess.open(manifest,FileAccess.WRITE)
    f.store_string("do not overwrite")
    f.close()
    if panel.batch_request(target) != {}:
        _fail("Existing private native scalar manifest can be overwritten")
        return
    DirAccess.remove_absolute(manifest)
    f = FileAccess.open(cache,FileAccess.WRITE)
    f.store_string("changed inventoried cache content")
    f.close()
    if panel.batch_request(target) != {}:
        _fail("Original actor cache tamper left batch output enabled")
        return
    panel.reset_context()
    if (not panel.original_actors.is_empty() or
        not panel.original_fields.is_empty() or
        not panel.staged.is_empty() or
        not panel.batch_button.disabled or
        not panel.scan_button.disabled):
        _fail("Source context reset left unsafe numeric batch controls enabled")
        return
    if FileAccess.file_exists(target):
        _fail("Godot invented source-only UI state wrote a native GMP")
        return
    panel.queue_free()
    DirAccess.remove_absolute(map)
    DirAccess.remove_absolute(cache)
    print("DX2Ed v0.15 synthetic 2..8 original native scalar GUI SHA/stage safety PASS")
    quit(0)
