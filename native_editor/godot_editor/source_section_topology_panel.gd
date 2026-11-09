extends VBoxContainer
## Read-only topology inspector for the MOPP-linked subset of one original render section.
## It never edits a map, native BSP surface, material assignment or physics object.

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
    var section: Dictionary = value.section_details(tid)
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
    visible = false

func _analyze() -> void:
    if picker == null or not bool(picker.get("ready")) or selected_triangle_id < 0:
        clear_selection()
        return
    var result: Dictionary = picker.section_topology_details(selected_triangle_id, ANALYSIS_CAP)
    if result.is_empty():
        summary.clear()
        copy_button.disabled = true
        report_label.text = "Topology analysis refused: source section identity or geometry is unavailable."
        return
    summary = result.duplicate(true)
    copy_button.disabled = false
    if bool(result.get("analysis_skipped_for_size", false)):
        report_label.text = (
            "Analysis skipped without partial results.\n"
            + "This section contains %d MOPP-linked triangles; the bounded analysis cap is %d.\n"
            + "The original source selection remains valid."
        ) % [int(result["section_triangle_count"]), int(result["analysis_cap"])]
        return
    var lines := PackedStringArray([
        "MOPP-linked triangles in section subset: %d" % int(result["section_triangle_count"]),
        "Unique exact-welded source vertices / edges: %d / %d" % [
            int(result["unique_source_vertex_count"]), int(result["unique_source_edge_count"])],
        "Area of MOPP subset: %.3f Level units²" % float(result["area_level_units_squared"]),
        "Area-weighted centroid (Level XYZ): %s" % str(result["area_weighted_centroid_level_xyz"]),
        "Bounds min / max (Level XYZ): %s / %s" % [
            str(result["bounds_min_level_xyz"]), str(result["bounds_max_level_xyz"])],
        "Connected components in MOPP subset: %d | largest sizes: %s" % [
            int(result["connected_component_count"]), str(result["largest_component_sizes"])],
        "Section perimeter / shared / non-manifold edges: %d / %d / %d" % [
            int(result["section_perimeter_edge_count"]), int(result["section_shared_edge_count"]),
            int(result["section_nonmanifold_edge_count"])],
        "MOPP-shared edges to other render sections: %d | perimeter edges shared across sections: %d" % [
            int(result["cross_section_mopp_shared_edge_count"]),
            int(result["section_perimeter_shared_with_other_sections"])],
        "Section perimeter length: %.3f Level units" % float(result["section_perimeter_length_level_units"]),
        "Cross-section shared edge length: %.3f Level units" % float(result["cross_section_mopp_shared_edge_length_level_units"]),
    ])
    var class_counts: Array = result.get("source_edge_class_counts", [])
    if class_counts.size() == 4:
        lines.append("Original full-Level edge classes on touched edges:")
        for index in range(4):
            lines.append("  %s: %d" % [EDGE_NAMES[index], int(class_counts[index])])
    lines.append("Adjacent MOPP-linked render sections: %d" % int(result["neighbor_section_count"]))
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
