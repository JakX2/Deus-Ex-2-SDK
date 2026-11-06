extends SceneTree
## v0.12 invented original GMP *identity* only. No DX2 retail data, native
## output, external worker launch or Source GameSys bytes are created.
const LightColorPanelScript = preload("res://light_color_panel.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed LightColor GUI smoke: " + message)
    quit(1)


func _fixture(sha: String, name: String) -> Dictionary:
    return {
        "bridge_schema": LightColorPanelScript.BRIDGE_SCHEMA,
        "action": "list",
        "schema": LightColorPanelScript.SOURCE_SCHEMA,
        "status": "read-only-source-verified",
        "source_map": name,
        "source_sha256": sha,
        "read_only": true,
        "gameplay_runtime_verified": false,
        "native_new_light_actor_creation_enabled": false,
        "source_original_modified": false,
        "shown": [
            {"actor": "StaticMeshActor__1", "export": 1,
             "actor_class": "StaticMeshActor",
             "original_values": {
                 "brightness": 96, "hue": 150, "saturation": 32},
             "strict_existing_struct_writer_candidate": true,
             "actual_gameplay_effect_for_this_actor_verified": false},
        ],
    }


func _run() -> void:
    var original_folder := ProjectSettings.globalize_path("user://lightcolor_v012_original")
    var private_folder := ProjectSettings.globalize_path("user://lightcolor_v012_private")
    if (DirAccess.make_dir_recursive_absolute(original_folder) != OK
        or DirAccess.make_dir_recursive_absolute(private_folder) != OK):
        _fail("Cannot create self-test private sandbox")
        return
    var source := original_folder.path_join("M1_Synthetic.gmp")
    var output := private_folder.path_join("M1_Synthetic.gmp")
    if FileAccess.file_exists(output):
        DirAccess.remove_absolute(output)
    var f := FileAccess.open(source, FileAccess.WRITE)
    if f == null:
        _fail("Cannot create invented source identity file")
        return
    f.store_buffer(PackedByteArray([1, 3, 5, 7, 11, 13]))
    f.close()
    var sha := FileAccess.get_sha256(source).to_lower()
    var script := ProjectSettings.globalize_path(
        "res://backend/dx2_sdk_lightcolor_worker.py")
    var panel := LightColorPanelScript.new()
    get_root().add_child(panel)
    if not panel.configure_original(source, sha, script):
        _fail("Original file and SHA cannot configure source UI")
        return
    var valid := _fixture(sha, source.get_file())
    if not panel.accept_inventory(valid):
        _fail("Source verified fixture LightColor inventory was not accepted")
        return
    if panel.inventory.size() != 1 or not panel.export_button.disabled:
        _fail("Inventory selection state enabled writing without a selection")
        return
    panel._pick_actor(0)
    if panel.edit_request(output) != {}:
        _fail("Unchanged LightColor values generated a write request")
        return
    panel.values["brightness"].value = 255
    panel.values["saturation"].value = 255
    var request := panel.edit_request(output)
    if (request.get("actor") != "StaticMeshActor__1"
        or request.get("export") != 1
        or request.get("source_sha256") != sha
        or request.get("expected") != [96, 150, 32]
        or request.get("changes") != {"brightness": 255, "saturation": 255}):
        _fail("UI request did not preserve exact original actor/byte provenance")
        return
    if FileAccess.file_exists(output):
        _fail("UI request unexpectedly wrote an output GMP")
        return
    if panel.edit_request(original_folder.path_join("Other.gmp")) != {}:
        _fail("Incorrect output GMP basename allowed")
        return
    if panel.edit_request(source) != {}:
        _fail("Original GMP allowed as an output destination")
        return
    var forged := valid.duplicate(true)
    forged["gameplay_runtime_verified"] = true
    if panel.accept_inventory(forged):
        _fail("Game runtime verified claim accepted from untrusted JSON")
        return
    forged = valid.duplicate(true)
    forged["shown"][0]["original_values"]["hue"] = 256
    if panel.accept_inventory(forged):
        _fail("Out-of-range original source color byte accepted")
        return
    forged = valid.duplicate(true)
    forged["shown"].append(forged["shown"][0].duplicate(true))
    if panel.accept_inventory(forged):
        _fail("Duplicate native actor identity accepted")
        return
    forged = valid.duplicate(true)
    forged["source_sha256"] = "0".repeat(64)
    if panel.accept_inventory(forged):
        _fail("Foreign GMP source identity accepted")
        return
    if panel.edit_request(output) != request:
        _fail("Bad candidate data mutated existing validated UI selection")
        return
    f = FileAccess.open(source, FileAccess.WRITE)
    f.store_buffer(PackedByteArray([1, 3, 5, 7, 11, 14]))
    f.close()
    if panel.edit_request(output) != {}:
        _fail("Modified original map left export request enabled")
        return
    panel.reset_context()
    if (not panel.inventory.is_empty() or panel.selected_index != -1
        or not panel.scan_button.disabled or not panel.export_button.disabled):
        _fail("Clearing original GMP left stale source LightColor controls")
        return
    panel.queue_free()
    DirAccess.remove_absolute(source)
    print("DX2Ed v0.12 synthetic LightColor GUI state and original SHA gate PASS")
    quit(0)
