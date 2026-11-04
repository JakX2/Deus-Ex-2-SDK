extends RefCounted
## Source-EXACT welded edge connectivity between original DX2 Level triangles.
## NO float-epsilon welding, Havok traversability, collision material or navmesh.

const SCHEMA := "DX2Ed-exact-Level-edge-transition-research-v1"
const MAX_PREVIEW_POSITION := 100000.0
const PREVIEW_ENDPOINT_TOLERANCE := 0.0001
const SIDE_TOLERANCE := 0.0000001
const EDGE_NAMES := ["AB", "BC", "CA"]

func _slope(normal: Vector3) -> float:
    return rad_to_deg(acos(clampf(absf(normal.y), 0., 1.)))

func _face(picker: RefCounted, tid: int) -> Dictionary:
    var data: Dictionary = picker.triangle_details(tid)
    var pts: Variant = data.get("vertices_godot")
    var weld: Variant = data.get("source_weld_ids")
    if (typeof(pts) != TYPE_ARRAY or pts.size() != 3
        or typeof(weld) != TYPE_ARRAY or weld.size() != 3):
        return {}
    var points: Array[Vector3] = []
    for v in pts:
        if not (v is Vector3) or not v.is_finite() or v.length() > MAX_PREVIEW_POSITION:
            return {}
        points.append(v)
    for v in weld:
        if typeof(v) != TYPE_INT:
            return {}
    var norm: Vector3 = (points[1]-points[0]).cross(points[2]-points[0])
    if not norm.is_finite() or norm.length() < 1e-12:
        return {}
    return {"points":points,"weld_ids":weld,"normal":norm.normalized(),
        "original_level_triangle_id":tid}

func _horizontal_edge_side(a: Vector3, b: Vector3, third: Vector3) -> float:
    var edge := Vector2(b.x-a.x,b.z-a.z)
    var offset := Vector2(third.x-a.x,third.z-a.z)
    if edge.length_squared() < SIDE_TOLERANCE*SIDE_TOLERANCE:
        return 0.
    return edge.cross(offset) / edge.length()

func inspect(picker: RefCounted, original_id: int,
             bend_limit_degrees: float = 15.,
             slope_limit_degrees: float = 45.) -> Dictionary:
    if (picker == null or not bool(picker.get("ready"))
        or not is_finite(bend_limit_degrees)
        or not 0. <= bend_limit_degrees <= 89.9
        or not is_finite(slope_limit_degrees)
        or not 0. <= slope_limit_degrees <= 89.9):
        return {}
    var source_map := str(picker.get("source_map"))
    var sha := str(picker.get("source_sha256"))
    if (not source_map.to_lower().ends_with(".gmp")
        or sha.length()!=64 or not sha.is_valid_hex_number()):
        return {}
    var main := _face(picker, original_id)
    if main.is_empty():
        return {}
    var source_edges: Array[Dictionary] = picker.edge_connected_original_triangles(original_id)
    if source_edges.size() != 3:
        return {}
    var findings: Array[Dictionary] = []
    for slot in 3:
        var entry: Dictionary = source_edges[slot]
        var kinds: Array = picker.triangle_details(original_id)["source_edge_kinds"]
        var kind: int = int(kinds[slot])
        if (int(entry.get("edge_slot",-1)) != slot
            or int(entry.get("source_class_code",-1)) != kind
            or not bool(entry.get("source_welding_is_exact_original_Level_XYZ",false))):
            return {}
        var links: Array = entry["neighbor_original_triangle_ids"]
        var link_slots: Array = entry["neighbor_source_edge_slots"]
        var degree: int = int(entry["original_incident_triangle_count"])
        if (links.size()!=degree-1 or link_slots.size()!=links.size()
            or degree<1 or (kind==1 and degree!=1)
            or (kind in [0,2] and degree!=2)
            or (kind==3 and degree<3)):
            return {}
        var corner_a: Vector3 = main["points"][slot]
        var corner_b: Vector3 = main["points"][(slot+1)%3]
        var base: Dictionary = {
            "source_edge_index":slot,
            "source_edge_name":EDGE_NAMES[slot],
            "original_incident_count":degree,
            "original_neighbor_triangle_ids":links.duplicate(),
            "original_neighbor_edge_slots":link_slots.duplicate(),
            "source_edge_class_code":kind,
            "edge_start_godot":corner_a,
            "edge_end_godot":corner_b,
            "edge_length_level_units":corner_a.distance_to(corner_b)*10.0,
            "source_exact_welded_connectivity":true,
            "one_unique_neighbor":degree==2,
            "preview_normal_bend_degrees":null,
            "preview_unsigned_neighbor_slope_degrees":null,
            "horizontal_opposite_side_test":"unavailable",
            "smooth_floorlike_geometric_proxy":false,
            "gameplay_transition_or_Havok_verified":false,
        }
        if degree == 2:
            var neighbor_id: int = int(links[0])
            var neighbor_slot: int = int(link_slots[0])
            if neighbor_id==original_id or neighbor_slot<0 or neighbor_slot>2:
                return {}
            var next := _face(picker,neighbor_id)
            if next.is_empty():
                return {}
            var nw: Array = next["weld_ids"]
            var w: Array = main["weld_ids"]
            var a: int = int(w[slot])
            var b: int = int(w[(slot+1)%3])
            var na: int = int(nw[neighbor_slot])
            var nb: int = int(nw[(neighbor_slot+1)%3])
            if not ((a==na and b==nb) or (a==nb and b==na)):
                return {}
            var other_a: Vector3 = next["points"][neighbor_slot]
            var other_b: Vector3 = next["points"][(neighbor_slot+1)%3]
            var same := (a==na and b==nb)
            var pair_a: Vector3 = other_a if same else other_b
            var pair_b: Vector3 = other_b if same else other_a
            if (corner_a.distance_to(pair_a)>PREVIEW_ENDPOINT_TOLERANCE
                or corner_b.distance_to(pair_b)>PREVIEW_ENDPOINT_TOLERANCE):
                return {}
            var n0: Vector3 = main["normal"]
            var n1: Vector3 = next["normal"]
            var unsigned_bend: float = rad_to_deg(acos(clampf(absf(n0.dot(n1)),0.,1.)))
            var slope_a: float = _slope(n0)
            var slope_b: float = _slope(n1)
            var opp_a: Vector3 = main["points"][(slot+2)%3]
            var opp_b: Vector3 = next["points"][(neighbor_slot+2)%3]
            var side_a: float = _horizontal_edge_side(corner_a,corner_b,opp_a)
            var side_b: float = _horizontal_edge_side(corner_a,corner_b,opp_b)
            var side_result := "inconclusive"
            if absf(side_a)>SIDE_TOLERANCE and absf(side_b)>SIDE_TOLERANCE:
                side_result = "opposite sides" if side_a*side_b<0. else "same side / overlapping projection"
            base["preview_normal_bend_degrees"] = unsigned_bend
            base["preview_unsigned_neighbor_slope_degrees"] = slope_b
            base["current_unsigned_slope_degrees"] = slope_a
            base["horizontal_opposite_side_test"] = side_result
            base["smooth_floorlike_geometric_proxy"] = (
                side_result=="opposite sides"
                and unsigned_bend<=bend_limit_degrees
                and slope_a<=slope_limit_degrees
                and slope_b<=slope_limit_degrees)
        findings.append(base)
    return {
        "schema":SCHEMA,
        "source_map":source_map,
        "source_sha256":sha,
        "original_level_triangle_id":original_id,
        "bend_limit_degrees":bend_limit_degrees,
        "slope_limit_degrees":slope_limit_degrees,
        "edges":findings,
        "all_connections_use_source_exact_welds":true,
        "preview_tolerance_creates_no_neighbor_links":true,
        "native_Havok_traversal_verified":false,
        "read_only":true,
    }
