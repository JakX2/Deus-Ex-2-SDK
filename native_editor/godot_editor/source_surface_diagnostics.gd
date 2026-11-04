extends RefCounted
## Read-only original DX2 Level triangle plane/edge/elevation measurements.
## The source picker supplies original Level IDs and geometry; this module never
## reads native game bytes, simulates Havok, asserts walkability or edits maps.

const SCHEMA := "DX2Ed-source-surface-transition-research-v1"
const EDGE_NAMES := [
    "two-triangle interior",
    "open boundary",
    "render-material seam (NOT physical material)",
    "non-manifold (3+ triangle uses)",
]
const POSITION_TOLERANCE_GODOT := 0.0001
const BARYCENTRIC_TOLERANCE := 0.0002
const MAX_LEVEL_THRESHOLD := 10000.0

func _finite_limit(value: float, lower: float, upper: float) -> bool:
    return is_finite(value) and value >= lower and value <= upper

func _point_to_segment(point: Vector3, a: Vector3, b: Vector3) -> float:
    var edge: Vector3 = b - a
    var span: float = edge.length_squared()
    if span <= 0.0:
        return point.distance_to(a)
    var factor: float = clampf((point-a).dot(edge) / span, 0.0, 1.0)
    return point.distance_to(a + edge * factor)

func inspect(picker: RefCounted, hit: Dictionary, slope_limit_degrees: float = 45.0) -> Dictionary:
    if (picker == null or not bool(picker.get("ready"))
        or not _finite_limit(slope_limit_degrees, 0.0, 89.9)
        or typeof(hit.get("original_level_triangle_id")) != TYPE_INT
        or not (hit.get("point_godot") is Vector3)):
        return {}
    var tid: int = int(hit["original_level_triangle_id"])
    var existing: Variant = picker.get("face_index_by_id")
    if typeof(existing) != TYPE_DICTIONARY or not existing.has(tid):
        return {}
    var source_map: String = str(picker.get("source_map"))
    var source_hash: String = str(picker.get("source_sha256"))
    if (not source_map.to_lower().ends_with(".gmp") or source_hash.length() != 64
        or not source_hash.is_valid_hex_number()):
        return {}
    var original: Dictionary = picker.triangle_details(tid)
    var raw: Variant = original.get("vertices_godot")
    var raw_kinds: Variant = original.get("source_edge_kinds")
    if (typeof(raw) != TYPE_ARRAY or raw.size() != 3
        or typeof(raw_kinds) != TYPE_ARRAY or raw_kinds.size() != 3):
        return {}
    for item in raw:
        if not (item is Vector3) or not item.is_finite():
            return {}
    for code in raw_kinds:
        if typeof(code) != TYPE_INT or int(code) < 0 or int(code) >= EDGE_NAMES.size():
            return {}
    var a: Vector3 = raw[0]
    var b: Vector3 = raw[1]
    var c: Vector3 = raw[2]
    var point: Vector3 = hit["point_godot"]
    if not point.is_finite():
        return {}
    var ab: Vector3 = b-a
    var ac: Vector3 = c-a
    var cross: Vector3 = ab.cross(ac)
    var len_cross: float = cross.length()
    if not is_finite(len_cross) or len_cross < 1e-14:
        return {}
    var normal: Vector3 = cross / len_cross
    # Ensure the selected point is actually on THIS authenticated triangle.
    # A source ID alone is not evidence that arbitrary supplied hit XYZ belongs.
    if absf((point-a).dot(normal)) > POSITION_TOLERANCE_GODOT:
        return {}
    var d00: float = ab.dot(ab)
    var d01: float = ab.dot(ac)
    var d11: float = ac.dot(ac)
    var ap: Vector3 = point-a
    var d20: float = ap.dot(ab)
    var d21: float = ap.dot(ac)
    var determinant: float = d00*d11 - d01*d01
    if determinant <= 1e-24 or not is_finite(determinant):
        return {}
    var wb: float = (d11*d20-d01*d21)/determinant
    var wc: float = (d00*d21-d01*d20)/determinant
    if minf(wb, minf(wc, 1.0-wb-wc)) < -BARYCENTRIC_TOLERANCE:
        return {}
    # Winding is not native Havok "front" and cannot establish floor versus ceiling.
    var slope_degrees: float = rad_to_deg(acos(clampf(absf(normal.y), 0.0, 1.0)))
    var lengths: Array[float] = []
    var rises: Array[float] = []
    var grades: Array[float] = []
    var labels: Array[String] = []
    var nearest := -1
    var nearest_distance := INF
    var vertices := [a, b, c]
    for i in 3:
        var first: Vector3 = vertices[i]
        var last: Vector3 = vertices[(i+1) % 3]
        var edge: Vector3 = last-first
        var run_horizontal: float = Vector2(edge.x, edge.z).length()
        var rise: float = absf(edge.y)
        var distance: float = _point_to_segment(point, first, last)
        if distance < nearest_distance:
            nearest_distance = distance
            nearest = i
        lengths.append(edge.length() * 10.0)
        rises.append(rise * 10.0)
        grades.append(rad_to_deg(atan2(rise, run_horizontal)))
        labels.append(EDGE_NAMES[int(raw_kinds[i])])
    return {
        "schema": SCHEMA,
        "original_level_triangle_id": tid,
        "source_map": source_map,
        "source_sha256": source_hash,
        "point_godot": point,
        "source_pick_is_ray_hit": bool(hit.get("selection_is_ray_hit", false)),
        "unsigned_plane_slope_degrees": slope_degrees,
        "user_slope_limit_degrees": slope_limit_degrees,
        "within_user_slope_threshold": slope_degrees <= slope_limit_degrees,
        "winding_dot_preview_up": normal.y,
        "nearest_edge_ab_bc_ca": nearest,
        "nearest_edge_distance_level_units": nearest_distance * 10.0,
        "edge_classes": labels,
        "edge_length_level_units": lengths,
        "edge_unsigned_rise_level_units": rises,
        "edge_incline_degrees": grades,
        "render_material_is_physical_material": false,
        "floor_or_ceiling_semantics_verified": false,
        "gameplay_walkability_verified": false,
        "native_havok_runtime_queried": false,
        "read_only": true,
    }

func compare(reference: Dictionary, selected: Dictionary,
             max_horizontal_gap_level: float = 1.0,
             max_step_height_level: float = 0.5,
             slope_limit_degrees: float = 45.0) -> Dictionary:
    if (not _finite_limit(max_horizontal_gap_level, 0.001, MAX_LEVEL_THRESHOLD)
        or not _finite_limit(max_step_height_level, 0.0, MAX_LEVEL_THRESHOLD)
        or not _finite_limit(slope_limit_degrees, 0.0, 89.9)):
        return {}
    if (reference.get("schema", "") != SCHEMA
        or selected.get("schema", "") != SCHEMA
        or reference.get("source_map", "") != selected.get("source_map", "")
        or reference.get("source_sha256", "") != selected.get("source_sha256", "")
        or not bool(reference.get("source_pick_is_ray_hit", false))
        or not bool(selected.get("source_pick_is_ray_hit", false))
        or not (reference.get("point_godot") is Vector3)
        or not (selected.get("point_godot") is Vector3)):
        return {}
    var first: Vector3 = reference["point_godot"]
    var second: Vector3 = selected["point_godot"]
    if not first.is_finite() or not second.is_finite():
        return {}
    var height_level: float = (second.y-first.y)*10.0
    var run_level: float = Vector2(second.x-first.x, second.z-first.z).length()*10.0
    var same_face: bool = (int(reference["original_level_triangle_id"])
        == int(selected["original_level_triangle_id"]))
    var a_slope: float = float(reference["unsigned_plane_slope_degrees"])
    var b_slope: float = float(selected["unsigned_plane_slope_degrees"])
    var both_floor_like: bool = (a_slope <= slope_limit_degrees
        and b_slope <= slope_limit_degrees)
    var nearby: bool = run_level <= max_horizontal_gap_level
    # This is a sampled signed elevation difference between *two* picked
    # surfaces, NOT a geometric stair, NavMesh connection, or Havok step limit.
    var proxy: bool = (nearby and both_floor_like and not same_face
        and absf(height_level) > 0.0001)
    return {
        "schema": SCHEMA,
        "signed_height_difference_level_units": height_level,
        "absolute_height_difference_level_units": absf(height_level),
        "horizontal_gap_level_units": run_level,
        "max_horizontal_gap_level_units": max_horizontal_gap_level,
        "max_step_height_level_units": max_step_height_level,
        "slope_limit_degrees": slope_limit_degrees,
        "same_original_triangle": same_face,
        "nearby_sampled_footprints": nearby,
        "both_unsigned_slopes_within_limit": both_floor_like,
        "vertical_discontinuity_proxy_only": proxy,
        "within_user_step_height_threshold": proxy and absf(height_level) <= max_step_height_level,
        "gameplay_step_or_walkability_verified": false,
        "vertical_link_between_surfaces_verified": false,
        "render_material_is_physical_material": false,
        "native_havok_runtime_queried": false,
    }
