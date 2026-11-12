extends RefCounted
## DX2Ed v0.86: inspect one *visible* authored convex Box clipping cap.
## No ray may select original BSP, imported actors or a hidden cap behind
## another surface. This helper never writes GMP/IBD or native collision.

const Brush = preload("res://brush_geometry.gd")
const SingleClip = preload("res://private_box_clip.gd")
const PLANE_TOLERANCE := 0.00012
const RAY_EDGE_TOLERANCE := 0.000001
const RAY_TIE_TOLERANCE := 0.0001
const HIGHLIGHT_OFFSET := 0.0075


static func _checked_spec(raw: Variant) -> Dictionary:
    var spec: Dictionary = Brush.validate(raw)
    if (spec.is_empty() or spec.get("kind", "") != "Box"
        or not spec.has("clip_plane") and not spec.has("clip_planes")):
        return {}
    return spec


static func _planes(spec: Dictionary) -> Array:
    if spec.has("clip_planes"):
        return spec["clip_planes"]
    return [spec["clip_plane"]]


static func _vertices(spec: Dictionary) -> PackedVector3Array:
    var mesh: Mesh = Brush.build_mesh(spec)
    if mesh == null or mesh.get_surface_count() != 1:
        return PackedVector3Array()
    var arrays: Array = mesh.surface_get_arrays(0)
    if arrays.size() <= Mesh.ARRAY_VERTEX:
        return PackedVector3Array()
    var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
    if vertices.is_empty() or vertices.size() % 3 != 0:
        return PackedVector3Array()
    return vertices


static func _cap_index(a: Vector3, b: Vector3, c: Vector3,
                        planes: Array) -> int:
    var matched := -1
    for index in range(planes.size()):
        var p: Dictionary = planes[index]
        var n := Vector3(p["normal"][0], p["normal"][1], p["normal"][2])
        var distance := float(p["distance"])
        if (absf(n.dot(a) - distance) <= PLANE_TOLERANCE
            and absf(n.dot(b) - distance) <= PLANE_TOLERANCE
            and absf(n.dot(c) - distance) <= PLANE_TOLERANCE):
            # Ambiguous coplanar metadata cannot identify one unique cap.
            if matched != -1:
                return -1
            matched = index
    return matched


static func _ray_triangle(origin: Vector3, direction: Vector3,
                          a: Vector3, b: Vector3, c: Vector3) -> float:
    # Double-sided Moller-Trumbore; do not select rays behind their origin.
    var edge_a := b - a
    var edge_b := c - a
    var p := direction.cross(edge_b)
    var determinant := edge_a.dot(p)
    if absf(determinant) <= 0.0000000001:
        return INF
    var inverse := 1.0 / determinant
    var from_a := origin - a
    var u := from_a.dot(p) * inverse
    if u < -RAY_EDGE_TOLERANCE or u > 1.0 + RAY_EDGE_TOLERANCE:
        return INF
    var q := from_a.cross(edge_a)
    var v := direction.dot(q) * inverse
    if v < -RAY_EDGE_TOLERANCE or u + v > 1.0 + RAY_EDGE_TOLERANCE:
        return INF
    var t := edge_b.dot(q) * inverse
    return t if is_finite(t) and t > 0.000001 else INF


static func pick_cap(raw: Variant, world: Transform3D,
                     world_origin: Vector3, world_direction: Vector3) -> Dictionary:
    var spec := _checked_spec(raw)
    if (spec.is_empty() or not world.origin.is_finite()
        or not world.basis.x.is_finite() or not world.basis.y.is_finite()
        or not world.basis.z.is_finite()
        or absf(world.basis.determinant()) < 0.00000001
        or not world_origin.is_finite() or not world_direction.is_finite()
        or world_direction.length_squared() < 0.0000000001):
        return {}
    var inverse := world.affine_inverse()
    var origin := inverse * world_origin
    var direction := inverse.basis * world_direction
    if not origin.is_finite() or not direction.is_finite():
        return {}
    var vertices := _vertices(spec)
    if vertices.is_empty():
        return {}
    var planes := _planes(spec)
    var nearest := INF
    var cap_index := -1
    var ambiguous := false
    # Search all front-facing *and* back-facing preview triangles. The
    # nearest ray hit wins, even if it is an ordinary Box face: no click
    # can select a cap hidden behind another surviving surface.
    for i in range(0, vertices.size(), 3):
        var a: Vector3 = vertices[i]
        var b: Vector3 = vertices[i+1]
        var c: Vector3 = vertices[i+2]
        var distance := _ray_triangle(origin, direction, a, b, c)
        if not is_finite(distance):
            continue
        var triangle_cap := _cap_index(a, b, c, planes)
        if distance < nearest - RAY_TIE_TOLERANCE:
            nearest = distance
            cap_index = triangle_cap
            ambiguous = false
        elif absf(distance - nearest) <= RAY_TIE_TOLERANCE:
            # Shared fan diagonals are fine; a cap/source edge or two
            # different caps meeting at one point is not a stable pick.
            if triangle_cap != cap_index:
                ambiguous = true
    if cap_index < 0 or ambiguous or not is_finite(nearest):
        return {}
    var point := world_origin + world_direction * nearest
    if not point.is_finite():
        return {}
    return {
        "plane_index": cap_index,
        "world_point": point,
        "ray_parameter": nearest,
    }


static func _key(point: Vector3) -> String:
    return SingleClip._vertex_key(point)


static func cap_outline_edges(raw: Variant, plane_index: int) -> PackedVector3Array:
    var result := PackedVector3Array()
    var spec := _checked_spec(raw)
    if spec.is_empty():
        return result
    var planes := _planes(spec)
    if plane_index < 0 or plane_index >= planes.size():
        return result
    var vertices := _vertices(spec)
    if vertices.is_empty():
        return result
    var edges := {}
    for i in range(0, vertices.size(), 3):
        var a: Vector3 = vertices[i]
        var b: Vector3 = vertices[i+1]
        var c: Vector3 = vertices[i+2]
        if _cap_index(a, b, c, planes) != plane_index:
            continue
        for pair in [[a,b], [b,c], [c,a]]:
            var first: Vector3 = pair[0]
            var second: Vector3 = pair[1]
            var ka := _key(first)
            var kb := _key(second)
            if ka == kb:
                return PackedVector3Array()
            var edge_key := ka + "|" + kb if ka < kb else kb + "|" + ka
            if edges.has(edge_key):
                var existing: Dictionary = edges[edge_key]
                existing["count"] = int(existing["count"]) + 1
                edges[edge_key] = existing
            else:
                edges[edge_key] = {
                    "count": 1, "a": first, "b": second,
                    "ka": ka, "kb": kb}
    var perimeter := []
    var degree := {}
    for entry in edges.values():
        if int(entry["count"]) == 1:
            perimeter.append(entry)
            degree[entry["ka"]] = int(degree.get(entry["ka"], 0)) + 1
            degree[entry["kb"]] = int(degree.get(entry["kb"], 0)) + 1
        elif int(entry["count"]) != 2:
            return PackedVector3Array()
    if (perimeter.size() < 3 or perimeter.size() > 16
        or degree.size() != perimeter.size()):
        return PackedVector3Array()
    for value in degree.values():
        if int(value) != 2:
            return PackedVector3Array()
    var plane: Dictionary = planes[plane_index]
    var outward := Vector3(
        plane["normal"][0], plane["normal"][1], plane["normal"][2])
    if bool(plane["keep_positive"]):
        outward = -outward
    for edge in perimeter:
        result.append(edge["a"] + outward * HIGHLIGHT_OFFSET)
        result.append(edge["b"] + outward * HIGHLIGHT_OFFSET)
    return result


static func cap_outline_mesh(raw: Variant, plane_index: int) -> ImmediateMesh:
    var mesh := ImmediateMesh.new()
    var edges := cap_outline_edges(raw, plane_index)
    if edges.size() < 6 or edges.size() % 2 != 0:
        return mesh
    mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    for point in edges:
        mesh.surface_add_vertex(point)
    mesh.surface_end()
    return mesh
