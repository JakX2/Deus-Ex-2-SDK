extends RefCounted
## DX2Ed source-only brush primitives. Godot metres, Y-up.
## These meshes are NOT Unreal CSG brushes or compiled DX2 BSP.

const TYPES := ["Box", "Wall", "Floor", "Stairs", "Cylinder", "Cone", "Sphere", "Ramp"]
const MIN_SIZE := 0.05
const MAX_SIZE := 256.0
const MAX_STEPS := 64


static func default_spec(kind: String) -> Dictionary:
    match kind:
        "Box": return {"kind": "Box", "size": [2.0, 2.0, 2.0], "steps": 1}
        "Wall": return {"kind": "Wall", "size": [4.0, 3.0, 0.2], "steps": 1}
        "Floor": return {"kind": "Floor", "size": [4.0, 0.2, 4.0], "steps": 1}
        "Stairs": return {"kind": "Stairs", "size": [2.0, 2.0, 4.0], "steps": 8}
        "Cylinder": return {"kind": "Cylinder", "size": [2.0, 3.0, 2.0], "steps": 1}
        "Cone": return {"kind": "Cone", "size": [2.0, 3.0, 2.0], "steps": 1}
        "Sphere": return {"kind": "Sphere", "size": [2.0, 2.0, 2.0], "steps": 1}
        "Ramp": return {"kind": "Ramp", "size": [3.0, 1.5, 4.0], "steps": 1}
    return {}


static func validate(raw: Variant) -> Dictionary:
    if typeof(raw) != TYPE_DICTIONARY:
        return {}
    var kind: Variant = raw.get("kind", null)
    if typeof(kind) != TYPE_STRING or not TYPES.has(kind):
        return {}
    var size: Variant = raw.get("size", null)
    if typeof(size) != TYPE_ARRAY or size.size() != 3:
        return {}
    var verified: Array[float] = []
    for value in size:
        if typeof(value) not in [TYPE_INT, TYPE_FLOAT]:
            return {}
        var number := float(value)
        if is_nan(number) or is_inf(number) or number < MIN_SIZE or number > MAX_SIZE:
            return {}
        verified.append(number)
    var steps: Variant = raw.get("steps", 1)
    if typeof(steps) != TYPE_INT and typeof(steps) != TYPE_FLOAT:
        return {}
    var count := int(steps)
    if float(steps) != float(count) or count < 1 or count > MAX_STEPS:
        return {}
    if kind != "Stairs" and count != 1:
        return {}
    return {"kind": kind, "size": verified, "steps": count}


## Editor-only T3Ed-style *face resize* for axis-aligned draft Box/Wall/Floor.
## Growing a chosen face by delta enlarges one dimension and displaces its
## centre by half the delta along its local outward normal. The opposite face
## stays stationary even after the caller transforms the local offset through
## the existing preview node's basis (including rotation and scale).
## Faces: -X, +X, -Y, +Y, -Z, +Z.
## NO original BSP, CSG, collision or native GMP/IBD writes.
const FACE_LABELS := ["-X", "+X", "-Y", "+Y", "-Z", "+Z"]
const FACE_EDIT_KINDS := ["Box", "Wall", "Floor"]


static func face_resize(raw: Variant, face: int, delta: float) -> Dictionary:
    var spec := validate(raw)
    if (spec.is_empty() or not FACE_EDIT_KINDS.has(str(spec["kind"]))
        or face < 0 or face >= FACE_LABELS.size()
        or not is_finite(delta) or is_zero_approx(delta)
        or abs(delta) > MAX_SIZE):
        return {}
    var axis := face / 2
    var new_size: Array = spec["size"].duplicate()
    var resized := float(new_size[axis]) + delta
    if not is_finite(resized) or resized < MIN_SIZE or resized > MAX_SIZE:
        return {}
    new_size[axis] = resized
    spec["size"] = new_size
    # Every side uses "positive delta = outward".
    var direction := -1.0 if face % 2 == 0 else 1.0
    var local_offset := Vector3.ZERO
    local_offset[axis] = direction * delta * 0.5
    return {"spec": spec, "center_offset_local": local_offset,
            "face": FACE_LABELS[face]}



## Local-axis face hit from an actual viewport ray against ONE selected
## editor-only Box/Wall/Floor draft. Face order matches FACE_LABELS.
## Ray origin/direction are WORLD values, and the inverse transform handles
## preview rotation and scale. This is never a native BSP face picker.
static func pick_draft_face(
        raw: Variant, world_transform: Transform3D,
        ray_origin: Vector3, ray_direction: Vector3) -> Dictionary:
    var spec := validate(raw)
    if (spec.is_empty() or not FACE_EDIT_KINDS.has(str(spec["kind"]))
        or not world_transform.origin.is_finite()
        or not world_transform.basis.x.is_finite()
        or not world_transform.basis.y.is_finite()
        or not world_transform.basis.z.is_finite()
        or abs(world_transform.basis.determinant()) < 0.00000001
        or not ray_origin.is_finite() or not ray_direction.is_finite()
        or ray_direction.length_squared() < 0.0000000001):
        return {}
    var inverse := world_transform.affine_inverse()
    var origin := inverse * ray_origin
    var direction := inverse.basis * ray_direction
    if not origin.is_finite() or not direction.is_finite():
        return {}
    var entry := -INF
    var leave := INF
    var entry_face := -1
    var exit_face := -1
    for axis in range(3):
        var half_extent := float(spec["size"][axis]) * 0.5
        var o := origin[axis]
        var d := direction[axis]
        if abs(d) < 0.00000001:
            if o < -half_extent or o > half_extent:
                return {}
            continue
        var near_t := (-half_extent - o) / d
        var far_t := (half_extent - o) / d
        var near_face := axis * 2
        var far_face := axis * 2 + 1
        if near_t > far_t:
            var saved := near_t
            near_t = far_t
            far_t = saved
            near_face = axis * 2 + 1
            far_face = axis * 2
        if near_t > entry:
            entry = near_t
            entry_face = near_face
        if far_t < leave:
            leave = far_t
            exit_face = far_face
        if entry > leave:
            return {}
    if leave < 0.0:
        return {}
    # If the ray originates inside the box, its first visible face is EXIT.
    var t := entry if entry >= 0.0 else leave
    var face := entry_face if entry >= 0.0 else exit_face
    if face < 0 or face >= FACE_LABELS.size() or not is_finite(t):
        return {}
    var point := ray_origin + ray_direction * t
    if not point.is_finite():
        return {}
    return {"face_index": face, "label": FACE_LABELS[face],
            "world_point": point, "ray_parameter": t}



## Single preview face wire outline, eight line vertices, local draft space.
## Positive offset avoids depth fighting, does not modify exported brush
## geometry and never enters source actor/BSP data.
static func face_outline_edges(raw: Variant, face: int) -> PackedVector3Array:
    var spec := validate(raw)
    var edges := PackedVector3Array()
    if (spec.is_empty() or not FACE_EDIT_KINDS.has(str(spec["kind"]))
        or face < 0 or face >= FACE_LABELS.size()):
        return edges
    var x := float(spec["size"][0]) * 0.5
    var y := float(spec["size"][1]) * 0.5
    var z := float(spec["size"][2]) * 0.5
    var corners: Array[Vector3] = []
    var side := -1.0 if face % 2 == 0 else 1.0
    var extra := 0.0075
    match face / 2:
        0:
            var fx := side * (x + extra)
            corners = [
                Vector3(fx,-y,-z), Vector3(fx,y,-z),
                Vector3(fx,y,z), Vector3(fx,-y,z)]
        1:
            var fy := side * (y + extra)
            corners = [
                Vector3(-x,fy,-z), Vector3(x,fy,-z),
                Vector3(x,fy,z), Vector3(-x,fy,z)]
        2:
            var fz := side * (z + extra)
            corners = [
                Vector3(-x,-y,fz), Vector3(x,-y,fz),
                Vector3(x,y,fz), Vector3(-x,y,fz)]
    if corners.size() != 4:
        return edges
    for i in range(4):
        edges.append(corners[i])
        edges.append(corners[(i + 1) % 4])
    return edges


static func face_outline_mesh(raw: Variant, face: int) -> ImmediateMesh:
    var mesh := ImmediateMesh.new()
    var edges := face_outline_edges(raw, face)
    if edges.size() != 8:
        return mesh
    mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    for point in edges:
        mesh.surface_add_vertex(point)
    mesh.surface_end()
    return mesh



static func _triangle(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, normal: Vector3) -> void:
    st.set_normal(normal)
    st.set_uv(Vector2(0.0, 0.0))
    st.add_vertex(a)
    st.set_normal(normal)
    st.set_uv(Vector2(1.0, 0.0))
    st.add_vertex(b)
    st.set_normal(normal)
    st.set_uv(Vector2(1.0, 1.0))
    st.add_vertex(c)


static func _quad(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3) -> void:
    var normal := (b - a).cross(c - a).normalized()
    _triangle(st, a, b, c, normal)
    _triangle(st, a, c, d, normal)


static func _cuboid(st: SurfaceTool, low: Vector3, high: Vector3) -> void:
    var x0 := low.x
    var y0 := low.y
    var z0 := low.z
    var x1 := high.x
    var y1 := high.y
    var z1 := high.z
    # One winding convention for all six faces; no baked collision.
    _quad(st, Vector3(x0,y0,z1), Vector3(x1,y0,z1), Vector3(x1,y1,z1), Vector3(x0,y1,z1))
    _quad(st, Vector3(x1,y0,z0), Vector3(x0,y0,z0), Vector3(x0,y1,z0), Vector3(x1,y1,z0))
    _quad(st, Vector3(x0,y0,z0), Vector3(x0,y0,z1), Vector3(x0,y1,z1), Vector3(x0,y1,z0))
    _quad(st, Vector3(x1,y0,z1), Vector3(x1,y0,z0), Vector3(x1,y1,z0), Vector3(x1,y1,z1))
    _quad(st, Vector3(x0,y1,z1), Vector3(x1,y1,z1), Vector3(x1,y1,z0), Vector3(x0,y1,z0))
    _quad(st, Vector3(x0,y0,z0), Vector3(x1,y0,z0), Vector3(x1,y0,z1), Vector3(x0,y0,z1))


static func _cylinder(st: SurfaceTool, size: Vector3) -> void:
    # Editor-only elliptical cylinder with fixed bounded tessellation.
    # Closed caps and sides; no native CSG, collision, or UV-unwrapping claim.
    const SEGMENTS := 24
    var top_center := Vector3(0.0, size.y * 0.5, 0.0)
    var bottom_center := Vector3(0.0, -size.y * 0.5, 0.0)
    for i in range(SEGMENTS):
        var a := TAU * float(i) / float(SEGMENTS)
        var b := TAU * float(i + 1) / float(SEGMENTS)
        var low_a := Vector3(cos(a) * size.x * 0.5, -size.y * 0.5, sin(a) * size.z * 0.5)
        var low_b := Vector3(cos(b) * size.x * 0.5, -size.y * 0.5, sin(b) * size.z * 0.5)
        var high_a := Vector3(low_a.x, size.y * 0.5, low_a.z)
        var high_b := Vector3(low_b.x, size.y * 0.5, low_b.z)
        _triangle(st, top_center, high_b, high_a, Vector3.UP)
        _triangle(st, bottom_center, low_a, low_b, Vector3.DOWN)
        _quad(st, low_a, high_a, high_b, low_b)


static func _cone(st: SurfaceTool, size: Vector3) -> void:
    # Elliptical 24-sided cone with outward sides and closed bottom.
    const SEGMENTS := 24
    var tip := Vector3(0.0, size.y * 0.5, 0.0)
    var bottom := Vector3(0.0, -size.y * 0.5, 0.0)
    for i in range(SEGMENTS):
        var a := TAU * float(i) / float(SEGMENTS)
        var b := TAU * float(i + 1) / float(SEGMENTS)
        var p := Vector3(cos(a) * size.x * 0.5, bottom.y, sin(a) * size.z * 0.5)
        var q := Vector3(cos(b) * size.x * 0.5, bottom.y, sin(b) * size.z * 0.5)
        var normal := (tip - p).cross(q - p).normalized()
        _triangle(st, p, tip, q, normal)
        _triangle(st, bottom, p, q, Vector3.DOWN)


static func _sphere(st: SurfaceTool, size: Vector3) -> void:
    # Closed latitude/longitude ellipsoid with fixed, bounded tessellation.
    const SEGMENTS := 24
    const RINGS := 12
    for ring in range(RINGS):
        var t0 := PI * float(ring) / float(RINGS)
        var t1 := PI * float(ring + 1) / float(RINGS)
        for i in range(SEGMENTS):
            var a := TAU * float(i) / float(SEGMENTS)
            var b := TAU * float(i + 1) / float(SEGMENTS)
            var p := Vector3(sin(t0) * cos(a), cos(t0), sin(t0) * sin(a))
            var q := Vector3(sin(t0) * cos(b), cos(t0), sin(t0) * sin(b))
            var r := Vector3(sin(t1) * cos(a), cos(t1), sin(t1) * sin(a))
            var u := Vector3(sin(t1) * cos(b), cos(t1), sin(t1) * sin(b))
            var scale := size * 0.5
            if ring > 0:
                _triangle(st, p * scale, q * scale, r * scale, (q - p).cross(r - p).normalized())
            if ring < RINGS - 1:
                _triangle(st, q * scale, u * scale, r * scale, (u - q).cross(r - q).normalized())


static func _ramp(st: SurfaceTool, size: Vector3) -> void:
    # Closed triangular prism, rising from -Z toward +Z. Preview only.
    var x0 := -size.x * 0.5
    var x1 := size.x * 0.5
    var y0 := -size.y * 0.5
    var y1 := size.y * 0.5
    var z0 := -size.z * 0.5
    var z1 := size.z * 0.5
    var a := Vector3(x0, y0, z0)
    var b := Vector3(x0, y0, z1)
    var c := Vector3(x0, y1, z1)
    var d := Vector3(x1, y0, z0)
    var e := Vector3(x1, y0, z1)
    var f := Vector3(x1, y1, z1)
    _triangle(st, a, b, c, Vector3.LEFT)
    _triangle(st, d, f, e, Vector3.RIGHT)
    _quad(st, a, d, e, b)
    _quad(st, b, e, f, c)
    _quad(st, a, c, f, d)


static func build_mesh(raw: Variant) -> Mesh:
    var spec := validate(raw)
    if spec.is_empty():
        return null
    var size := Vector3(spec["size"][0], spec["size"][1], spec["size"][2])
    var st := SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    if spec["kind"] == "Ramp":
        _ramp(st, size)
    elif spec["kind"] == "Cone":
        _cone(st, size)
    elif spec["kind"] == "Sphere":
        _sphere(st, size)
    elif spec["kind"] == "Cylinder":
        _cylinder(st, size)
    elif spec["kind"] == "Stairs":
        # Rise in +Y, walk in -Z, with complete closed treads.
        # Temporary overlapping step blocks are visual, not CSG union.
        var count: int = spec["steps"]
        var step_height := size.y / float(count)
        var step_depth := size.z / float(count)
        for i in range(count):
            var bottom := Vector3(-size.x * 0.5, 0.0, -size.z * 0.5 + i * step_depth)
            var top := Vector3(size.x * 0.5, step_height * float(i + 1), size.z * 0.5)
            _cuboid(st, bottom, top)
    else:
        _cuboid(st, -size * 0.5, size * 0.5)
    return st.commit()
