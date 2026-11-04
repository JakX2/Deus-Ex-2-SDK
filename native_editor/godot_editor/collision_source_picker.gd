extends RefCounted
## Source-authenticated DX2 collision geometry picker for the Godot preview.
## This is NOT Havok physics, a native shape writer, or an editable GMP layer.
## Level flat XYZ -> Godot preview axes (x,z,y) times 0.1, as verified by
## existing packed Flesh render geometry. Source IDs remain intact.

const SCHEMA := "DX2Ed-source-MOPP-collision-selection-cache-v1"
const MAX_VERTICES := 300000
const MAX_FACES := 300000
const MAX_TREE_NODES := 100000
const LEAF_LIMIT := 8

var vertices := PackedVector3Array()
var faces: Array[Dictionary] = []
var materials: Array[String] = []
var face_bounds: Array[AABB] = []
var face_centers := PackedVector3Array()
var tree: Array[Dictionary] = []
var source_map := ""
var source_sha256 := ""
var last_error := ""
var ready := false

func clear() -> void:
    vertices.clear()
    faces.clear()
    materials.clear()
    face_bounds.clear()
    face_centers.clear()
    tree.clear()
    source_map = ""
    source_sha256 = ""
    ready = false
    last_error = ""

func _fail(reason: String) -> bool:
    clear()
    last_error = reason
    return false

func load_cache(path: String, expected_hash: String, expected_map: String) -> bool:
    if not FileAccess.file_exists(path):
        return _fail("Source collision cache is missing")
    var raw: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
    if typeof(raw) != TYPE_DICTIONARY:
        return _fail("Source collision cache is not a JSON object")
    return load_document(raw, expected_hash, expected_map)

func _bounded_integer(value: Variant, minimum: int, maximum: int) -> bool:
    if typeof(value) not in [TYPE_FLOAT, TYPE_INT]:
        return false
    var numeric := float(value)
    return is_finite(numeric) and numeric == floor(numeric) and numeric >= minimum and numeric <= maximum

func load_document(doc: Dictionary, expected_hash: String, expected_map: String) -> bool:
    clear()
    if (expected_hash.length() != 64 or not expected_hash.is_valid_hex_number()
        or expected_map.is_empty() or not expected_map.to_lower().ends_with(".gmp")):
        return _fail("Missing authenticated GMP hash or name")
    if (doc.get("schema", "") != SCHEMA or doc.get("source_sha256", "") != expected_hash
        or doc.get("source_map", "") != expected_map or doc.get("read_only", false) != true
        or doc.get("not_a_native_collision_writer", false) != true
        or doc.get("physics_materials_verified", true) != false
        or doc.get("coordinate_system", "") != "Godot preview (Level.x/10, Level.z/10, Level.y/10)"):
        return _fail("Untrusted, stale, or wrongly scaled original map cache")
    var raw_vertices: Variant = doc.get("vertices_godot_xyz")
    var raw_faces: Variant = doc.get("leaf_triangles")
    var raw_materials: Variant = doc.get("render_material_names")
    if (typeof(raw_vertices) != TYPE_ARRAY or typeof(raw_faces) != TYPE_ARRAY
        or typeof(raw_materials) != TYPE_ARRAY or raw_materials.is_empty()
        or raw_vertices.size() < 3 or raw_vertices.size() > MAX_VERTICES
        or raw_faces.is_empty() or raw_faces.size() > MAX_FACES
        or not _bounded_integer(doc.get("source_flat_vertex_count", -1), 3, MAX_VERTICES)
        or not _bounded_integer(doc.get("mopp_leaf_triangle_count", -1), 1, MAX_FACES)
        or not _bounded_integer(doc.get("source_triangle_count", -1), 1, MAX_FACES)
        or int(doc["source_flat_vertex_count"]) != raw_vertices.size()
        or int(doc["mopp_leaf_triangle_count"]) != raw_faces.size()):
        return _fail("Collision geometry counts or field types are invalid")
    if int(doc["source_triangle_count"]) < raw_faces.size() or int(doc["source_triangle_count"]) > MAX_FACES:
        return _fail("Invalid original Level triangle total")
    for triple in raw_vertices:
        if typeof(triple) != TYPE_ARRAY or triple.size() != 3:
            return _fail("Malformed collision source vertex")
        for number in triple:
            if typeof(number) not in [TYPE_INT, TYPE_FLOAT] or not is_finite(float(number)):
                return _fail("Nonfinite collision source vertex")
        var pos := Vector3(float(triple[0]), float(triple[1]), float(triple[2]))
        if not pos.is_finite():
            return _fail("Invalid preview position")
        if abs(pos.x) > 100000 or abs(pos.y) > 100000 or abs(pos.z) > 100000:
            return _fail("Preview position out of allowed range")
        vertices.append(pos)
    for material in raw_materials:
        if typeof(material) != TYPE_STRING or str(material).is_empty():
            return _fail("Missing source render material name")
        materials.append(material)
    var previous_id := -1
    for f in raw_faces:
        if typeof(f) != TYPE_DICTIONARY:
            return _fail("Malformed original collision triangle row")
        var tid: Variant = f.get("triangle_id")
        var ids: Variant = f.get("vertex_indices")
        var mat: Variant = f.get("render_material_id")
        if (not _bounded_integer(tid, 0, int(doc["source_triangle_count"])-1)
            or int(tid) <= previous_id or typeof(ids) != TYPE_ARRAY or ids.size() != 3
            or not _bounded_integer(mat, 0, materials.size()-1)) :
            return _fail("Source triangle ID, material, or vertex indices invalid")
        for index in ids:
            if not _bounded_integer(index, 0, vertices.size()-1):
                return _fail("Source collision vertex index out of bounds")
        for name in ["source_block_id", "render_block_ordinal", "render_section_ordinal"]:
            if not _bounded_integer(f.get(name), 0, MAX_FACES * 10):
                return _fail("Missing verified original render-section provenance")
        var v0: Vector3 = vertices[int(ids[0])]
        var v1: Vector3 = vertices[int(ids[1])]
        var v2: Vector3 = vertices[int(ids[2])]
        if (v1 - v0).cross(v2 - v0).length_squared() <= 0.0:
            return _fail("Zero-area triangle must not be in MOPP leaf cache")
        var corner := Vector3(minf(v0.x, minf(v1.x, v2.x)), minf(v0.y, minf(v1.y, v2.y)), minf(v0.z, minf(v1.z, v2.z)))
        var upper := Vector3(maxf(v0.x, maxf(v1.x, v2.x)), maxf(v0.y, maxf(v1.y, v2.y)), maxf(v0.z, maxf(v1.z, v2.z)))
        face_bounds.append(AABB(corner, upper-corner))
        face_centers.append((v0+v1+v2)/3.0)
        faces.append({"triangle_id": int(tid),
            "vertex_indices": [int(ids[0]), int(ids[1]), int(ids[2])],
            "source_block_id": int(f["source_block_id"]),
            "render_block_ordinal": int(f["render_block_ordinal"]),
            "render_section_ordinal": int(f["render_section_ordinal"]),
            "render_material_id": int(mat)})
        previous_id = int(tid)
    var list: Array[int] = []
    for index in faces.size():
        list.append(index)
    if _build_tree(list, 0) != 0 or tree.size() > MAX_TREE_NODES:
        return _fail("Collision picker BVH could not be constructed")
    source_map = expected_map
    source_sha256 = expected_hash
    ready = true
    return true

func _build_tree(indices: Array[int], depth: int) -> int:
    if indices.is_empty() or depth > 50 or tree.size() >= MAX_TREE_NODES:
        return -1
    var bounds: AABB = face_bounds[indices[0]]
    for index in indices:
        bounds = bounds.merge(face_bounds[index])
    var node := tree.size()
    tree.append({"bounds": bounds, "left": -1, "right": -1, "faces": []})
    if indices.size() <= LEAF_LIMIT:
        tree[node]["faces"] = indices
        return node
    var axis := 0
    if bounds.size.y > bounds.size.x:
        axis = 1
    if bounds.size.z > bounds.size[axis]:
        axis = 2
    indices.sort_custom(func(a: int, b: int) -> bool:
        if face_centers[a][axis] == face_centers[b][axis]:
            return a < b
        return face_centers[a][axis] < face_centers[b][axis])
    var half := int(indices.size() / 2)
    var left := _build_tree(indices.slice(0, half), depth + 1)
    var right := _build_tree(indices.slice(half), depth + 1)
    if left < 0 or right < 0:
        return -1
    tree[node]["left"] = left
    tree[node]["right"] = right
    return node

func _ray_box(origin: Vector3, direction: Vector3, box: AABB, maximum: float) -> bool:
    var near := 0.0
    var far := maximum
    for axis in 3:
        var d: float = direction[axis]
        var o: float = origin[axis]
        var lo: float = box.position[axis]
        var hi: float = box.end[axis]
        if abs(d) < 0.0000000001:
            if o < lo or o > hi:
                return false
            continue
        var t0 := (lo-o)/d
        var t1 := (hi-o)/d
        near = maxf(near, minf(t0,t1))
        far = minf(far, maxf(t0,t1))
        if far < near:
            return false
    return far >= 0.0

func ray_pick(origin: Vector3, direction: Vector3, max_distance: float = 100000.0) -> Dictionary:
    if not ready or not origin.is_finite() or not direction.is_finite() or direction.length_squared() < 1e-14:
        return {}
    if not is_finite(max_distance) or max_distance <= 0.0 or max_distance > 10000000.0:
        return {}
    var ray := direction.normalized()
    var pending: Array[int] = [0]
    var best_distance := max_distance
    var best: Dictionary = {}
    while not pending.is_empty():
        var node: Dictionary = tree[pending.pop_back()]
        if not _ray_box(origin, ray, node["bounds"], best_distance):
            continue
        if int(node["left"]) >= 0:
            pending.append(node["left"])
            pending.append(node["right"])
            continue
        for ix in node["faces"]:
            var face: Dictionary = faces[ix]
            var ids: Array = face["vertex_indices"]
            var a: Vector3 = vertices[ids[0]]
            var b: Vector3 = vertices[ids[1]]
            var c: Vector3 = vertices[ids[2]]
            var p: Variant = Geometry3D.ray_intersects_triangle(origin, ray, a, b, c)
            if p == null:
                p = Geometry3D.ray_intersects_triangle(origin, ray, c, b, a)
            if not (p is Vector3):
                continue
            var distance: float = (p-origin).dot(ray)
            if distance < 0.0000001 or distance > best_distance:
                continue
            if (not best.is_empty() and abs(distance-best_distance) <= 0.00000001
                and int(face["triangle_id"]) >= int(best["original_level_triangle_id"])):
                continue
            best_distance = distance
            var normal: Vector3 = (c-a).cross(b-a).normalized()
            best = {
                "original_level_triangle_id": face["triangle_id"],
                "source_block_id": face["source_block_id"],
                "render_block_ordinal": face["render_block_ordinal"],
                "render_section_ordinal": face["render_section_ordinal"],
                "render_material_name": materials[face["render_material_id"]],
                "render_material_is_physics_material": false,
                "point_godot": p,
                "normal_godot": normal,
                "vertices_godot": [a,b,c],
                "distance_godot_units": distance,
                "query_is_havok_runtime": false,
            }
    return best