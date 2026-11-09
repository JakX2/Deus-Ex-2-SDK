extends VBoxContainer
## Read-only browser for source-backed DX2 MatLib records and local PNG previews.
## The catalog is generated from user-supplied IBD/Maps ZIP files. This panel
## never edits source bundles or writes native material/BSP data.

const PythonRuntime = preload("res://python_runtime.gd")
const CustomPolygon = preload("res://custom_polygon_geometry.gd")
const CATALOG_SCHEMA := "DX2Ed-MatLib-catalog-v1"
const MAX_CATALOG_BYTES := 64 * 1024 * 1024
const MAX_MATERIALS := 50000
const MAX_SOURCE_FILES := 64
const MAX_PREVIEW_BYTES := 2 * 1024 * 1024
## These are parser-decoded texture resource usage codes, not MatLib shader-stage meanings.
const TEXTURE_USAGE_FILTERS := [
    {"code": 0, "label": "diffuse"},
    {"code": 1, "label": "normal"},
    {"code": 2, "label": "specular"},
    {"code": 3, "label": "mask"},
    {"code": 4, "label": "detail"},
    {"code": 5, "label": "emissive"},
    {"code": 6, "label": "environment"}
]

signal material_apply_requested(assignment: Dictionary, slot_index: int)

var source_dialog: FileDialog
var search_box: LineEdit
var filter_selector: OptionButton
var category_filter_selector: OptionButton
var flags_filter_selector: OptionButton
var raw_filter_summary_label: Label
var category_filter_values: Array[int] = []
var flags_filter_values: Array[int] = []
var material_list: ItemList
var details_label: Label
var stage_audit_label: Label
var stage_grid: GridContainer
var status_label: Label
var apply_button: Button
var target_slot_selector: OptionButton
var catalog_audit_button: Button
var catalog_audit_label: Label

var catalog_path := ""
var catalog: Dictionary = {}
var materials: Array = []
var visible_materials: Array = []
var selected_material: Dictionary = {}


func _ready() -> void:
    _build_ui()


func _build_ui() -> void:
    size_flags_vertical = Control.SIZE_EXPAND_FILL
    var heading := Label.new()
    heading.text = "DX2 MatLib / Texture Browser"
    heading.add_theme_font_size_override("font_size", 16)
    add_child(heading)

    var note := Label.new()
    note.text = (
        "Read-only original IBD material records and decoded texture thumbnails. "
        + "Nine stage references are shown without inventing shader semantics; no native writer."
    )
    note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(note)

    var import_row := HBoxContainer.new()
    add_child(import_row)
    var import_button := Button.new()
    import_button.text = "Import IBD / Maps ZIP"
    import_button.tooltip_text = "Decode a user-supplied source bundle into a private metadata and thumbnail cache."
    import_button.pressed.connect(_choose_source)
    import_row.add_child(import_button)

    source_dialog = FileDialog.new()
    source_dialog.title = "Choose original DX2 IBD bundle or Maps ZIP"
    source_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    source_dialog.access = FileDialog.ACCESS_FILESYSTEM
    source_dialog.add_filter("*.ibd ; DX2 IBD resource bundle")
    source_dialog.add_filter("*.zip ; Maps ZIP containing IBD bundles")
    source_dialog.file_selected.connect(_import_bundle)
    add_child(source_dialog)

    var filter_row := HBoxContainer.new()
    add_child(filter_row)
    search_box = LineEdit.new()
    search_box.placeholder_text = "Search material, source or stage..."
    search_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    search_box.text_changed.connect(func(_value: String): _refresh_list())
    filter_row.add_child(search_box)

    filter_selector = OptionButton.new()
    filter_selector.add_item("All materials")
    filter_selector.add_item("Resolved slot 0 (legacy preview candidate)")
    filter_selector.add_item("Missing slot 0 (legacy preview candidate)")
    filter_selector.add_item("Unresolved stage refs")
    for usage_filter in TEXTURE_USAGE_FILTERS:
        filter_selector.add_item(
            "Contains usage code %d (%s parser label)" % [
                int(usage_filter["code"]), str(usage_filter["label"])
            ])
    filter_selector.item_selected.connect(func(_index: int): _refresh_list())
    filter_row.add_child(filter_selector)

    var raw_filter_row := HBoxContainer.new()
    add_child(raw_filter_row)
    var category_label := Label.new()
    category_label.text = "Raw category ID"
    raw_filter_row.add_child(category_label)
    category_filter_selector = OptionButton.new()
    category_filter_selector.add_item("All")
    category_filter_selector.tooltip_text = (
        "Filter by opaque source category_id values. No category meanings are inferred.")
    category_filter_selector.item_selected.connect(func(_index: int): _refresh_list())
    raw_filter_row.add_child(category_filter_selector)

    var flags_label := Label.new()
    flags_label.text = "Raw flags"
    raw_filter_row.add_child(flags_label)
    flags_filter_selector = OptionButton.new()
    flags_filter_selector.add_item("All")
    flags_filter_selector.tooltip_text = (
        "Filter by opaque source flags values. No bit meanings are inferred.")
    flags_filter_selector.item_selected.connect(func(_index: int): _refresh_list())
    raw_filter_row.add_child(flags_filter_selector)

    raw_filter_summary_label = Label.new()
    raw_filter_summary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    raw_filter_summary_label.text = (
        "Raw category and flags filters are opaque source values, not decoded material semantics.")
    add_child(raw_filter_summary_label)

    var split := HSplitContainer.new()
    split.size_flags_vertical = Control.SIZE_EXPAND_FILL
    add_child(split)

    material_list = ItemList.new()
    material_list.custom_minimum_size.x = 180
    material_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    material_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    material_list.item_selected.connect(_material_selected)
    split.add_child(material_list)

    var detail_column := VBoxContainer.new()
    detail_column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    detail_column.size_flags_vertical = Control.SIZE_EXPAND_FILL
    split.add_child(detail_column)

    details_label = Label.new()
    details_label.text = "Import an original IBD or Maps ZIP to inspect MatLib records."
    details_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    details_label.custom_minimum_size.y = 96
    detail_column.add_child(details_label)

    stage_audit_label = Label.new()
    stage_audit_label.text = "Raw stage diagnostics appear when a material is selected."
    stage_audit_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    stage_audit_label.custom_minimum_size.y = 52
    detail_column.add_child(stage_audit_label)

    var target_row := HBoxContainer.new()
    detail_column.add_child(target_row)
    var target_label := Label.new()
    target_label.text = "Target surface"
    target_row.add_child(target_label)
    target_slot_selector = OptionButton.new()
    target_slot_selector.add_item("Top cap")
    target_slot_selector.add_item("Bottom cap")
    target_slot_selector.add_item("Side walls")
    target_slot_selector.select(0)
    target_row.add_child(target_slot_selector)

    apply_button = Button.new()
    apply_button.text = "Apply slot-0 preview candidate to selected Polygon brush(es)"
    apply_button.tooltip_text = (
        "Use the current slot-0 preview candidate on the chosen surface of every selected "
        + "editor-only Polygon brush. Its diffuse shader meaning is not independently verified. "
        + "All selected objects must be private Polygon drafts; one Undo/Redo transaction. "
        + "No native material or BSP write.")
    apply_button.disabled = true
    apply_button.pressed.connect(_request_apply_selected_material)
    detail_column.add_child(apply_button)

    var stage_scroll := ScrollContainer.new()
    stage_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
    detail_column.add_child(stage_scroll)
    stage_grid = GridContainer.new()
    stage_grid.columns = 3
    stage_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    stage_scroll.add_child(stage_grid)

    var catalog_audit_row := HBoxContainer.new()
    detail_column.add_child(catalog_audit_row)
    catalog_audit_button = Button.new()
    catalog_audit_button.text = "Run stage-mask / slot audit"
    catalog_audit_button.disabled = true
    catalog_audit_button.tooltip_text = (
        "Compare raw low-nine stage-mask bits with non-empty ordered MatLib slot positions. "
        + "This is an exploratory structural audit, not a shader-stage decode.")
    catalog_audit_button.pressed.connect(_run_catalog_stage_mask_audit)
    catalog_audit_row.add_child(catalog_audit_button)

    catalog_audit_label = Label.new()
    catalog_audit_label.text = "Import a catalog, then run the read-only stage-mask / slot correspondence audit."
    catalog_audit_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    catalog_audit_label.custom_minimum_size.y = 96
    detail_column.add_child(catalog_audit_label)

    status_label = Label.new()
    status_label.text = "No source catalog loaded. Original bundles remain read-only."
    status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(status_label)


func _choose_source() -> void:
    source_dialog.popup_centered_ratio(0.72)


func _import_bundle(path: String) -> void:
    var source_sha := FileAccess.get_sha256(path).to_lower()
    if not _is_sha256(source_sha):
        status_label.text = "Could not fingerprint the selected source bundle."
        return
    var cache_root := ProjectSettings.globalize_path("user://dx2ed_material_cache")
    var directory_error := DirAccess.make_dir_recursive_absolute(cache_root)
    if directory_error != OK and directory_error != ERR_ALREADY_EXISTS:
        status_label.text = "Could not create the private MatLib cache directory."
        return
    var output_path := cache_root.path_join(source_sha + ".json")
    var worker := ProjectSettings.globalize_path("res://backend/dx2_matlib_catalog.py")
    if not FileAccess.file_exists(worker):
        status_label.text = "MatLib catalog worker is missing from this prototype."
        return
    var arguments := PackedStringArray(["--bundle", path, "--output", output_path])
    var output: Array = []
    var exit_code := _execute_python_worker(worker, arguments, output)
    if exit_code != 0:
        status_label.text = "MatLib import failed: " + "\n".join(output).left(500)
        return
    if not load_catalog(output_path):
        status_label.text = "The generated MatLib catalog failed validation."
        return
    status_label.text = (
        "Imported %d materials and %d referenced textures; %d verified PNG previews. "
        + "Source bytes modified: no. Native writer: disabled."
    ) % [
        int(catalog.get("material_count", 0)),
        int(catalog.get("texture_count", 0)),
        int(catalog.get("preview_count", 0))
    ]


func load_catalog(path: String) -> bool:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        status_label.text = "Cannot open MatLib catalog."
        return false
    if file.get_length() > MAX_CATALOG_BYTES:
        status_label.text = "MatLib catalog exceeds the 64 MiB limit."
        return false
    var parsed: Variant = JSON.parse_string(file.get_as_text())
    var absolute_path := ProjectSettings.globalize_path(path)
    if not _validate_catalog(parsed, absolute_path):
        status_label.text = "MatLib catalog rejected; existing browser contents were retained."
        return false
    catalog = parsed
    catalog_path = absolute_path
    materials = parsed["materials"]
    selected_material.clear()
    _populate_raw_metadata_filters()
    _refresh_list()
    if catalog_audit_button != null:
        catalog_audit_button.disabled = false
    if catalog_audit_label != null:
        catalog_audit_label.text = "Catalog loaded. Run the read-only stage-mask / slot correspondence audit."
    status_label.text = (
        "Loaded %d MatLib records from %d source file(s). "
        + "Stage references and raw masks are shown without shader-semantic inference."
    ) % [materials.size(), parsed["source_files"].size()]
    return true


func _validate_catalog(raw: Variant, path: String) -> bool:
    if typeof(raw) != TYPE_DICTIONARY:
        return false
    if (raw.get("schema", "") != CATALOG_SCHEMA
        or raw.get("read_only", false) != true
        or raw.get("native_writer_enabled", true) != false
        or raw.get("source_bytes_modified", true) != false):
        return false
    var source_files: Variant = raw.get("source_files", null)
    var records: Variant = raw.get("materials", null)
    if (typeof(source_files) != TYPE_ARRAY or source_files.is_empty()
        or source_files.size() > MAX_SOURCE_FILES
        or typeof(records) != TYPE_ARRAY or records.size() > MAX_MATERIALS):
        return false
    for source in source_files:
        if (typeof(source) != TYPE_DICTIONARY
            or str(source.get("path", "")).is_empty()
            or not _is_sha256(str(source.get("sha256", "")))):
            return false
    for material in records:
        if typeof(material) != TYPE_DICTIONARY or str(material.get("name", "")).is_empty():
            return false
        if (_usage_code_value(material.get("flags", null)) < 0
            or _usage_code_value(material.get("stage_mask", null)) < 0
            or _usage_code_value(material.get("category_id", null)) < 0):
            return false
        var stages: Variant = material.get("stages", null)
        if typeof(stages) != TYPE_ARRAY or stages.size() != 9:
            return false
        for index in range(9):
            var stage: Variant = stages[index]
            if (typeof(stage) != TYPE_DICTIONARY
                or int(stage.get("index", -1)) != index
                or typeof(stage.get("name", "")) != TYPE_STRING
                or str(stage.get("name", "")).length() > 260
                or typeof(stage.get("resolved", false)) != TYPE_BOOL):
                return false
            if bool(stage.get("resolved", false)):
                var texture: Variant = stage.get("texture", null)
                if typeof(texture) != TYPE_DICTIONARY:
                    return false
                if texture.has("usage_code") and _usage_code_value(texture.get("usage_code", null)) < 0:
                    return false
                if texture.has("usage"):
                    var usage_label: Variant = texture.get("usage", null)
                    if typeof(usage_label) != TYPE_STRING or str(usage_label).length() > 64:
                        return false
                var relative: String = str(texture.get("preview_path", ""))
                if not relative.is_empty():
                    if _safe_preview_path(relative, path).is_empty():
                        return false
                    if not _is_sha256(str(texture.get("preview_sha256", ""))):
                        return false
    return true


func _populate_raw_metadata_filters() -> void:
    category_filter_values.clear()
    flags_filter_values.clear()
    var categories: Dictionary = {}
    var flag_patterns: Dictionary = {}
    for material in materials:
        if typeof(material) != TYPE_DICTIONARY:
            continue
        var category := _usage_code_value(material.get("category_id", null))
        var flags := _usage_code_value(material.get("flags", null))
        if category >= 0:
            categories[category] = true
        if flags >= 0:
            flag_patterns[flags] = true
    for value in categories.keys():
        category_filter_values.append(int(value))
    for value in flag_patterns.keys():
        flags_filter_values.append(int(value))
    category_filter_values.sort()
    flags_filter_values.sort()

    if category_filter_selector != null:
        category_filter_selector.clear()
        category_filter_selector.add_item("All")
        for value in category_filter_values:
            category_filter_selector.add_item(str(value))
        category_filter_selector.select(0)
    if flags_filter_selector != null:
        flags_filter_selector.clear()
        flags_filter_selector.add_item("All")
        for value in flags_filter_values:
            flags_filter_selector.add_item("0x%08X" % value)
        flags_filter_selector.select(0)
    if raw_filter_summary_label != null:
        raw_filter_summary_label.text = (
            "Raw values only: %d category IDs and %d distinct flag patterns. "
            + "No category or flag semantics are inferred."
        ) % [category_filter_values.size(), flags_filter_values.size()]


func _safe_preview_path(relative_path: String, for_catalog: String) -> String:
    if (relative_path.is_empty() or relative_path.begins_with("/")
        or relative_path.contains("\\") or relative_path.contains(":")):
        return ""
    var segments := relative_path.split("/", false)
    for segment in segments:
        if segment.is_empty() or segment == "." or segment == "..":
            return ""
    var base := ProjectSettings.globalize_path(for_catalog.get_base_dir()).simplify_path()
    var candidate := ProjectSettings.globalize_path(
        for_catalog.get_base_dir().path_join(relative_path)
    ).simplify_path()
    if candidate == base or not candidate.begins_with(base + "/"):
        return ""
    return candidate


func _is_sha256(value: String) -> bool:
    if value.length() != 64:
        return false
    for index in range(value.length()):
        if "0123456789abcdef".find(value.substr(index, 1).to_lower()) < 0:
            return false
    return true


func _refresh_list() -> void:
    if material_list == null:
        return
    material_list.clear()
    visible_materials.clear()
    var query := search_box.text.strip_edges().to_lower() if search_box != null else ""
    var mode := filter_selector.selected if filter_selector != null else 0
    var category_index := category_filter_selector.selected if category_filter_selector != null else 0
    var flags_index := flags_filter_selector.selected if flags_filter_selector != null else 0
    var selected_category := category_filter_values[category_index - 1] if category_index > 0 and category_index <= category_filter_values.size() else -1
    var selected_flags := flags_filter_values[flags_index - 1] if flags_index > 0 and flags_index <= flags_filter_values.size() else -1

    for material in materials:
        if typeof(material) != TYPE_DICTIONARY:
            continue
        if category_index > 0 and int(material.get("category_id", -1)) != selected_category:
            continue
        if flags_index > 0 and int(material.get("flags", -1)) != selected_flags:
            continue
        var stages: Array = material.get("stages", [])
        if stages.size() != 9:
            continue
        var slot_zero: Dictionary = stages[0]
        var has_slot_zero := bool(slot_zero.get("resolved", false))
        var has_unresolved := false
        var stage_names: Array[String] = []
        for stage in stages:
            var stage_name := str(stage.get("name", ""))
            if not stage_name.is_empty():
                stage_names.append(stage_name)
                if not bool(stage.get("resolved", false)):
                    has_unresolved = true
                elif typeof(stage.get("texture", null)) == TYPE_DICTIONARY:
                    var texture_record: Dictionary = stage["texture"]
                    stage_names.append(str(texture_record.get("usage", "")))
                    stage_names.append(str(texture_record.get("usage_code", "")))
        if mode >= 4:
            var usage_filter_index := mode - 4
            if usage_filter_index >= TEXTURE_USAGE_FILTERS.size():
                continue
            if not _material_has_usage_code(
                material, int(TEXTURE_USAGE_FILTERS[usage_filter_index]["code"])
            ):
                continue
        match mode:
            1:
                if not has_slot_zero:
                    continue
            2:
                if has_slot_zero:
                    continue
            3:
                if not has_unresolved:
                    continue
        var searchable := (
            str(material.get("name", "")) + " "
            + str(material.get("source_bundle", "")) + " "
            + str(material.get("source", "")) + " "
            + " ".join(stage_names)
        ).to_lower()
        if not query.is_empty() and not searchable.contains(query):
            continue
        visible_materials.append(material)
        material_list.add_item(
            str(material.get("name", ""))
            + "  [category " + str(material.get("category_id", "?"))
            + " | flags 0x%08X]" % int(material.get("flags", 0))
        )

    if raw_filter_summary_label != null:
        var category_text := "all"
        if selected_category >= 0:
            category_text = str(selected_category)
        var flags_text := "all"
        if selected_flags >= 0:
            flags_text = "0x%08X" % selected_flags
        raw_filter_summary_label.text = (
            "Raw filters: category_id=%s | flags=%s. Catalog has %d category IDs / %d flag patterns; values are opaque."
            % [category_text, flags_text, category_filter_values.size(), flags_filter_values.size()]
        )

    var selected_index := visible_materials.find(selected_material) if not selected_material.is_empty() else -1
    if visible_materials.is_empty():
        selected_material.clear()
        details_label.text = "No materials match the current filter."
        stage_audit_label.text = "No material selected."
        _clear_stage_cards()
    elif selected_index < 0:
        selected_material.clear()
        details_label.text = "%d materials match. Select one to inspect all nine stage slots." % visible_materials.size()
        stage_audit_label.text = "Select a material to inspect its raw stage references."
        _clear_stage_cards()
    else:
        material_list.select(selected_index)
    status_label.text = "%d / %d materials in current filter." % [visible_materials.size(), materials.size()]
    _refresh_apply_button()


func _material_selected(index: int) -> void:
    if index < 0 or index >= visible_materials.size():
        return
    selected_material = visible_materials[index]
    var named_slot_mask := _named_stage_slot_mask(selected_material)
    var raw_stage_mask := int(selected_material.get("stage_mask", 0))
    var low9_stage_mask := raw_stage_mask & 0x1FF
    var mask_xor := low9_stage_mask ^ named_slot_mask
    var lines: Array[String] = [
        "Material: " + str(selected_material.get("name", "")),
        "Source bundle: " + str(selected_material.get("source_bundle", "")),
        "Source label: " + str(selected_material.get("source", "")),
        "Version: " + str(selected_material.get("version", "?")),
        "Flags (raw): 0x%08X" % int(selected_material.get("flags", 0)),
        "Stage mask (raw): 0x%08X" % int(selected_material.get("stage_mask", 0)),
        "Category ID (raw): " + str(selected_material.get("category_id", "?")),
        "Named-slot mask (derived): 0x%03X" % named_slot_mask,
        "Low-nine XOR: 0x%03X (%s; candidate only)" % [
            mask_xor, "exact match" if mask_xor == 0 else "mismatch"
        ],
        "Colors: " + str(selected_material.get("colors", [])),
        "Parameters: " + str(selected_material.get("params", [])),
        "Slot 0 is the existing preview candidate only; diffuse shader semantics are unverified.",
        "No native material or BSP assignment."
    ]
    details_label.text = "\n".join(lines)
    _clear_stage_cards()
    var named_count := 0
    var resolved_count := 0
    var unresolved_count := 0
    var empty_count := 0
    for stage in selected_material.get("stages", []):
        var stage_name := str(stage.get("name", ""))
        if stage_name.is_empty():
            empty_count += 1
        else:
            named_count += 1
            if bool(stage.get("resolved", false)):
                resolved_count += 1
            else:
                unresolved_count += 1
        _add_stage_card(stage)
    stage_audit_label.text = (
        "Raw stage_mask: 0x%08X (uninterpreted)\n" % int(selected_material.get("stage_mask", 0))
        + "Slots: %d named, %d resolved, %d unresolved, %d empty. "
        % [named_count, resolved_count, unresolved_count, empty_count]
        + "Texture usage labels come from the parser; they do not establish shader-stage semantics."
    )
    _refresh_apply_button()



static func _named_stage_slot_mask(material: Dictionary) -> int:
    var stages: Variant = material.get("stages", null)
    if typeof(stages) != TYPE_ARRAY or stages.size() != 9:
        return -1
    var result := 0
    for index in range(9):
        var stage: Variant = stages[index]
        if typeof(stage) != TYPE_DICTIONARY:
            return -1
        if not str(stage.get("name", "")).is_empty():
            result |= 1 << index
    return result


func _execute_python_worker(worker: String, arguments: PackedStringArray, output: Array) -> int:
    var direct_arguments := PackedStringArray([worker])
    direct_arguments.append_array(arguments)
    var exit_code := OS.execute(PythonRuntime.executable(), direct_arguments, output, true)
    if exit_code == -1:
        output.clear()
        var fallback := PackedStringArray(["-3", worker])
        fallback.append_array(arguments)
        exit_code = OS.execute("py", fallback, output, true)
    return exit_code


func _run_catalog_stage_mask_audit() -> bool:
    if catalog_path.is_empty() or not FileAccess.file_exists(catalog_path):
        if catalog_audit_label != null:
            catalog_audit_label.text = "No readable MatLib catalog is loaded."
        return false
    var worker := ProjectSettings.globalize_path("res://backend/dx2_matlib_catalog.py")
    if not FileAccess.file_exists(worker):
        catalog_audit_label.text = "The MatLib catalog worker is missing from this prototype."
        return false
    var output: Array = []
    var exit_code := _execute_python_worker(
        worker, PackedStringArray(["--audit-catalog", catalog_path]), output)
    var output_lines := PackedStringArray()
    for item in output:
        output_lines.append(str(item))
    var output_text := "\n".join(output_lines)
    if exit_code != 0:
        catalog_audit_label.text = "Stage-mask audit failed: " + output_text.left(500)
        return false
    var parsed: Variant = JSON.parse_string(output_text)
    if (typeof(parsed) != TYPE_DICTIONARY
        or parsed.get("status", "") != "ok"
        or parsed.get("schema", "") != "DX2Ed-MatLib-stage-mask-audit-v1"
        or parsed.get("native_writer_enabled", true) != false
        or parsed.get("source_bytes_modified", true) != false
        or typeof(parsed.get("category_flag_cohorts", null)) != TYPE_ARRAY
        or _usage_code_value(parsed.get("category_flag_cohort_count", null)) < 0
        or _usage_code_value(parsed.get("category_flag_cohorts_omitted", null)) < 0):
        catalog_audit_label.text = "Stage-mask audit returned an invalid or writable report."
        return false
    catalog_audit_label.text = _format_catalog_stage_mask_audit(parsed)
    return true


func _format_catalog_stage_mask_audit(report: Dictionary) -> String:
    var lines := PackedStringArray([
        "Materials: %d | exact low-nine matches: %d (%d non-empty) | mismatches: %d." % [
            int(report.get("material_count", 0)),
            int(report.get("exact_low9_match_count", 0)),
            int(report.get("exact_nonempty_low9_match_count", 0)),
            int(report.get("mismatch_count", 0))
        ],
        "Records with high bits set: %d; no named slots: %d; nonzero mask without names: %d." % [
            int(report.get("high_bits_set_count", 0)),
            int(report.get("no_named_slots_count", 0)),
            int(report.get("nonzero_mask_without_named_slots_count", 0))
        ],
        "Per-slot resource usage codes (parser labels are not shader roles):"
    ])
    var per_slot: Variant = report.get("per_slot", [])
    if typeof(per_slot) == TYPE_ARRAY:
        for raw_slot in per_slot:
            if typeof(raw_slot) != TYPE_DICTIONARY:
                continue
            var slot: Dictionary = raw_slot
            var usage_parts := PackedStringArray()
            for item in slot.get("usage_code_counts", []):
                if typeof(item) == TYPE_DICTIONARY:
                    usage_parts.append("%s:%s" % [
                        str(item.get("code", "?")), str(item.get("count", 0))
                    ])
            var name_parts := PackedStringArray()
            for item in slot.get("common_names", []):
                if typeof(item) == TYPE_DICTIONARY:
                    name_parts.append("%s×%s" % [
                        str(item.get("name", "")), str(item.get("count", 0))
                    ])
            lines.append("Slot %d: named=%d resolved=%d | codes [%s] | names [%s]" % [
                int(slot.get("slot_index", -1)),
                int(slot.get("named_count", 0)),
                int(slot.get("resolved_count", 0)),
                ", ".join(usage_parts) if not usage_parts.is_empty() else "none",
                ", ".join(name_parts) if not name_parts.is_empty() else "none"
            ])
    var categories := PackedStringArray()
    for item in report.get("top_category_ids", []):
        if typeof(item) == TYPE_DICTIONARY:
            categories.append("%s×%s" % [
                str(item.get("value", "?")), str(item.get("count", 0))
            ])
    var flags := PackedStringArray()
    for item in report.get("top_flags", []):
        if typeof(item) == TYPE_DICTIONARY:
            flags.append("0x%08X×%s" % [
                int(item.get("value", 0)), str(item.get("count", 0))
            ])
    lines.append("Most common raw category IDs: " + (", ".join(categories) if not categories.is_empty() else "none"))
    lines.append("Most common raw flags: " + (", ".join(flags) if not flags.is_empty() else "none"))
    lines.append(
        "Raw category/flags cohorts: %d unique, %d omitted (opaque grouping only)." % [
            int(report.get("category_flag_cohort_count", 0)),
            int(report.get("category_flag_cohorts_omitted", 0))
        ])
    for raw_cohort in report.get("category_flag_cohorts", []):
        if typeof(raw_cohort) != TYPE_DICTIONARY:
            continue
        var cohort: Dictionary = raw_cohort
        var low9_parts := PackedStringArray()
        for item in cohort.get("top_low9_masks", []):
            if typeof(item) == TYPE_DICTIONARY:
                low9_parts.append("0x%03X×%s" % [
                    int(item.get("mask", 0)), str(item.get("count", 0))
                ])
        var named_parts := PackedStringArray()
        for item in cohort.get("top_named_slot_masks", []):
            if typeof(item) == TYPE_DICTIONARY:
                named_parts.append("0x%03X×%s" % [
                    int(item.get("mask", 0)), str(item.get("count", 0))
                ])
        lines.append("Cohort cat=%d flags=0x%08X n=%d exact=%d mismatch=%d high=%d | raw low9 [%s] | named slots [%s]" % [
            int(cohort.get("category_id", 0)),
            int(cohort.get("flags", 0)),
            int(cohort.get("material_count", 0)),
            int(cohort.get("exact_low9_match_count", 0)),
            int(cohort.get("mismatch_count", 0)),
            int(cohort.get("high_bits_set_count", 0)),
            ", ".join(low9_parts) if not low9_parts.is_empty() else "none",
            ", ".join(named_parts) if not named_parts.is_empty() else "none"
        ])
    for item in report.get("mismatch_examples", []):
        if typeof(item) == TYPE_DICTIONARY:
            lines.append("Mismatch %s: raw=0x%08X named=0x%03X xor=0x%03X" % [
                str(item.get("name", "")),
                int(item.get("raw_stage_mask", 0)),
                int(item.get("named_slot_mask", 0)),
                int(item.get("xor_mask", 0))
            ])
    lines.append("Exact equality is only a candidate bit/slot relationship, not proof of runtime shader semantics.")
    return "\n".join(lines).left(6000)



static func _usage_code_value(raw: Variant) -> int:
    if typeof(raw) == TYPE_INT:
        var integer_value := int(raw)
        return integer_value if integer_value >= 0 and integer_value <= 0xFFFFFFFF else -1
    if typeof(raw) == TYPE_FLOAT:
        var numeric_value := float(raw)
        if (is_nan(numeric_value) or is_inf(numeric_value)
            or numeric_value < 0.0 or numeric_value > 4294967295.0
            or floor(numeric_value) != numeric_value):
            return -1
        return int(numeric_value)
    return -1


func _material_has_usage_code(material: Dictionary, usage_code: int) -> bool:
    var stages: Variant = material.get("stages", null)
    if typeof(stages) != TYPE_ARRAY or stages.size() != 9:
        return false
    for stage in stages:
        if typeof(stage) != TYPE_DICTIONARY or not bool(stage.get("resolved", false)):
            continue
        var texture: Variant = stage.get("texture", null)
        if typeof(texture) != TYPE_DICTIONARY:
            continue
        if _usage_code_value(texture.get("usage_code", null)) == usage_code:
            return true
    return false


func selected_diffuse_assignment() -> Dictionary:
    if (selected_material.is_empty() or catalog_path.is_empty()
        or not FileAccess.file_exists(catalog_path)):
        return {}
    var stages: Variant = selected_material.get("stages", null)
    if typeof(stages) != TYPE_ARRAY or stages.size() != 9:
        return {}
    var diffuse: Variant = stages[0]
    if typeof(diffuse) != TYPE_DICTIONARY or not bool(diffuse.get("resolved", false)):
        return {}
    var texture: Variant = diffuse.get("texture", null)
    if typeof(texture) != TYPE_DICTIONARY or _preview_texture(diffuse) == null:
        return {}
    var catalog_sha := FileAccess.get_sha256(catalog_path).to_lower()
    var assignment := {
        "catalog_path": catalog_path,
        "catalog_sha256": catalog_sha,
        "catalog_id": str(catalog.get("catalog_id", "")),
        "material_name": str(selected_material.get("name", "")),
        "material_source_bundle": str(selected_material.get("source_bundle", "")),
        "material_source": str(selected_material.get("source", "")),
        "material_version": int(selected_material.get("version", -1)),
        "material_flags": int(selected_material.get("flags", -1)),
        "material_stage_mask": int(selected_material.get("stage_mask", -1)),
        "material_category_id": int(selected_material.get("category_id", -1)),
        "diffuse_name": str(diffuse.get("name", "")),
        "texture_name": str(texture.get("name", "")),
        "texture_source_bundle": str(texture.get("source_bundle", "")),
        "texture_format": str(texture.get("format", "")),
        "texture_width": int(texture.get("width", 0)),
        "texture_height": int(texture.get("height", 0)),
        "texture_usage": str(texture.get("usage", "")),
        "preview_path": str(texture.get("preview_path", "")),
        "preview_sha256": str(texture.get("preview_sha256", ""))
    }
    var checked := CustomPolygon.validate_source_material_assignment(assignment)
    if checked.is_empty() or load_assignment_texture(checked) == null:
        return {}
    return checked


func _refresh_apply_button() -> void:
    if apply_button != null:
        apply_button.disabled = selected_diffuse_assignment().is_empty()


func _request_apply_selected_material() -> void:
    var assignment := selected_diffuse_assignment()
    if assignment.is_empty():
        status_label.text = "Select a material with a verified resolved slot-0 preview candidate first."
        return
    if target_slot_selector == null or target_slot_selector.selected < 0:
        status_label.text = "Choose a Polygon surface slot first."
        return
    material_apply_requested.emit(assignment, target_slot_selector.selected)
    status_label.text = (
        "Requested slot-0 preview-candidate assignment to selected private Polygon brush(es). "
        + "This is not a verified native diffuse binding."
    )


func _clear_stage_cards() -> void:
    if stage_audit_label != null:
        stage_audit_label.text = "Raw stage diagnostics appear when a material is selected."
    if stage_grid == null:
        return
    for child in stage_grid.get_children():
        child.queue_free()


func _add_stage_card(stage: Dictionary) -> void:
    var card := PanelContainer.new()
    card.custom_minimum_size = Vector2(108, 132)
    var column := VBoxContainer.new()
    card.add_child(column)
    var texture_preview := _preview_texture(stage)
    if texture_preview != null:
        var image_rect := TextureRect.new()
        image_rect.texture = texture_preview
        image_rect.custom_minimum_size = Vector2(96, 72)
        image_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
        image_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
        column.add_child(image_rect)
    else:
        var placeholder := Label.new()
        placeholder.text = "No preview"
        placeholder.custom_minimum_size = Vector2(96, 72)
        placeholder.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
        placeholder.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
        column.add_child(placeholder)
    var stage_label := Label.new()
    stage_label.text = "MatLib slot %d" % int(stage.get("index", -1))
    column.add_child(stage_label)
    var name_label := Label.new()
    var name := str(stage.get("name", ""))
    name_label.text = name if not name.is_empty() else "(empty)"
    name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    column.add_child(name_label)
    var detail := Label.new()
    if bool(stage.get("resolved", false)):
        var texture: Dictionary = stage.get("texture", {})
        var usage_code_text := (
            str(_usage_code_value(texture.get("usage_code", null)))
            if texture.has("usage_code") else "unknown"
        )
        detail.text = "%s · %s×%s\nUsage code %s · parser label: %s" % [
            str(texture.get("format", "?")),
            str(texture.get("width", "?")),
            str(texture.get("height", "?")),
            usage_code_text,
            str(texture.get("usage", "unknown"))
        ]
    elif not name.is_empty():
        detail.text = "Unresolved texture reference"
    else:
        detail.text = "No stage reference"
    detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    column.add_child(detail)
    stage_grid.add_child(card)


func _preview_texture(stage: Dictionary) -> Texture2D:
    if not bool(stage.get("resolved", false)):
        return null
    var texture: Variant = stage.get("texture", null)
    if typeof(texture) != TYPE_DICTIONARY:
        return null
    var relative := str(texture.get("preview_path", ""))
    if relative.is_empty():
        return null
    var absolute := _safe_preview_path(relative, catalog_path)
    if absolute.is_empty() or not FileAccess.file_exists(absolute):
        return null
    var file := FileAccess.open(absolute, FileAccess.READ)
    if file == null or file.get_length() > MAX_PREVIEW_BYTES:
        return null
    var expected := str(texture.get("preview_sha256", "")).to_lower()
    if not _is_sha256(expected) or FileAccess.get_sha256(absolute).to_lower() != expected:
        return null
    var image := Image.new()
    if image.load(absolute) != OK or image.get_width() > 512 or image.get_height() > 512:
        return null
    return ImageTexture.create_from_image(image)


static func _safe_assignment_preview_path(relative_path: String, for_catalog: String) -> String:
    if (relative_path.is_empty() or relative_path.begins_with("/")
        or relative_path.contains("\\") or relative_path.contains(":")):
        return ""
    for segment in relative_path.split("/", false):
        if segment.is_empty() or segment == "." or segment == "..":
            return ""
    var base := ProjectSettings.globalize_path(for_catalog.get_base_dir()).simplify_path()
    var candidate := ProjectSettings.globalize_path(
        for_catalog.get_base_dir().path_join(relative_path)
    ).simplify_path()
    if candidate == base or not candidate.begins_with(base + "/"):
        return ""
    return candidate


## Re-open and re-verify the catalog, exact material/stage identity, preview
## confinement and thumbnail digest before using a saved assignment on a mesh.
## If a source cache disappears or changes, callers fall back to the procedural
## checker while retaining the source identity in the private project.
static func load_assignment_texture(raw: Variant) -> Texture2D:
    var assignment := CustomPolygon.validate_source_material_assignment(raw)
    if assignment.is_empty():
        return null
    var catalog_file: String = assignment["catalog_path"]
    if (not FileAccess.file_exists(catalog_file)
        or FileAccess.get_sha256(catalog_file).to_lower() != assignment["catalog_sha256"]):
        return null
    var file := FileAccess.open(catalog_file, FileAccess.READ)
    if file == null or file.get_length() > MAX_CATALOG_BYTES:
        return null
    var parsed: Variant = JSON.parse_string(file.get_as_text())
    if (typeof(parsed) != TYPE_DICTIONARY
        or parsed.get("schema", "") != CATALOG_SCHEMA
        or parsed.get("read_only", false) != true
        or parsed.get("native_writer_enabled", true) != false
        or parsed.get("source_bytes_modified", true) != false
        or str(parsed.get("catalog_id", "")).to_lower() != assignment["catalog_id"]):
        return null
    var records: Variant = parsed.get("materials", null)
    if typeof(records) != TYPE_ARRAY or records.size() > MAX_MATERIALS:
        return null
    var matched := false
    for material in records:
        if typeof(material) != TYPE_DICTIONARY:
            continue
        if (str(material.get("name", "")) != assignment["material_name"]
            or str(material.get("source_bundle", "")) != assignment["material_source_bundle"]
            or str(material.get("source", "")) != assignment["material_source"]
            or int(material.get("version", -1)) != assignment["material_version"]
            or int(material.get("flags", -1)) != assignment["material_flags"]
            or int(material.get("stage_mask", -1)) != assignment["material_stage_mask"]
            or int(material.get("category_id", -1)) != assignment["material_category_id"]):
            continue
        var stages: Variant = material.get("stages", null)
        if typeof(stages) != TYPE_ARRAY or stages.size() != 9:
            continue
        var diffuse: Variant = stages[0]
        if (typeof(diffuse) != TYPE_DICTIONARY
            or not bool(diffuse.get("resolved", false))
            or str(diffuse.get("name", "")) != assignment["diffuse_name"]):
            continue
        var texture: Variant = diffuse.get("texture", null)
        if typeof(texture) != TYPE_DICTIONARY:
            continue
        if (str(texture.get("name", "")) != assignment["texture_name"]
            or str(texture.get("source_bundle", "")) != assignment["texture_source_bundle"]
            or str(texture.get("format", "")) != assignment["texture_format"]
            or int(texture.get("width", 0)) != assignment["texture_width"]
            or int(texture.get("height", 0)) != assignment["texture_height"]
            or str(texture.get("usage", "")) != assignment["texture_usage"]
            or str(texture.get("preview_path", "")) != assignment["preview_path"]
            or str(texture.get("preview_sha256", "")).to_lower() != assignment["preview_sha256"]):
            continue
        matched = true
        break
    if not matched:
        return null
    var absolute := _safe_assignment_preview_path(
        assignment["preview_path"], catalog_file)
    if absolute.is_empty() or not FileAccess.file_exists(absolute):
        return null
    var preview_file := FileAccess.open(absolute, FileAccess.READ)
    if (preview_file == null or preview_file.get_length() <= 0
        or preview_file.get_length() > MAX_PREVIEW_BYTES
        or FileAccess.get_sha256(absolute).to_lower() != assignment["preview_sha256"]):
        return null
    var image := Image.new()
    if (image.load(absolute) != OK or image.get_width() <= 0 or image.get_height() <= 0
        or image.get_width() > 512 or image.get_height() > 512):
        return null
    return ImageTexture.create_from_image(image)
