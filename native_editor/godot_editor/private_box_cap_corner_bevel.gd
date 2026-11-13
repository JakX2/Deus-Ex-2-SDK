extends RefCounted
## DX2Ed v0.91: bevel a genuine three-face corner on an authored private
## capped Box. Not a native DX2 BSP, GMP/IBD, CSG or collision writer.
const Brush = preload("res://brush_geometry.gd")
const Picker = preload("res://private_box_cap_picker.gd")
const EdgeBevel = preload("res://private_box_cap_edge_bevel.gd")
const MultiClip = preload("res://private_box_multiclip.gd")
const SingleClip = preload("res://private_box_clip.gd")

const MIN_DEPTH := 0.05
const MAX_DEPTH := 0.40
const MIN_TRIAD_DETERMINANT := 0.05
const FACE_NORMAL_EPS := 0.001


static func _unique_normal(normals: Array, value: Vector3) -> void:
    for existing in normals:
        if (existing as Vector3).distance_to(value) < FACE_NORMAL_EPS:
            return
    normals.append(value)


static func cap_corner_vertices(raw: Variant, cap_index: int) -> Array:
    var spec: Dictionary = Picker._checked_spec(raw)
    if spec.is_empty():
        return []
    var cuts: Array = Picker._planes(spec)
    if cap_index < 0 or cap_index >= cuts.size():
        return []
    # Start with the real cap polygon boundary. The existing edge helper
    # excludes interior fan diagonals, nonmanifold and unowned edges.
    var edges: Array = EdgeBevel.cap_boundary_edges(spec, cap_index)
    if edges.is_empty():
        return []
    var vertices := {}
    for edge in edges:
        var neighbor: Vector3 = edge["adjacent"]
        for endpoint in [edge["a"], edge["b"]]:
            var point: Vector3 = endpoint
            var key := SingleClip._vertex_key(point)
            if not vertices.has(key):
                vertices[key] = {
                    "point": point, "edge_count": 0, "neighbor_normals": []}
            var row: Dictionary = vertices[key]
            if (row["point"] as Vector3).distance_to(point) > 0.00015:
                return []
            row["edge_count"] = int(row["edge_count"]) + 1
            var neighbors: Array = row["neighbor_normals"]
            _unique_normal(neighbors, neighbor)
            row["neighbor_normals"] = neighbors
            vertices[key] = row
    if vertices.size() != edges.size():
        return []
    var triangles: PackedVector3Array = Picker._vertices(spec)
    if triangles.is_empty():
        return []
    var keys: Array = vertices.keys()
    keys.sort()
    var result: Array = []
    for key in keys:
        var row: Dictionary = vertices[key]
        # Every genuine cap polygon corner has two incident perimeter
        # edges. Do not expose irregular/ambiguous boundary topology.
        if int(row["edge_count"]) != 2:
            return []
        var neighbors: Array = row["neighbor_normals"]
        if neighbors.size() != 2:
            continue
        var point: Vector3 = row["point"]
        var incident: Array = []
        # A fourth face can touch a vertex without sharing either cap
        # perimeter edge. Count ALL incident surface normals, not merely
        # the two neighbors inferred from cap edges.
        for i in range(0, triangles.size(), 3):
            var a: Vector3 = triangles[i]
            var b: Vector3 = triangles[i + 1]
            var c: Vector3 = triangles[i + 2]
            if (SingleClip._vertex_key(a) != key
                and SingleClip._vertex_key(b) != key
                and SingleClip._vertex_key(c) != key):
                continue
            var cross := (b - a).cross(c - a)
            if not cross.is_finite() or cross.length_squared() < 0.0000000001:
                return []
            _unique_normal(incident, cross.normalized())
        # Only simple trihedral vertices qualify. A 4+-face junction is
        # not a well-defined corner bisector for this authoring action.
        if incident.size() != 3:
            continue
        var cap: Dictionary = cuts[cap_index]
        var outward := Vector3(
            cap["normal"][0], cap["normal"][1], cap["normal"][2])
        if bool(cap["keep_positive"]):
            outward = -outward
        var first: Vector3 = neighbors[0]
        var second: Vector3 = neighbors[1]
        if (absf(outward.dot(first.cross(second)))
            < MIN_TRIAD_DETERMINANT):
            continue
        var unique_trihedral := true
        for wanted in [outward, first, second]:
            var found := false
            for face_normal in incident:
                if (face_normal as Vector3).distance_to(wanted) < FACE_NORMAL_EPS:
                    found = true
                    break
            if not found:
                unique_trihedral = false
                break
        if not unique_trihedral:
            continue
        result.append({
            "point": point,
            "cap_outward": outward,
            "adjacent_a": first,
            "adjacent_b": second,
        })
    return result


static func bevel_cap_corner(raw: Variant, cap_index: int,
                             corner_index: int, depth: float) -> Dictionary:
    if not is_finite(depth) or depth < MIN_DEPTH or depth > MAX_DEPTH:
        return {}
    var spec: Dictionary = Picker._checked_spec(raw)
    if spec.is_empty():
        return {}
    var planes: Array = Picker._planes(spec).duplicate(true)
    if planes.size() >= MultiClip.MAX_PLANES:
        return {}
    var corners: Array = cap_corner_vertices(spec, cap_index)
    if corner_index < 0 or corner_index >= corners.size():
        return {}
    var corner: Dictionary = corners[corner_index]
    var normal := (
        (corner["cap_outward"] as Vector3)
        + (corner["adjacent_a"] as Vector3)
        + (corner["adjacent_b"] as Vector3)).normalized()
    if not normal.is_finite():
        return {}
    # Remove a local tetrahedral corner along the outward trihedral
    # bisector. The old vertex remains the anchor of the cut distance.
    var distance := normal.dot(corner["point"]) - depth
    if not is_finite(distance) or absf(distance) > SingleClip.MAX_ABS_DISTANCE:
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
