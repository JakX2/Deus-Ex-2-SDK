extends VBoxContainer
## Read-only name correlation from an authenticated original MOPP-linked render section to a user-supplied MatLib catalog. Not a native material binding.
const CATALOG_SCHEMA := "DX2Ed-MatLib-catalog-v1"
const EVIDENCE_SCHEMA := "DX2Ed-read-only-source-render-material-evidence-v1"
const MAX_MATERIALS := 50000
const MAX_NAME_LENGTH := 260
const MAX_PREVIEW_BYTES := 2 * 1024 * 1024
const MAX_PREVIEW_SIDE := 96
var catalog_path := ""
var catalog: Dictionary = {}
var source_evidence: Dictionary = {}
var candidates: Array = []
var match_kind := ""
var selected_candidate_index := -1
var source_label: Label
var match_label: Label
var candidate_list: ItemList
var details_label: Label
var preview_label: Label
var preview_rect: TextureRect

func initialize() -> void:
    visible = false
    size_flags_vertical = Control.SIZE_EXPAND_FILL
    var heading := Label.new()
    heading.text = "SOURCE RENDER SECTION -> MATLIB NAME CROSS-REFERENCE"
    heading.add_theme_font_size_override("font_size", 14)
    add_child(heading)
    var note := Label.new()
    note.text = "Read-only name correlation. It does not prove a native material index, shader-stage role or physics material."
    note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(note)
    source_label = Label.new()
    source_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(source_label)
    match_label = Label.new()
    match_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(match_label)
    candidate_list = ItemList.new()
    candidate_list.custom_minimum_size = Vector2(0, 76)
    candidate_list.item_selected.connect(_candidate_selected)
    add_child(candidate_list)
    details_label = Label.new()
    details_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(details_label)
    preview_label = Label.new()
    preview_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(preview_label)
    preview_rect = TextureRect.new()
    preview_rect.custom_minimum_size = Vector2(128, 128)
    preview_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    preview_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
    preview_rect.visible = false
    add_child(preview_rect)

func set_catalog(path: String, value: Dictionary) -> bool:
    var absolute_path := ProjectSettings.globalize_path(path)
    if not _validate_catalog(value, absolute_path):
        return false
    catalog_path = absolute_path
    catalog = value
    _refresh()
    return true

func set_source_evidence(value: Dictionary) -> bool:
    if not _validate_source_evidence(value):
        clear_source_evidence()
        return false
    source_evidence = value.duplicate(true)
    _refresh()
    return true

func clear_source_evidence() -> void:
    source_evidence.clear()
    candidates.clear()
    match_kind = ""
    selected_candidate_index = -1
    if candidate_list != null:
        candidate_list.clear()
    if source_label != null:
        source_label.text = ""
    if match_label != null:
        match_label.text = ""
    if details_label != null:
        details_label.text = ""
    _clear_preview()
    visible = false

func _is_sha256(value: String) -> bool:
    if value.length() != 64:
        return false
    for index in range(value.length()):
        if "0123456789abcdef".find(value.substr(index, 1).to_lower()) < 0:
            return false
    return true

func _is_nonnegative_int(value: Variant, maximum: int = 0x7FFFFFFF) -> bool:
    return typeof(value) == TYPE_INT and int(value) >= 0 and int(value) <= maximum

func _safe_preview_path(relative_path: String, for_catalog: String) -> String:
    if (relative_path.is_empty() or relative_path.begins_with("/")
        or relative_path.contains("\\") or relative_path.contains(":")
        or relative_path.get_extension().to_lower() != "png"):
        return ""
    for segment in relative_path.split("/", false):
        if segment.is_empty() or segment == "." or segment == "..":
            return ""
    var base := ProjectSettings.globalize_path(for_catalog.get_base_dir()).simplify_path()
    var candidate := ProjectSettings.globalize_path(for_catalog.get_base_dir().path_join(relative_path)).simplify_path()
    if candidate == base or not candidate.begins_with(base + "/"):
        return ""
    return candidate

func _validate_catalog(raw: Variant, path: String) -> bool:
    if (typeof(raw) != TYPE_DICTIONARY or path.is_empty()
        or not FileAccess.file_exists(path) or path.get_extension().to_lower() != "json"):
        return false
    if (raw.get("schema", "") != CATALOG_SCHEMA
        or raw.get("read_only", false) != true
        or raw.get("native_writer_enabled", true) != false
        or raw.get("source_bytes_modified", true) != false
        or not _is_sha256(str(raw.get("catalog_id", "")))):
        return false
    var source_files = raw.get("source_files", null)
    var records = raw.get("materials", null)
    if (typeof(source_files) != TYPE_ARRAY or source_files.is_empty()
        or source_files.size() > 64 or typeof(records) != TYPE_ARRAY
        or records.size() > MAX_MATERIALS):
        return false
    for source in source_files:
        if (typeof(source) != TYPE_DICTIONARY
            or str(source.get("path", "")).is_empty()
            or not _is_sha256(str(source.get("sha256", "")))):
            return false
    for material in records:
        if (typeof(material) != TYPE_DICTIONARY
            or typeof(material.get("name", null)) != TYPE_STRING
            or str(material.get("name", "")).is_empty()
            or str(material.get("name", "")).length() > MAX_NAME_LENGTH):
            return false
        var stages = material.get("stages", null)
        if typeof(stages) != TYPE_ARRAY or stages.size() != 9:
            return false
        for index in range(9):
            var stage = stages[index]
            if (typeof(stage) != TYPE_DICTIONARY or int(stage.get("index", -1)) != index
                or typeof(stage.get("name", "")) != TYPE_STRING
                or typeof(stage.get("resolved", false)) != TYPE_BOOL):
                return false
            if bool(stage.get("resolved", false)):
                var texture = stage.get("texture", null)
                if typeof(texture) != TYPE_DICTIONARY:
                    return false
                var relative := str(texture.get("preview_path", ""))
                if not relative.is_empty():
                    if (_safe_preview_path(relative, path).is_empty()
                        or not _is_sha256(str(texture.get("preview_sha256", "")))):
                        return false
    return true

func _validate_source_evidence(value: Dictionary) -> bool:
    var source_map := str(value.get("source_map", ""))
    var material_name := str(value.get("render_material_name", ""))
    return (
        value.get("schema", "") == EVIDENCE_SCHEMA
        and not source_map.is_empty()
        and not source_map.contains("/")
        and not source_map.contains("\\")
        and source_map.to_lower().ends_with(".gmp")
        and _is_sha256(str(value.get("source_sha256", "")))
        and _is_nonnegative_int(value.get("original_level_triangle_id", null), 299999)
        and _is_nonnegative_int(value.get("source_block_id", null))
        and _is_nonnegative_int(value.get("render_block_ordinal", null), 100000)
        and _is_nonnegative_int(value.get("render_section_ordinal", null), 100000)
        and _is_nonnegative_int(value.get("source_section_triangle_count", null), 300000)
        and int(value.get("source_section_triangle_count", 0)) > 0
        and not material_name.is_empty() and material_name.length() <= MAX_NAME_LENGTH
        and not material_name.contains("\n") and not material_name.contains("\r")
        and typeof(value.get("selection_is_ray_hit", null)) == TYPE_BOOL
        and value.get("render_material_is_physics_material", true) == false
        and value.get("native_map_written", true) == false
        and value.get("native_material_index_verified", true) == false
        and value.get("shader_semantics_verified", true) == false
    )

func _refresh() -> void:
    if source_evidence.is_empty():
        visible = false
        return
    visible = true
    var source_name := str(source_evidence.get("render_material_name", ""))
    var source_sha := str(source_evidence.get("source_sha256", ""))
    source_label.text = (
        "Source: %s | GMP SHA-256 %s...\nLevel triangle %d | source block %d | render block %d / section %d | section triangles %d\nRender-material name: %s"
    ) % [
        str(source_evidence.get("source_map", "")), source_sha.left(12),
        int(source_evidence.get("original_level_triangle_id", -1)),
        int(source_evidence.get("source_block_id", -1)),
        int(source_evidence.get("render_block_ordinal", -1)),
        int(source_evidence.get("render_section_ordinal", -1)),
        int(source_evidence.get("source_section_triangle_count", 0)), source_name
    ]
    candidate_list.clear()
    candidates.clear()
    selected_candidate_index = -1
    _clear_preview()
    if catalog.is_empty():
        match_kind = "no_catalog"
        match_label.text = "NO MATLIB CATALOG LOADED. Import the original IBD / Maps ZIP in Materials; the cross-reference refreshes automatically."
        details_label.text = ""
        return
    var exact_matches: Array[Dictionary] = []
    var folded_matches: Array[Dictionary] = []
    for material in catalog.get("materials", []):
        if typeof(material) != TYPE_DICTIONARY:
            continue
        var candidate_name := str(material.get("name", ""))
        if candidate_name == source_name:
            exact_matches.append(material)
        elif candidate_name.to_lower() == source_name.to_lower():
            folded_matches.append(material)
    if not exact_matches.is_empty():
        candidates = exact_matches
        match_kind = "exact"
    elif not folded_matches.is_empty():
        candidates = folded_matches
        match_kind = "casefold"
    else:
        match_kind = "none"
    if candidates.is_empty():
        match_label.text = "NO MATCH IN IMPORTED CATALOG. The name was not found among currently imported MatLib records; bundle coverage may be incomplete."
        details_label.text = "No material candidate is selected."
        return
    var duplicate_names = catalog.get("duplicate_names", {})
    var duplicate_count := 0
    if typeof(duplicate_names) == TYPE_DICTIONARY:
        duplicate_count = int(duplicate_names.get("materials", 0))
    if candidates.size() > 1:
        match_label.text = "AMBIGUOUS: %d %s name candidates. Select one; none is an authenticated native material index." % [candidates.size(), "exact-string" if match_kind == "exact" else "case-insensitive"]
    elif match_kind == "exact":
        match_label.text = "EXACT STRING MATCH - one candidate in this imported catalog only; this is not proof of the native surface material index."
    else:
        match_label.text = "CASE-INSENSITIVE MATCH ONLY - spelling differs; treat this as a weaker candidate."
    if duplicate_count > 0:
        match_label.text += "\nCatalog reports %d duplicate MatLib name collisions overall; per-name duplicate variants are not retained, so source-level uniqueness is not established." % duplicate_count
    for material in candidates:
        candidate_list.add_item(str(material.get("name", "")) + " | " + str(material.get("source_bundle", "unknown bundle")) + " | " + str(material.get("source", "")))
    if candidates.size() == 1:
        candidate_list.select(0)
        _candidate_selected(0)
    else:
        details_label.text = "Select a candidate above to inspect its nine raw stage references."

func _candidate_selected(index: int) -> void:
    if index < 0 or index >= candidates.size():
        return
    selected_candidate_index = index
    var material: Dictionary = candidates[index]
    var lines := PackedStringArray([
        "MatLib record: " + str(material.get("name", "")),
        "Source bundle: " + str(material.get("source_bundle", "")),
        "Source label: " + str(material.get("source", "")),
        "Version: " + str(material.get("version", "?")),
        "Raw category_id: " + str(material.get("category_id", "?")),
        "Raw flags: 0x%08X" % int(material.get("flags", 0)),
        "Raw stage_mask: 0x%08X (uninterpreted)" % int(material.get("stage_mask", 0)),
        "Nine named stage references (slot roles unverified):"
    ])
    var stages: Array = material.get("stages", [])
    for index in range(9):
        var stage: Dictionary = stages[index]
        var name := str(stage.get("name", ""))
        var state := "empty"
        if not name.is_empty():
            if bool(stage.get("resolved", false)):
                state = "resolved"
            else:
                state = "unresolved"
        lines.append("Slot %d: %s [%s]" % [index, name if not name.is_empty() else "(empty)", state])
    lines.append("Native material index: NOT VERIFIED.")
    lines.append("Shader-stage semantics: NOT VERIFIED.")
    lines.append("Physical material / Havok role: NOT VERIFIED.")
    lines.append("Native map written: NO.")
    details_label.text = "\n".join(lines)
    _clear_preview()
    if not stages.is_empty():
        var slot_zero: Dictionary = stages[0]
        if bool(slot_zero.get("resolved", false)):
            if _load_slot_zero_preview(slot_zero.get("texture", {})):
                preview_label.text = "Slot 0 thumbnail - parser-decoded pixels; native shader use is unverified."

func _load_slot_zero_preview(texture: Dictionary) -> bool:
    var relative := str(texture.get("preview_path", ""))
    var expected_sha := str(texture.get("preview_sha256", ""))
    if relative.is_empty() or not _is_sha256(expected_sha):
        return false
    var path := _safe_preview_path(relative, catalog_path)
    if path.is_empty() or not FileAccess.file_exists(path):
        return false
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return false
    var size := file.get_length()
    file.close()
    if size > MAX_PREVIEW_BYTES or FileAccess.get_sha256(path).to_lower() != expected_sha.to_lower():
        return false
    var image := Image.new()
    if image.load(path) != OK:
        return false
    if image.get_width() < 1 or image.get_height() < 1 or image.get_width() > MAX_PREVIEW_SIDE or image.get_height() > MAX_PREVIEW_SIDE:
        return false
    preview_rect.texture = ImageTexture.create_from_image(image)
    preview_rect.visible = preview_rect.texture != null
    return preview_rect.visible

func _clear_preview() -> void:
    if preview_rect != null:
        preview_rect.texture = null
        preview_rect.visible = false
    if preview_label != null:
        preview_label.text = ""
