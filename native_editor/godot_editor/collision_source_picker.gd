extends RefCounted
## Source-authenticated DX2 collision geometry picker for the Godot preview.
## This is NOT Havok physics, a native shape writer, or an editable GMP layer.
## Level flat XYZ -> Godot preview axes (x,z,y) times 0.1, as verified by
## existing packed Flesh render geometry. Source IDs remain intact.

const SCHEMA := "DX2Ed-source-MOPP-collision-selection-cache-v3"
const EDGE_SCHEMA := "DX2Ed-MOPP-source-exact-edge-provenance-v1"
const EDGE_NAMES := ["interior", "open boundary", "render-material seam", "non-manifold"]
const MAX_VERTICES := 300000
const MAX_FACES := 300000
const MAX_TREE_NODES := 100000
const LEAF_LIMIT := 8

var vertices := PackedVector3Array()
var faces: Array[Dictionary] = []
# Original Level IDs, not Godot-imported triangle ordinals.
var face_index_by_id: Dictionary = {}
# Group by original source block ID + render block/section; no material physics claim.
var section_triangle_ids: Dictionary = {}
var materials: Array[String] = []
var face_bounds: Array[AABB] = []
var face_centers := PackedVector3Array()
var tree: Array[Dictionary] = []
var source_map := ""
var source_sha256 := ""
var source_topology_summary: Dictionary = {}
# Each source edge is keyed by exact ORIGINAL Level float32 coordinate weld IDs.
# Never use Godot Vector3 proximity to manufacture authentic adjacency.
var original_edge_incidence: Dictionary = {}
var last_error := ""
var ready := false

func clear() -> void:
    vertices.clear()
    faces.clear()
    face_index_by_id.clear()
    section_triangle_ids.clear()
    materials.clear()
    face_bounds.clear()
    face_centers.clear()
    tree.clear()
    source_map = ""
    source_sha256 = ""
    source_topology_summary.clear()
    original_edge_incidence.clear()
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
    var top: Variant = doc.get("source_topology_summary")
    if (doc.get("edge_provenance_schema", "") != EDGE_SCHEMA
        or typeof(top) != TYPE_DICTIONARY
        or doc.get("source_edge_welding", "") != "exact_original_Level_XYZ_no_epsilon"):
        return _fail("Missing source-validated original collision edge provenance")
    for key in ["source_exact_welded_vertex_count", "unique_source_edges",
                "open_boundary_edges", "two_triangle_same_material_edges",
                "two_triangle_render_material_seams",
                "three_or_more_triangle_edges", "max_triangles_using_one_edge"]:
        if not _bounded_integer(top.get(key), 0, MAX_FACES * 3):
            return _fail("Invalid source topology edge count " + key)
    if int(top["source_exact_welded_vertex_count"]) < 3 or int(top["source_exact_welded_vertex_count"]) > raw_vertices.size():
        return _fail("Source welded vertex count exceeds original vertex count")
    if int(top["unique_source_edges"]) > raw_faces.size() * 3:
        return _fail("Source edge count exceeds original triangle edge uses")
    var edge_uses := [0, 0, 0, 0]
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
        var kinds: Variant = f.get("source_edge_kinds")
        var source_welds: Variant = f.get("source_weld_ids")
        if (typeof(source_welds) != TYPE_ARRAY or source_welds.size() != 3):
            return _fail("Missing exact original Level welded vertex IDs")
        for weld in source_welds:
            if not _bounded_integer(weld, 0, int(top["source_exact_welded_vertex_count"])-1):
                return _fail("Original source weld ID outside authenticated Level range")
        if (int(source_welds[0]) == int(source_welds[1])
            or int(source_welds[1]) == int(source_welds[2])
            or int(source_welds[2]) == int(source_welds[0])):
            return _fail("Collapsed original welded collision triangle edge")
        if (typeof(kinds) != TYPE_ARRAY or kinds.size() != 3):
            return _fail("Missing three source-validated edge classifications")
        for kind in kinds:
            if not _bounded_integer(kind, 0, 3):
                return _fail("Invalid original topology edge kind")
            edge_uses[int(kind)] += 1
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
        var key := "%d/%d/%d" % [
            int(f["source_block_id"]), int(f["render_block_ordinal"]),
            int(f["render_section_ordinal"])]
        # Every triangle with the same original section must share its material.
        var group: Array = section_triangle_ids.get(key, [])
        if not group.is_empty():
            var first_face: Dictionary = faces[int(face_index_by_id[group[0]])]
            if int(first_face["render_material_id"]) != int(mat):
                return _fail("Contradictory render material within one original section")
        face_index_by_id[int(tid)] = faces.size()
        faces.append({"triangle_id": int(tid),
            "vertex_indices": [int(ids[0]), int(ids[1]), int(ids[2])],
            "source_block_id": int(f["source_block_id"]),
            "render_block_ordinal": int(f["render_block_ordinal"]),
            "render_section_ordinal": int(f["render_section_ordinal"]),
            "render_material_id": int(mat), "source_section_key": key,
            "source_edge_kinds": [int(kinds[0]), int(kinds[1]), int(kinds[2])],
            "source_weld_ids": [int(source_welds[0]), int(source_welds[1]), int(source_welds[2])]})
        # Build edge incidence using the original, exact-float32 source weld
        # IDs; preview f32 coordinate coincidences are insufficient proof.
        for slot in 3:
            var low: int = mini(int(source_welds[slot]), int(source_welds[(slot+1)%3]))
            var high: int = maxi(int(source_welds[slot]), int(source_welds[(slot+1)%3]))
            var edge_key := "%d:%d" % [low, high]
            var incident: Array = original_edge_incidence.get(edge_key, [])
            incident.append({
                "triangle_id": int(tid),
                "edge_slot": slot,
                "render_material_id": int(mat),
            })
            original_edge_incidence[edge_key] = incident
        group.append(int(tid))
        section_triangle_ids[key] = group
        previous_id = int(tid)
    if (edge_uses[1] != int(top["open_boundary_edges"])
        or edge_uses[0] != int(top["two_triangle_same_material_edges"]) * 2
        or edge_uses[2] != int(top["two_triangle_render_material_seams"]) * 2
        or edge_uses[3] < int(top["three_or_more_triangle_edges"]) * 3
        or (edge_uses[3] == 0 and int(top["three_or_more_triangle_edges"]) != 0)
        or (edge_uses[3] > 0 and int(top["three_or_more_triangle_edges"]) == 0)
        or int(top["unique_source_edges"]) !=
            (int(top["open_boundary_edges"])
             + int(top["two_triangle_same_material_edges"])
             + int(top["two_triangle_render_material_seams"])
             + int(top["three_or_more_triangle_edges"]))):
        return _fail("Source edge incidence counts do not match the original map cache")
    # Independently re-count original edge incidence from exact welded IDs.
    # A forged preview-side seam or neighboring face must not be accepted.
    var confirmed := [0, 0, 0, 0]
    var largest := 0
    for uses in original_edge_incidence.values():
        var members: Array = uses
        var n := members.size()
        largest = maxi(largest, n)
        var expected_class := 3
        if n == 1:
            expected_class = 1
        elif n == 2:
            expected_class = (0 if int(members[0]["render_material_id"])
                == int(members[1]["render_material_id"]) else 2)
        confirmed[expected_class] += 1
        for incident in members:
            var incident_face: Dictionary = faces[int(face_index_by_id[incident["triangle_id"]])]
            if int(incident_face["source_edge_kinds"][int(incident["edge_slot"])]) != expected_class:
                return _fail("Original exact welded edge topology contradicts source edge class")
    if (original_edge_incidence.size() != int(top["unique_source_edges"])
        or confirmed[1] != int(top["open_boundary_edges"])
        or confirmed[0] != int(top["two_triangle_same_material_edges"])
        or confirmed[2] != int(top["two_triangle_render_material_seams"])
        or confirmed[3] != int(top["three_or_more_triangle_edges"])
        or largest != int(top["max_triangles_using_one_edge"])):
        return _fail("Source exact-weld topology count mismatches original collision cache")
    source_topology_summary = top.duplicate(true)
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
                "source_edge_kinds": face["source_edge_kinds"].duplicate(),
                "point_godot": p,
                "normal_godot": normal,
                "vertices_godot": [a,b,c],
                "distance_godot_units": distance,
                "query_is_havok_runtime": false,
            }
    return best


# Triangles are arranged in original Level order, not nearest-neighbor order.
# Navigating by original section is an inspection convenience, NOT Havok topology.
# Exact source-vertex-welded edge neighbors, including duplicated raw
# indices. No inference from a shared screen coordinate or render material.
func edge_connected_original_triangles(original_id: int) -> Array[Dictionary]:
    var report: Array[Dictionary] = []
    if not ready or not face_index_by_id.has(original_id):
        return report
    var face: Dictionary = faces[int(face_index_by_id[original_id])]
    var weld: Array = face["source_weld_ids"]
    for slot in 3:
        var low: int = mini(int(weld[slot]), int(weld[(slot+1)%3]))
        var high: int = maxi(int(weld[slot]), int(weld[(slot+1)%3]))
        var key := "%d:%d" % [low, high]
        var neighbors: Array[int] = []
        var neighbors_slots: Array[int] = []
        var incidence: Array = original_edge_incidence.get(key, [])
        for other in incidence:
            var partner: int = int(other["triangle_id"])
            if partner != original_id:
                neighbors.append(partner)
                neighbors_slots.append(int(other["edge_slot"]))
        report.append({
            "edge_slot": slot,
            "source_class_code": int(face["source_edge_kinds"][slot]),
            "original_incident_triangle_count": incidence.size(),
            "neighbor_original_triangle_ids": neighbors,
            "neighbor_source_edge_slots": neighbors_slots,
            "source_welding_is_exact_original_Level_XYZ": true,
            "havok_runtime_adjacency_verified": false,
        })
    return report


func triangle_details(original_id: int) -> Dictionary:
    if not ready or not face_index_by_id.has(original_id):
        return {}
    var face: Dictionary = faces[int(face_index_by_id[original_id])]
    var ids: Array = face["vertex_indices"]
    var a: Vector3 = vertices[ids[0]]
    var b: Vector3 = vertices[ids[1]]
    var c: Vector3 = vertices[ids[2]]
    return {
        "original_level_triangle_id": original_id,
        "source_block_id": face["source_block_id"],
        "render_block_ordinal": face["render_block_ordinal"],
        "render_section_ordinal": face["render_section_ordinal"],
        "render_material_name": materials[int(face["render_material_id"])],
        "render_material_is_physics_material": false,
        "source_edge_kinds": face["source_edge_kinds"].duplicate(),
        "source_weld_ids": face["source_weld_ids"].duplicate(),
        "point_godot": (a+b+c)/3.0,
        "normal_godot": (c-a).cross(b-a).normalized(),
        "vertices_godot": [a, b, c],
        "distance_godot_units": -1.0,
        "selection_is_ray_hit": false,
        "query_is_havok_runtime": false,
    }


func section_details(original_id: int, preview_cap: int = 1024) -> Dictionary:
    if (not ready or not face_index_by_id.has(original_id)
        or preview_cap < 1 or preview_cap > 4096):
        return {}
    var face: Dictionary = faces[int(face_index_by_id[original_id])]
    var key: String = face["source_section_key"]
    var ids: Array = section_triangle_ids.get(key, [])
    if ids.is_empty():
        return {}
    var at: int = ids.find(original_id)
    if at < 0:
        return {}
    var total := ids.size()
    var limited := total > preview_cap
    var edge_points := PackedVector3Array()
    if not limited:
        for tid in ids:
            var source_face: Dictionary = faces[int(face_index_by_id[tid])]
            var corners: Array = source_face["vertex_indices"]
            for edge in 3:
                edge_points.append(vertices[int(corners[edge])])
                edge_points.append(vertices[int(corners[(edge+1) % 3])])
    return {
        "source_block_id": face["source_block_id"],
        "render_block_ordinal": face["render_block_ordinal"],
        "render_section_ordinal": face["render_section_ordinal"],
        "render_material_name": materials[int(face["render_material_id"])],
        "triangle_count": total,
        "triangle_index_in_section": at,
        "previous_triangle_id": ids[(at+total-1) % total],
        "next_triangle_id": ids[(at+1) % total],
        "outline_vertices_godot": edge_points,
        "preview_skipped_for_size": limited,
        "preview_triangle_cap": preview_cap,
        "not_a_havok_contact_or_native_surface": true,
    }
