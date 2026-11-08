extends RefCounted
## DX2Ed custom planar polygon footprint -> extruded closed preview mesh.
## Each vertex is local normalized X/Z in [-1, +1]; the existing brush
## Size X / Y / Z controls scale width, height and depth in Godot metres.
## This is PRIVATE editor draft geometry, NOT native DX2 BSP/CSG.
const MAX_VERTICES := 32
const MIN_VERTICES := 3
const MIN_EDGE_LENGTH := 0.0001
const MIN_AREA := 0.005


static func default_outline() -> Array:
    # An L-shaped six-corner footprint invites real editing, not another box.
    return [[-1.0,-1.0], [1.0,-1.0], [1.0,0.0],
            [0.0,0.0], [0.0,1.0], [-1.0,1.0]]


static func _cross(a: Vector2, b: Vector2) -> float:
    return a.x * b.y - a.y * b.x


static func _on_segment(a: Vector2, b: Vector2, p: Vector2) -> bool:
    return (abs(_cross(b - a, p - a)) <= MIN_EDGE_LENGTH
        and p.x >= minf(a.x,b.x) - MIN_EDGE_LENGTH
        and p.x <= maxf(a.x,b.x) + MIN_EDGE_LENGTH
        and p.y >= minf(a.y,b.y) - MIN_EDGE_LENGTH
        and p.y <= maxf(a.y,b.y) + MIN_EDGE_LENGTH)


static func _segments_intersect(a: Vector2, b: Vector2,
                                c: Vector2, d: Vector2) -> bool:
    var ab_c := _cross(b-a,c-a)
    var ab_d := _cross(b-a,d-a)
    var cd_a := _cross(d-c,a-c)
    var cd_b := _cross(d-c,b-c)
    if ((ab_c > MIN_EDGE_LENGTH and ab_d < -MIN_EDGE_LENGTH
        or ab_c < -MIN_EDGE_LENGTH and ab_d > MIN_EDGE_LENGTH)
        and (cd_a > MIN_EDGE_LENGTH and cd_b < -MIN_EDGE_LENGTH
        or cd_a < -MIN_EDGE_LENGTH and cd_b > MIN_EDGE_LENGTH)):
        return true
    for point in [c,d]:
        if _on_segment(a,b,point):
            return true
    for point in [a,b]:
        if _on_segment(c,d,point):
            return true
    return false


static func signed_area(points: PackedVector2Array) -> float:
    var area := 0.0
    for i in range(points.size()):
        area += _cross(points[i], points[(i+1) % points.size()])
    return area * 0.5


static func validate_outline(raw: Variant) -> Array:
    if typeof(raw) != TYPE_ARRAY or raw.size() < MIN_VERTICES or raw.size() > MAX_VERTICES:
        return []
    var points := PackedVector2Array()
    var rows: Array = []
    for entry in raw:
        if typeof(entry) != TYPE_ARRAY or entry.size() != 2:
            return []
        for v in entry:
            if typeof(v) not in [TYPE_FLOAT, TYPE_INT]:
                return []
            if not is_finite(float(v)) or abs(float(v)) > 1.0:
                return []
        var v := Vector2(float(entry[0]),float(entry[1]))
        points.append(v)
        rows.append([v.x,v.y])
    var n := points.size()
    for i in range(n):
        var a := points[i]
        var b := points[(i+1) % n]
        if a.distance_squared_to(b) < MIN_EDGE_LENGTH * MIN_EDGE_LENGTH:
            return []
        for j in range(i+1,n):
            # Neighbouring edges share one endpoint by design.
            if j == i+1 or (i == 0 and j == n-1):
                continue
            if _segments_intersect(a,b,points[j],points[(j+1) % n]):
                return []
    if abs(signed_area(points)) < MIN_AREA:
        return []
    var triangles := Geometry2D.triangulate_polygon(points)
    if triangles.size() != (n-2)*3:
        return []
    return rows


static func with_moved_vertex(raw: Variant, index: int,
                              axis: int, value: float) -> Array:
    var rows := validate_outline(raw)
    if rows.is_empty() or index < 0 or index >= rows.size():
        return []
    if axis < 0 or axis > 1 or not is_finite(value) or abs(value) > 1.0:
        return []
    rows[index][axis] = value
    return validate_outline(rows)


static func with_inserted_vertex(raw: Variant, edge: int) -> Array:
    var rows := validate_outline(raw)
    if rows.is_empty() or rows.size() >= MAX_VERTICES
        or edge < 0 or edge >= rows.size():
        return []
    var b := rows[(edge+1) % rows.size()]
    var a := rows[edge]
    # Add an editable corner slightly INSIDE the original edge; this
    # avoids a degenerate collinear triangle during initial triangulation.
    # A narrow/concave polygon can reject it rather than introduce a cut.
    var p := Vector2(float(a[0]),float(a[1]))
    var q := Vector2(float(b[0]),float(b[1]))
    var edge_vector := q - p
    if edge_vector.length_squared() < MIN_EDGE_LENGTH * MIN_EDGE_LENGTH:
        return []
    var packed := PackedVector2Array()
    for row in rows:
        packed.append(Vector2(float(row[0]),float(row[1])))
    var inward := Vector2(-edge_vector.y,edge_vector.x).normalized()
    if signed_area(packed) < 0.0:
        inward = -inward
    var point := (p+q)*0.5 + inward * minf(0.08, edge_vector.length()*0.125)
    rows.insert(edge+1, [point.x,point.y])
    return validate_outline(rows)


static func with_deleted_vertex(raw: Variant, index: int) -> Array:
    var rows := validate_outline(raw)
    if rows.size() <= MIN_VERTICES or index < 0 or index >= rows.size():
        return []
    rows.remove_at(index)
    return validate_outline(rows)


static func build_mesh(size: Vector3, raw_outline: Variant) -> Mesh:
    if not size.is_finite() or size.x <= 0.0 or size.y <= 0.0 or size.z <= 0.0:
        return null
    var rows := validate_outline(raw_outline)
    if rows.is_empty():
        return null
    var points := PackedVector2Array()
    for row in rows:
        points.append(Vector2(float(row[0]),float(row[1])))
    var triangles := Geometry2D.triangulate_polygon(points)
    if triangles.size() != (points.size()-2) * 3:
        return null
    var st := SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    var half := size * 0.5
    for i in range(0, triangles.size(), 3):
        var top: Array[Vector3] = []
        var bottom: Array[Vector3] = []
        for k in range(3):
            var p := points[triangles[i+k]]
            top.append(Vector3(p.x * half.x, half.y, p.y * half.z))
            bottom.append(Vector3(p.x * half.x, -half.y, p.y * half.z))
        var a: Vector3 = top[0]
        var b: Vector3 = top[1]
        var c: Vector3 = top[2]
        # In XZ coordinates, a CCW triangle faces down (-Y). Explicitly
        # correct every ear to have a top +Y and lower -Y outward winding.
        if (b-a).cross(c-a).y < 0.0:
            var saved := b
            b = c
            c = saved
        _triangle(st,a,b,c,Vector3.UP)
        _triangle(st,Vector3(a.x,-half.y,a.z),
                  Vector3(c.x,-half.y,c.z),
                  Vector3(b.x,-half.y,b.z),Vector3.DOWN)
    var clockwise := signed_area(points) < 0.0
    for i in range(points.size()):
        var p := points[i]
        var q := points[(i+1) % points.size()]
        var lo_a := Vector3(p.x * half.x,-half.y,p.y * half.z)
        var lo_b := Vector3(q.x * half.x,-half.y,q.y * half.z)
        var hi_a := Vector3(lo_a.x,half.y,lo_a.z)
        var hi_b := Vector3(lo_b.x,half.y,lo_b.z)
        if clockwise:
            _quad(st,lo_b,hi_b,hi_a,lo_a)
        else:
            _quad(st,lo_a,hi_a,hi_b,lo_b)
    return st.commit()


static func _triangle(st: SurfaceTool, a: Vector3,b: Vector3,c: Vector3,n: Vector3) -> void:
    st.set_normal(n)
    st.set_uv(Vector2(0,0))
    st.add_vertex(a)
    st.set_normal(n)
    st.set_uv(Vector2(1,0))
    st.add_vertex(b)
    st.set_normal(n)
    st.set_uv(Vector2(1,1))
    st.add_vertex(c)


static func _quad(st: SurfaceTool, a: Vector3,b: Vector3,c: Vector3,d: Vector3) -> void:
    var normal := (b-a).cross(c-a).normalized()
    _triangle(st,a,b,c,normal)
    _triangle(st,a,c,d,normal)
