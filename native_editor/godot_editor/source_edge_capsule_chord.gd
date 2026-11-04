extends RefCounted
## Exact-original-Level-welded edge crossing chord for a geometry-only capsule
## sweep. Chord endpoints are INTERIOR to both source triangles; no Havok
## walkability, controller stepping, pathfinding, or writable collision.
const EdgeAnalyzer = preload("res://source_edge_transition_diagnostics.gd")

const SCHEMA := "DX2Ed-source-exact-edge-capsule-chord-v1"
const MIN_HORIZONTAL_SPAN := 0.000001

var edge_analyzer = EdgeAnalyzer.new()

func build(picker: RefCounted, original_id: int, edge_slot: int,
           fraction: float = 0.2, clearance_level: float = 1.,
           radius_level: float = .2, half_axis_level: float = .5,
           hinge_limit: float = 15., slope_limit: float = 45.) -> Dictionary:
    if (picker == null or not bool(picker.get("ready"))
        or edge_slot < 0 or edge_slot > 2
        or not is_finite(fraction) or fraction < 0.01 or fraction > 0.45
        or not is_finite(clearance_level) or clearance_level < 0. or clearance_level > 100.
        or not is_finite(radius_level) or radius_level < .01 or radius_level > 20.
        or not is_finite(half_axis_level) or half_axis_level < 0. or half_axis_level > 20.
        or not is_finite(hinge_limit) or hinge_limit < 0. or hinge_limit > 89.9
        or not is_finite(slope_limit) or slope_limit < 0. or slope_limit > 89.9):
        return {}
    var inspected: Dictionary = edge_analyzer.inspect(
        picker, original_id, hinge_limit, slope_limit)
    if inspected.is_empty() or not bool(inspected.get("all_connections_use_source_exact_welds", false)):
        return {}
    var source_edge: Dictionary = inspected["edges"][edge_slot]
    if (not bool(source_edge.get("one_unique_neighbor", false))
        or int(source_edge["original_incident_count"]) != 2
        or source_edge.get("horizontal_opposite_side_test", "") != "opposite sides"
        or not bool(source_edge.get("smooth_floorlike_geometric_proxy", false))):
        return {}
    var neighbors: Array = source_edge["original_neighbor_triangle_ids"]
    var slots: Array = source_edge["original_neighbor_edge_slots"]
    if neighbors.size() != 1 or slots.size() != 1:
        return {}
    var neighbor_id: int = int(neighbors[0])
    var neighbor_slot: int = int(slots[0])
    if neighbor_id == original_id or neighbor_slot not in [0,1,2]:
        return {}
    var face0: Dictionary = picker.triangle_details(original_id)
    var face1: Dictionary = picker.triangle_details(neighbor_id)
    var p: Array = face0.get("vertices_godot", [])
    var q: Array = face1.get("vertices_godot", [])
    if p.size() != 3 or q.size() != 3:
        return {}
    var edge_a: Vector3 = source_edge["edge_start_godot"]
    var edge_b: Vector3 = source_edge["edge_end_godot"]
    var midpoint: Vector3 = (edge_a + edge_b) * .5
    var third0: Vector3 = p[(edge_slot+2)%3]
    var third1: Vector3 = q[(neighbor_slot+2)%3]
    if (not edge_a.is_finite() or not edge_b.is_finite()
        or not third0.is_finite() or not third1.is_finite()):
        return {}
    var start_on_triangle: Vector3 = midpoint.lerp(third0, fraction)
    var end_on_triangle: Vector3 = midpoint.lerp(third1, fraction)
    var a: Vector2 = Vector2(edge_a.x, edge_a.z)
    var b: Vector2 = Vector2(edge_b.x, edge_b.z)
    var c: Vector2 = Vector2(start_on_triangle.x, start_on_triangle.z)
    var d: Vector2 = Vector2(end_on_triangle.x, end_on_triangle.z)
    var edge: Vector2 = b-a
    var trajectory: Vector2 = d-c
    if edge.length() < MIN_HORIZONTAL_SPAN or trajectory.length() < MIN_HORIZONTAL_SPAN:
        return {}
    # Solve (a + edge*u) = (c + trajectory*t) in horizontal preview XZ.
    # Even an exact neighbor can produce a chord that passes beyond the
    # finite shared segment for highly skewed triangles: refuse those.
    var det: float = edge.cross(trajectory)
    if absf(det) < MIN_HORIZONTAL_SPAN * MIN_HORIZONTAL_SPAN:
        return {}
    var u: float = (c-a).cross(trajectory) / det
    var t: float = (c-a).cross(edge) / det
    if (not is_finite(u) or not is_finite(t)
        or u < .0001 or u > .9999 or t < .0001 or t > .9999):
        return {}
    var offset: Vector3 = Vector3.UP * (clearance_level / 10.)
    var start: Vector3 = start_on_triangle + offset
    var end: Vector3 = end_on_triangle + offset
    var crossing: Vector3 = start.lerp(end, t)
    var edge_level: Vector3 = edge_a.lerp(edge_b, u) + offset
    if (not start.is_finite() or not end.is_finite()
        or start.distance_to(end) < .00000001 or not crossing.is_finite()):
        return {}
    var source_hash: String = str(picker.get("source_sha256"))
    var source_map: String = str(picker.get("source_map"))
    return {
        "schema": SCHEMA,
        "source_map": source_map,
        "source_sha256": source_hash,
        "source_original_triangle_id": original_id,
        "neighbor_original_triangle_id": neighbor_id,
        "source_edge_slot": edge_slot,
        "neighbor_source_edge_slot": neighbor_slot,
        "source_edge_class_code": source_edge["source_edge_class_code"],
        "bend_limit_degrees": hinge_limit,
        "slope_limit_degrees": slope_limit,
        "source_exact_welded_connectivity": true,
        "horizontal_opposite_side_test": "opposite sides",
        "start_godot_xyz": start,
        "end_godot_xyz": end,
        "crossing_godot_xyz": crossing,
        "crossing_path_normalized_t": t,
        "crossing_shared_edge_normalized_u": u,
        "vertical_chord_deviation_from_edge_level_units": (crossing.y-edge_level.y)*10.,
        "interior_fraction": fraction,
        "above_face_vertical_offset_level_units": clearance_level,
        "radius_level_units": radius_level,
        "axis_half_length_level_units": half_axis_level,
        "fixed_capsule_axis_original_Level": "positive Z",
        "swept_capsule_contact_tested": false,
        "walkability_or_Havok_runtime_verified": false,
        "game_original_assets_written": false,
    }
