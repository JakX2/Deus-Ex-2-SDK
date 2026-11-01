extends RefCounted
## DX2Ed source-only brush primitives. Godot metres, Y-up.
## These meshes are NOT Unreal CSG brushes or compiled DX2 BSP.

const TYPES := ["Box", "Wall", "Floor", "Stairs"]
const MIN_SIZE := 0.05
const MAX_SIZE := 256.0
const MAX_STEPS := 64


static func default_spec(kind: String) -> Dictionary:
    match kind:
        "Box": return {"kind": "Box", "size": [2.0, 2.0, 2.0], "steps": 1}
        "Wall": return {"kind": "Wall", "size": [4.0, 3.0, 0.2], "steps": 1}
        "Floor": return {"kind": "Floor", "size": [4.0, 0.2, 4.0], "steps": 1}
        "Stairs": return {"kind": "Stairs", "size": [2.0, 2.0, 4.0], "steps": 8}
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


static func build_mesh(raw: Variant) -> Mesh:
    var spec := validate(raw)
    if spec.is_empty():
        return null
    var size := Vector3(spec["size"][0], spec["size"][1], spec["size"][2])
    var st := SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    if spec["kind"] == "Stairs":
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
