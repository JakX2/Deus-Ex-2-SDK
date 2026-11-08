extends VBoxContainer
## Read-only browser for source-backed DX2 MatLib records and local PNG previews.
## The catalog is generated from user-supplied IBD/Maps ZIP files. This panel
## never edits source bundles or writes native material/BSP data.

const PythonRuntime = preload("res://python_runtime.gd")
const CATALOG_SCHEMA := "DX2Ed-MatLib-catalog-v1"
const MAX_CATALOG_BYTES := 64 * 1024 * 1024
const MAX_MATERIALS := 50000
const MAX_SOURCE_FILES := 64
const MAX_PREVIEW_BYTES := 2 * 1024 * 1024

var source_dialog: FileDialog
var search_box: LineEdit
var filter_selector: OptionButton
var material_list: ItemList
var details_label: Label
var stage_grid: GridContainer
var status_label: Label

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
    filter_selector.add_item("Resolved diffuse")
    filter_selector.add_item("Missing diffuse")
    filter_selector.add_item("Unresolved stage refs")
    filter_selector.item_selected.connect(func(_index: int): _refresh_list())
    filter_row.add_child(filter_selector)

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

    var stage_scroll := ScrollContainer.new()
    stage_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
    detail_column.add_child(stage_scroll)
    stage_grid = GridContainer.new()
    stage_grid.columns = 3
    stage_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    stage_scroll.add_child(stage_grid)

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
    var exit_code := OS.execute(PythonRuntime.executable(), arguments, output, true)
    if exit_code == -1:
        output.clear()
        var fallback := PackedStringArray(["-3", worker, "--bundle", path, "--output", output_path])
        exit_code = OS.execute("py", fallback, output, true)
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
    _refresh_list()
    status_label.text = (
        "Loaded %d MatLib records from %d source file(s). "
        + "Stage references are metadata; shader effects are not interpreted."
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
                var relative: String = str(texture.get("preview_path", ""))
                if not relative.is_empty():
                    if _safe_preview_path(relative, path).is_empty():
                        return false
                    if not _is_sha256(str(texture.get("preview_sha256", ""))):
                        return false
    return true


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
    for material in materials:
        if typeof(material) != TYPE_DICTIONARY:
            continue
        var stages: Array = material.get("stages", [])
        if stages.size() != 9:
            continue
        var diffuse: Dictionary = stages[0]
        var has_diffuse := bool(diffuse.get("resolved", false))
        var has_unresolved := false
        var stage_names: Array[String] = []
        for stage in stages:
            var stage_name := str(stage.get("name", ""))
            if not stage_name.is_empty():
                stage_names.append(stage_name)
                if not bool(stage.get("resolved", false)):
                    has_unresolved = true
        match mode:
            1:
                if not has_diffuse:
                    continue
            2:
                if has_diffuse:
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
            str(material.get("name", "")) + "  [category " + str(material.get("category_id", "?")) + "]"
        )
    if visible_materials.is_empty():
        selected_material.clear()
        details_label.text = "No materials match the current filter."
        _clear_stage_cards()
    elif selected_material.is_empty():
        details_label.text = "%d materials match. Select one to inspect all nine stage slots." % visible_materials.size()
    status_label.text = "%d / %d materials in current filter." % [visible_materials.size(), materials.size()]


func _material_selected(index: int) -> void:
    if index < 0 or index >= visible_materials.size():
        return
    selected_material = visible_materials[index]
    var lines: Array[String] = [
        "Material: " + str(selected_material.get("name", "")),
        "Source bundle: " + str(selected_material.get("source_bundle", "")),
        "Source label: " + str(selected_material.get("source", "")),
        "Version: " + str(selected_material.get("version", "?")),
        "Flags: 0x%08X" % int(selected_material.get("flags", 0)),
        "Stage mask: 0x%08X" % int(selected_material.get("stage_mask", 0)),
        "Category ID: " + str(selected_material.get("category_id", "?")),
        "Colors: " + str(selected_material.get("colors", [])),
        "Parameters: " + str(selected_material.get("params", [])),
        "Shader interpretation: metadata only; no native assignment."
    ]
    details_label.text = "\n".join(lines)
    _clear_stage_cards()
    for stage in selected_material.get("stages", []):
        _add_stage_card(stage)


func _clear_stage_cards() -> void:
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
    stage_label.text = "Stage %d" % int(stage.get("index", -1))
    column.add_child(stage_label)
    var name_label := Label.new()
    var name := str(stage.get("name", ""))
    name_label.text = name if not name.is_empty() else "(empty)"
    name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    column.add_child(name_label)
    var detail := Label.new()
    if bool(stage.get("resolved", false)):
        var texture: Dictionary = stage.get("texture", {})
        detail.text = "%s · %s×%s\n%s" % [
            str(texture.get("format", "?")),
            str(texture.get("width", "?")),
            str(texture.get("height", "?")),
            str(texture.get("usage", "usage unknown"))
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
