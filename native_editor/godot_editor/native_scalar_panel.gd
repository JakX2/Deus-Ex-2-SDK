extends VBoxContainer
## DX2Ed v0.14: guarded top-level source-native int32/float32 editor.
## ONLY original placed StaticMeshActor with a matching owner actors.json,
## and only PREEXISTING four-byte UE95 tagged property kinds 2/4.
## Never edits GameSys, transforms, native Light, BSP or collision geometry.
const PythonRuntime = preload("res://python_runtime.gd")
const BRIDGE_SCHEMA := "DX2Ed-GUI-original-native-scalar-worker-v1"
const SDK_SCHEMA := "DX2SDK-native-tagged-scalar-copy-v1"
const MAX_NATIVE_ACTORS := 1000

var source_map := ""
var actors_file := ""
var source_sha256 := ""
var actors_sha256 := ""
var worker_script := ""
var generation := 0
var worker: Thread = null
var original_actors: Array[Dictionary] = []
var original_fields: Array[Dictionary] = []
var chosen_actor_index := -1
var chosen_field_index := -1
var pending: Dictionary = {}

var note: Label
var status: Label
var scan_button: Button
var actor_list: ItemList
var field_list: ItemList
var field_value: SpinBox
var field_origin: Label
var save_button: Button
var save_dialog: FileDialog
var confirmation: ConfirmationDialog


func _ready() -> void:
    name = "Native Scalars"
    note = Label.new()
    note.text = ("Existing original StaticMeshActor IntProperty / FloatProperty only."
        + " The GMP AND its matching private actors.json are SHA-pinned."
        + " Location, Rotation, geometry, GameSys, scripts and native actor"
        + " creation are unavailable. Retail runtime effect is unverified.")
    note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(note)
    scan_button = Button.new()
    scan_button.text = "Scan original StaticMeshActors"
    scan_button.disabled = true
    scan_button.pressed.connect(_scan)
    add_child(scan_button)
    var a_title := Label.new()
    a_title.text = "Original source actors"
    add_child(a_title)
    actor_list = ItemList.new()
    actor_list.custom_minimum_size.y = 130
    actor_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    actor_list.item_selected.connect(_pick_actor)
    add_child(actor_list)
    var f_title := Label.new()
    f_title.text = "Eligible authored 4-byte numeric fields"
    add_child(f_title)
    field_list = ItemList.new()
    field_list.custom_minimum_size.y = 125
    field_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    field_list.item_selected.connect(_pick_field)
    add_child(field_list)
    field_origin = Label.new()
    field_origin.text = "Select an actor, then an original numeric field."
    field_origin.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(field_origin)
    var value_row := HBoxContainer.new()
    add_child(value_row)
    var label := Label.new()
    label.text = "New native value"
    value_row.add_child(label)
    field_value = SpinBox.new()
    field_value.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    field_value.min_value = -1000000.0
    field_value.max_value = 1000000.0
    field_value.step = 0.01
    field_value.allow_greater = false
    field_value.allow_lesser = false
    field_value.editable = false
    value_row.add_child(field_value)
    save_button = Button.new()
    save_button.text = "Preview original scalar and Save As..."
    save_button.tooltip_text = (
        "Preview rechecks unchanged original GMP + actors.json and T3SDK no-op"
        + " reassembly, but writes nothing. Confirm to create one isolated GMP"
        + " and its independently verified original-byte manifest.")
    save_button.disabled = true
    save_button.pressed.connect(_choose_output)
    add_child(save_button)
    status = Label.new()
    status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    status.text = "Open a GMP through DX2Ed to establish source actor/cache identity."
    add_child(status)
    save_dialog = FileDialog.new()
    save_dialog.access = FileDialog.ACCESS_FILESYSTEM
    save_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    save_dialog.filters = PackedStringArray(
        ["*.gmp ; Fresh isolated original native scalar GMP"])
    save_dialog.file_selected.connect(_output_selected)
    add_child(save_dialog)
    confirmation = ConfirmationDialog.new()
    confirmation.title = "Confirm experimental native scalar Save As"
    confirmation.confirmed.connect(_confirmed_apply)
    add_child(confirmation)


func _exit_tree() -> void:
    if worker != null:
        worker.wait_to_finish()
        worker = null


func reset_context() -> void:
    generation += 1
    source_map = ""
    actors_file = ""
    source_sha256 = ""
    actors_sha256 = ""
    worker_script = ""
    original_actors.clear()
    original_fields.clear()
    chosen_actor_index = -1
    chosen_field_index = -1
    pending.clear()
    if actor_list != null:
        actor_list.clear()
    if field_list != null:
        field_list.clear()
    if field_value != null:
        field_value.editable = false
        field_value.value = 0
    if field_origin != null:
        field_origin.text = "No eligible authored scalar selected."
    _update_buttons()
    if status != null:
        status.text = "Source context cleared. No original GMP or actor cache can be changed."


func configure_original(map: String, cache: String, map_sha: String,
                        bridge: String) -> bool:
    reset_context()
    if (map.get_extension().to_lower() != "gmp"
        or cache.get_file().to_lower() != "actors.json"
        or not FileAccess.file_exists(map)
        or not FileAccess.file_exists(cache)
        or not FileAccess.file_exists(bridge)
        or map_sha.length() != 64 or not map_sha.is_valid_hex_number()
        or FileAccess.get_sha256(map).to_lower() != map_sha.to_lower()):
        if status != null:
            status.text = "Native scalar editor unavailable: unverified map/cache/worker."
        return false
    source_map = map
    actors_file = cache
    source_sha256 = map_sha.to_lower()
    actors_sha256 = FileAccess.get_sha256(cache).to_lower()
    worker_script = bridge
    _update_buttons()
    status.text = ("Original GMP and private actors.json pinned. Scan native"
                   + " StaticMeshActor names; only authored numeric tags may be edited.")
    return true


func _context_ok() -> bool:
    return (not source_map.is_empty() and not actors_file.is_empty()
        and not source_sha256.is_empty() and not actors_sha256.is_empty()
        and FileAccess.file_exists(source_map)
        and FileAccess.file_exists(actors_file)
        and FileAccess.file_exists(worker_script)
        and FileAccess.get_sha256(source_map).to_lower() == source_sha256
        and FileAccess.get_sha256(actors_file).to_lower() == actors_sha256)


func _int_in_range(value: Variant, lo: int, hi: int) -> bool:
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value))
        and float(value) >= float(lo) and float(value) <= float(hi)
        and float(int(value)) == float(value))


func accept_actor_inventory(doc: Dictionary) -> bool:
    if (not _context_ok() or doc.get("bridge_schema") != BRIDGE_SCHEMA
        or doc.get("action") != "list" or doc.get("schema") != SDK_SCHEMA
        or doc.get("status") != "original_staticmeshactor_list"
        or doc.get("source_sha256") != source_sha256
        or doc.get("actors_sha256") != actors_sha256
        or doc.get("source_map") != source_map.get_file()
        or doc.get("source_actor_cache_verified") != true
        or doc.get("read_only") != true
        or doc.get("source_original_modified") != false
        or doc.get("runtime_game_verified") != false
        or doc.get("native_new_actor_creation_enabled") != false
        or doc.get("native_gamesys_or_script_writer_enabled") != false
        or typeof(doc.get("actors")) != TYPE_ARRAY
        or doc["actors"].size() > MAX_NATIVE_ACTORS
        or doc.get("shown_count") != doc["actors"].size()):
        return false
    var rows: Array[Dictionary] = []
    var exports := {}
    for item in doc["actors"]:
        if (typeof(item) != TYPE_DICTIONARY
            or not _int_in_range(item.get("export"), 1, 2147483647)
            or typeof(item.get("actor")) != TYPE_STRING
            or str(item["actor"]).is_empty()
            or item.get("actor_class") != "StaticMeshActor"):
            return false
        var export := int(item["export"])
        if exports.has(export):
            return false
        exports[export] = true
        rows.append({"actor": str(item["actor"]), "export": export})
    original_actors = rows
    original_fields.clear()
    chosen_actor_index = -1
    chosen_field_index = -1
    pending.clear()
    actor_list.clear()
    field_list.clear()
    for item in original_actors:
        actor_list.add_item("#%d  %s" % [
            int(item["export"]), str(item["actor"])])
    field_value.editable = false
    field_origin.text = ("Select an original StaticMeshActor to inspect its"
                         + " existing safe top-level IntProperty/FloatProperty fields.")
    _update_buttons()
    status.text = "%d original positioned StaticMeshActors listed. Source-only." % rows.size()
    return true


func _pick_actor(index: int) -> void:
    if (worker != null or not _context_ok()
        or index < 0 or index >= original_actors.size()):
        return
    chosen_actor_index = index
    original_fields.clear()
    chosen_field_index = -1
    field_list.clear()
    field_value.editable = false
    pending.clear()
    _update_buttons()
    var row: Dictionary = original_actors[index]
    _start("fields", {
        "actor": str(row["actor"]), "export": int(row["export"]),
    })


func accept_original_fields(doc: Dictionary) -> bool:
    if (not _context_ok() or chosen_actor_index < 0
        or chosen_actor_index >= original_actors.size()
        or doc.get("bridge_schema") != BRIDGE_SCHEMA
        or doc.get("action") != "fields" or doc.get("schema") != SDK_SCHEMA
        or doc.get("status") != "original_scalar_field_inventory"
        or doc.get("source_sha256") != source_sha256
        or doc.get("actors_sha256") != actors_sha256
        or doc.get("source_map") != source_map.get_file()
        or doc.get("original_map_sha256") != source_sha256
        or doc.get("original_map") != source_map.get_file()
        or doc.get("actor_name") != original_actors[chosen_actor_index]["actor"]
        or doc.get("export") != original_actors[chosen_actor_index]["export"]
        or doc.get("read_only") != true
        or doc.get("runtime_game_verified") != false
        or doc.get("native_gamesys_or_script_writer_enabled") != false
        or doc.get("source_original_modified") != false
        or typeof(doc.get("fields")) != TYPE_ARRAY
        or doc["fields"].size() > 256):
        return false
    var accepted: Array[Dictionary] = []
    var names := {}
    for item in doc["fields"]:
        if (typeof(item) != TYPE_DICTIONARY
            or typeof(item.get("property")) != TYPE_STRING
            or str(item["property"]).is_empty()
            or item.get("type") not in ["int32", "float32"]):
            return false
        var name := str(item["property"])
        var old: Variant = item.get("source_value")
        if names.has(name) or name.to_lower() in [
            "location", "rotation", "drawscale3d", "collisionradius",
            "collisionheight", "physics", "mesh", "staticmesh", "brush"]:
            return false
        if item["type"] == "int32":
            if not _int_in_range(old, -2147483648, 2147483647):
                return false
            old = int(old)
        else:
            if (typeof(old) not in [TYPE_FLOAT, TYPE_INT]
                or not is_finite(float(old))
                or abs(float(old)) > 1000000.0):
                return false
            old = float(old)
        accepted.append({
            "property": name, "type": item["type"], "source_value": old,
        })
        names[name] = true
    original_fields = accepted
    chosen_field_index = -1
    pending.clear()
    field_list.clear()
    for item in original_fields:
        field_list.add_item("%s  [%s]  source=%s" % [
            str(item["property"]), str(item["type"]), str(item["source_value"])])
    field_value.editable = false
    field_origin.text = ("Only %d original tagged numeric fields passed source"
                         + " verification. No GameSys or transform fields.") % accepted.size()
    _update_buttons()
    status.text = "Actor inspected; select an original int32 or float32 tag to edit."
    return true


func _pick_field(index: int) -> void:
    if (worker != null or not _context_ok()
        or index < 0 or index >= original_fields.size()
        or chosen_actor_index < 0):
        return
    chosen_field_index = index
    pending.clear()
    var row: Dictionary = original_fields[index]
    if row["type"] == "int32":
        field_value.min_value = -2147483648.0
        field_value.max_value = 2147483647.0
        field_value.step = 1.0
        field_value.rounded = true
    else:
        field_value.min_value = -1000000.0
        field_value.max_value = 1000000.0
        field_value.step = 0.01
        field_value.rounded = false
    field_value.value = float(row["source_value"])
    field_value.editable = true
    field_origin.text = (
        "Original authored %s [%s] = %s. Change a value before Save As."
        % [str(row["property"]), str(row["type"]), str(row["source_value"])])
    _update_buttons()


func edit_request(target: String) -> Dictionary:
    if (worker != null or not _context_ok()
        or chosen_actor_index < 0 or chosen_actor_index >= original_actors.size()
        or chosen_field_index < 0 or chosen_field_index >= original_fields.size()
        or target.get_file().to_lower() != source_map.get_file().to_lower()
        or target == source_map
        or FileAccess.file_exists(target)):
        return {}
    var manifest := target.get_basename() + ".dx2sdk-scalar.json"
    if FileAccess.file_exists(manifest):
        return {}
    var actor: Dictionary = original_actors[chosen_actor_index]
    var field: Dictionary = original_fields[chosen_field_index]
    var new_value: Variant = field_value.value
    if field["type"] == "int32":
        if not _int_in_range(new_value, -2147483648, 2147483647):
            return {}
        new_value = int(new_value)
    else:
        if (not is_finite(float(new_value))
            or abs(float(new_value)) > 1000000.0):
            return {}
        new_value = float(new_value)
    if new_value == field["source_value"]:
        return {}
    return {
        "actor": str(actor["actor"]), "export": int(actor["export"]),
        "property": str(field["property"]), "type": str(field["type"]),
        "expected": field["source_value"],
        "replacement": new_value,
        "output": target,
    }


func _update_buttons() -> void:
    if scan_button != null:
        scan_button.disabled = worker != null or not _context_ok()
    if save_button != null:
        save_button.disabled = (
            worker != null or not _context_ok()
            or chosen_actor_index < 0 or chosen_field_index < 0)


func _scan() -> void:
    if _context_ok():
        _start("list", {})
    else:
        status.text = "Scalar source or original actors.json has changed. Reopen the GMP."


func _choose_output() -> void:
    if save_button.disabled or not _context_ok():
        status.text = "Select an original safe numeric field and unchanged map/cache."
        return
    save_dialog.current_file = source_map.get_file()
    save_dialog.popup_centered_ratio(0.7)


func _output_selected(target: String) -> void:
    var request := edit_request(target)
    if request.is_empty():
        status.text = ("Scalar Save As refused: change a source numeric value"
                       + " and choose a NEW isolated original-basename GMP.")
        return
    pending = request.duplicate(true)
    _start("preview", pending)


func _confirmed_apply() -> void:
    if pending.is_empty() or worker != null:
        return
    var target := str(pending.get("output", ""))
    if edit_request(target) != pending:
        pending.clear()
        status.text = "Scalar Save As refused: original actor, field, cache or edit changed."
        return
    _start("apply", pending)


func _start(action: String, req: Dictionary) -> void:
    if worker != null or not _context_ok():
        if status != null:
            status.text = "Source/checksum mismatch; scalar worker unavailable."
        return
    var argv := PackedStringArray([
        worker_script, action, "--map", source_map,
        "--actors", actors_file, "--source-sha256", source_sha256,
        "--actors-sha256", actors_sha256,
    ])
    if action == "fields":
        argv.append_array(PackedStringArray([
            "--actor", str(req["actor"]), "--export", str(req["export"])]))
    elif action in ["preview", "apply"]:
        var copy: Dictionary = req.duplicate(true)
        copy.erase("output")
        argv.append("--request-json")
        argv.append(JSON.stringify(copy))
        argv.append("--output")
        argv.append(str(req["output"]))
    worker = Thread.new()
    _update_buttons()
    var started := worker.start(_execute.bind(argv, action, generation))
    if started != OK:
        worker = null
        _update_buttons()
        status.text = "Could not start source-only original scalar Python worker."
        return
    status.text = ("Scanning original StaticMeshActor source metadata..." if action == "list"
        else "Checking original native numeric tagged properties..." if action == "fields"
        else "Proving original T3SDK no-op and in-memory scalar patch..." if action == "preview"
        else "Saving one isolated GMP and verifying every original package byte...")


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
                       else raw.strip_edges().substr(0, 310))
        status.text = "Original scalar worker refused: " + reason
        pending.clear()
    elif action == "list":
        if not accept_actor_inventory(doc):
            status.text = "Source StaticMeshActor inventory rejected."
    elif action == "fields":
        if not accept_original_fields(doc):
            status.text = "Original scalar fields rejected: source, type or actor identity."
    elif action == "preview":
        var fresh := edit_request(str(pending.get("output", "")))
        if (fresh != pending or doc.get("action") != "preview"
            or doc.get("schema") != SDK_SCHEMA or doc.get("status") != "dry-run"
            or doc.get("source_sha256") != source_sha256
            or doc.get("actors_sha256") != actors_sha256
            or doc.get("actor") != pending.get("actor")
            or doc.get("export") != pending.get("export")
            or doc.get("property") != pending.get("property")
            or doc.get("type") != pending.get("type")
            or doc.get("expected") != pending.get("expected")
            or doc.get("output") != pending.get("output")
            or not _int_in_range(doc.get("changed_byte_count"), 1, 4)
            or doc.get("source_noop_T3SDK_parity_verified") != true
            or doc.get("edited_package_written") != false
            or doc.get("saved_binary_structure_verified") != false
            or doc.get("source_original_modified") != false
            or doc.get("runtime_game_verified") != false
            or doc.get("native_gamesys_or_script_writer_enabled") != false):
            pending.clear()
            status.text = "Scalar preview rejected: stale value or incorrect native proof."
        else:
            confirmation.dialog_text = (
                "EXPERIMENTAL ORIGINAL STATICMESH ACTOR NUMERIC TAG ONLY\n\n"
                + "Actor: " + str(pending["actor"])
                + " | export #" + str(pending["export"])
                + "\nNative property: " + str(pending["property"])
                + " [" + str(pending["type"]) + "]"
                + "\nOriginal source: " + str(pending["expected"])
                + "\nReplacement: " + str(pending["replacement"])
                + "\nEstimated changed source bytes: " + str(doc["changed_byte_count"])
                + "\nOriginal/cache SHA: " + source_sha256.substr(0, 12)
                + " / " + actors_sha256.substr(0, 12)
                + "\nNew isolated GMP: " + str(pending["output"])
                + "\n\nPreview: original full T3SDK no-op and in-memory patch passed."
                + "\nConfirm Save As to WRITE and independently verify each package byte."
                + "\nNative gameplay and runtime behavior remain UNVERIFIED.")
            confirmation.popup_centered(Vector2i(745, 370))
            status.text = "Preview passed without writing. Confirm isolated scalar Save As."
    elif action == "apply":
        if (doc.get("action") == "apply" and doc.get("schema") == SDK_SCHEMA
            and doc.get("status") == "isolated-native-scalar-verified-runtime-unverified"
            and doc.get("source_sha256") == source_sha256
            and doc.get("actors_sha256") == actors_sha256
            and doc.get("output") == pending.get("output")
            and doc.get("actor") == pending.get("actor")
            and doc.get("export") == pending.get("export")
            and doc.get("property") == pending.get("property")
            and doc.get("type") == pending.get("type")
            and doc.get("saved_binary_structure_verified") == true
            and doc.get("independent_saved_whole_GMP_byte_verification") == true
            and doc.get("source_original_modified") == false
            and doc.get("runtime_game_verified") == false
            and doc.get("native_gamesys_or_script_writer_enabled") == false):
            status.text = ("Verified native scalar GMP Save As: " + str(doc["output"])
                           + " | Original and actors.json unchanged. Retail untested.")
        else:
            status.text = "Scalar copy failed source replay/byte verification."
        pending.clear()
    _update_buttons()
