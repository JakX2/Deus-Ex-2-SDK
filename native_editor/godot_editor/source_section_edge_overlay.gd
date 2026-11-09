extends RefCounted
## Exact-weld MOPP-leaf subset edge overlay. No source mesh or native map is edited.

const MAX_EDGE_COUNT := 24576
const MAX_LOCAL_INCIDENCE := 8192
const MAX_EXTERNAL_INCIDENCE := 1024

const EDGE_COLORS := {
    "subset_open_boundary": Color(0.05, 0.90, 0.91, 1.0),
    "within_section_shared": Color(1.0, 0.77, 0.08, 1.0),
    "cross_section_mopp_shared": Color(1.0, 0.24, 0.72, 1.0),
    "subset_nonmanifold": Color(1.0, 0.10, 0.10, 1.0),
}

static func _valid_number(value: Variant) -> bool:
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value)) and absf(float(value)) <= 1_000_000_000.0)

static func _point(value: Variant) -> Vector3:
    if typeof(value) != TYPE_ARRAY:
        return Vector3(INF, INF, INF)
    var coordinates: Array = value
    if coordinates.size() != 3:
        return Vector3(INF, INF, INF)
    for component in coordinates:
        if not _valid_number(component):
            return Vector3(INF, INF, INF)
    return Vector3(float(coordinates[0]), float(coordinates[1]), float(coordinates[2]))

static func build_marker(details: Dictionary) -> Dictionary:
    if (details.get("schema", "") != "DX2Ed-source-section-topology-v1"
        or details.get("mopp_leaf_subset_only", false) != true
        or details.get("read_only", false) != true
        or details.get("native_map_written", true) != false
        or details.get("native_bsp_surface_verified", true) != false
        or details.get("edge_report_uses_original_float32_weld_ids", false) != true
        or details.get("edge_report_is_mopp_leaf_subset_only", false) != true):
        return {}
    var raw_records: Variant = details.get("edge_records", null)
    if typeof(raw_records) != TYPE_ARRAY:
        return {}
    var records: Array = raw_records
    if (records.is_empty() or records.size() > MAX_EDGE_COUNT
        or records.size() != int(details.get("edge_record_count", -1))
        or records.size() != int(details.get("unique_source_edge_count", -2))):
        return {}
    var raw_counts: Variant = details.get("edge_classification_counts", null)
    if typeof(raw_counts) != TYPE_DICTIONARY:
        return {}
    var expected_counts: Dictionary = raw_counts
    var counts := {
        "subset_open_boundary": 0,
        "within_section_shared": 0,
        "cross_section_mopp_shared": 0,
        "subset_nonmanifold": 0,
    }
    var mesh := ImmediateMesh.new()
    mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    for raw_record in records:
        if typeof(raw_record) != TYPE_DICTIONARY:
            return {}
        var record: Dictionary = raw_record
        var raw_welds: Variant = record.get("source_weld_ids", null)
        if typeof(raw_welds) != TYPE_ARRAY:
            return {}
        var welds: Array = raw_welds
        if (welds.size() != 2 or typeof(welds[0]) != TYPE_INT
            or typeof(welds[1]) != TYPE_INT):
            return {}
        var low := int(welds[0])
        var high := int(welds[1])
        if low < 0 or high <= low or str(record.get("edge_key", "")) != "%d:%d" % [low, high]:
            return {}
        var source_class = record.get("source_edge_class_code", null)
        if typeof(source_class) != TYPE_INT or int(source_class) < 0 or int(source_class) > 3:
            return {}
        var local_count := int(record.get("section_incidence_count", -1))
        var external_count := int(record.get("cross_section_neighbor_count", -1))
        if (local_count < 1 or local_count > MAX_LOCAL_INCIDENCE
            or external_count < 0 or external_count > MAX_EXTERNAL_INCIDENCE):
            return {}
        var raw_triangles: Variant = record.get("section_triangle_ids", null)
        if typeof(raw_triangles) != TYPE_ARRAY:
            return {}
        var triangle_ids: Array = raw_triangles
        if triangle_ids.size() != local_count:
            return {}
        var seen_triangles: Dictionary = {}
        for raw_triangle_id in triangle_ids:
            if typeof(raw_triangle_id) != TYPE_INT or int(raw_triangle_id) < 0:
                return {}
            if seen_triangles.has(int(raw_triangle_id)):
                return {}
            seen_triangles[int(raw_triangle_id)] = true
        var classification := str(record.get("edge_classification", ""))
        if not EDGE_COLORS.has(classification):
            return {}
        var expected_classification := "subset_open_boundary"
        if local_count >= 3:
            expected_classification = "subset_nonmanifold"
        elif external_count > 0:
            expected_classification = "cross_section_mopp_shared"
        elif local_count == 2:
            expected_classification = "within_section_shared"
        if classification != expected_classification:
            return {}
        var a := _point(record.get("a_godot_xyz", null))
        var b := _point(record.get("b_godot_xyz", null))
        if (not a.is_finite() or not b.is_finite()
            or a.distance_squared_to(b) <= 1e-12):
            return {}
        mesh.surface_set_color(EDGE_COLORS[classification])
        mesh.surface_add_vertex(a)
        mesh.surface_add_vertex(b)
        counts[classification] = int(counts[classification]) + 1
    mesh.surface_end()
    var count_total := 0
    for key in counts:
        count_total += int(counts[key])
        if int(expected_counts.get(key, -1)) != int(counts[key]):
            return {}
    if count_total != records.size():
        return {}
    var material := StandardMaterial3D.new()
    material.albedo_color = Color.WHITE
    material.vertex_color_use_as_albedo = true
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.no_depth_test = true
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    material.render_priority = 2
    var marker := MeshInstance3D.new()
    marker.name = "SourceCollision_EditorOnly_SectionEdgeTopology"
    marker.mesh = mesh
    marker.material_override = material
    marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    return {
        "marker": marker,
        "edge_count": records.size(),
        "preview_vertex_count": records.size() * 2,
        "edge_classification_counts": counts,
        "mopp_leaf_subset_only": true,
        "native_bsp_surface_verified": false,
        "native_map_written": false,
    }
