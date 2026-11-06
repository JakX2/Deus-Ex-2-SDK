extends VBoxContainer
## DX2Ed v0.12: original existing LightColor (#116) editing panel.
## This is NOT a native Light factory, arbitrary GameSys writer, or gameplay
## runtime guarantee. Every eligible actor is enumerated afresh by DX2SDK.
## Preview proves full-package T3SDK/direct-offset byte parity; explicit
## confirmation writes only a fresh same-basename isolated copy.
const PythonRuntime = preload("res://python_runtime.gd")
const BRIDGE_SCHEMA := "DX2Ed-GUI-original-LightColor-worker-v1"
const SOURCE_SCHEMA := "DX2SDK-source-existing-LightColor-v1"
const BYTE_FIELDS := ["brightness", "hue", "saturation"]

var source_map := ""
var source_sha256 := ""
var worker_script := ""
var inventory: Array[Dictionary] = []
var selected_index := -1
var pending: Dictionary = {}
var worker: Thread = null
var generation := 0

var note: Label
var status: Label
var scan_button: Button
var actors_list: ItemList
var values: Dictionary = {}
var export_button: Button
var save_dialog: FileDialog
var confirm_dialog: ConfirmationDialog


func _ready() -> void:
    name = "LightColor"
    var heading := Label.new()
    heading.text = "Original LightColor | Experimental isolated GMP Save As"
    heading.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(heading)
    note = Label.new()
    note.text = "Open an original DX2 GMP first. Only existing authored LightColor (GameSys 116) bytes can change. This does not add native Lights or rebuild BSP."
    note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(note)
    scan_button = Button.new()
    scan_button.text = "Scan original LightColor fields"
    scan_button.disabled = true
    scan_button.pressed.connect(_scan)
    add_child(scan_button)
    actors_list = ItemList.new()
    actors_list.custom_minimum_size.y = 160
    actors_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    actors_list.item_selected.connect(_pick_actor)
    add_child(actors_list)
    for key in BYTE_FIELDS:
        var row := HBoxContainer.new()
        add_child(row)
        var label := Label.new()
        label.text = key.capitalize()
        label.custom_minimum_size.x = 100
        row.add_child(label)
        var spin := SpinBox.new()
        spin.min_value = 0
        spin.max_value = 255
        spin.step = 1
        spin.rounded = true
        spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        spin.editable = false
        row.add_child(spin)
        values[key] = spin
    export_button = Button.new()
    export_button.text = "Preview byte parity and Save As..."
    export_button.disabled = true
    export_button.tooltip_text = (
        "First compare independent full GMP bytes in memory. Then confirm a new"
        + " isolated same-basename GMP and private manifest. Original remains unchanged.")
    export_button.pressed.connect(_choose_output)
    add_child(export_button)
    status = Label.new()
    status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    status.text = "No original map selected. Native gameplay effect remains unverified."
    add_child(status)
    save_dialog = FileDialog.new()
    save_dialog.access = FileDialog.ACCESS_FILESYSTEM
    save_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    save_dialog.filters = PackedStringArray([
        "*.gmp ; Private existing-LightColor GMP copy"
    ])
    save_dialog.file_selected.connect(_selected_destination)
    add_child(save_dialog)
    confirm_dialog = ConfirmationDialog.new()
    confirm_dialog.title = "Confirm existing original LightColor byte edit"
    confirm_dialog.confirmed.connect(_confirmed_write)
    add_child(confirm_dialog)


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
    selected_index = -1
    pending.clear()
    if actors_list != null:
        actors_list.clear()
    for key in BYTE_FIELDS:
        if values.has(key):
            values[key].editable = false
            values[key].value = 0
    if scan_button != null:
        scan_button.disabled = true
    if export_button != null:
        export_button.disabled = true
    if status != null:
        status.text = "No verified original GMP. Never writes into a game folder."


func configure_original(map_path: String, sha: String, script: String) -> bool:
    reset_context()
    if (map_path.get_extension().to_lower() != "gmp"
        or not FileAccess.file_exists(map_path)
        or sha.length() != 64 or not sha.is_valid_hex_number()
        or not FileAccess.file_exists(script)
        or FileAccess.get_sha256(map_path).to_lower() != sha.to_lower()):
        if status != null:
            status.text = "LightColor unavailable: original GMP or SHA/source worker mismatch."
        return false
    source_map = map_path
    source_sha256 = sha.to_lower()
    worker_script = script
    if status != null:
        status.text = "Ready: scan eligible original GameSys 116 structs. No GMP output by scanning."
    if scan_button != null:
        scan_button.disabled = worker != null
    return true


func _context_ok() -> bool:
    return (not source_map.is_empty() and not source_sha256.is_empty()
        and FileAccess.file_exists(source_map)
        and FileAccess.file_exists(worker_script)
        and FileAccess.get_sha256(source_map).to_lower() == source_sha256)


func accept_inventory(response: Dictionary) -> bool:
    ## The Python worker is the native authority. This is a second UI-side
    ## schema/identity/byte check, NOT standalone qualification for writing.
    if (not _context_ok() or response.get("bridge_schema") != BRIDGE_SCHEMA
        or response.get("schema") != SOURCE_SCHEMA
        or response.get("action") != "list"
        or response.get("status") != "read-only-source-verified"
        or response.get("source_sha256") != source_sha256
        or str(response.get("source_map", "")).to_lower() != source_map.get_file().to_lower()
        or response.get("read_only") != true
        or response.get("gameplay_runtime_verified") != false
        or response.get("native_new_light_actor_creation_enabled") != false
        or response.get("source_original_modified") != false
        or typeof(response.get("shown")) != TYPE_ARRAY
        or response["shown"].size() > 1000):
        return false
    var rows: Array[Dictionary] = []
    var used: Dictionary = {}
    for record in response["shown"]:
        if typeof(record) != TYPE_DICTIONARY:
            return false
        var exp: Variant = record.get("export")
        if not _whole(exp, 1, 2147483647):
            return false
        var index := int(exp)
        var actor: Variant = record.get("actor")
        var cls: Variant = record.get("actor_class")
        if (used.has(index)
            or typeof(actor) != TYPE_STRING or str(actor).is_empty()
            or typeof(cls) != TYPE_STRING or str(cls).is_empty()
            or record.get("strict_existing_struct_writer_candidate") != true
            or record.get("actual_gameplay_effect_for_this_actor_verified") != false):
            return false
        var original: Variant = record.get("original_values")
        if typeof(original) != TYPE_DICTIONARY or original.size() != 3:
            return false
        var source_values: Dictionary = {}
        for field in BYTE_FIELDS:
            if not original.has(field) or not _whole(original[field], 0, 255):
                return false
            source_values[field] = int(original[field])
        rows.append({
            "export": index, "actor": actor, "actor_class": cls,
            "original_values": source_values,
        })
        used[index] = true
    inventory = rows
    selected_index = -1
    pending.clear()
    if actors_list != null:
        actors_list.clear()
        for row in inventory:
            var original: Dictionary = row["original_values"]
            actors_list.add_item(
                "#%d %s | B%d H%d S%d" % [
                    int(row["export"]), str(row["actor"]),
                    int(original["brightness"]), int(original["hue"]),
                    int(original["saturation"])])
    for field in BYTE_FIELDS:
        if values.has(field):
            values[field].editable = false
            values[field].value = 0
    if export_button != null:
        export_button.disabled = true
    if status != null:
        status.text = ("%d original authored LightColor candidates scanned."
                       + " Select one. Every Save As requires full-byte parity.") % inventory.size()
    return true


func _whole(value: Variant, minimum: int, maximum: int) -> bool:
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value))
        and float(value) >= float(minimum) and float(value) <= float(maximum)
        and float(int(value)) == float(value))


func _pick_actor(index: int) -> void:
    if index < 0 or index >= inventory.size():
        return
    selected_index = index
    pending.clear()
    var source: Dictionary = inventory[index]["original_values"]
    for key in BYTE_FIELDS:
        if values.has(key):
            values[key].value = int(source[key])
            values[key].editable = true
    if export_button != null:
        export_button.disabled = worker != null
    if status != null:
        status.text = ("Source #%d %s selected. Change 1–3 bytes."
                       + " Preview proves exact GMP parity before confirmation.") % [
                           int(inventory[index]["export"]),
                           str(inventory[index]["actor"])]


func edit_request(target: String) -> Dictionary:
    ## Empty unless the original source, original actor and output remain safe.
    if (not _context_ok() or selected_index < 0
        or selected_index >= inventory.size()
        or target.get_file().to_lower() != source_map.get_file().to_lower()
        or target == source_map
        or FileAccess.file_exists(target)):
        return {}
    var row: Dictionary = inventory[selected_index]
    var source: Dictionary = row["original_values"]
    var changes: Dictionary = {}
    for key in BYTE_FIELDS:
        var value := int(values[key].value)
        if value != int(source[key]):
            changes[key] = value
    if changes.is_empty():
        return {}
    return {
        "map": source_map, "source_sha256": source_sha256,
        "actor": row["actor"], "export": row["export"],
        "expected": [
            int(source["brightness"]), int(source["hue"]),
            int(source["saturation"])],
        "changes": changes, "output": target,
    }


func _scan() -> void:
    if not _context_ok():
        status.text = "Original map changed. Reopen the map to rescan source LightColor."
        return
    _start("list", {
        "map": source_map, "source_sha256": source_sha256,
    })


func _choose_output() -> void:
    if selected_index < 0 or not _context_ok() or worker != null:
        status.text = "Select an original LightColor field after a verified map scan."
        return
    save_dialog.current_file = source_map.get_file()
    save_dialog.popup_centered_ratio(0.7)


func _selected_destination(target: String) -> void:
    var request := edit_request(target)
    if request.is_empty():
        status.text = ("Save As refused: select changed byte values and a NEW"
                       + " isolated GMP with the original filename.")
        return
    pending = request.duplicate(true)
    _start("preview", pending)


func _confirmed_write() -> void:
    if pending.is_empty() or worker != null:
        return
    var request := edit_request(str(pending.get("output", "")))
    if request != pending:
        pending.clear()
        status.text = "Save As refused: selected actor, source or edit changed after preview."
        return
    _start("apply", request)


func _start(action: String, request: Dictionary) -> void:
    if worker != null or not _context_ok():
        if status != null:
            status.text = "LightColor worker unavailable or original source has changed."
        return
    var argv := PackedStringArray([
        worker_script, action,
        "--map", source_map, "--source-sha256", source_sha256])
    if action == "list":
        argv.append_array(PackedStringArray(["--limit", "1000"]))
    else:
        argv.append_array(PackedStringArray([
            "--actor", str(request["actor"]),
            "--export", str(request["export"]),
            "--expect", str(request["expected"][0]),
            str(request["expected"][1]), str(request["expected"][2]),
            "--output", str(request["output"]),
        ]))
        for key in BYTE_FIELDS:
            if request["changes"].has(key):
                argv.append("--" + key)
                argv.append(str(request["changes"][key]))
    worker = Thread.new()
    if scan_button != null:
        scan_button.disabled = true
    if export_button != null:
        export_button.disabled = true
    var started := worker.start(_run_worker.bind(argv, action, generation))
    if started != OK:
        worker = null
        if scan_button != null:
            scan_button.disabled = false
        status.text = "Unable to start original LightColor Python worker."
        return
    status.text = ("Reading source-only LightColor inventory..." if action == "list"
        else "Rechecking exact original LightColor bytes and independent serializer parity..."
        if action == "preview"
        else "Saving isolated GMP with independent full-package verification...")


func _run_worker(argv: PackedStringArray, action: String, epoch: int) -> void:
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), argv, output, true)
    if code == -1:
        var py_args := PackedStringArray(["-3"])
        py_args.append_array(argv)
        output.clear()
        code = OS.execute("py", py_args, output, true)
    call_deferred("_worker_finished", code, "\n".join(output), action, epoch)


func _worker_finished(code: int, output: String, action: String, epoch: int) -> void:
    if worker != null:
        worker.wait_to_finish()
        worker = null
    if epoch != generation or not _context_ok():
        reset_context()
        return
    var doc: Variant = JSON.parse_string(output.strip_edges())
    if (code != 0 or typeof(doc) != TYPE_DICTIONARY
        or doc.get("bridge_schema") != BRIDGE_SCHEMA):
        var reason := (str(doc.get("reason", "Refused")) if typeof(doc) == TYPE_DICTIONARY
                       else output.strip_edges().substr(0, 280))
        status.text = "Original LightColor operation refused: " + reason
        pending.clear()
    elif action == "list":
        if not accept_inventory(doc):
            status.text = "Refused inventory: mismatched source, unknown format or unsafe actor."
            pending.clear()
    elif action == "preview":
        var changes: Dictionary = pending.get("changes", {})
        if (doc.get("action") != "preview" or doc.get("status") != "dry-run"
            or doc.get("source_sha256") != source_sha256
            or doc.get("actor") != pending.get("actor")
            or not _whole(doc.get("actor_export"), 1, 2147483647)
            or int(doc["actor_export"]) != int(pending.get("export", -1))
            or doc.get("dual_serializer_full_package_match") != true
            or doc.get("edited_package_written") != false
            or doc.get("original_map_modified") != false
            or doc.get("gameplay_runtime_verified") != false
            or int(doc.get("changed_bytes", -1)) != changes.size()
            or pending != edit_request(str(pending.get("output", "")))):
            status.text = "Preview rejected: source, edit or exact GMP parity changed."
            pending.clear()
        else:
            confirm_dialog.dialog_text = (
                "EXPERIMENTAL EXISTING-ACTOR LightColor ONLY\n\n"
                + "Original actor: " + str(pending["actor"])
                + " | export #" + str(pending["export"])
                + "\nOriginal B/H/S: " + str(pending["expected"])
                + "\nChanged bytes: " + str(changes)
                + "\nIsolated output: " + str(pending["output"])
                + "\n\nIndependent full-package parity PASSED in memory."
                + "\nConfirm to create one new GMP and private manifest."
                + "\nNever install over retail files. Runtime effects remain unverified.")
            confirm_dialog.popup_centered(Vector2i(720, 350))
            status.text = "Dry-run parity passed. Confirm isolated Save As to write."
    elif action == "apply":
        if (doc.get("action") == "apply"
            and doc.get("status") == "isolated-verified-runtime-unverified"
            and doc.get("source_sha256") == source_sha256
            and doc.get("output") == str(pending.get("output", ""))
            and doc.get("verified_binary_structure") == true
            and doc.get("dual_serializer_full_package_match") == true
            and doc.get("original_map_modified") == false
            and doc.get("new_light_actor_created") == false
            and doc.get("gameplay_runtime_verified") == false):
            status.text = ("Isolated GMP verified: " + str(doc["output"])
                           + ". Original unchanged; retail runtime NOT tested.")
        else:
            status.text = "Isolated LightColor copy failed independent verification."
        pending.clear()
    if scan_button != null:
        scan_button.disabled = false
    if export_button != null:
        export_button.disabled = selected_index < 0
