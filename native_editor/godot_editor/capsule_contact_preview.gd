extends RefCounted
## Explicitly opt-in, source-hash-gated visualization of a PR #46 NUMERICAL
## capsule first-contact result. NOT Havok, game collision, or writable data.

const SCHEMA := "DX2Ed-capsule-first-contact-preview-v1"
const COORD := "Godot preview (Level.x/10, Level.z/10, Level.y/10)"
const MAX_POSITION := 100000.0

var ready := false
var last_error := ""
var doc: Dictionary = {}
var start := Vector3.ZERO
var finish := Vector3.ZERO
var axis := Vector3.UP
var radius := 0.0
var axis_half := 0.0
var contact_t := 0.0
var contact_triangle_id := -1
var contact_triangle_point := Vector3.ZERO
var contact_axis_point := Vector3.ZERO
var normal := Vector3.ZERO
var normal_resolved := false

func clear() -> void:
    ready = false
    last_error = ""
    doc.clear()
    start = Vector3.ZERO
    finish = Vector3.ZERO
    axis = Vector3.UP
    radius = 0.0
    axis_half = 0.0
    contact_t = 0.0
    contact_triangle_id = -1
    contact_triangle_point = Vector3.ZERO
    contact_axis_point = Vector3.ZERO
    normal = Vector3.ZERO
    normal_resolved = false

func _fail(reason: String) -> bool:
    clear()
    last_error = reason
    return false

func _finite_number(value: Variant, low: float, high: float) -> bool:
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value)) and float(value) >= low and float(value) <= high)

func _xyz(value: Variant) -> bool:
    if typeof(value) != TYPE_ARRAY or value.size() != 3:
        return false
    for item in value:
        if not _finite_number(item, -MAX_POSITION, MAX_POSITION):
            return false
    return true

func _vec(value: Array) -> Vector3:
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

func load_file(path: String, expected_hash: String,
               expected_map: String, original_face_ids: Dictionary) -> bool:
    if not FileAccess.file_exists(path) or path.get_extension().to_lower() != "json":
        return _fail("Research preview JSON missing")
    var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
    if typeof(parsed) != TYPE_DICTIONARY:
        return _fail("Research preview is not a JSON object")
    return load_document(parsed, expected_hash, expected_map, original_face_ids)

func load_document(data: Dictionary, expected_hash: String,
                   expected_map: String, original_face_ids: Dictionary) -> bool:
    clear()
    if (expected_hash.length() != 64 or not expected_hash.is_valid_hex_number()
        or expected_map.is_empty() or not expected_map.to_lower().ends_with(".gmp")
        or original_face_ids.is_empty()
        or data.get("schema", "") != SCHEMA
        or data.get("source_sha256", "") != expected_hash
        or data.get("source_map", "") != expected_map
        or data.get("coordinate_system", "") != COORD
        or data.get("read_only", false) != true
        or data.get("not_a_native_collision_writer", false) != true
        or data.get("havok_runtime_contact_verified", true) != false
        or data.get("time_of_impact_exact_havok", true) != false
        or data.get("physics_materials_verified", true) != false
        or data.get("original_game_assets_modified", true) != false
        or not _xyz(data.get("capsule_start_godot_xyz"))
        or not _xyz(data.get("capsule_end_godot_xyz"))
        or not _xyz(data.get("capsule_axis_unit_godot_xyz"))
        or not _finite_number(data.get("capsule_radius_godot_units"), 0.0, 100.0)
        or not _finite_number(data.get("capsule_axis_half_length_godot_units"), 0.0, 100.0)
        or not _finite_number(data.get("geometric_source_triangle_hits"), 0.0, 300000.0)
        or not _finite_number(data.get("source_verified_mopp_leaf_ids"), 1.0, 300000.0)):
        return _fail("Stale, unverified or invalid research capsule preview")
    var first := _vec(data["capsule_start_godot_xyz"])
    var last := _vec(data["capsule_end_godot_xyz"])
    var unit := _vec(data["capsule_axis_unit_godot_xyz"])
    if ((last - first).length() <= 0.00000001
        or absf(unit.length() - 1.0) > 0.00001):
        return _fail("Malformed capsule motion or axis")
    var raw_hit: Variant = data.get("first_hit")
    var tid := -1
    var time := 0.0
    var hit_triangle := Vector3.ZERO
    var hit_axis := Vector3.ZERO
    var outward := Vector3.ZERO
    var has_normal := false
    if raw_hit != null:
        if (typeof(raw_hit) != TYPE_DICTIONARY
            or not _finite_number(raw_hit.get("original_level_triangle_id"), 0.0, 300000.0)
            or float(raw_hit["original_level_triangle_id"]) != floor(float(raw_hit["original_level_triangle_id"]))
            or not original_face_ids.has(int(raw_hit["original_level_triangle_id"]))
            or not _finite_number(raw_hit.get("t_first_inside"), 0.0, 1.0)
            or not _xyz(raw_hit.get("contact_triangle_point_godot_xyz"))
            or not _xyz(raw_hit.get("contact_capsule_axis_point_godot_xyz"))
            or typeof(raw_hit.get("contact_normal_resolved")) != TYPE_BOOL
            or typeof(raw_hit.get("initial_overlap")) != TYPE_BOOL
            or typeof(raw_hit.get("near_tangency")) != TYPE_BOOL
            or typeof(raw_hit.get("numerical_contact_only")) != TYPE_BOOL
            or raw_hit.get("original_mopp_candidate_included", false) != true
            or not _finite_number(raw_hit.get("signed_gap_at_contact_level_units"), -1000.0, 1000.0)):
            return _fail("Unknown original source triangle ID or invalid first-contact evidence")
        time = float(raw_hit["t_first_inside"])
        var previous: Variant = raw_hit.get("t_last_outside")
        if bool(raw_hit["initial_overlap"]):
            if time != 0.0 or previous != null:
                return _fail("Initial-overlap timing contradicts first entry")
        elif (not _finite_number(previous, 0.0, time)
              or time - float(previous) > 0.00001):
            return _fail("First-entry time bracket missing or too wide")
        tid = int(raw_hit["original_level_triangle_id"])
        has_normal = bool(raw_hit["contact_normal_resolved"])
        var raw_normal: Variant = raw_hit.get("contact_normal_godot_xyz")
        if has_normal:
            if not _xyz(raw_normal):
                return _fail("Contact normal cannot be resolved from source geometry")
            outward = _vec(raw_normal)
            if absf(outward.length() - 1.0) > 0.0001:
                return _fail("First-contact normal not a unit vector")
        elif raw_normal != null:
            return _fail("Ambiguous normal must remain unresolved")
        hit_triangle = _vec(raw_hit["contact_triangle_point_godot_xyz"])
        hit_axis = _vec(raw_hit["contact_capsule_axis_point_godot_xyz"])
    else:
        if int(data["geometric_source_triangle_hits"]) != 0:
            return _fail("No-contact preview contradicts geometric hit count")
    doc = data.duplicate(true)
    start = first
    finish = last
    axis = unit
    radius = float(data["capsule_radius_godot_units"])
    axis_half = float(data["capsule_axis_half_length_godot_units"])
    contact_t = time
    contact_triangle_id = tid
    contact_triangle_point = hit_triangle
    contact_axis_point = hit_axis
    normal = outward
    normal_resolved = has_normal
    ready = true
    return true

func description() -> String:
    if not ready:
        return ""
    var text := "CAPSULE CONTACT RESEARCH PREVIEW | READ-ONLY\n"
    text += "Source GMP: %s\n" % str(doc["source_map"])
    text += "Capsule radius / half-axis: %.4f / %.4f Godot units\n" % [radius, axis_half]
    text += "Original Level triangles touched: %d\n" % int(doc["geometric_source_triangle_hits"])
    if contact_triangle_id < 0:
        text += "No geometric contact on this segment.\n"
    else:
        text += "First original Level triangle ID: %d\n" % contact_triangle_id
        text += "Normalized first-entry time: %.8f\n" % contact_t
        var hit: Dictionary = doc["first_hit"]
        text += "Initial overlap: %s | near tangency: %s\n" % [
            str(hit["initial_overlap"]), str(hit["near_tangency"])]
        text += ("Normal: %s\n" % str(normal)) if normal_resolved else (
            "Normal: unresolved (zero separation)\n")
    text += "Numerical source geometry only. NOT Havok gameplay, editing or Save As."
    return text

func _segment(mesh: ImmediateMesh, a: Vector3,
              b: Vector3, color: Color) -> void:
    mesh.surface_set_color(color)
    mesh.surface_add_vertex(a)
    mesh.surface_set_color(color)
    mesh.surface_add_vertex(b)

func _outline_capsule(mesh: ImmediateMesh, center: Vector3, ink: Color) -> void:
    var reference := Vector3.UP if absf(axis.dot(Vector3.UP)) < 0.9 else Vector3.RIGHT
    var u := axis.cross(reference).normalized()
    var v := axis.cross(u).normalized()
    var low := center - axis * axis_half
    var high := center + axis * axis_half
    _segment(mesh, low, high, ink)
    for base in [low, high]:
        for i in 16:
            var a := TAU * float(i) / 16.0
            var b := TAU * float(i+1) / 16.0
            var first := base + radius * (u * cos(a) + v * sin(a))
            var last := base + radius * (u * cos(b) + v * sin(b))
            _segment(mesh, first, last, ink)
    for i in 4:
        var angle := TAU * float(i) / 4.0
        var offset := radius * (u * cos(angle) + v * sin(angle))
        _segment(mesh, low + offset, high + offset, ink)

func make_mesh() -> ImmediateMesh:
    if not ready:
        return null
    var mesh := ImmediateMesh.new()
    mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    _segment(mesh, start, finish, Color(0.15, 0.9, 1.0))
    _outline_capsule(mesh, start, Color(0.1, 0.5, 1.0))
    _outline_capsule(mesh, finish, Color(0.35, 0.75, 1.0))
    if contact_triangle_id >= 0:
        var center := start.lerp(finish, contact_t)
        _outline_capsule(mesh, center, Color(1.0, 0.82, 0.15))
        var cross_size := maxf(radius * 0.6, 0.03)
        for basis in [Vector3.RIGHT, Vector3.UP, Vector3.BACK]:
            _segment(mesh, contact_triangle_point - basis * cross_size,
                     contact_triangle_point + basis * cross_size,
                     Color(1.0, 0.27, 0.35))
        _segment(mesh, contact_triangle_point, contact_axis_point,
                 Color(0.94, 0.37, 0.95))
        if normal_resolved:
            var arrow_length := maxf(2.0 * radius, 0.2)
            _segment(mesh, contact_triangle_point,
                     contact_triangle_point + normal * arrow_length,
                     Color(1.0, 0.15, 0.86))
    mesh.surface_end()
    return mesh
