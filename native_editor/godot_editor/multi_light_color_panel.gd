extends VBoxContainer
## DX2Ed v0.13 original GameSys #116 batch authoring, 2..8 EXISTING actors.
## This is not a native Light/Level/Region spawner or runtime renderer test.
## A new original-source-locked private plan is created only on explicit save.
const PythonRuntime = preload("res://python_runtime.gd")
const BRIDGE_SCHEMA := "DX2Ed-GUI-source-multi-LightColor-worker-v1"
const SOURCE_SCHEMA := "DX2SDK-source-existing-LightColor-v1"
const BATCH_SCHEMA := "DX2SDK-source-multi-LightColor-copy-v1"
const FIELDS := ["brightness", "hue", "saturation"]
const MAX_BATCH := 8

var source_map := ""
var source_sha256 := ""
var worker_script := ""
var inventory: Array[Dictionary] = []
var selected_index := -1
var staged: Array[Dictionary] = []
var pending: Dictionary = {}
var worker: Thread = null
var generation := 0

var status: Label
var scan_button: Button
var source_list: ItemList
var staged_list: ItemList
var values: Dictionary = {}
var stage_button: Button
var remove_button: Button
var clear_button: Button
var preview_button: Button
var save_dialog: FileDialog
var confirmation: ConfirmationDialog


func _ready() -> void:
    name = "LightColor Batch"
    var header := Label.new()
    header.text = "Original GameSys LightColor batch | 2–8 existing actors"
    header.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(header)
    var hint := Label.new()
    hint.text = ("Select an original actor, adjust its B/H/S bytes, stage it,"
        + " and repeat for 2–8 actors. Preview is read-only."
        + " Save As creates one isolated GMP and a new private plan/manifest."
        + " Native Light spawning and runtime color fidelity are unverified.")
    hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(hint)
    scan_button = Button.new()
    scan_button.text = "Scan original LightColor actors"
    scan_button.disabled = true
    scan_button.pressed.connect(_scan)
    add_child(scan_button)
    source_list = ItemList.new()
    source_list.custom_minimum_size.y = 135
    source_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    source_list.item_selected.connect(_pick)
    add_child(source_list)
    for field in FIELDS:
        var line := HBoxContainer.new()
        add_child(line)
        var label := Label.new()
        label.text = field.capitalize()
        label.custom_minimum_size.x = 110
        line.add_child(label)
        var spin := SpinBox.new()
        spin.min_value = 0
        spin.max_value = 255
        spin.step = 1
        spin.rounded = true
        spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        spin.editable = false
        line.add_child(spin)
        values[field] = spin
    stage_button = Button.new()
    stage_button.text = "Stage / update selected original actor"
    stage_button.disabled = true
    stage_button.pressed.connect(_stage)
    add_child(stage_button)
    var stage_title := Label.new()
    stage_title.text = "Staged edits (2–8 required)"
    add_child(stage_title)
    staged_list = ItemList.new()
    staged_list.custom_minimum_size.y = 135
    staged_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    staged_list.item_selected.connect(func(_idx): _update_buttons())
    add_child(staged_list)
    var controls := HBoxContainer.new()
    add_child(controls)
    remove_button = Button.new()
    remove_button.text = "Remove staged"
    remove_button.disabled = true
    remove_button.pressed.connect(_remove_staged)
    controls.add_child(remove_button)
    clear_button = Button.new()
    clear_button.text = "Clear all"
    clear_button.disabled = true
    clear_button.pressed.connect(_clear_staged)
    controls.add_child(clear_button)
    preview_button = Button.new()
    preview_button.text = "Preview 2–8 actors and Save As..."
    preview_button.disabled = true
    preview_button.tooltip_text = (
        "Two entire-package serializers must exactly agree on approved"
        + " original byte offsets; preview writes no GMP or plan.")
    preview_button.pressed.connect(_choose_output)
    add_child(preview_button)
    status = Label.new()
    status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    status.text = "Open your own unchanged original GMP before scanning."
    add_child(status)
    save_dialog = FileDialog.new()
    save_dialog.access = FileDialog.ACCESS_FILESYSTEM
    save_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    save_dialog.filters = PackedStringArray(["*.gmp ; Fresh isolated original LightColor group GMP"])
    save_dialog.file_selected.connect(_destination_chosen)
    add_child(save_dialog)
    confirmation = ConfirmationDialog.new()
    confirmation.title = "Confirm guarded multi-actor LightColor Save As"
    confirmation.confirmed.connect(_confirmed_apply)
    add_child(confirmation)


func _exit_tree() -> void:
    if worker != null:
        worker.wait_to_finish()
        worker = null


func reset_context() -> void:
    generation += 1
    source_map = ""
    source_sha256 = ""
    worker_script = ""
    inventory.clear()
    staged.clear()
    selected_index = -1
    pending.clear()
    if source_list != null:
        source_list.clear()
    if staged_list != null:
        staged_list.clear()
    for field in FIELDS:
        if values.has(field):
            values[field].editable = false
            values[field].value = 0
    _update_buttons()
    if status != null:
        status.text = "No verified original GMP. No game-native file can be overwritten."


func configure_original(map_path: String, sha: String, bridge: String) -> bool:
    reset_context()
    if (map_path.get_extension().to_lower() != "gmp"
        or not FileAccess.file_exists(map_path)
        or sha.length() != 64 or not sha.is_valid_hex_number()
        or not FileAccess.file_exists(bridge)
        or FileAccess.get_sha256(map_path).to_lower() != sha.to_lower()):
        if status != null:
            status.text = "Batch LightColor unavailable: original GMP SHA or bridge mismatch."
        return false
    source_map = map_path
    source_sha256 = sha.to_lower()
    worker_script = bridge
    _update_buttons()
    if status != null:
        status.text = "Original GMP pinned. Scan its eligible LightColor actors (read-only)."
    return true


func _context_ok() -> bool:
    return (not source_map.is_empty() and not source_sha256.is_empty()
        and FileAccess.file_exists(source_map)
        and FileAccess.file_exists(worker_script)
        and FileAccess.get_sha256(source_map).to_lower() == source_sha256)


func _whole(value: Variant, lo: int, hi: int) -> bool:
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value))
        and float(value) >= float(lo) and float(value) <= float(hi)
        and float(int(value)) == float(value))


func accept_inventory(doc: Dictionary) -> bool:
    if (not _context_ok() or doc.get("bridge_schema") != BRIDGE_SCHEMA
        or doc.get("action") != "list" or doc.get("schema") != SOURCE_SCHEMA
        or doc.get("status") != "read-only-source-verified"
        or doc.get("source_sha256") != source_sha256
        or str(doc.get("source_map", "")).to_lower() != source_map.get_file().to_lower()
        or doc.get("read_only") != true
        or doc.get("source_original_modified") != false
        or doc.get("gameplay_runtime_verified") != false
        or doc.get("native_new_light_actor_creation_enabled") != false
        or typeof(doc.get("shown")) != TYPE_ARRAY
        or doc["shown"].size() > 1000):
        return false
    var normalized: Array[Dictionary] = []
    var used: Dictionary = {}
    for rec in doc["shown"]:
        if typeof(rec) != TYPE_DICTIONARY:
            return false
        if (not _whole(rec.get("export"), 1, 2147483647)
            or typeof(rec.get("actor")) != TYPE_STRING or str(rec["actor"]).is_empty()
            or typeof(rec.get("actor_class")) != TYPE_STRING
            or str(rec["actor_class"]).is_empty()
            or rec.get("strict_existing_struct_writer_candidate") != true
            or rec.get("actual_gameplay_effect_for_this_actor_verified") != false):
            return false
        var exp := int(rec["export"])
        if used.has(exp):
            return false
        var raw: Variant = rec.get("original_values")
        if typeof(raw) != TYPE_DICTIONARY or raw.size() != 3:
            return false
        var vals: Dictionary = {}
        for key in FIELDS:
            if not raw.has(key) or not _whole(raw[key], 0, 255):
                return false
            vals[key] = int(raw[key])
        normalized.append({
            "export": exp, "actor": rec["actor"], "actor_class": rec["actor_class"],
            "original_values": vals,
        })
        used[exp] = true
    inventory = normalized
    selected_index = -1
    staged.clear()
    pending.clear()
    source_list.clear()
    for item in inventory:
        var original: Dictionary = item["original_values"]
        source_list.add_item("#%d %s  B%d H%d S%d" % [
            int(item["export"]), str(item["actor"]), int(original["brightness"]),
            int(original["hue"]), int(original["saturation"])])
    _refresh_staged()
    for field in FIELDS:
        values[field].editable = false
        values[field].value = 0
    _update_buttons()
    status.text = "%d source-validated original LightColor actors. Select to stage." % inventory.size()
    return true


func _pick(index: int) -> void:
    if (worker != null or index < 0 or index >= inventory.size()
        or not _context_ok()):
        return
    selected_index = index
    pending.clear()
    var source: Dictionary = inventory[index]["original_values"]
    var staged_row: Dictionary = {}
    for item in staged:
        if int(item["export"]) == int(inventory[index]["export"]):
            staged_row = item
            break
    for key in FIELDS:
        var current := int(source[key])
        if staged_row.has("changes") and staged_row["changes"].has(key):
            current = int(staged_row["changes"][key])
        values[key].value = current
        values[key].editable = true
    _update_buttons()
    status.text = "Editing original export #%d. Stage only changed source bytes." % (
        int(inventory[index]["export"]))


func _edited_selected_row() -> Dictionary:
    if (not _context_ok() or selected_index < 0
        or selected_index >= inventory.size()):
        return {}
    var item: Dictionary = inventory[selected_index]
    var source: Dictionary = item["original_values"]
    var changes: Dictionary = {}
    for key in FIELDS:
        if not values.has(key):
            return {}
        var value := int(values[key].value)
        if value != int(source[key]):
            changes[key] = value
    if changes.is_empty():
        return {}
    return {
        "actor": str(item["actor"]),
        "export": int(item["export"]),
        "expected": [
            int(source["brightness"]), int(source["hue"]),
            int(source["saturation"])],
        "changes": changes,
    }


func stage_selected() -> bool:
    if worker != null:
        return false
    var row := _edited_selected_row()
    if row.is_empty():
        return false
    var matched := false
    for i in range(staged.size()):
        if int(staged[i]["export"]) == int(row["export"]):
            staged[i] = row
            matched = true
            break
    if not matched:
        if staged.size() >= MAX_BATCH:
            return false
        staged.append(row)
    staged.sort_custom(func(a, b): return int(a["export"]) < int(b["export"]))
    pending.clear()
    _refresh_staged()
    return true


func _stage() -> void:
    if not stage_selected():
        status.text = "Stage refused: change a byte, select original actor or keep at most 8."
    else:
        status.text = "%d of 2–8 original LightColor actors staged." % staged.size()


func _refresh_staged() -> void:
    if staged_list == null:
        return
    staged_list.clear()
    for item in staged:
        staged_list.add_item("#%d %s  %s" % [
            int(item["export"]), str(item["actor"]), str(item["changes"])])
    _update_buttons()


func _remove_staged() -> void:
    if worker != null:
        return
    var selection := staged_list.get_selected_items()
    if selection.is_empty():
        return
    var i := int(selection[0])
    if i >= 0 and i < staged.size():
        staged.remove_at(i)
        pending.clear()
        _refresh_staged()
        status.text = "%d source actors staged." % staged.size()


func _clear_staged() -> void:
    if worker != null:
        return
    staged.clear()
    pending.clear()
    _refresh_staged()
    status.text = "Batch stage cleared; original source unchanged."


func _update_buttons() -> void:
    var busy := worker != null
    if scan_button != null:
        scan_button.disabled = busy or not _context_ok()
    if stage_button != null:
        stage_button.disabled = busy or selected_index < 0 or not _context_ok()
    if remove_button != null and staged_list != null:
        remove_button.disabled = busy or staged_list.get_selected_items().is_empty()
    if clear_button != null:
        clear_button.disabled = busy or staged.is_empty()
    if preview_button != null:
        preview_button.disabled = busy or not _context_ok() or not (staged.size() >= 2 and staged.size() <= MAX_BATCH)


func edit_request(target: String) -> Dictionary:
    if (worker != null or not _context_ok() or
        not (staged.size() >= 2 and staged.size() <= MAX_BATCH) or
        target.get_file().to_lower() != source_map.get_file().to_lower() or
        target == source_map or FileAccess.file_exists(target)):
        return {}
    var plan := target.get_basename() + ".dx2sdk-multi-lightcolor-plan.json"
    var manifest := target.get_basename() + ".dx2sdk-multi-lightcolor.json"
    if FileAccess.file_exists(plan) or FileAccess.file_exists(manifest):
        return {}
    return {
        "map": source_map, "source_sha256": source_sha256,
        "rows": staged.duplicate(true), "output": target,
    }


func _scan() -> void:
    if _context_ok():
        _start("list", {"map": source_map, "source_sha256": source_sha256})
    else:
        status.text = "Source GMP changed. Reopen map before scanning."


func _choose_output() -> void:
    if not preview_button.disabled:
        save_dialog.current_file = source_map.get_file()
        save_dialog.popup_centered_ratio(0.75)


func _destination_chosen(target: String) -> void:
    var req := edit_request(target)
    if req.is_empty():
        status.text = "Need 2–8 distinct staged changes and a new isolated same-basename GMP."
        return
    pending = req.duplicate(true)
    _start("preview", pending)


func _confirmed_apply() -> void:
    if pending.is_empty() or worker != null:
        return
    var req := edit_request(str(pending.get("output", "")))
    if req != pending:
        pending.clear()
        status.text = "Batch confirmation refused: selection, edits or source changed."
        return
    _start("apply", req)


func _start(action: String, req: Dictionary) -> void:
    if worker != null or not _context_ok():
        status.text = "Original LightColor batch worker unavailable or source changed."
        return
    var argv := PackedStringArray([
        worker_script, action,
        "--map", source_map, "--source-sha256", source_sha256])
    if action != "list":
        argv.append("--rows-json")
        argv.append(JSON.stringify(req["rows"]))
        argv.append("--output")
        argv.append(str(req["output"]))
    worker = Thread.new()
    _update_buttons()
    var started := worker.start(_execute.bind(argv, action, generation))
    if started != OK:
        worker = null
        _update_buttons()
        status.text = "Could not start source-only multi-LightColor Python worker."
        return
    status.text = ("Scanning original GameSys #116 data..." if action == "list"
        else "Replaying full-GMP dual-serializer byte proof..." if action == "preview"
        else "Writing new private plan, isolated GMP and verifier manifest...")


func _execute(argv: PackedStringArray, action: String, epoch: int) -> void:
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), argv, output, true)
    if code == -1:
        var py_args := PackedStringArray(["-3"])
        py_args.append_array(argv)
        output.clear()
        code = OS.execute("py", py_args, output, true)
    call_deferred("_finished", code, "\n".join(output), action, epoch)


func _finished(code: int, raw: String, action: String, epoch: int) -> void:
    if worker != null:
        worker.wait_to_finish()
        worker = null
    if epoch != generation or not _context_ok():
        reset_context()
        return
    var doc: Variant = JSON.parse_string(raw.strip_edges())
    if (code != 0 or typeof(doc) != TYPE_DICTIONARY
        or doc.get("bridge_schema") != BRIDGE_SCHEMA):
        var reason := (str(doc.get("reason", "Refused")) if typeof(doc) == TYPE_DICTIONARY
                       else raw.strip_edges().substr(0, 300))
        status.text = "Original LightColor batch refused: " + reason
        pending.clear()
    elif action == "list":
        if not accept_inventory(doc):
            status.text = "Original batch inventory rejected: unverified actor or source."
    elif action == "preview":
        var request := edit_request(str(pending.get("output", "")))
        if (request != pending
            or doc.get("action") != "preview" or doc.get("schema") != BATCH_SCHEMA
            or doc.get("status") != "dry-run"
            or doc.get("actors") != pending.get("rows")
            or doc.get("source_sha256") != source_sha256
            or doc.get("output") != pending.get("output")
            or doc.get("edited_actor_count") != staged.size()
            or not _whole(doc.get("changed_bytes"), staged.size(), 24)
            or doc.get("independent_full_package_byte_match") != true
            or doc.get("edited_package_written") != false
            or doc.get("plan_created") != false
            or doc.get("source_original_modified") != false
            or doc.get("gameplay_runtime_verified") != false
            or doc.get("native_light_spawn_enabled") != false
            or doc.get("native_bsp_or_zone_rebuild_enabled") != false):
            pending.clear()
            status.text = "Full-GMP parity preview refused: stale source, edits or unsupported result."
        else:
            confirmation.dialog_text = (
                "EXPERIMENTAL: 2–8 EXISTING ORIGINAL LightColor ACTORS ONLY\n\n"
                + "Original map: " + source_map.get_file()
                + "\nSource SHA: " + source_sha256
                + "\nStaged actors: " + str(staged.size())
                + "\nChanged native byte fields: " + str(doc["changed_bytes"])
                + "\nIsolated GMP: " + str(pending["output"])
                + "\nPrivate plan and manifest will be created alongside GMP."
                + "\n\nEntire native package parity: VERIFIED IN MEMORY."
                + "\nConfirm Save As? Native actor spawning and retail runtime behavior remain unverified.")
            confirmation.popup_centered(Vector2i(745, 360))
            status.text = "Preview passed: confirm isolated multi-actor Save As."
    elif action == "apply":
        if (doc.get("action") == "apply"
            and doc.get("schema") == BATCH_SCHEMA
            and doc.get("status") == "isolated-multi-LightColor-verified-runtime-unverified"
            and doc.get("source_sha256") == source_sha256
            and doc.get("output") == pending.get("output")
            and doc.get("actors") == pending.get("rows")
            and doc.get("edited_actor_count") == staged.size()
            and doc.get("independent_full_package_byte_match") == true
            and doc.get("verified_binary_structure") == true
            and doc.get("source_original_modified") == false
            and doc.get("gameplay_runtime_verified") == false
            and doc.get("native_light_spawn_enabled") == false
            and doc.get("native_bsp_or_zone_rebuild_enabled") == false):
            status.text = (
                "Verified isolated LightColor group: " + str(doc.get("output"))
                + " | Plan and manifest saved. Original unchanged; runtime not tested.")
        else:
            status.text = "Batch output failed final verification. Inspect the private files."
        pending.clear()
    _update_buttons()
