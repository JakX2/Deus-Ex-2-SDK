extends SceneTree
## Synthetic Godot 4.3 regression for source render-section topology subset diagnostics.
## All geometry is synthetic; no retail map or source asset is included.

const Picker = preload("res://collision_source_picker.gd")
const TopologyPanel = preload("res://source_section_topology_panel.gd")
const FillPreview = preload("res://source_section_fill_preview.gd")
const EdgeOverlay = preload("res://source_section_edge_overlay.gd")
const EdgePicker = preload("res://source_section_edge_picker.gd")
const VertexPicker = preload("res://source_section_vertex_picker.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"

var requested_neighbor_triangle_id := -1
var requested_edge_overlay_enabled := false
var edge_selection_cleared := false
var requested_vertex_overlay_enabled := false
var vertex_selection_cleared := false

func _initialize() -> void:
    call_deferred("_run")

func _on_neighbor_triangle_requested(triangle_id: int) -> void:
    requested_neighbor_triangle_id = triangle_id

func _on_edge_overlay_toggled(enabled: bool) -> void:
    requested_edge_overlay_enabled = enabled

func _on_edge_selection_cleared() -> void:
    edge_selection_cleared = true

func _on_vertex_overlay_toggled(enabled: bool) -> void:
    requested_vertex_overlay_enabled = enabled

func _on_vertex_selection_cleared() -> void:
    vertex_selection_cleared = true

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
        var expected_a: Vector3 = picker.vertices[int(welds[0])]
        var expected_b: Vector3 = picker.vertices[int(welds[1])]
        var actual_a := Vector3(float(edge["a_godot_xyz"][0]), float(edge["a_godot_xyz"][1]), float(edge["a_godot_xyz"][2]))
        var actual_b := Vector3(float(edge["b_godot_xyz"][0]), float(edge["b_godot_xyz"][1]), float(edge["b_godot_xyz"][2]))
        if actual_a != expected_a or actual_b != expected_b:
            _fail("Edge endpoint coordinates must follow the sorted original weld-ID pair, including reversed triangle winding.")
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
    var camera := Camera3D.new()
    camera.position = Vector3(0.0, 10.0, 10.0)
    root.add_child(camera)
    camera.look_at(Vector3.ZERO, Vector3.UP)
    camera.current = true
    var viewport_size := camera.get_viewport().get_visible_rect().size
    var screen_index: Dictionary = EdgePicker.build_screen_index(report, camera, viewport_size)
    var target_record: Dictionary = edge_records[0]
    var target_a := Vector3(
        float(target_record["a_godot_xyz"][0]),
        float(target_record["a_godot_xyz"][1]),
        float(target_record["a_godot_xyz"][2]))
    var target_b := Vector3(
        float(target_record["b_godot_xyz"][0]),
        float(target_record["b_godot_xyz"][1]),
        float(target_record["b_godot_xyz"][2]))
    var target_screen := camera.unproject_position((target_a + target_b) * 0.5)
    var picked_edge: Dictionary = EdgePicker.pick_edge(screen_index, target_screen, 18.0)
    if (screen_index.is_empty()
        or screen_index.get("projected_edge_count", -1) <= 0
        or not EdgePicker.camera_signature_matches(screen_index, camera, viewport_size)
        or picked_edge.get("edge_key", "") != str(target_record.get("edge_key", ""))
        or picked_edge.get("record", {}).get("source_weld_ids", []) != target_record.get("source_weld_ids", [])):
        _fail("Screen-space edge picking did not recover the exact original weld pair.")
        return
    if not EdgePicker.pick_edge(screen_index, Vector2(-10000.0, -10000.0), 18.0).is_empty():
        _fail("Screen-space edge picker selected an edge outside its bounded viewport index.")
        return
    if not EdgePicker.pick_edge(screen_index, target_screen, 19.0).is_empty():
        _fail("Screen-space edge picker accepted a radius wider than its indexed 18-pixel search envelope.")
        return
    var edge_highlight: Node3D = EdgePicker.build_highlight(
        picked_edge, camera, viewport_size.y, Color(0.2, 1.0, 0.5, 1.0))
    if (not is_instance_valid(edge_highlight) or edge_highlight.get_child_count() != 2
        or edge_highlight.get_meta("editor_only", false) != true):
        _fail("Selected-edge screen-width highlight was not built as a transient editor-only marker.")
        return
    edge_highlight.free()
    var stale_camera_index: Dictionary = screen_index.duplicate(true)
    camera.position += Vector3(0.25, 0.0, 0.0)
    if EdgePicker.camera_signature_matches(stale_camera_index, camera, viewport_size):
        _fail("Camera motion must invalidate the projected screen-space edge index.")
        return
    camera.position -= Vector3(0.25, 0.0, 0.0)
    var tampered_pick_report: Dictionary = report.duplicate(true)
    var tampered_pick_records: Array = tampered_pick_report["edge_records"]
    var tampered_pick_first: Dictionary = tampered_pick_records[0]
    tampered_pick_first["source_weld_ids"] = [1, 1]
    tampered_pick_records[0] = tampered_pick_first
    tampered_pick_report["edge_records"] = tampered_pick_records
    if not EdgePicker.build_screen_index(tampered_pick_report, camera, viewport_size).is_empty():
        _fail("Screen-space edge picker must reject tampered source-weld identity atomically.")
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

    var vertex_report: Dictionary = VertexPicker.build_vertex_report(report)
    var vertex_records: Array = vertex_report.get("vertex_records", [])
    if (vertex_report.is_empty() or vertex_records.size() != 7
        or vertex_report.get("schema", "") != "DX2Ed-source-section-vertex-report-v1"
        or vertex_report.get("exact_original_float32_weld_ids", false) != true
        or vertex_report.get("mopp_leaf_subset_only", false) != true
        or vertex_report.get("native_bsp_vertex_verified", true) != false
        or vertex_report.get("native_map_written", true) != false):
        _fail("Exact-weld vertex report did not derive a bounded read-only MOPP-subset vertex inventory.")
        return
    var target_vertex: Dictionary = {}
    for raw_vertex in vertex_records:
        var candidate: Dictionary = raw_vertex
        if int(candidate.get("weld_id", -1)) == 1:
            target_vertex = candidate
            break
    if (target_vertex.is_empty()
        or target_vertex.get("incident_edge_keys", []).size() < 2
        or target_vertex.get("incident_level_triangle_ids", []) != [0,1]
        or target_vertex.get("external_section_representative_triangle_ids", []) != [3]):
        _fail("Source weld ID 1 did not retain its incident local triangles and adjacent-section representative.")
        return
    var vertex_overlay: Dictionary = VertexPicker.build_overlay(
        vertex_report, camera, viewport_size)
    var vertex_marker: MultiMeshInstance3D = vertex_overlay.get("marker", null)
    var vertex_material: StandardMaterial3D = null
    if is_instance_valid(vertex_marker):
        vertex_material = vertex_marker.material_override as StandardMaterial3D
    if (vertex_overlay.is_empty() or not is_instance_valid(vertex_marker)
        or vertex_marker.multimesh == null
        or vertex_marker.multimesh.instance_count <= 0
        or vertex_material == null or not vertex_material.no_depth_test
        or vertex_material.shading_mode != BaseMaterial3D.SHADING_MODE_UNSHADED
        or vertex_marker.cast_shadow != GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        or vertex_marker.get_meta("editor_only", false) != true):
        _fail("Exact-weld vertex handle overlay was not built as a bounded editor-only MultiMesh.")
        return
    var target_point := Vector3(
        float(target_vertex["godot_xyz"][0]),
        float(target_vertex["godot_xyz"][1]),
        float(target_vertex["godot_xyz"][2]))
    var target_vertex_screen := camera.unproject_position(target_point)
    var vertex_index: Dictionary = VertexPicker.build_screen_index(
        vertex_report, camera, viewport_size)
    var picked_vertex: Dictionary = VertexPicker.pick_vertex(
        vertex_index, target_vertex_screen, 12.0)
    if (vertex_index.is_empty()
        or vertex_index.get("projected_vertex_count", -1) <= 0
        or not VertexPicker.camera_signature_matches(vertex_index, camera, viewport_size)
        or picked_vertex.get("vertex_key", "") != "1"
        or int(picked_vertex.get("source_weld_id", -1)) != 1
        or not is_equal_approx(float(picked_vertex.get("depth_godot_units", -1.0)),
            -camera.global_basis.z.dot(target_point - camera.global_position))
        or not VertexPicker.record_belongs_to_report(vertex_report, picked_vertex.get("record", {}))):
        _fail("Screen-space vertex picking did not recover the exact original Level weld identity.")
        return
    if not VertexPicker.pick_vertex(vertex_index, Vector2(-10000.0, -10000.0), 12.0).is_empty():
        _fail("Screen-space vertex picker selected a handle outside its bounded viewport index.")
        return
    var tampered_vertex_index: Dictionary = vertex_index.duplicate(true)
    tampered_vertex_index["cell_size"] = 64.0
    if not VertexPicker.pick_vertex(tampered_vertex_index, target_vertex_screen).is_empty():
        _fail("Screen-space vertex picker accepted a tampered spatial-index cell size.")
        return
    if not VertexPicker.pick_vertex(vertex_index, target_vertex_screen, 13.0).is_empty():
        _fail("Screen-space vertex picker accepted a radius wider than its indexed 12-pixel envelope.")
        return
    var vertex_highlight: Node3D = VertexPicker.build_highlight(
        picked_vertex, camera, viewport_size.y, Color(0.2, 1.0, 0.5, 1.0))
    if (not is_instance_valid(vertex_highlight) or vertex_highlight.get_child_count() != 2
        or vertex_highlight.get_meta("editor_only", false) != true):
        _fail("Selected source vertex did not receive a transient editor-only sphere/crosshair highlight.")
        return
    vertex_highlight.free()
    var stale_vertex_index: Dictionary = vertex_index.duplicate(true)
    camera.position += Vector3(0.25, 0.0, 0.0)
    if VertexPicker.camera_signature_matches(stale_vertex_index, camera, viewport_size):
        _fail("Camera motion must invalidate the projected screen-space source vertex index.")
        return
    camera.position -= Vector3(0.25, 0.0, 0.0)
    var original_near := camera.near
    var original_far := camera.far
    camera.near = original_near + 0.01
    if VertexPicker.camera_signature_matches(stale_vertex_index, camera, viewport_size):
        _fail("Camera near-plane changes must invalidate the projected source vertex index.")
        return
    camera.near = original_near
    camera.far = camera.near + 0.01
    if not VertexPicker.build_screen_index(vertex_report, camera, viewport_size).is_empty():
        _fail("Vertices outside the active camera far clip plane must not receive selectable handles.")
        return
    camera.far = original_far
    var invalid_vertex_report: Dictionary = vertex_report.duplicate(true)
    var invalid_vertex_records: Array = invalid_vertex_report["vertex_records"]
    for record_index in range(invalid_vertex_records.size()):
        var invalid_record: Dictionary = invalid_vertex_records[record_index]
        if int(invalid_record.get("weld_id", -1)) == 1:
            invalid_record["incident_edge_keys"] = ["2:3"]
            invalid_vertex_records[record_index] = invalid_record
            break
    invalid_vertex_report["vertex_records"] = invalid_vertex_records
    if VertexPicker._valid_vertex_report(invalid_vertex_report):
        _fail("A vertex report must reject incident edge keys that do not contain that exact weld ID.")
        return
    var mismatched_weld_report: Dictionary = report.duplicate(true)
    var mismatched_edges: Array = mismatched_weld_report["edge_records"]
    var mismatched_first: Dictionary = mismatched_edges[0]
    mismatched_first["b_godot_xyz"] = [999.0, 0.0, 0.0]
    mismatched_edges[0] = mismatched_first
    mismatched_weld_report["edge_records"] = mismatched_edges
    if not VertexPicker.build_vertex_report(mismatched_weld_report).is_empty():
        _fail("Conflicting coordinates for one exact original weld ID must refuse the complete vertex report.")
        return
    var tampered_vertex: Dictionary = target_vertex.duplicate(true)
    tampered_vertex["weld_id"] = 99
    if VertexPicker.record_belongs_to_report(vertex_report, tampered_vertex):
        _fail("A copied vertex record with a different weld ID must not validate against the source report.")
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
    panel.edge_selection_cleared.connect(_on_edge_selection_cleared)
    panel.vertex_overlay_toggled.connect(_on_vertex_overlay_toggled)
    panel.vertex_selection_cleared.connect(_on_vertex_selection_cleared)
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
    var cross_section_edge: Dictionary = {}
    for edge in edge_records:
        if str(edge.get("edge_classification", "")) == "cross_section_mopp_shared":
            cross_section_edge = edge
            break
    if cross_section_edge.is_empty() or not panel.set_selected_edge(cross_section_edge):
        _fail("Topology Inspector refused a source edge present in its authenticated report.")
        return
    if (not panel.edge_selection_panel.visible
        or panel.edge_triangle_selector.get_item_count() != int(cross_section_edge.get("section_incidence_count", -1))
        or panel.edge_triangle_button.disabled
        or panel.edge_neighbor_button.disabled
        or panel.edge_copy_button.disabled
        or not panel.edge_selection_label.text.contains("original float32 weld IDs")):
        _fail("Selected-edge Inspector did not expose weld IDs, incident triangles and adjacent section.")
        return
    panel.edge_triangle_selector.select(0)
    panel._select_edge_triangle()
    if requested_neighbor_triangle_id != int(cross_section_edge["section_triangle_ids"][0]):
        _fail("Selected-edge Inspector did not navigate to an incident original Level triangle.")
        return
    panel._select_edge_neighbor()
    if requested_neighbor_triangle_id != 3:
        _fail("Selected-edge Inspector did not navigate to the adjacent MOPP section representative triangle.")
        return
    var selected_payload: Dictionary = panel.selected_edge_payload()
    if (selected_payload.get("schema", "") != "DX2Ed-selected-source-section-edge-v1"
        or selected_payload.get("native_map_written", true) != false
        or selected_payload.get("edge", {}).get("source_weld_ids", []) != cross_section_edge.get("source_weld_ids", [])):
        _fail("Selected-edge evidence JSON lost exact source identity or read-only scope.")
        return

    if (panel.vertex_toggle.disabled or panel.copy_vertices_button.disabled
        or panel.vertex_report.get("vertex_record_count", -1) != 7):
        _fail("Topology Inspector did not expose the complete exact-weld vertex handle/report controls.")
        return
    panel.vertex_toggle.set_pressed_no_signal(true)
    panel.vertex_toggle.emit_signal("toggled", true)
    if not requested_vertex_overlay_enabled:
        _fail("Topology Inspector vertex handle toggle did not emit its viewport request.")
        return
    var copied_vertex_report: Dictionary = panel.vertex_report_payload()
    if (copied_vertex_report.get("schema", "") != "DX2Ed-source-section-vertex-report-v1"
        or copied_vertex_report.get("vertex_record_count", -1) != 7
        or copied_vertex_report.get("native_map_written", true) != false):
        _fail("Copyable source vertex report lost exact weld identity or read-only scope.")
        return
    if not panel.set_selected_vertex(target_vertex, vertex_report):
        _fail("Topology Inspector refused an exact-weld vertex present in its authenticated report.")
        return
    if (not panel.vertex_selection_panel.visible
        or panel.vertex_triangle_selector.get_item_count() != 2
        or panel.vertex_triangle_button.disabled
        or panel.vertex_neighbor_selector.get_item_count() != 1
        or panel.vertex_neighbor_button.disabled
        or panel.vertex_copy_button.disabled
        or not panel.vertex_selection_label.text.contains("Original Level float32 weld ID: 1")
        or not panel.vertex_selection_label.text.contains("not native BSP vertex IDs")):
        _fail("Selected-vertex Inspector did not expose weld ID, local incident triangles and observed adjacent representative.")
        return
    panel.vertex_triangle_selector.select(0)
    panel._select_vertex_triangle()
    if requested_neighbor_triangle_id != 0:
        _fail("Selected-vertex Inspector did not navigate to an incident original Level triangle.")
        return
    panel.vertex_neighbor_selector.select(0)
    panel._select_vertex_neighbor()
    if requested_neighbor_triangle_id != 3:
        _fail("Selected-vertex Inspector did not navigate to the adjacent MOPP-section representative.")
        return
    var selected_vertex_json: Dictionary = panel.selected_vertex_payload()
    if (selected_vertex_json.get("schema", "") != "DX2Ed-selected-source-section-vertex-v1"
        or selected_vertex_json.get("native_map_written", true) != false
        or selected_vertex_json.get("native_bsp_vertex_verified", true) != false
        or selected_vertex_json.get("vertex", {}).get("weld_id", -1) != 1):
        _fail("Selected-vertex evidence JSON lost source identity or read-only scope.")
        return
    panel.clear_selected_vertex()
    if not vertex_selection_cleared or panel.vertex_selection_panel.visible:
        _fail("Clearing selected vertex did not notify the viewport lifecycle and hide its Inspector.")
        return

    panel.clear_selected_edge()
    if not edge_selection_cleared or panel.edge_selection_panel.visible:
        _fail("Clearing selected edge did not notify the viewport lifecycle and hide its Inspector.")
        return
    panel.clear_selection()
    if (panel.visible or not panel.summary.is_empty() or not panel.copy_button.disabled
        or requested_edge_overlay_enabled
        or not panel.edge_toggle.disabled or panel.edge_toggle.button_pressed
        or not panel.copy_edges_button.disabled
        or panel.vertex_toggle.button_pressed or not panel.vertex_toggle.disabled
        or not panel.copy_vertices_button.disabled
        or not panel.vertex_report.is_empty()
        or requested_vertex_overlay_enabled
        or panel.neighbor_selector.get_item_count() != 0
        or not panel.neighbor_button.disabled or panel.neighbor_row.visible):
        _fail("Clearing source selection left stale topology or neighbor-navigation state visible.")
        return
    edge_marker.free()
    preview_marker.free()
    vertex_marker.free()
    camera.free()
    print("DX2Ed source section topology, exact-weld edge and vertex overlays, screen-space picking, selected-edge/vertex Inspectors and adjacent navigation smoke: PASS")
    quit(0)
