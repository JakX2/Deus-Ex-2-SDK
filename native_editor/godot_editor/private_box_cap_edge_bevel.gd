extends RefCounted
## DX2Ed v0.90: bounded bevel of one existing editor-authored clipped
## Box cap perimeter edge. All inputs are source-private Godot geometry,
## never imported DX2 BSP, original GMP/IBD or Havok collision.

const Brush = preload("res://brush_geometry.gd")
const Picker = preload("res://private_box_cap_picker.gd")
const MultiClip = preload("res://private_box_multiclip.gd")
const SingleClip = preload("res://private_box_clip.gd")
const MIN_DEPTH := 0.05
const MAX_DEPTH := 0.5
const MIN_EDGE_LENGTH := 0.1


static func cap_boundary_edges(raw: Variant, cap_index: int) -> Array:
    var spec: Dictionary = Picker._checked_spec(raw)
    if spec.is_empty():
        return []
    var planes: Array = Picker._planes(spec)
    if cap_index < 0 or cap_index >= planes.size():
        return []
    var vertices: PackedVector3Array = Picker._vertices(spec)
    if vertices.is_empty():
        return []
    var edge_map := {}
    for i in range(0, vertices.size(), 3):
        var a: Vector3 = vertices[i]
        var b: Vector3 = vertices[i + 1]
        var c: Vector3 = vertices[i + 2]
        var cap := Picker._cap_index(a, b, c, planes) == cap_index
        var normal := (b - a).cross(c - a).normalized()
        if not normal.is_finite():
            return []
        for pair in [[a, b], [b, c], [c, a]]:
            var pa: Vector3 = pair[0]
            var pb: Vector3 = pair[1]
            var ka := SingleClip._vertex_key(pa)
            var kb := SingleClip._vertex_key(pb)
            if ka == kb:
                return []
            var ordered := ka + "|" + kb if ka < kb else kb + "|" + ka
            if not edge_map.has(ordered):
                edge_map[ordered] = {
                    "a": pa, "b": pb, "count": 0,
                    "cap_count": 0, "other": []}
            var row: Dictionary = edge_map[ordered]
            row["count"] = int(row["count"]) + 1
            if cap:
                row["cap_count"] = int(row["cap_count"]) + 1
            else:
                var others: Array = row["other"]
                others.append(normal)
                row["other"] = others
            edge_map[ordered] = row
    var keys: Array = edge_map.keys()
    keys.sort()
    var result: Array = []
    var cap_plane: Dictionary = planes[cap_index]
    var outward := Vector3(
        cap_plane["normal"][0], cap_plane["normal"][1],
        cap_plane["normal"][2])
    if bool(cap_plane["keep_positive"]):
        outward = -outward
    for key in keys:
        var item: Dictionary = edge_map[key]
        if int(item["cap_count"]) != 1:
            continue
        var others: Array = item["other"]
        # A genuine cap-boundary edge has one incident cap triangle and
        # exactly one neighboring surface triangle in the closed mesh.
        if int(item["count"]) != 2 or others.size() != 1:
            return []
        var a: Vector3 = item["a"]
        var b: Vector3 = item["b"]
        var length := a.distance_to(b)
        var adjacent: Vector3 = others[0]
        if (not is_finite(length) or length < MIN_EDGE_LENGTH
            or not adjacent.is_finite()
            or (outward + adjacent).length_squared() < 0.1
            or adjacent.dot(outward) > 0.999):
            return []
        result.append({
            "a": a, "b": b, "midpoint": (a + b) * 0.5,
            "length": length, "outward": outward,
            "adjacent": adjacent})
    # Refuse invisible/empty caps, incomplete outlines, or overly complex
    # perimeter data rather than offering an unreliable edge operation.
    if result.size() < 3 or result.size() > 16:
        return []
    return result


static func bevel_cap_edge(raw: Variant, cap_index: int,
                           edge_index: int, depth: float) -> Dictionary:
    if (not is_finite(depth) or depth < MIN_DEPTH or depth > MAX_DEPTH):
        return {}
    var spec: Dictionary = Picker._checked_spec(raw)
    if spec.is_empty():
        return {}
    var planes: Array = Picker._planes(spec).duplicate(true)
    if planes.size() >= MultiClip.MAX_PLANES:
        return {}
    var edges := cap_boundary_edges(spec, cap_index)
    if edge_index < 0 or edge_index >= edges.size():
        return {}
    var edge: Dictionary = edges[edge_index]
    var normal := (
        (edge["outward"] as Vector3)
        + (edge["adjacent"] as Vector3)).normalized()
    if not normal.is_finite():
        return {}
    # Trim the selected true perimeter edge inward along the *outward*
    # dihedral bisector. A new closed planar cap is created.
    var distance := normal.dot(edge["midpoint"]) - depth
    if not is_finite(distance) or absf(distance) > 256.0:
        return {}
    planes.append({
        "normal": [normal.x, normal.y, normal.z],
        "distance": distance, "keep_positive": false})
    spec.erase("clip_plane")
    spec.erase("clip_planes")
    spec["clip_planes"] = planes
    var verified: Dictionary = Brush.validate(spec)
    if verified.is_empty() or Brush.build_mesh(verified) == null:
        return {}
    return verified
