extends RefCounted
## DX2Ed v0.83: up to EIGHT successive 3D planes on one private Box.
## This creates a capped convex Godot preview, NEVER native DX2 BSP,
## CSG, Havok/MOPP collision, or an original GMP/IBD modification.

const SingleClip = preload("res://private_box_clip.gd")
const MAX_PLANES := 8
# A convex clipping pass can introduce at most one new planar face.
# Eight corner cuts yield the 14-face truncated cube in the regression.
const MAX_FACES := 6 + MAX_PLANES
const MAX_CAP_VERTICES := 16
const EPSILON := 0.00001
const ON_PLANE_EPSILON := 0.00008
const MIN_CUT_CLEARANCE := 0.05
const MIN_VOLUME_FRACTION := 0.00001


static func validate_planes(raw: Variant, size: Vector3) -> Array:
    if (typeof(raw) != TYPE_ARRAY or raw.is_empty()
        or raw.size() > MAX_PLANES or not size.is_finite()):
        return []
    var result: Array = []
    for value in raw:
        var checked: Dictionary = SingleClip.validate_clip(value, size)
        if checked.is_empty():
            return []
        result.append(checked)
    return result


static func _closed_triangles(faces: Array) -> PackedVector3Array:
    var triangles := PackedVector3Array()
    if faces.is_empty() or faces.size() > MAX_FACES:
        return triangles
    for face in faces:
        if typeof(face) != TYPE_ARRAY or face.size() < 3:
            return PackedVector3Array()
        # A triangle fan must not cross a degenerate collinear first corner.
        # The final edge and signed-volume preflight will reject malformed
        # or nonmanifold triangulations, including T-junctions.
        for i in range(1, face.size() - 1):
            var a: Vector3 = face[0]
            var b: Vector3 = face[i]
            var c: Vector3 = face[i + 1]
            if (not a.is_finite() or not b.is_finite()
                or not c.is_finite()
                or (b - a).cross(c - a).length_squared() < 0.0000000001):
                return PackedVector3Array()
            triangles.append(a)
            triangles.append(b)
            triangles.append(c)
    return triangles


static func _signed_volume(triangles: PackedVector3Array) -> float:
    var volume := 0.0
    for i in range(0, triangles.size(), 3):
        volume += triangles[i].dot(
            triangles[i+1].cross(triangles[i+2])) / 6.0
    return volume


static func _cut_cap(clipped_faces: Array, outward: Vector3,
                     offset: float) -> Array:
    var cap: Array = []
    for face in clipped_faces:
        for value in face:
            var point: Vector3 = value
            if absf(outward.dot(point) - offset) <= ON_PLANE_EPSILON:
                SingleClip._unique_point(cap, point)
    if cap.size() < 3 or cap.size() > MAX_CAP_VERTICES:
        return []
    var center := Vector3.ZERO
    for value in cap:
        var point: Vector3 = value
        center += point
    center /= float(cap.size())
    var helper := Vector3.UP if absf(outward.y) < 0.85 else Vector3.RIGHT
    var u := helper.cross(outward).normalized()
    var v := outward.cross(u).normalized()
    cap.sort_custom(func(a, b):
        var da: Vector3 = a - center
        var db: Vector3 = b - center
        return atan2(da.dot(v), da.dot(u)) < atan2(db.dot(v), db.dot(u)))
    return cap


static func _clip_current_faces(faces: Array, outward: Vector3,
                                offset: float) -> Array:
    if (faces.is_empty() or faces.size() > MAX_FACES
        or not outward.is_finite() or not is_finite(offset)):
        return []
    var nearest := INF
    var furthest := -INF
    for face in faces:
        for value in face:
            var point: Vector3 = value
            var signed := outward.dot(point) - offset
            nearest = minf(nearest, signed)
            furthest = maxf(furthest, signed)
    # The new plane must genuinely reduce THIS intermediate convex hull,
    # rather than being a no-op relative to an earlier cut or deleting it.
    if nearest >= -MIN_CUT_CLEARANCE or furthest <= MIN_CUT_CLEARANCE:
        return []
    var new_faces: Array = []
    for face in faces:
        var clipped := SingleClip._face_in_halfspace(face, outward, offset)
        if clipped.size() >= 3:
            new_faces.append(clipped)
    var cap := _cut_cap(new_faces, outward, offset)
    if cap.is_empty() or new_faces.size() + 1 > MAX_FACES:
        return []
    new_faces.append(cap)
    return new_faces


static func build_mesh(size: Vector3, raw: Variant) -> ArrayMesh:
    var planes := validate_planes(raw, size)
    if planes.is_empty():
        return null
    var original_volume := size.x * size.y * size.z
    if not is_finite(original_volume) or original_volume <= 0.0:
        return null
    var previous_volume := original_volume
    var faces: Array = SingleClip._faces(size)
    for plane in planes:
        var outward := Vector3(
            plane["normal"][0], plane["normal"][1], plane["normal"][2])
        var offset := float(plane["distance"])
        if bool(plane["keep_positive"]):
            outward = -outward
            offset = -offset
        faces = _clip_current_faces(faces, outward, offset)
        if faces.is_empty():
            return null
        var triangles := _closed_triangles(faces)
        if (triangles.is_empty()
            or not SingleClip._valid_closed_soup(triangles, original_volume)):
            return null
        var volume := _signed_volume(triangles)
        var minimum := maxf(0.0001, original_volume * MIN_VOLUME_FRACTION)
        if (not is_finite(volume) or volume <= minimum
            or volume >= previous_volume - minimum):
            return null
        previous_volume = volume
    var final_triangles := _closed_triangles(faces)
    if final_triangles.is_empty():
        return null
    var st := SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    for i in range(0, final_triangles.size(), 3):
        var a := final_triangles[i]
        var b := final_triangles[i+1]
        var c := final_triangles[i+2]
        var normal := (b-a).cross(c-a).normalized()
        st.set_normal(normal)
        st.set_uv(Vector2(0.0, 0.0))
        st.add_vertex(a)
        st.set_normal(normal)
        st.set_uv(Vector2(1.0, 0.0))
        st.add_vertex(b)
        st.set_normal(normal)
        st.set_uv(Vector2(0.0, 1.0))
        st.add_vertex(c)
    return st.commit()
