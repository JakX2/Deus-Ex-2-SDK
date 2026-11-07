extends SceneTree
## v0.13 Godot UI state fixture: invented source SHA only.
## No actual game data, binary writers, native Light creation or side effects.
const BatchLightColorScript = preload("res://multi_light_color_panel.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(reason: String) -> void:
    push_error("DX2Ed v0.13 batch LightColor GUI: " + reason)
    quit(1)


func _inventory(sha: String, name: String, count: int = 9) -> Dictionary:
    var shown: Array = []
    for i in range(count):
        shown.append({
            "actor": "StaticMeshActor__" + str(i + 1),
            "export": i + 1,
            "actor_class": "StaticMeshActor",
            "original_values": {
                "brightness": 96, "hue": 150, "saturation": 32},
            "strict_existing_struct_writer_candidate": true,
            "actual_gameplay_effect_for_this_actor_verified": false,
        })
    return {
        "bridge_schema": BatchLightColorScript.BRIDGE_SCHEMA,
        "action": "list",
        "schema": BatchLightColorScript.SOURCE_SCHEMA,
        "status": "read-only-source-verified",
        "source_map": name,
        "source_sha256": sha,
        "read_only": true,
        "source_original_modified": false,
        "gameplay_runtime_verified": false,
        "native_new_light_actor_creation_enabled": false,
        "shown": shown,
    }


func _run() -> void:
    var source_folder := ProjectSettings.globalize_path("user://multi_color_v013_original")
    var private_folder := ProjectSettings.globalize_path("user://multi_color_v013_private")
    if (DirAccess.make_dir_recursive_absolute(source_folder) != OK
        or DirAccess.make_dir_recursive_absolute(private_folder) != OK):
        _fail("Cannot create private invented source identity directory")
        return
    var source := source_folder.path_join("M1_BatchSynthetic.gmp")
    var dest := private_folder.path_join("M1_BatchSynthetic.gmp")
    var stale_plan := dest.get_basename() + ".dx2sdk-multi-lightcolor-plan.json"
    var output_file := FileAccess.open(source, FileAccess.WRITE)
    if output_file == null:
        _fail("Cannot create synthetic source hash fixture")
        return
    output_file.store_buffer(PackedByteArray([7, 11, 13, 17, 19]))
    output_file.close()
    var sha := FileAccess.get_sha256(source).to_lower()
    var bridge := ProjectSettings.globalize_path(
        "res://backend/dx2_sdk_multi_lightcolor_worker.py")
    var panel := BatchLightColorScript.new()
    get_root().add_child(panel)
    if not panel.configure_original(source, sha, bridge):
        _fail("Original synthetic hash and worker were not accepted")
        return
    var doc := _inventory(sha, source.get_file())
    if not panel.accept_inventory(doc):
        _fail("Original valid source actors failed GUI list validation")
        return
    if panel.inventory.size() != 9 or not panel.preview_button.disabled:
        _fail("Original inventory incorrectly enabled 2..8 actor output")
        return
    panel._pick(0)
    if panel.stage_selected() or not panel.staged.is_empty():
        _fail("An unchanged source byte was added as a native edit")
        return
    panel.values["brightness"].value = 255
    if not panel.stage_selected() or panel.staged.size() != 1:
        _fail("First original actor could not be staged")
        return
    if panel.edit_request(dest) != {} or not panel.preview_button.disabled:
        _fail("One actor incorrectly qualified as a batch of 2")
        return
    panel._pick(1)
    panel.values["hue"].value = 0
    if not panel.stage_selected() or panel.staged.size() != 2:
        _fail("Second distinct original actor could not be staged")
        return
    var request := panel.edit_request(dest)
    if (request.get("source_sha256") != sha
        or request.get("rows", []).size() != 2
        or request["rows"][0]["export"] != 1
        or request["rows"][1]["export"] != 2
        or request["rows"][0]["expected"] != [96, 150, 32]
        or request["rows"][0]["changes"] != {"brightness": 255}
        or request["rows"][1]["changes"] != {"hue": 0}):
        _fail("Two-actor request lost pinned original exports/byte values")
        return
    if panel.edit_request(source) != {}:
        _fail("Source GMP passed as a destination")
        return
    if panel.edit_request(private_folder.path_join("Wrong.gmp")) != {}:
        _fail("Different output basename accepted")
        return
    if FileAccess.file_exists(dest):
        _fail("A GUI-only validation created a native GMP")
        return
    var forged := doc.duplicate(true)
    forged["gameplay_runtime_verified"] = true
    if panel.accept_inventory(forged):
        _fail("Forged runtime success flag accepted")
        return
    forged = doc.duplicate(true)
    forged["shown"][0]["original_values"]["brightness"] = 256
    if panel.accept_inventory(forged):
        _fail("Original source byte outside 0..255 accepted")
        return
    forged = doc.duplicate(true)
    forged["shown"].append(forged["shown"][0].duplicate(true))
    if panel.accept_inventory(forged):
        _fail("Duplicate actor identity accepted")
        return
    forged = doc.duplicate(true)
    forged["source_sha256"] = "0".repeat(64)
    if panel.accept_inventory(forged):
        _fail("Foreign original source hash accepted")
        return
    if panel.edit_request(dest) != request:
        _fail("Invalid inventory silently mutated a previously staged safe edit")
        return
    for i in range(2, 8):
        panel._pick(i)
        panel.values["saturation"].value = 33 + i
        if not panel.stage_selected():
            _fail("Cannot stage distinct original actor up to eight")
            return
    if panel.staged.size() != 8:
        _fail("Eight original actors were not staged")
        return
    panel._pick(8)
    panel.values["brightness"].value = 255
    if panel.stage_selected() or panel.staged.size() != 8:
        _fail("Ninth original actor bypassed the maximum batch safety limit")
        return
    panel._pick(0)
    panel.values["brightness"].value = 254
    if not panel.stage_selected() or panel.staged.size() != 8:
        _fail("Updating one existing staged actor incorrectly counted as ninth")
        return
    if panel.edit_request(dest).is_empty():
        _fail("Exactly eight source-verified actors were rejected")
        return
    panel.pending = panel.edit_request(dest)
    panel._clear_staged()
    if not panel.pending.is_empty() or not panel.preview_button.disabled:
        _fail("Clearing staged edits preserved a stale save confirmation")
        return
    if not panel.accept_inventory(doc):
        _fail("Original inventory cannot be reset after clearing staging")
        return
    panel._pick(0)
    panel.values["hue"].value = 0
    panel.stage_selected()
    panel._pick(1)
    panel.values["brightness"].value = 255
    panel.stage_selected()
    if panel.edit_request(dest).is_empty():
        _fail("Prepared two-actor request lost after stage reset")
        return
    output_file = FileAccess.open(stale_plan, FileAccess.WRITE)
    if output_file == null:
        _fail("Cannot create private plan overwrite test")
        return
    output_file.store_string("already exists")
    output_file.close()
    if panel.edit_request(dest) != {}:
        _fail("Existing private plan can be overwritten")
        return
    DirAccess.remove_absolute(stale_plan)
    output_file = FileAccess.open(source, FileAccess.WRITE)
    output_file.store_buffer(PackedByteArray([7, 11, 13, 17, 21]))
    output_file.close()
    if panel.edit_request(dest) != {}:
        _fail("Changed original GMP did not invalidate source-locked batch")
        return
    panel.reset_context()
    if (not panel.inventory.is_empty() or not panel.staged.is_empty()
        or panel.selected_index != -1 or not panel.scan_button.disabled
        or not panel.preview_button.disabled):
        _fail("Original source reset left native batch controls armed")
        return
    panel.queue_free()
    DirAccess.remove_absolute(source)
    print("DX2Ed v0.13 synthetic 2..8 LightColor GUI stage/preview safety PASS")
    quit(0)
