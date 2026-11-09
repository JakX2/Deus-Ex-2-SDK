extends RefCounted
## DX2Ed custom planar polygon footprint -> extruded closed preview mesh.
## Each vertex is local normalized X/Z in [-1, +1]; the existing brush
## Size X / Y / Z controls scale width, height and depth in Godot metres.
## This is PRIVATE editor draft geometry, NOT native DX2 BSP/CSG.
const MAX_VERTICES := 32
const MIN_VERTICES := 3
const MIN_EDGE_LENGTH := 0.0001
const MIN_AREA := 0.005
const SURFACE_SLOTS := ["top", "bottom", "sides"]
const SURFACE_PRESETS := ["Neutral", "Concrete", "Metal", "Ceramic", "Hazard"]


static func default_surface_style() -> Dictionary:
    return {
        "top": {"preset": "Concrete", "tint": [1.0, 1.0, 1.0, 1.0],
                "uv_scale": [1.0, 1.0], "uv_offset": [0.0, 0.0],
                "source_material": {}},
        "bottom": {"preset": "Neutral", "tint": [1.0, 1.0, 1.0, 1.0],
                   "uv_scale": [1.0, 1.0], "uv_offset": [0.0, 0.0],
                   "source_material": {}},
        "sides": {"preset": "Metal", "tint": [1.0, 1.0, 1.0, 1.0],
                  "uv_scale": [1.0, 1.0], "uv_offset": [0.0, 0.0],
                  "source_material": {}}
    }


static func _bounded_number_array(raw: Variant, count: int,
                                  minimum: float, maximum: float) -> Array:
    if typeof(raw) != TYPE_ARRAY or raw.size() != count:
        return []
    var result: Array = []
    for value in raw:
        if typeof(value) not in [TYPE_INT, TYPE_FLOAT]:
            return []
        var number := float(value)
        if not is_finite(number) or number < minimum or number > maximum:
            return []
        result.append(number)
    return result


## Private polygon surface metadata only. Missing legacy style fields receive
## defaults; malformed present fields fail closed before a draft is reloaded.
static func validate_surface_style(raw: Variant) -> Dictionary:
    var defaults := default_surface_style()
    if raw == null:
        return defaults
    if typeof(raw) != TYPE_DICTIONARY:
        return {}
    var result: Dictionary = {}
    for slot in SURFACE_SLOTS:
        var fallback: Dictionary = defaults[slot]
        var entry: Variant = raw.get(slot, fallback)
        if typeof(entry) != TYPE_DICTIONARY:
            return {}
        var preset: Variant = entry.get("preset", fallback["preset"])
        if typeof(preset) != TYPE_STRING or not SURFACE_PRESETS.has(preset):
            return {}
        var tint := _bounded_number_array(
            entry.get("tint", fallback["tint"]), 4, 0.0, 1.0)
        var uv_scale := _bounded_number_array(
            entry.get("uv_scale", fallback["uv_scale"]), 2, 0.05, 64.0)
        var uv_offset := _bounded_number_array(
            entry.get("uv_offset", fallback["uv_offset"]), 2, -64.0, 64.0)
        var source_raw: Variant = entry.get("source_material", fallback["source_material"])
        if tint.is_empty() or uv_scale.is_empty() or uv_offset.is_empty():
            return {}
        if typeof(source_raw) != TYPE_DICTIONARY:
            return {}
        var source_material: Dictionary = {}
        if not source_raw.is_empty():
            source_material = validate_source_material_assignment(source_raw)
            if source_material.is_empty():
                return {}
        result[slot] = {
            "preset": preset,
            "tint": tint,
            "uv_scale": uv_scale,
            "uv_offset": uv_offset,
            "source_material": source_material
        }
    return result


static func _valid_assignment_text(
        value: Variant, maximum: int, allow_empty: bool = false) -> bool:
    if typeof(value) != TYPE_STRING or str(value).length() > maximum:
        return false
    return allow_empty or not str(value).strip_edges().is_empty()


static func _valid_sha256(value: Variant) -> bool:
    if typeof(value) != TYPE_STRING or str(value).length() != 64:
        return false
    for index in range(64):
        if "0123456789abcdef".find(str(value).substr(index, 1).to_lower()) < 0:
            return false
    return true


## Exact, source-pinned metadata for one resolved diffuse preview. Paths point
## only to the private catalog/cache; they never authorize source or BSP writes.
static func validate_source_material_assignment(raw: Variant) -> Dictionary:
    if typeof(raw) != TYPE_DICTIONARY or raw.is_empty() or raw.size() != 19:
        return {}
    var required := [
        "catalog_path", "catalog_sha256", "catalog_id", "material_name",
        "material_source_bundle", "material_source", "material_version",
        "material_flags", "material_stage_mask", "material_category_id",
        "diffuse_name", "texture_name", "texture_source_bundle", "texture_format",
        "texture_width", "texture_height", "texture_usage", "preview_path",
        "preview_sha256"
    ]
    for key in required:
        if not raw.has(key):
            return {}
    var catalog_path: Variant = raw["catalog_path"]
    if (not _valid_assignment_text(catalog_path, 4096)
        or not str(catalog_path).is_absolute_path()):
        return {}
    var normalized_catalog := str(catalog_path).simplify_path()
    var private_cache_root := ProjectSettings.globalize_path(
        "user://dx2ed_material_cache").simplify_path().trim_suffix("/")
    if (not normalized_catalog.ends_with(".json")
        or not normalized_catalog.begins_with(private_cache_root + "/")):
        return {}
    for key in ["catalog_sha256", "catalog_id", "preview_sha256"]:
        if not _valid_sha256(raw[key]):
            return {}
    for key in [
        "material_name", "material_source_bundle",
        "diffuse_name", "texture_name", "texture_source_bundle", "texture_format",
        "texture_usage"
    ]:
        if not _valid_assignment_text(raw[key], 260):
            return {}
    if not _valid_assignment_text(raw["material_source"], 260, true):
        return {}
    if str(raw["diffuse_name"]).to_lower() != str(raw["texture_name"]).to_lower():
        return {}
    var integer_limits := {
        "material_version": [0, 65535],
        "material_flags": [0, 4294967295],
        "material_stage_mask": [0, 4294967295],
        "material_category_id": [0, 65535],
        "texture_width": [1, 16384],
        "texture_height": [1, 16384]
    }
    for key in integer_limits:
        if typeof(raw[key]) != TYPE_INT:
            return {}
        var value := int(raw[key])
        if value < integer_limits[key][0] or value > integer_limits[key][1]:
            return {}
    var preview_path: Variant = raw["preview_path"]
    if (not _valid_assignment_text(preview_path, 260)
        or str(preview_path).begins_with("/")
        or str(preview_path).contains("\\")
        or str(preview_path).contains(":")):
        return {}
    for segment in str(preview_path).split("/", false):
        if segment.is_empty() or segment == "." or segment == "..":
            return {}
    return {
        "catalog_path": str(catalog_path),
        "catalog_sha256": str(raw["catalog_sha256"]).to_lower(),
        "catalog_id": str(raw["catalog_id"]).to_lower(),
        "material_name": str(raw["material_name"]),
        "material_source_bundle": str(raw["material_source_bundle"]),
        "material_source": str(raw["material_source"]),
        "material_version": int(raw["material_version"]),
        "material_flags": int(raw["material_flags"]),
        "material_stage_mask": int(raw["material_stage_mask"]),
        "material_category_id": int(raw["material_category_id"]),
        "diffuse_name": str(raw["diffuse_name"]),
        "texture_name": str(raw["texture_name"]),
        "texture_source_bundle": str(raw["texture_source_bundle"]),
        "texture_format": str(raw["texture_format"]),
        "texture_width": int(raw["texture_width"]),
        "texture_height": int(raw["texture_height"]),
        "texture_usage": str(raw["texture_usage"]),
        "preview_path": str(preview_path),
        "preview_sha256": str(raw["preview_sha256"]).to_lower()
    }


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
        var corner := Vector2(float(entry[0]),float(entry[1]))
        points.append(corner)
        rows.append([corner.x,corner.y])
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
    if (rows.is_empty() or rows.size() >= MAX_VERTICES
        or edge < 0 or edge >= rows.size()):
        return []
    var b: Array = rows[(edge+1) % rows.size()]
    var a: Array = rows[edge]
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
        points.append(Vector2(float(row[0]), float(row[1])))
    var triangles := Geometry2D.triangulate_polygon(points)
    if triangles.size() != (points.size() - 2) * 3:
        return null
    var half := size * 0.5
    var mesh := ArrayMesh.new()

    # Separate top, bottom and side surfaces let the editor assign three
    # independent preview materials and UV transforms without face merging.
    var top_tool := SurfaceTool.new()
    top_tool.begin(Mesh.PRIMITIVE_TRIANGLES)
    for i in range(0, triangles.size(), 3):
        var i0: int = triangles[i]
        var i1: int = triangles[i + 1]
        var i2: int = triangles[i + 2]
        var a := Vector3(points[i0].x * half.x, half.y, points[i0].y * half.z)
        var b := Vector3(points[i1].x * half.x, half.y, points[i1].y * half.z)
        var c := Vector3(points[i2].x * half.x, half.y, points[i2].y * half.z)
        if (b - a).cross(c - a).y < 0.0:
            var saved_index := i1
            i1 = i2
            i2 = saved_index
            b = Vector3(points[i1].x * half.x, half.y, points[i1].y * half.z)
            c = Vector3(points[i2].x * half.x, half.y, points[i2].y * half.z)
        _triangle_uv(top_tool, a, b, c, Vector3.UP,
            _footprint_uv(points[i0]), _footprint_uv(points[i1]), _footprint_uv(points[i2]))
    top_tool.commit(mesh)

    var bottom_tool := SurfaceTool.new()
    bottom_tool.begin(Mesh.PRIMITIVE_TRIANGLES)
    for i in range(0, triangles.size(), 3):
        var i0: int = triangles[i]
        var i1: int = triangles[i + 1]
        var i2: int = triangles[i + 2]
        var a := Vector3(points[i0].x * half.x, -half.y, points[i0].y * half.z)
        var b := Vector3(points[i1].x * half.x, -half.y, points[i1].y * half.z)
        var c := Vector3(points[i2].x * half.x, -half.y, points[i2].y * half.z)
        if (b - a).cross(c - a).y > 0.0:
            var saved_index := i1
            i1 = i2
            i2 = saved_index
            b = Vector3(points[i1].x * half.x, -half.y, points[i1].y * half.z)
            c = Vector3(points[i2].x * half.x, -half.y, points[i2].y * half.z)
        _triangle_uv(bottom_tool, a, b, c, Vector3.DOWN,
            _footprint_uv(points[i0]), _footprint_uv(points[i1]), _footprint_uv(points[i2]))
    bottom_tool.commit(mesh)

    var perimeter := 0.0
    for i in range(points.size()):
        var p := points[i]
        var q := points[(i + 1) % points.size()]
        perimeter += Vector2((q.x - p.x) * half.x, (q.y - p.y) * half.z).length()
    if perimeter <= MIN_EDGE_LENGTH:
        return null
    var side_tool := SurfaceTool.new()
    side_tool.begin(Mesh.PRIMITIVE_TRIANGLES)
    var distance := 0.0
    var clockwise := signed_area(points) < 0.0
    for i in range(points.size()):
        var p := points[i]
        var q := points[(i + 1) % points.size()]
        var edge_length := Vector2((q.x - p.x) * half.x, (q.y - p.y) * half.z).length()
        var u0 := distance / perimeter
        var u1 := (distance + edge_length) / perimeter
        var lo_a := Vector3(p.x * half.x, -half.y, p.y * half.z)
        var lo_b := Vector3(q.x * half.x, -half.y, q.y * half.z)
        var hi_a := Vector3(lo_a.x, half.y, lo_a.z)
        var hi_b := Vector3(lo_b.x, half.y, lo_b.z)
        if clockwise:
            _quad_uv(side_tool, lo_b, hi_b, hi_a, lo_a,
                Vector2(u1, 0.0), Vector2(u1, 1.0),
                Vector2(u0, 1.0), Vector2(u0, 0.0))
        else:
            _quad_uv(side_tool, lo_a, hi_a, hi_b, lo_b,
                Vector2(u0, 0.0), Vector2(u0, 1.0),
                Vector2(u1, 1.0), Vector2(u1, 0.0))
        distance += edge_length
    side_tool.commit(mesh)
    return mesh


static func _footprint_uv(point: Vector2) -> Vector2:
    return Vector2((point.x + 1.0) * 0.5, (point.y + 1.0) * 0.5)


static func _triangle_uv(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3,
                         normal: Vector3, uv_a: Vector2, uv_b: Vector2,
                         uv_c: Vector2) -> void:
    st.set_normal(normal)
    st.set_uv(uv_a)
    st.add_vertex(a)
    st.set_normal(normal)
    st.set_uv(uv_b)
    st.add_vertex(b)
    st.set_normal(normal)
    st.set_uv(uv_c)
    st.add_vertex(c)


static func _quad_uv(st: SurfaceTool, a: Vector3, b: Vector3,
                     c: Vector3, d: Vector3, uv_a: Vector2,
                     uv_b: Vector2, uv_c: Vector2, uv_d: Vector2) -> void:
    var normal := (b - a).cross(c - a).normalized()
    _triangle_uv(st, a, b, c, normal, uv_a, uv_b, uv_c)
    _triangle_uv(st, a, c, d, normal, uv_a, uv_c, uv_d)
