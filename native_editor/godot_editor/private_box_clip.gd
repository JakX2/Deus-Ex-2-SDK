extends RefCounted
## DX2Ed v0.80: ONE private Box preview cut by ONE arbitrary 3D local plane.
## A capped convex mesh, never engine-native BSP, Havok or GMP geometry.
## All operations are source-independent. No original game bytes enter here.

const MIN_CLEARANCE := 0.05
const EPSILON := 0.00001
const MAX_ABS_DISTANCE := 256.0
# Strict upper bound for a triangulated convex polyhedron with 6 original
# Box faces plus 8 clip caps: E <= 3F-6, triangles = 2E-2F <= 4F-12 = 44.
const MAX_TRIANGLES := 44


static func validate_clip(raw: Variant, size: Vector3) -> Dictionary:
    if (typeof(raw) != TYPE_DICTIONARY or not size.is_finite()
        or size.x < 0.05 or size.y < 0.05 or size.z < 0.05):
        return {}
    var components: Variant = raw.get("normal", null)
    var distance: Variant = raw.get("distance", null)
    var keep: Variant = raw.get("keep_positive", null)
    if (typeof(components) != TYPE_ARRAY or components.size() != 3
        or typeof(distance) not in [TYPE_FLOAT, TYPE_INT] or typeof(keep) != TYPE_BOOL):
        return {}
    var normal := Vector3.ZERO
    for i in range(3):
        if typeof(components[i]) not in [TYPE_FLOAT, TYPE_INT]:
            return {}
        normal[i] = float(components[i])
    var offset := float(distance)
    if (not normal.is_finite() or not is_finite(offset)
        or absf(offset) > MAX_ABS_DISTANCE
        or absf(normal.length_squared() - 1.0) > 0.0001):
        return {}
    normal = normal.normalized()
    var signed_min := INF
    var signed_max := -INF
    for x in [-1.0, 1.0]:
        for y in [-1.0, 1.0]:
            for z in [-1.0, 1.0]:
                var point := Vector3(x*size.x*0.5, y*size.y*0.5, z*size.z*0.5)
                var signed := normal.dot(point) - offset
                signed_min = minf(signed_min, signed)
                signed_max = maxf(signed_max, signed)
    # No-op, empty or numerically near-tangent cuts are not authoring edits.
    if signed_min >= -MIN_CLEARANCE or signed_max <= MIN_CLEARANCE:
        return {}
    return {
        "normal": [normal.x, normal.y, normal.z],
        "distance": offset,
        "keep_positive": keep,
    }


static func _faces(size: Vector3) -> Array:
    var x := size.x*0.5
    var y := size.y*0.5
    var z := size.z*0.5
    # All six polygons use outward winding.
    return [
        [Vector3(-x,-y,+z), Vector3(+x,-y,+z), Vector3(+x,+y,+z), Vector3(-x,+y,+z)],
        [Vector3(+x,-y,-z), Vector3(-x,-y,-z), Vector3(-x,+y,-z), Vector3(+x,+y,-z)],
        [Vector3(-x,-y,-z), Vector3(-x,-y,+z), Vector3(-x,+y,+z), Vector3(-x,+y,-z)],
        [Vector3(+x,-y,+z), Vector3(+x,-y,-z), Vector3(+x,+y,-z), Vector3(+x,+y,+z)],
        [Vector3(-x,+y,+z), Vector3(+x,+y,+z), Vector3(+x,+y,-z), Vector3(-x,+y,-z)],
        [Vector3(-x,-y,-z), Vector3(+x,-y,-z), Vector3(+x,-y,+z), Vector3(-x,-y,+z)],
    ]


static func _face_in_halfspace(face: Array, normal: Vector3,
                               offset: float) -> Array:
    var clipped: Array = []
    var previous: Vector3 = face.back()
    var previous_dist := normal.dot(previous) - offset
    for current in face:
        var current_dist := normal.dot(current) - offset
        var prev_inside := previous_dist <= EPSILON
        var curr_inside := current_dist <= EPSILON
        if prev_inside != curr_inside:
            var denominator := current_dist - previous_dist
            if absf(denominator) <= EPSILON:
                return []
            var t := clampf(-previous_dist / denominator, 0.0, 1.0)
            var hit := previous.lerp(current, t)
            hit -= normal*(normal.dot(hit)-offset)
            if clipped.is_empty() or clipped.back().distance_to(hit) > EPSILON:
                clipped.append(hit)
        if curr_inside:
            if clipped.is_empty() or clipped.back().distance_to(current) > EPSILON:
                clipped.append(current)
        previous = current
        previous_dist = current_dist
    if clipped.size() >= 2 and clipped.front().distance_to(clipped.back()) <= EPSILON:
        clipped.pop_back()
    return clipped


static func _unique_point(points: Array, candidate: Vector3) -> void:
    for point in points:
        if point.distance_to(candidate) <= EPSILON:
            return
    points.append(candidate)


static func _cut_cap(size: Vector3, normal: Vector3, offset: float) -> Array:
    var corners: Array = []
    for x in [-1.0, 1.0]:
        for y in [-1.0, 1.0]:
            for z in [-1.0, 1.0]:
                corners.append(Vector3(x*size.x*0.5, y*size.y*0.5, z*size.z*0.5))
    var cap: Array = []
    # Cube edges: one coordinate differs, two coordinates identical.
    for i in range(corners.size()):
        var a: Vector3 = corners[i]
        var da := normal.dot(a) - offset
        if absf(da) <= EPSILON:
            _unique_point(cap, a)
        for j in range(i+1, corners.size()):
            if (i ^ j) not in [1, 2, 4]:
                continue
            var b: Vector3 = corners[j]
            var db := normal.dot(b) - offset
            if da * db < -EPSILON * EPSILON:
                var point := a.lerp(b, clampf(-da/(db-da), 0.0, 1.0))
                point -= normal*(normal.dot(point)-offset)
                _unique_point(cap, point)
    if cap.size() < 3 or cap.size() > 6:
        return []
    var center := Vector3.ZERO
    for point in cap:
        center += point
    center /= float(cap.size())
    var helper := Vector3.UP if absf(normal.y) < 0.85 else Vector3.RIGHT
    var u := helper.cross(normal).normalized()
    var v := normal.cross(u).normalized()
    cap.sort_custom(func(a, b):
        var da: Vector3 = a - center
        var db: Vector3 = b - center
        return atan2(da.dot(v), da.dot(u)) < atan2(db.dot(v), db.dot(u)))
    return cap


static func _vertex_key(point: Vector3) -> String:
    return "%d:%d:%d" % [
        roundi(point.x*10000.0),
        roundi(point.y*10000.0),
        roundi(point.z*10000.0),
    ]


static func _valid_closed_soup(vertices: PackedVector3Array,
                               original_volume: float) -> bool:
    if (vertices.size() < 18 or vertices.size()%3 != 0
        or vertices.size()/3 > MAX_TRIANGLES):
        return false
    var edges := {}
    var volume := 0.0
    for at in range(0, vertices.size(), 3):
        var a := vertices[at]
        var b := vertices[at+1]
        var c := vertices[at+2]
        if (not a.is_finite() or not b.is_finite() or not c.is_finite()
            or (b-a).cross(c-a).length_squared() < 0.0000000001):
            return false
        volume += a.dot(b.cross(c))/6.0
        for edge in [[a,b],[b,c],[c,a]]:
            var first := _vertex_key(edge[0])
            var second := _vertex_key(edge[1])
            if first == second:
                return false
            var key := first+"|"+second if first < second else second+"|"+first
            edges[key] = int(edges.get(key, 0)) + 1
    # Exact triangular edge pairing is a conservative manifold gate.
    # Refuse questionable cut-through-corner or T-junction geometry.
    for count in edges.values():
        if count != 2:
            return false
    var min_volume := maxf(0.0001, original_volume*0.00001)
    return volume > min_volume and volume < original_volume - min_volume


static func build_mesh(size: Vector3, raw: Variant) -> ArrayMesh:
    var clip := validate_clip(raw, size)
    if clip.is_empty():
        return null
    var outward := Vector3(
        clip["normal"][0], clip["normal"][1], clip["normal"][2])
    var cut_offset := float(clip["distance"])
    if bool(clip["keep_positive"]):
        outward = -outward
        cut_offset = -cut_offset
    var triangles := PackedVector3Array()
    for face in _faces(size):
        var clipped := _face_in_halfspace(face, outward, cut_offset)
        if clipped.size() < 3:
            continue
        for index in range(1, clipped.size()-1):
            triangles.append(clipped[0])
            triangles.append(clipped[index])
            triangles.append(clipped[index+1])
    var cap := _cut_cap(size, outward, cut_offset)
    if cap.is_empty():
        return null
    for index in range(1, cap.size()-1):
        triangles.append(cap[0])
        triangles.append(cap[index])
        triangles.append(cap[index+1])
    if not _valid_closed_soup(triangles, size.x*size.y*size.z):
        return null
    var st := SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    for index in range(0, triangles.size(), 3):
        var a := triangles[index]
        var b := triangles[index+1]
        var c := triangles[index+2]
        var normal := (b-a).cross(c-a).normalized()
        st.set_normal(normal)
        st.set_uv(Vector2(0, 0))
        st.add_vertex(a)
        st.set_normal(normal)
        st.set_uv(Vector2(1, 0))
        st.add_vertex(b)
        st.set_normal(normal)
        st.set_uv(Vector2(0, 1))
        st.add_vertex(c)
    return st.commit()
