extends VBoxContainer
## Read-only topology inspector for the MOPP-linked subset of one original render section.
## It never edits a map, native BSP surface, material assignment or physics object.

signal triangle_requested(original_level_triangle_id: int)
signal edge_overlay_toggled(enabled: bool)

const ANALYSIS_CAP := 8192
const EDGE_NAMES := ["same-material interior", "open boundary", "render-material seam", "non-manifold"]

var picker: RefCounted
var selected_triangle_id := -1
var summary: Dictionary = {}
var heading_label: Label
var note_label: Label
var report_label: Label
var analyze_button: Button
var copy_button: Button
var neighbor_row: HBoxContainer
var neighbor_selector: OptionButton
var neighbor_button: Button
var edge_toggle: CheckBox
var copy_edges_button: Button

func initialize() -> void:
    visible = false
    size_flags_vertical = Control.SIZE_SHRINK_BEGIN
    heading_label = Label.new()
    heading_label.text = "ORIGINAL SOURCE SECTION TOPOLOGY"
    heading_label.add_theme_font_size_override("font_size", 13)
    add_child(heading_label)
    note_label = Label.new()
    note_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    note_label.text = "Select an authenticated original MOPP-linked triangle to inspect its render-section subset."
    add_child(note_label)
    var controls := HFlowContainer.new()
    add_child(controls)
    analyze_button = Button.new()
    analyze_button.text = "Analyze MOPP subset"
    analyze_button.disabled = true
    analyze_button.pressed.connect(_analyze)
    controls.add_child(analyze_button)
    copy_button = Button.new()
    copy_button.text = "Copy topology JSON"
    copy_button.disabled = true
    copy_button.pressed.connect(_copy_report)
    controls.add_child(copy_button)
    edge_toggle = CheckBox.new()
    edge_toggle.text = "Show exact-weld edge overlay"
    edge_toggle.tooltip_text = "Color the authenticated MOPP-leaf subset edges by local incidence; not complete BSP topology."
    edge_toggle.disabled = true
    edge_toggle.toggled.connect(_on_edge_overlay_toggled)
    controls.add_child(edge_toggle)
    copy_edges_button = Button.new()
    copy_edges_button.text = "Copy edge report JSON"
    copy_edges_button.disabled = true
    copy_edges_button.pressed.connect(_copy_edge_report)
    controls.add_child(copy_edges_button)
    neighbor_row = HBoxContainer.new()
    neighbor_row.visible = false
    add_child(neighbor_row)
    neighbor_selector = OptionButton.new()
    neighbor_selector.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    neighbor_selector.disabled = true
    neighbor_selector.tooltip_text = "Adjacent sections discovered through exact-weld shared edges in the MOPP leaf subset."
    neighbor_row.add_child(neighbor_selector)
    neighbor_button = Button.new()
    neighbor_button.text = "Select adjacent section"
    neighbor_button.disabled = true
    neighbor_button.pressed.connect(_select_neighbor)
    neighbor_row.add_child(neighbor_button)
    report_label = Label.new()
    report_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    report_label.text = "No source section selected."
    add_child(report_label)

func set_selection(value: RefCounted, hit: Dictionary) -> void:
    clear_selection()
    if value == null or not bool(value.get("ready")):
        return
    var raw_id: Variant = hit.get("original_level_triangle_id", -1)
    if typeof(raw_id) not in [TYPE_INT, TYPE_FLOAT] or not is_finite(float(raw_id)) or float(raw_id) != floor(float(raw_id)):
        return
    var tid := int(raw_id)
    var section: Dictionary = value.call("section_details", tid)
    if section.is_empty():
        return
    picker = value
    selected_triangle_id = tid
    heading_label.text = "SOURCE SECTION TOPOLOGY | %d / %d / %d" % [
        int(section["source_block_id"]), int(section["render_block_ordinal"]),
        int(section["render_section_ordinal"])]
    note_label.text = (
        "Selected Level triangle #%d | %d MOPP-linked triangle(s) in this section subset. "
        + "Analysis uses exact original Level weld IDs; it is not a complete render/BSP surface."
    ) % [tid, int(section["triangle_count"])]
    report_label.text = "Press Analyze MOPP subset to calculate bounded geometry and adjacency diagnostics."
    analyze_button.disabled = false
    visible = true

func clear_selection() -> void:
    picker = null
    selected_triangle_id = -1
    summary.clear()
    if heading_label != null:
        heading_label.text = "ORIGINAL SOURCE SECTION TOPOLOGY"
    if note_label != null:
        note_label.text = "Select an authenticated original MOPP-linked triangle to inspect its render-section subset."
    if report_label != null:
        report_label.text = "No source section selected."
    if analyze_button != null:
        analyze_button.disabled = true
    if copy_button != null:
        copy_button.disabled = true
    if edge_toggle != null:
        if edge_toggle.button_pressed:
            edge_overlay_toggled.emit(false)
        edge_toggle.set_pressed_no_signal(false)
        edge_toggle.disabled = true
    if copy_edges_button != null:
        copy_edges_button.disabled = true
    _clear_neighbors()
    visible = false

func _clear_neighbors() -> void:
    if neighbor_selector != null:
        neighbor_selector.clear()
        neighbor_selector.disabled = true
    if neighbor_button != null:
        neighbor_button.disabled = true
    if neighbor_row != null:
        neighbor_row.visible = false

func _populate_neighbors(result: Dictionary) -> void:
    _clear_neighbors()
    if neighbor_selector == null:
        return
    for raw_neighbor in result.get("neighbor_sections", []):
        if typeof(raw_neighbor) != TYPE_DICTIONARY:
            continue
        var neighbor: Dictionary = raw_neighbor
        var triangle_id := int(neighbor.get("representative_triangle_id", -1))
        if triangle_id < 0:
            continue
        var label := "Block %d / render %d / section %d | %s | %d shared edge(s)" % [
            int(neighbor.get("source_block_id", -1)),
            int(neighbor.get("render_block_ordinal", -1)),
            int(neighbor.get("render_section_ordinal", -1)),
            str(neighbor.get("render_material_name", "")),
            int(neighbor.get("shared_edge_count", 0)),
        ]
        neighbor_selector.add_item(label)
        var item_index := neighbor_selector.get_item_count() - 1
        neighbor_selector.set_item_metadata(item_index, {
            "triangle_id": triangle_id,
            "source_block_id": int(neighbor.get("source_block_id", -1)),
            "render_block_ordinal": int(neighbor.get("render_block_ordinal", -1)),
            "render_section_ordinal": int(neighbor.get("render_section_ordinal", -1)),
        })
    var has_neighbors := neighbor_selector.get_item_count() > 0
    neighbor_selector.disabled = not has_neighbors
    neighbor_button.disabled = not has_neighbors
    neighbor_row.visible = has_neighbors
    if has_neighbors:
        neighbor_selector.select(0)

func _select_neighbor() -> void:
    if (picker == null or not bool(picker.get("ready"))
        or neighbor_selector == null or neighbor_button == null
        or neighbor_selector.disabled):
        return
    var item_index := neighbor_selector.selected
    if item_index < 0 or item_index >= neighbor_selector.get_item_count():
        return
    var raw_metadata: Variant = neighbor_selector.get_item_metadata(item_index)
    if typeof(raw_metadata) != TYPE_DICTIONARY:
        return
    var metadata: Dictionary = raw_metadata
    var triangle_id := int(metadata.get("triangle_id", -1))
    if triangle_id < 0:
        return
    var hit: Dictionary = picker.call("triangle_details", triangle_id)
    if (hit.is_empty()
        or int(hit.get("original_level_triangle_id", -1)) != triangle_id
        or int(hit.get("source_block_id", -1)) != int(metadata.get("source_block_id", -2))
        or int(hit.get("render_block_ordinal", -1)) != int(metadata.get("render_block_ordinal", -2))
        or int(hit.get("render_section_ordinal", -1)) != int(metadata.get("render_section_ordinal", -2))):
        report_label.text = "Adjacent section target no longer matches the authenticated source cache."
        return
    triangle_requested.emit(triangle_id)

func _analyze() -> void:
    if picker == null or not bool(picker.get("ready")) or selected_triangle_id < 0:
        clear_selection()
        return
    if edge_toggle.button_pressed:
        edge_toggle.set_pressed_no_signal(false)
        edge_overlay_toggled.emit(false)
    edge_toggle.disabled = true
    copy_edges_button.disabled = true
    var result: Dictionary = picker.call("section_topology_details", selected_triangle_id, ANALYSIS_CAP)
    if result.is_empty():
        summary.clear()
        copy_button.disabled = true
        edge_toggle.disabled = true
        copy_edges_button.disabled = true
        _clear_neighbors()
        report_label.text = "Topology analysis refused: source section identity or geometry is unavailable."
        return
    summary = result.duplicate(true)
    copy_button.disabled = false
    if bool(result.get("analysis_skipped_for_size", false)):
        edge_toggle.disabled = true
        copy_edges_button.disabled = true
        _clear_neighbors()
        report_label.text = (
            "Analysis skipped without partial results.\n"
            + "This section contains %d MOPP-linked triangles; the bounded analysis cap is %d.\n"
            + "The original source selection remains valid."
        ) % [int(result["section_triangle_count"]), int(result["analysis_cap"])]
        return
    if bool(result.get("analysis_skipped_for_edge_incidence", false)):
        edge_toggle.disabled = true
        copy_edges_button.disabled = true
        _clear_neighbors()
        report_label.text = (
            "Analysis skipped without partial results.\n"
            + "A touched source edge has %d MOPP incidences; the per-edge cap is %d.\n"
            + "The original source selection remains valid."
        ) % [int(result["edge_incidence_count"]), int(result["edge_incidence_cap"])]
        return
    _populate_neighbors(result)
    var raw_edge_records: Variant = result.get("edge_records", null)
    var edge_records: Array = raw_edge_records if typeof(raw_edge_records) == TYPE_ARRAY else []
    var has_complete_edge_report := (
        not edge_records.is_empty()
        and edge_records.size() == int(result.get("unique_source_edge_count", -1))
        and edge_records.size() == int(result.get("edge_record_count", -2))
        and result.has("edge_classification_counts")
    )
    edge_toggle.disabled = not has_complete_edge_report
    copy_edges_button.disabled = not has_complete_edge_report
    var lines := PackedStringArray([
        "MOPP-linked triangles in section subset: %d" % int(result["section_triangle_count"]),
        "Unique exact-welded source vertices / edges: %d / %d" % [
            int(result["unique_source_vertex_count"]), int(result["unique_source_edge_count"])],
        "Summed MOPP triangle area: %.3f Level units²" % float(result["area_level_units_squared"]),
        "Area-weighted centroid (Level XYZ): %s" % str(result["area_weighted_centroid_level_xyz"]),
        "Bounds min / max (Level XYZ): %s / %s" % [
            str(result["bounds_min_level_xyz"]), str(result["bounds_max_level_xyz"])],
        "Connected components in MOPP subset: %d | largest sizes: %s" % [
            int(result["connected_component_count"]), str(result["largest_component_sizes"])],
        "MOPP-subset perimeter / within-section shared / subset non-manifold edges: %d / %d / %d" % [
            int(result["section_perimeter_edge_count"]), int(result["section_shared_edge_count"]),
            int(result["section_nonmanifold_edge_count"])],
        "MOPP-shared edges to other render sections: %d | perimeter edges shared across sections: %d" % [
            int(result["cross_section_mopp_shared_edge_count"]),
            int(result["section_perimeter_shared_with_other_sections"])],
        "MOPP-subset perimeter length: %.3f Level units" % float(result["section_perimeter_length_level_units"]),
        "Cross-section shared edge length: %.3f Level units" % float(result["cross_section_mopp_shared_edge_length_level_units"]),
    ])
    var class_counts: Array = result.get("source_edge_class_counts", [])
    if class_counts.size() == 4:
        lines.append("MOPP-leaf source edge classes on touched edges:")
        for index in range(4):
            lines.append("  %s: %d" % [EDGE_NAMES[index], int(class_counts[index])])
    if has_complete_edge_report:
        var overlay_counts: Dictionary = result["edge_classification_counts"]
        lines.append("Exact-weld overlay edges: open %d | within-section shared %d | cross-section MOPP shared %d | subset non-manifold %d" % [
            int(overlay_counts["subset_open_boundary"]),
            int(overlay_counts["within_section_shared"]),
            int(overlay_counts["cross_section_mopp_shared"]),
            int(overlay_counts["subset_nonmanifold"]),
        ])
        lines.append("Overlay classifications describe this MOPP-leaf subset only; source edge class codes remain raw.")
    lines.append("Adjacent MOPP-linked render sections: %d" % int(result["neighbor_section_count"]))
    if int(result.get("neighbor_section_count", 0)) > 0:
        lines.append("Choose an adjacent section above to jump to its representative MOPP-linked triangle.")
    for neighbor in result.get("neighbor_sections", []):
        lines.append("  Block %d / render %d / section %d | %s | %d shared edge(s)" % [
            int(neighbor["source_block_id"]), int(neighbor["render_block_ordinal"]),
            int(neighbor["render_section_ordinal"]), str(neighbor["render_material_name"]),
            int(neighbor["shared_edge_count"])])
    if int(result.get("omitted_neighbor_section_count", 0)) > 0:
        lines.append("  ... %d additional adjacent section(s) omitted by report cap." % int(result["omitted_neighbor_section_count"]))
    if int(result.get("omitted_component_count", 0)) > 0:
        lines.append("  ... %d additional component size(s) omitted by report cap." % int(result["omitted_component_count"]))
    lines.append("Scope: MOPP terminal-leaf subset only; zero-area non-leaf triangles are excluded.")
    lines.append("Not a complete BSP/render surface, Havok adjacency, physics material or shader result.")
    lines.append("Native map written: NO.")
    report_label.text = "\n".join(lines)

func _copy_report() -> void:
    if summary.is_empty():
        return
    DisplayServer.clipboard_set(JSON.stringify(summary, "  "))
    note_label.text = "Copied bounded read-only source-section topology JSON."


func edge_report_payload() -> Dictionary:
    if summary.is_empty():
        return {}
    var raw_records: Variant = summary.get("edge_records", null)
    if typeof(raw_records) != TYPE_ARRAY:
        return {}
    return {
        "schema": "DX2Ed-source-section-edge-report-v1",
        "source_map": str(summary.get("source_map", "")),
        "source_sha256": str(summary.get("source_sha256", "")),
        "source_section_key": str(summary.get("source_section_key", "")),
        "source_block_id": int(summary.get("source_block_id", -1)),
        "render_block_ordinal": int(summary.get("render_block_ordinal", -1)),
        "render_section_ordinal": int(summary.get("render_section_ordinal", -1)),
        "edge_record_count": int(summary.get("edge_record_count", -1)),
        "edge_classification_counts": summary.get("edge_classification_counts", {}),
        "edge_records": raw_records,
        "mopp_leaf_subset_only": true,
        "edge_report_uses_original_float32_weld_ids": true,
        "native_bsp_surface_verified": false,
        "native_map_written": false,
    }


func _on_edge_overlay_toggled(enabled: bool) -> void:
    if enabled and (summary.is_empty() or not summary.has("edge_records")):
        return
    edge_overlay_toggled.emit(enabled)


func _copy_edge_report() -> void:
    var payload := edge_report_payload()
    if payload.is_empty():
        return
    DisplayServer.clipboard_set(JSON.stringify(payload, "  "))
    note_label.text = "Copied bounded exact-weld MOPP-subset edge report JSON."
