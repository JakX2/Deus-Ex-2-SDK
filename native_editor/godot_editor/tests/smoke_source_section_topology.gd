extends SceneTree
## Synthetic Godot 4.3 regression for source render-section topology subset diagnostics.
## All geometry is synthetic; no retail map or source asset is included.

const Picker = preload("res://collision_source_picker.gd")
const TopologyPanel = preload("res://source_section_topology_panel.gd")
const FillPreview = preload("res://source_section_fill_preview.gd")
const EdgeOverlay = preload("res://source_section_edge_overlay.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"

var requested_neighbor_triangle_id := -1
var requested_edge_overlay_enabled := false

func _initialize() -> void:
    call_deferred("_run")

func _on_neighbor_triangle_requested(triangle_id: int) -> void:
    requested_neighbor_triangle_id = triangle_id

func _on_edge_overlay_toggled(enabled: bool) -> void:
    requested_edge_overlay_enabled = enabled

func _fail(reason: String) -> void:
    push_error("DX2Ed source section topology smoke: " + reason)
    quit(1)

func _fixture() -> Dictionary:
    return {
        "schema": Picker.SCHEMA,
        "source_map": "Fixture.gmp",
        "source_sha256": SHA,
        "read_only": true,
        "not_a_native_collision_writer": true,
        "physics_materials_verified": false,
        "coordinate_system": "Godot preview (Level.x/10, Level.z/10, Level.y/10)",
        "source_flat_vertex_count": 7,
        "source_triangle_count": 4,
        "mopp_leaf_triangle_count": 4,
        "edge_provenance_schema": Picker.EDGE_SCHEMA,
        "source_edge_welding": "exact_original_Level_XYZ_no_epsilon",
        "source_topology_summary": {
            "source_exact_welded_vertex_count": 7,
            "unique_source_edges": 10,
            "open_boundary_edges": 8,
            "two_triangle_same_material_edges": 1,
            "two_triangle_render_material_seams": 1,
            "three_or_more_triangle_edges": 0,
            "max_triangles_using_one_edge": 2
        },
        "vertices_godot_xyz": [
            [0.0,0.0,0.0], [2.0,0.0,0.0], [0.0,0.0,2.0],
            [2.0,0.0,2.0], [4.0,0.0,0.0], [6.0,0.0,0.0], [4.0,0.0,2.0]
        ],
        "render_material_names": ["MatA", "MatB"],
        "leaf_triangles": [
            {"triangle_id": 0, "vertex_indices": [0,1,2], "source_block_id": 3,
             "render_block_ordinal": 0, "render_section_ordinal": 0,
             "render_material_id": 0, "source_edge_kinds": [1,0,1],
             "source_weld_ids": [0,1,2]},
            {"triangle_id": 1, "vertex_indices": [1,3,2], "source_block_id": 3,
             "render_block_ordinal": 0, "render_section_ordinal": 0,
             "render_material_id": 0, "source_edge_kinds": [2,1,0],
             "source_weld_ids": [1,3,2]},
            {"triangle_id": 2, "vertex_indices": [4,5,6], "source_block_id": 3,
             "render_block_ordinal": 0, "render_section_ordinal": 0,
             "render_material_id": 0, "source_edge_kinds": [1,1,1],
             "source_weld_ids": [4,5,6]},
            {"triangle_id": 3, "vertex_indices": [1,4,3], "source_block_id": 3,
             "render_block_ordinal": 0, "render_section_ordinal": 1,
             "render_material_id": 1, "source_edge_kinds": [1,1,2],
             "source_weld_ids": [1,4,3]}
        ]
    }

func _run() -> void:
    var picker := Picker.new()
    var doc: Variant = JSON.parse_string(JSON.stringify(_fixture()))
    if not picker.load_document(doc, SHA, "Fixture.gmp"):
        _fail("Synthetic exact-weld source cache refused: " + picker.last_error)
        return
    var report: Dictionary = picker.section_topology_details(0)
    if report.is_empty() or report.get("analysis_skipped_for_size", true):
        _fail("Bounded source section topology report was not generated.")
        return
    var edge_records: Array = report.get("edge_records", [])
    var edge_counts: Dictionary = report.get("edge_classification_counts", {})
    if (edge_records.size() != 8
        or report.get("edge_record_count", -1) != 8
        or report.get("edge_report_uses_original_float32_weld_ids", false) != true
        or report.get("edge_report_is_mopp_leaf_subset_only", false) != true
        or edge_counts.get("subset_open_boundary", -1) != 6
        or edge_counts.get("within_section_shared", -1) != 1
        or edge_counts.get("cross_section_mopp_shared", -1) != 1
        or edge_counts.get("subset_nonmanifold", -1) != 0):
        _fail("Exact-weld subset edge classifications or counts are incorrect: " + JSON.stringify(edge_counts))
        return
    for edge in edge_records:
        var welds: Array = edge.get("source_weld_ids", [])
        if (welds.size() != 2 or int(welds[0]) >= int(welds[1])
            or str(edge.get("edge_key", "")) != "%d:%d" % [int(welds[0]), int(welds[1])]
            or int(edge.get("source_edge_class_code", -1)) not in range(4)
            or edge.get("section_triangle_ids", []).size() != int(edge.get("section_incidence_count", -1))):
            _fail("An edge record lost its exact source-weld or raw source-class identity: " + JSON.stringify(edge))
            return
    var edge_overlay: Dictionary = EdgeOverlay.build_marker(report)
    var edge_marker: MeshInstance3D = edge_overlay.get("marker", null)
    var edge_material: StandardMaterial3D = null
    if is_instance_valid(edge_marker):
        edge_material = edge_marker.material_override as StandardMaterial3D
    if (edge_overlay.is_empty() or not is_instance_valid(edge_marker)
        or edge_marker.mesh == null or edge_marker.mesh.get_surface_count() != 1
        or edge_overlay.get("edge_count", -1) != 8
        or edge_overlay.get("preview_vertex_count", -1) != 16
        or edge_material == null or not edge_material.vertex_color_use_as_albedo
        or not edge_material.no_depth_test
        or edge_material.shading_mode != BaseMaterial3D.SHADING_MODE_UNSHADED
        or edge_marker.cast_shadow != GeometryInstance3D.SHADOW_CASTING_SETTING_OFF):
        _fail("Exact-weld MOPP-subset edge overlay was not built as a bounded editor-only line mesh.")
        return
    var tampered_report: Dictionary = report.duplicate(true)
    var tampered_records: Array = tampered_report["edge_records"]
    var tampered_first: Dictionary = tampered_records[0]
    tampered_first["source_weld_ids"] = [1, 1]
    tampered_records[0] = tampered_first
    tampered_report["edge_records"] = tampered_records
    if not EdgeOverlay.build_marker(tampered_report).is_empty():
        _fail("Malformed duplicate-weld edge identity must refuse the entire overlay.")
        return
    var preview_details: Dictionary = picker.section_surface_preview_details(0)
    var preview_vertices: PackedVector3Array = preview_details.get(
        "triangle_vertices_godot", PackedVector3Array())
    if (preview_details.is_empty()
        or preview_details.get("preview_skipped_for_size", true)
        or preview_details.get("triangle_count", -1) != 3
        or preview_details.get("preview_vertex_count", -1) != 9
        or preview_vertices.size() != 9
        or preview_details.get("mopp_leaf_subset_only", false) != true
        or preview_details.get("native_map_written", true) != false
        or preview_details.get("native_bsp_surface_verified", true) != false):
        _fail("Bounded filled-section preview geometry or read-only provenance is incorrect.")
        return
    var preview_capped: Dictionary = picker.section_surface_preview_details(0, 2)
    if (preview_capped.get("preview_skipped_for_size", false) != true
        or preview_capped.get("triangle_count", -1) != 3
        or preview_capped.has("triangle_vertices_godot")
        or not picker.section_surface_preview_details(0, 0).is_empty()
        or not picker.section_surface_preview_details(0, 8193).is_empty()):
        _fail("Filled-section preview cap must refuse atomically and reject invalid caps.")
        return
    var preview_result: Dictionary = FillPreview.build_marker(picker, 0)
    var preview_marker: MeshInstance3D = preview_result.get("marker", null)
    var preview_material: StandardMaterial3D = null
    if is_instance_valid(preview_marker):
        preview_material = preview_marker.material_override as StandardMaterial3D
    if (preview_result.is_empty() or not is_instance_valid(preview_marker)
        or preview_marker.mesh == null or preview_marker.mesh.get_surface_count() != 1
        or preview_result.get("preview_vertex_count", -1) != 9
        or preview_material == null
        or preview_material.transparency != BaseMaterial3D.TRANSPARENCY_ALPHA
        or preview_material.no_depth_test
        or preview_marker.cast_shadow != GeometryInstance3D.SHADOW_CASTING_SETTING_OFF):
        _fail("Translucent filled MOPP-subset preview marker was not built safely.")
        return
    if (report.get("schema", "") != "DX2Ed-source-section-topology-v1"
        or report.get("section_triangle_count", -1) != 3
        or report.get("unique_source_vertex_count", -1) != 7
        or report.get("unique_source_edge_count", -1) != 8
        or report.get("connected_component_count", -1) != 2
        or report.get("largest_component_sizes", []) != [2,1]):
        _fail("Section subset connectivity or exact-weld counts are incorrect: " + JSON.stringify(report))
        return
    if (abs(float(report.get("area_level_units_squared", 0.0)) - 600.0) > 0.001
        or report.get("bounds_min_level_xyz", []) != [0.0,0.0,0.0]
        or report.get("bounds_max_level_xyz", []) != [60.0,20.0,0.0]):
        _fail("Source Level-unit area/bounds conversion is incorrect: " + JSON.stringify(report))
        return
    if (report.get("section_perimeter_edge_count", -1) != 7
        or report.get("section_shared_edge_count", -1) != 1
        or report.get("section_nonmanifold_edge_count", -1) != 0
        or report.get("cross_section_mopp_shared_edge_count", -1) != 1
        or report.get("section_perimeter_shared_with_other_sections", -1) != 1
        or report.get("source_edge_class_counts", []) != [1,6,1,0]):
        _fail("Section perimeter, cross-section seam or original edge classes are incorrect.")
        return
    var neighbors: Array = report.get("neighbor_sections", [])
    if (neighbors.size() != 1
        or neighbors[0].get("render_section_ordinal", -1) != 1
        or neighbors[0].get("render_material_name", "") != "MatB"
        or neighbors[0].get("shared_edge_count", -1) != 1
        or neighbors[0].get("representative_triangle_id", -1) != 3):
        _fail("Adjacent render-section provenance was not preserved.")
        return

    # A three-way source edge can expose two neighboring sections on the same
    # edge. Their representative IDs must remain attached to their own section,
    # rather than inheriting the final incidence-loop ID.
    var multi_doc := _fixture()
    multi_doc["source_flat_vertex_count"] = 5
    multi_doc["source_triangle_count"] = 3
    multi_doc["mopp_leaf_triangle_count"] = 3
    multi_doc["source_topology_summary"] = {
        "source_exact_welded_vertex_count": 5,
        "unique_source_edges": 7,
        "open_boundary_edges": 6,
        "two_triangle_same_material_edges": 0,
        "two_triangle_render_material_seams": 0,
        "three_or_more_triangle_edges": 1,
        "max_triangles_using_one_edge": 3,
    }
    multi_doc["vertices_godot_xyz"] = [
        [0.0,0.0,0.0], [2.0,0.0,0.0], [0.0,0.0,2.0],
        [2.0,0.0,2.0], [4.0,0.0,0.0],
    ]
    multi_doc["render_material_names"] = ["MatA", "MatB", "MatC"]
    multi_doc["leaf_triangles"] = [
        {"triangle_id": 0, "vertex_indices": [0,1,2], "source_block_id": 3,
         "render_block_ordinal": 0, "render_section_ordinal": 0,
         "render_material_id": 0, "source_edge_kinds": [1,3,1],
         "source_weld_ids": [0,1,2]},
        {"triangle_id": 1, "vertex_indices": [1,3,2], "source_block_id": 3,
         "render_block_ordinal": 0, "render_section_ordinal": 1,
         "render_material_id": 1, "source_edge_kinds": [1,1,3],
         "source_weld_ids": [1,3,2]},
        {"triangle_id": 2, "vertex_indices": [1,4,2], "source_block_id": 3,
         "render_block_ordinal": 0, "render_section_ordinal": 2,
         "render_material_id": 2, "source_edge_kinds": [1,1,3],
         "source_weld_ids": [1,4,2]},
    ]
    var multi_picker := Picker.new()
    if not multi_picker.load_document(multi_doc, SHA, "Fixture.gmp"):
        _fail("Three-way exact-weld edge fixture refused: " + multi_picker.last_error)
        return
    var multi_report: Dictionary = multi_picker.section_topology_details(0)
    var multi_neighbors: Array = multi_report.get("neighbor_sections", [])
    if (multi_neighbors.size() != 2
        or int(multi_neighbors[0].get("render_section_ordinal", -1)) != 1
        or int(multi_neighbors[0].get("representative_triangle_id", -1)) != 1
        or int(multi_neighbors[1].get("render_section_ordinal", -1)) != 2
        or int(multi_neighbors[1].get("representative_triangle_id", -1)) != 2):
        _fail("Three-way edge neighbor representative IDs crossed between adjacent sections: " + JSON.stringify(multi_neighbors))
        return
    if (report.get("mopp_leaf_subset_only", false) != true
        or report.get("area_measure", "") != "sum_of_mopp_leaf_triangle_areas"
        or report.get("area_is_triangle_sum", false) != true
        or report.get("source_edge_classification_full_original_level", true) != false
        or report.get("source_edge_classification_mopp_leaf_subset", false) != true
        or report.get("connectivity_uses_exact_original_level_weld_ids", false) != true
        or report.get("native_bsp_surface_verified", true) != false
        or report.get("full_render_section_geometry_verified", true) != false
        or report.get("havok_runtime_adjacency_verified", true) != false
        or report.get("render_material_is_physics_material", true) != false
        or report.get("native_map_written", true) != false):
        _fail("Evidence scope or read-only guarantees were not explicit.")
        return
    var skipped: Dictionary = picker.section_topology_details(0, 2)
    if (skipped.is_empty() or skipped.get("analysis_skipped_for_size", false) != true
        or skipped.get("section_triangle_count", -1) != 3
        or skipped.has("unique_source_edge_count") or skipped.has("area_level_units_squared")):
        _fail("Oversized section must skip atomically without partial statistics.")
        return
    if not picker.section_topology_details(-1).is_empty() or not picker.section_topology_details(0, 0).is_empty():
        _fail("Invalid triangle IDs or analysis caps must refuse.")
        return

    var original_incidence: Array = picker.original_edge_incidence["0:1"].duplicate(true)
    var crowded_incidence: Array = []
    for incidence_index in range(1025):
        crowded_incidence.append({"triangle_id": 0, "edge_slot": 0})
    picker.original_edge_incidence["0:1"] = crowded_incidence
    var incidence_skipped: Dictionary = picker.section_topology_details(0)
    if (incidence_skipped.get("analysis_skipped_for_edge_incidence", false) != true
        or incidence_skipped.get("edge_incidence_cap", -1) != 1024
        or incidence_skipped.has("unique_source_edge_count")):
        _fail("Pathological edge incidence must skip atomically without partial statistics.")
        return
    picker.original_edge_incidence["0:1"] = original_incidence

    var panel := TopologyPanel.new()
    root.add_child(panel)
    panel.initialize()
    panel.triangle_requested.connect(_on_neighbor_triangle_requested)
    panel.edge_overlay_toggled.connect(_on_edge_overlay_toggled)
    if panel.visible:
        _fail("Topology Inspector should start hidden.")
        return
    panel.set_selection(picker, picker.triangle_details(0))
    if (not panel.visible or panel.selected_triangle_id != 0
        or panel.analyze_button.disabled):
        _fail("Actual topology panel did not receive the source triangle selection.")
        return
    panel._analyze()
    if (panel.summary.is_empty() or panel.copy_button.disabled
        or panel.edge_toggle.disabled or panel.copy_edges_button.disabled
        or not panel.report_label.text.contains("Connected components in MOPP subset: 2")
        or not panel.report_label.text.contains("Exact-weld overlay edges: open 6")
        or not panel.report_label.text.contains("Native map written: NO.")
        or panel.neighbor_selector.get_item_count() != 1
        or panel.neighbor_button.disabled):
        _fail("Actual topology panel did not render the bounded analysis and adjacent-section selector.")
        return
    panel.edge_toggle.set_pressed_no_signal(true)
    panel.edge_toggle.emit_signal("toggled", true)
    if not requested_edge_overlay_enabled:
        _fail("Topology Inspector edge overlay toggle did not emit its viewport request.")
        return
    var edge_payload: Dictionary = panel.edge_report_payload()
    if (edge_payload.get("schema", "") != "DX2Ed-source-section-edge-report-v1"
        or edge_payload.get("edge_record_count", -1) != 8
        or edge_payload.get("native_map_written", true) != false):
        _fail("Copyable edge report payload lost source identity or read-only scope.")
        return
    panel._select_neighbor()
    if requested_neighbor_triangle_id != 3:
        _fail("Selecting an adjacent section did not emit its representative original triangle ID.")
        return
    panel.clear_selection()
    if (panel.visible or not panel.summary.is_empty() or not panel.copy_button.disabled
        or requested_edge_overlay_enabled
        or not panel.edge_toggle.disabled or panel.edge_toggle.button_pressed
        or not panel.copy_edges_button.disabled
        or panel.neighbor_selector.get_item_count() != 0
        or not panel.neighbor_button.disabled or panel.neighbor_row.visible):
        _fail("Clearing source selection left stale topology or neighbor-navigation state visible.")
        return
    edge_marker.free()
    preview_marker.free()
    print("DX2Ed source section topology, exact-weld edge overlay, neighbor navigation and filled MOPP preview smoke: PASS")
    quit(0)
