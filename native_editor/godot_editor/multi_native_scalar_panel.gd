extends "res://native_scalar_panel.gd"
## DX2Ed v0.17: source-only searchable Actor Workbench plus staged 2..8 numeric tags.
## Inherits v0.14's source SHA+private actors.json SHA proof, authentic
## StaticMeshActor and eligible tagged-property inspection and typed controls.
## The Python worker alone decides whether native bytes can be written.
const WorkbenchView = preload("res://workbench_view_model.gd")
const BATCH_BRIDGE_SCHEMA := "DX2Ed-GUI-original-multi-native-scalar-worker-v1"
const WORKBENCH_SCHEMA := "DX2SDK-original-actor-property-workbench-v1"
const WORKBENCH_CATEGORY_ORDER := [
    "eligible-original-numeric", "protected-original",
    "duplicate-original-name", "indexed-or-special",
    "unsupported-numeric-layout", "opaque-uninterpreted",
]
const MAX_BATCH := 8
const MIN_BATCH := 2

var staged: Array[Dictionary] = []
var stage_button: Button
var stage_list: ItemList
var remove_button: Button
var clear_button: Button
var batch_button: Button
var batch_confirmation: ConfirmationDialog
var batch_save_dialog: FileDialog
var source_property_tree: Tree
var property_search: LineEdit
var property_mode: OptionButton
var property_statistics: Label
var property_details: TextEdit
var selected_tag_ordinal := -1
var property_catalog: Dictionary = {}


func _ready() -> void:
    super._ready()
    name = "Actor Workbench"
    note.text = ("Original Actor Property Workbench: inspect every authored"
        + " top-level UE95 tag, including protected and opaque fields."
        + " Stage 2–8 already existing int32/float32 tags for isolated Save As."
        + " Both original GMP and actors.json are SHA-locked."
        + " Unknown kinds are read only. No new actor, GameSys or BSP writer.")
    save_button.hide()
    confirmation.hide()
    save_dialog.hide()
    var browser_title := Label.new()
    browser_title.text = "Source property tree | Original / Staged or access"
    add_child(browser_title)
    var filter_row := HBoxContainer.new()
    add_child(filter_row)
    property_search = LineEdit.new()
    property_search.placeholder_text = "Search original tag, kind, category or byte offset..."
    property_search.max_length = WorkbenchView.MAX_QUERY_LENGTH
    property_search.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    property_search.text_changed.connect(_property_search_changed)
    filter_row.add_child(property_search)
    property_mode = OptionButton.new()
    for mode in WorkbenchView.modes():
        property_mode.add_item(mode)
    property_mode.select(0)
    property_mode.item_selected.connect(_property_mode_changed)
    filter_row.add_child(property_mode)
    property_statistics = Label.new()
    property_statistics.text = "No original tags loaded"
    add_child(property_statistics)
    source_property_tree = Tree.new()
    source_property_tree.columns = 3
    source_property_tree.column_titles_visible = true
    source_property_tree.set_column_title(0, "Original tag")
    source_property_tree.set_column_title(1, "Source value / layout")
    source_property_tree.set_column_title(2, "Staged / access")
    source_property_tree.hide_root = true
    source_property_tree.custom_minimum_size.y = 175
    source_property_tree.size_flags_vertical = Control.SIZE_EXPAND_FILL
    source_property_tree.item_selected.connect(_property_tree_selected)
    add_child(source_property_tree)
    var detail_title := Label.new()
    detail_title.text = "Selected source tag: serialized evidence (read only)"
    add_child(detail_title)
    property_details = TextEdit.new()
    property_details.editable = false
    property_details.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
    property_details.custom_minimum_size.y = 130
    property_details.size_flags_vertical = Control.SIZE_EXPAND_FILL
    property_details.text = "Choose an original tagged property to see source identity and access."
    add_child(property_details)
    var title := Label.new()
    title.text = "Original numeric field batch, 2–8 unique tags"
    add_child(title)
    stage_button = Button.new()
    stage_button.text = "Stage / update selected native numeric field"
    stage_button.disabled = true
    stage_button.pressed.connect(_stage)
    add_child(stage_button)
    stage_list = ItemList.new()
    stage_list.custom_minimum_size.y = 160
    stage_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    stage_list.item_selected.connect(func(_i): _update_buttons())
    add_child(stage_list)
    var row := HBoxContainer.new()
    add_child(row)
    remove_button = Button.new()
    remove_button.text = "Remove staged"
    remove_button.disabled = true
    remove_button.pressed.connect(_remove)
    row.add_child(remove_button)
    clear_button = Button.new()
    clear_button.text = "Clear batch"
    clear_button.disabled = true
    clear_button.pressed.connect(_clear)
    row.add_child(clear_button)
    batch_button = Button.new()
    batch_button.text = "Preview 2–8 numeric tags and Save As..."
    batch_button.disabled = true
    batch_button.tooltip_text = (
        "No-write original GMP no-op parity and 2..8 exact native patch proof."
        + " Confirmation creates one private GMP and full-byte scalar manifest.")
    batch_button.pressed.connect(_choose_batch_output)
    add_child(batch_button)
    batch_save_dialog = FileDialog.new()
    batch_save_dialog.access = FileDialog.ACCESS_FILESYSTEM
    batch_save_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    batch_save_dialog.filters = PackedStringArray([
        "*.gmp ; Fresh isolated source-authored numeric scalar copy"])
    batch_save_dialog.file_selected.connect(_destination)
    add_child(batch_save_dialog)
    batch_confirmation = ConfirmationDialog.new()
    batch_confirmation.title = "Confirm original native scalar batch Save As"
    batch_confirmation.confirmed.connect(_confirmed_batch)
    add_child(batch_confirmation)
    _update_buttons()


func reset_context() -> void:
    property_catalog.clear()
    selected_tag_ordinal = -1
    if property_search != null:
        property_search.text = ""
    if property_mode != null:
        property_mode.select(0)
    if property_statistics != null:
        property_statistics.text = "No original tags loaded"
    if property_details != null:
        property_details.text = "No source-authenticated property selected."
    if source_property_tree != null:
        source_property_tree.clear()
    staged.clear()
    if stage_list != null:
        stage_list.clear()
    super.reset_context()
    _update_buttons()


func accept_actor_inventory(doc: Dictionary) -> bool:
    var result := super.accept_actor_inventory(doc)
    if result:
        property_catalog.clear()
        selected_tag_ordinal = -1
        if source_property_tree != null:
            source_property_tree.clear()
        if property_statistics != null:
            property_statistics.text = "Select an original actor for native properties"
        if property_details != null:
            property_details.text = "No source-authenticated property selected."
        staged.clear()
        pending.clear()
        _refresh_staged()
    return result


func _pick_actor(index: int) -> void:
    property_catalog.clear()
    selected_tag_ordinal = -1
    if property_details != null:
        property_details.text = "Loading original actor tagged properties..."
    if property_statistics != null:
        property_statistics.text = "Source actor changed; awaiting source-tag inventory."
    if source_property_tree != null:
        source_property_tree.clear()
    super._pick_actor(index)



func _start_property_catalog(actor: String, export: int) -> void:
    if worker != null or not _context_ok():
        return
    var argv := PackedStringArray([
        worker_script, "catalog", "--map", source_map,
        "--actors", actors_file, "--source-sha256", source_sha256,
        "--actors-sha256", actors_sha256,
        "--actor", actor, "--export", str(export),
    ])
    worker = Thread.new()
    _update_buttons()
    var started := worker.start(_execute.bind(argv, "catalog", generation))
    if started != OK:
        worker = null
        _update_buttons()
        status.text = "Source tag catalog worker could not be started."
        return
    status.text = "Scanning original native tags, protected and opaque layouts (read only)..."


func accept_original_property_catalog(doc: Dictionary) -> bool:
    if (not _context_ok() or chosen_actor_index < 0
        or chosen_actor_index >= original_actors.size()
        or doc.get("bridge_schema") != BATCH_BRIDGE_SCHEMA
        or doc.get("schema") != WORKBENCH_SCHEMA
        or doc.get("action") != "catalog"
        or doc.get("status") != "source-original-actor-property-catalog"
        or doc.get("source_map") != source_map.get_file()
        or doc.get("source_sha256") != source_sha256
        or doc.get("actors_sha256") != actors_sha256
        or doc.get("actor_class") != "StaticMeshActor"
        or doc.get("actor") != original_actors[chosen_actor_index]["actor"]
        or doc.get("export") != original_actors[chosen_actor_index]["export"]
        or doc.get("source_actor_cache_verified") != true
        or doc.get("read_only") != true
        or doc.get("no_map_or_cache_mutation") != true
        or doc.get("new_tag_insertion_enabled") != false
        or doc.get("arbitrary_gamesys_editing_enabled") != false
        or doc.get("gameplay_runtime_verified") != false
        or not _int_in_range(doc.get("source_top_level_tag_count"), 0, 4096)
        or not _int_in_range(doc.get("eligible_original_numeric_count"), 0, 4096)
        or typeof(doc.get("categories")) != TYPE_ARRAY
        or doc["categories"].size() != WORKBENCH_CATEGORY_ORDER.size()):
        return false
    var numeric: Dictionary = {}
    for field in original_fields:
        numeric[str(field["property"])] = field
    var total := 0
    var editable := 0
    var ordinals := {}
    var usable_names := {}
    for i in range(WORKBENCH_CATEGORY_ORDER.size()):
        var cat: Variant = doc["categories"][i]
        if (typeof(cat) != TYPE_DICTIONARY
            or cat.get("key") != WORKBENCH_CATEGORY_ORDER[i]
            or typeof(cat.get("label")) != TYPE_STRING
            or typeof(cat.get("fields")) != TYPE_ARRAY
            or not _int_in_range(cat.get("count"), 0, 4096)
            or cat["count"] != cat["fields"].size()):
            return false
        for field in cat["fields"]:
            if (typeof(field) != TYPE_DICTIONARY
                or field.get("category") != cat["key"]
                or typeof(field.get("property")) != TYPE_STRING
                or str(field["property"]).is_empty()
                or not _int_in_range(field.get("tag_ordinal"), 0, 4095)
                or not _int_in_range(field.get("native_kind"), 0, 15)
                or not _int_in_range(field.get("serialized_payload_size"), 0, 16777216)
                or not _int_in_range(field.get("source_byte_offset"), 0, 268435456)
                or typeof(field.get("indexed_or_special")) != TYPE_BOOL
                or typeof(field.get("editable_existing_tag")) != TYPE_BOOL
                or field.get("runtime_effect_verified") != false
                or field.get("can_insert_property") != false):
                return false
            if ordinals.has(field["tag_ordinal"]):
                return false
            ordinals[field["tag_ordinal"]] = true
            total += 1
            if field["editable_existing_tag"]:
                var name := str(field["property"])
                if (cat["key"] != "eligible-original-numeric"
                    or field["native_kind"] not in [2, 4]
                    or field["serialized_payload_size"] != 4
                    or field["indexed_or_special"]
                    or not numeric.has(name) or usable_names.has(name)):
                    return false
                var prior: Dictionary = numeric[name]
                if (prior["source_value"] != field.get("original_value")
                    or prior["type"] != ("int32" if field["native_kind"] == 2
                        else "float32")):
                    return false
                usable_names[name] = true
                editable += 1
            elif field.get("original_value") != null:
                return false
    if (total != int(doc["source_top_level_tag_count"])
        or editable != int(doc["eligible_original_numeric_count"])
        or editable != numeric.size()
        or int(doc.get("read_only_original_tag_count", -1)) != total - editable):
        return false
    property_catalog = doc.duplicate(true)
    selected_tag_ordinal = -1
    _render_property_catalog()
    return true


func _property_search_changed(_value: String) -> void:
    _render_property_catalog()


func _property_mode_changed(_index: int) -> void:
    _render_property_catalog()


func _active_property_mode() -> String:
    if property_mode == null or property_mode.selected < 0:
        return WorkbenchView.MODE_ALL
    return property_mode.get_item_text(property_mode.selected)


func _catalog_field(ordinal: int) -> Dictionary:
    if property_catalog.is_empty():
        return {}
    for category in property_catalog["categories"]:
        for field in category["fields"]:
            if int(field["tag_ordinal"]) == ordinal:
                return field
    return {}


func _show_selected_property() -> void:
    if property_details == null:
        return
    var field := _catalog_field(selected_tag_ordinal)
    if field.is_empty():
        property_details.text = (
            "Choose an original tagged property to inspect its bytes, native kind and write scope.")
    else:
        property_details.text = WorkbenchView.detail(property_catalog, field, staged)


func _render_property_catalog() -> void:
    if source_property_tree == null:
        return
    source_property_tree.clear()
    if property_catalog.is_empty():
        if property_statistics != null:
            property_statistics.text = "No source-authenticated tags for this actor"
        _show_selected_property()
        return
    var result := WorkbenchView.filtered(
        property_catalog,
        property_search.text if property_search != null else "",
        _active_property_mode(), staged)
    var root := source_property_tree.create_item()
    for category in result["groups"]:
        var section := source_property_tree.create_item(root)
        section.set_text(0, str(category["label"]) + " (" + str(category["count"]) + ")")
        section.set_selectable(0, false)
        for field in category["fields"]:
            var entry := source_property_tree.create_item(section)
            var pname := str(field["property"])
            entry.set_text(0, pname + " (kind " + str(field["native_kind"]) + ")")
            # An ordinal identifies one exact original serialized tag, including
            # duplicate names. Read-only entries can be SELECTED for inspection,
            # but never authorize numeric editing.
            entry.set_metadata(0, int(field["tag_ordinal"]))
            if field["editable_existing_tag"]:
                entry.set_text(1, str(field["original_value"]))
                entry.set_text(2,
                    ("STAGED -> " + str(field["staged_replacement"])
                     if field["has_staged_change"] else "Eligible original numeric tag"))
            else:
                entry.set_text(1, str(field["serialized_payload_size"]) + " bytes (not decoded)")
                entry.set_text(2, "Read only | " + str(field["category"]))
    if property_statistics != null:
        property_statistics.text = ("%d of %d original tags visible | %d currently staged" % [
            int(result["shown"]), int(result["total"]), staged.size()])
    _show_selected_property()


func _property_tree_selected() -> void:
    if source_property_tree == null or worker != null or not _context_ok():
        return
    var selected := source_property_tree.get_selected()
    if selected == null:
        return
    var ordinal: Variant = selected.get_metadata(0)
    if typeof(ordinal) != TYPE_INT:
        return
    var field := _catalog_field(int(ordinal))
    if field.is_empty():
        return
    selected_tag_ordinal = int(ordinal)
    _show_selected_property()
    if field["editable_existing_tag"]:
        for i in range(original_fields.size()):
            var approved: Dictionary = original_fields[i]
            if (approved["property"] == field["property"]
                and approved["source_value"] == field["original_value"]
                and approved["type"] == ("int32" if field["native_kind"] == 2 else "float32")):
                _pick_field(i)
                status.text = "Original authenticated numeric tag selected: " + str(field["property"])
                return
    # A protected/opaque field is selectable for its source layout detail,
    # never to stage a writer field. Already staged edits are preserved.
    chosen_field_index = -1
    field_value.editable = false
    field_list.deselect_all()
    _update_buttons()
    status.text = "Source-native tag is READ ONLY. No numeric writer is authorized."


func _current_row() -> Dictionary:
    if (worker != null or not _context_ok()
        or chosen_actor_index < 0 or chosen_actor_index >= original_actors.size()
        or chosen_field_index < 0 or chosen_field_index >= original_fields.size()):
        return {}
    var actor: Dictionary = original_actors[chosen_actor_index]
    var field: Dictionary = original_fields[chosen_field_index]
    var replacement: Variant = field_value.value
    if field["type"] == "int32":
        if not _int_in_range(replacement, -2147483648, 2147483647):
            return {}
        replacement = int(replacement)
    elif field["type"] == "float32":
        if (not is_finite(float(replacement))
            or abs(float(replacement)) > 1000000.0):
            return {}
        replacement = float(replacement)
    else:
        return {}
    if replacement == field["source_value"]:
        return {}
    return {
        "actor": str(actor["actor"]), "export": int(actor["export"]),
        "property": str(field["property"]), "type": str(field["type"]),
        "expected": field["source_value"], "replacement": replacement,
    }


func stage_selected() -> bool:
    if worker != null:
        return false
    var row := _current_row()
    if row.is_empty():
        return false
    var found := -1
    for i in range(staged.size()):
        if (staged[i]["actor"] == row["actor"]
            and staged[i]["property"] == row["property"]):
            found = i
            break
    if found != -1:
        staged[found] = row
    else:
        if staged.size() >= MAX_BATCH:
            return false
        staged.append(row)
    staged.sort_custom(func(a, b):
        if int(a["export"]) == int(b["export"]):
            return str(a["property"]) < str(b["property"])
        return int(a["export"]) < int(b["export"]))
    pending.clear()
    _refresh_staged()
    return true


func _stage() -> void:
    if stage_selected():
        status.text = "%d original numeric fields staged (2–8 required)." % staged.size()
    else:
        status.text = "Cannot stage: use an existing changed original int32/float32 tag (max 8)."


func _refresh_staged() -> void:
    if not property_catalog.is_empty():
        _render_property_catalog()
    if stage_list != null:
        stage_list.clear()
        for item in staged:
            stage_list.add_item("#%d %s.%s [%s]  %s -> %s" % [
                int(item["export"]), str(item["actor"]),
                str(item["property"]), str(item["type"]),
                str(item["expected"]), str(item["replacement"])])
    _update_buttons()


func _remove() -> void:
    if worker != null or stage_list == null:
        return
    var selection := stage_list.get_selected_items()
    if selection.is_empty():
        return
    var idx := int(selection[0])
    if idx >= 0 and idx < staged.size():
        staged.remove_at(idx)
        pending.clear()
        _refresh_staged()
        status.text = "%d original numeric fields remain staged." % staged.size()


func _clear() -> void:
    if worker != null:
        return
    staged.clear()
    pending.clear()
    _refresh_staged()
    status.text = "Original actor numeric field staging cleared. No GMP changed."


func _update_buttons() -> void:
    super._update_buttons()
    if save_button != null:
        save_button.disabled = true
    var busy := worker != null
    var original_ok := _context_ok()
    if stage_button != null:
        stage_button.disabled = busy or not original_ok or _current_row().is_empty()
    if remove_button != null and stage_list != null:
        remove_button.disabled = busy or stage_list.get_selected_items().is_empty()
    if clear_button != null:
        clear_button.disabled = busy or staged.is_empty()
    if batch_button != null:
        batch_button.disabled = (
            busy or not original_ok or
            staged.size() < MIN_BATCH or staged.size() > MAX_BATCH)


func batch_request(target: String) -> Dictionary:
    if (worker != null or not _context_ok()
        or staged.size() < MIN_BATCH or staged.size() > MAX_BATCH
        or target.get_file().to_lower() != source_map.get_file().to_lower()
        or target == source_map or FileAccess.file_exists(target)
        or FileAccess.file_exists(target.get_basename() + ".dx2sdk-scalar.json")):
        return {}
    var keys := {}
    var actor_exports := {}
    var export_actors := {}
    for row in staged:
        var key := str(row["actor"]) + "\u001e" + str(row["property"])
        if (keys.has(key) or
            (actor_exports.has(row["actor"]) and
             actor_exports[row["actor"]] != row["export"]) or
            (export_actors.has(row["export"]) and
             export_actors[row["export"]] != row["actor"])):
            return {}
        keys[key] = true
        actor_exports[row["actor"]] = row["export"]
        export_actors[row["export"]] = row["actor"]
    return {
        "map": source_map, "actors_file": actors_file,
        "source_sha256": source_sha256, "actors_sha256": actors_sha256,
        "rows": staged.duplicate(true), "output": target,
    }


func _choose_batch_output() -> void:
    if batch_button.disabled or worker != null or not _context_ok():
        status.text = "Stage 2–8 changed original numeric fields first."
        return
    batch_save_dialog.current_file = source_map.get_file()
    batch_save_dialog.popup_centered_ratio(0.74)


func _destination(path: String) -> void:
    var request := batch_request(path)
    if request.is_empty():
        status.text = "Batch Save As refused: need 2–8 distinct edits and a fresh isolated same-name GMP."
        return
    pending = request.duplicate(true)
    _start("preview", pending)


func _confirmed_batch() -> void:
    if pending.is_empty() or worker != null:
        return
    var again := batch_request(str(pending.get("output", "")))
    if again != pending:
        pending.clear()
        status.text = "Batch confirmation refused: original map/cache, staged rows or destination changed."
        return
    _start("apply", pending)


func _start(action: String, request: Dictionary) -> void:
    if action in ["list", "fields"]:
        super._start(action, request)
        return
    if (worker != null or not _context_ok()
        or action not in ["preview", "apply"]):
        status.text = "Original native batch worker unavailable or source/cache changed."
        return
    var argv := PackedStringArray([
        worker_script, action, "--map", source_map,
        "--actors", actors_file,
        "--source-sha256", source_sha256,
        "--actors-sha256", actors_sha256,
        "--rows-json", JSON.stringify(request["rows"]),
        "--output", str(request["output"]),
    ])
    worker = Thread.new()
    _update_buttons()
    var started := worker.start(_execute.bind(argv, action, generation))
    if started != OK:
        worker = null
        _update_buttons()
        status.text = "Could not start original native scalar batch subprocess."
        return
    status.text = ("Proving 2–8 original tagged scalar byte edits in memory..."
        if action == "preview" else
        "Writing one isolated GMP with independent whole-source-byte verification...")


func _finished(code: int, raw: String, action: String, epoch: int) -> void:
    if action == "catalog":
        if worker != null:
            worker.wait_to_finish()
            worker = null
        if epoch != generation or not _context_ok():
            reset_context()
            return
        var doc: Variant = JSON.parse_string(raw.strip_edges())
        if (code != 0 or typeof(doc) != TYPE_DICTIONARY
            or not accept_original_property_catalog(doc)):
            property_catalog.clear()
            source_property_tree.clear()
            status.text = "Original Actor property catalog rejected: invalid source identity or tags."
        else:
            status.text = ("Original Actor catalog verified: %d top-level source"
                + " tags, %d existing eligible numeric fields. Opaque tags are read only.") % [
                    int(property_catalog["source_top_level_tag_count"]),
                    int(property_catalog["eligible_original_numeric_count"])]
        _update_buttons()
        return
    if action in ["list", "fields"]:
        var doc: Variant = JSON.parse_string(raw.strip_edges())
        if typeof(doc) == TYPE_DICTIONARY and doc.get("bridge_schema") == BATCH_BRIDGE_SCHEMA:
            doc["bridge_schema"] = BRIDGE_SCHEMA
            super._finished(code, JSON.stringify(doc), action, epoch)
        else:
            super._finished(code, raw, action, epoch)
        if (action == "fields" and code == 0 and epoch == generation
            and worker == null and _context_ok()
            and chosen_actor_index >= 0
            and chosen_actor_index < original_actors.size()
            and typeof(doc) == TYPE_DICTIONARY
            and doc.get("status") == "original_scalar_field_inventory"):
            var row: Dictionary = original_actors[chosen_actor_index]
            _start_property_catalog(str(row["actor"]), int(row["export"]))
        return
    if worker != null:
        worker.wait_to_finish()
        worker = null
    if epoch != generation or not _context_ok():
        reset_context()
        return
    var report: Variant = JSON.parse_string(raw.strip_edges())
    if (code != 0 or typeof(report) != TYPE_DICTIONARY
        or report.get("bridge_schema") != BATCH_BRIDGE_SCHEMA):
        var why := (str(report.get("reason", "refused")) if typeof(report) == TYPE_DICTIONARY
            else raw.strip_edges().substr(0, 300))
        status.text = "Native scalar batch refused: " + why
        pending.clear()
    elif action == "preview":
        var new_request := batch_request(str(pending.get("output", "")))
        if (new_request != pending
            or report.get("schema") != SDK_SCHEMA
            or report.get("action") != "preview"
            or report.get("status") != "dry-run"
            or report.get("source_sha256") != source_sha256
            or report.get("actors_sha256") != actors_sha256
            or report.get("output") != pending.get("output")
            or report.get("requested_rows") != pending.get("rows")
            or report.get("edited_field_count") != staged.size()
            or not _int_in_range(report.get("changed_byte_count"), 1, 32)
            or report.get("original_source_noop_T3SDK_parity_verified") != true
            or report.get("edited_package_written") != false
            or report.get("saved_binary_structure_verified") != false
            or report.get("source_original_modified") != false
            or report.get("runtime_game_verified") != false
            or report.get("native_gamesys_or_script_writer_enabled") != false
            or report.get("bsp_collision_rebuild_enabled") != false):
            pending.clear()
            status.text = "Native scalar batch preview rejected: stale inputs or invalid source proof."
        else:
            batch_confirmation.dialog_text = (
                "EXPERIMENTAL SOURCE-AUTHORED NATIVE SCALARS ONLY\n\n"
                + "Original GMP: " + source_map.get_file()
                + "\nOriginal GMP SHA: " + source_sha256
                + "\nSource actors.json SHA: " + actors_sha256
                + "\nStaged original int32/float32 fields: " + str(staged.size())
                + "\nNative changed bytes: " + str(report["changed_byte_count"])
                + "\nNew isolated output: " + str(pending["output"])
                + "\nPrivate verifier manifest: .dx2sdk-scalar.json"
                + "\n\nPreview: original T3SDK no-op baseline and byte patch passed."
                + "\nConfirm a fresh GMP and full independent saved-byte verification?"
                + "\nRetail runtime behavior, scripts, GameSys, BSP remain unverified.")
            batch_confirmation.popup_centered(Vector2i(760, 390))
            status.text = "Source-verified 2–8 numeric field preview passed; confirm isolated Save As."
    elif action == "apply":
        if (report.get("schema") == SDK_SCHEMA
            and report.get("action") == "apply"
            and report.get("status") == "isolated-multi-native-scalars-verified-runtime-unverified"
            and report.get("source_sha256") == source_sha256
            and report.get("actors_sha256") == actors_sha256
            and report.get("output") == pending.get("output")
            and report.get("requested_rows") == pending.get("rows")
            and report.get("edited_field_count") == staged.size()
            and report.get("saved_binary_structure_verified") == true
            and report.get("independent_saved_whole_GMP_byte_verification") == true
            and report.get("source_original_modified") == false
            and report.get("runtime_game_verified") == false
            and report.get("native_gamesys_or_script_writer_enabled") == false):
            status.text = ("Verified isolated 2–8 native numeric property GMP: "
                + str(report["output"])
                + ". Original unchanged; game runtime NOT verified.")
        else:
            status.text = "Native scalar batch output failed source-byte verification."
        pending.clear()
    _update_buttons()
