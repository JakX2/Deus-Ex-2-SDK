extends RefCounted
## Read-only per-height original Level capsule CHORD overlay, not a physics
## manifold, collision editor, traversability classifier or Havok runtime.
## Every displayed segment must match the authenticated worker's submitted
## baseline and requested offsets, not arbitrary JSON-supplied coordinates.

const SCHEMA := "DX2Ed-source-edge-capsule-height-profile-v1"
const COORD := "Godot preview (Level.x/10, Level.z/10, Level.y/10)"
const MAX_POSITION := 100000.0
const EPS := 0.00001

var ready := false
var last_error := ""
var start := Vector3.ZERO
var finish := Vector3.ZERO
var radius_level := 0.0
var half_axis_level := 0.0
var profile_rows: Array[Dictionary] = []
var source_map := ""
var source_sha256 := ""

func clear() -> void:
    ready = false
    last_error = ""
    start = Vector3.ZERO
    finish = Vector3.ZERO
    radius_level = 0.0
    half_axis_level = 0.0
    profile_rows.clear()
    source_map = ""
    source_sha256 = ""

func _fail(message: String) -> bool:
    clear()
    last_error = message
    return false

func _number(value: Variant, low: float, high: float) -> bool:
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value))
        and float(value) >= low and float(value) <= high)

func _int(value: Variant, low: int, high: int) -> bool:
    return _number(value, float(low), float(high)) and float(value) == float(int(value))

func _xyz(value: Variant) -> bool:
    if typeof(value) != TYPE_ARRAY or value.size() != 3:
        return false
    for v in value:
        if not _number(v, -MAX_POSITION, MAX_POSITION):
            return false
    return true

func _vec(value: Array) -> Vector3:
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

func load_document(data: Dictionary, map_name: String, hash: String,
                   expected_start: Vector3, expected_end: Vector3,
                   expected_offsets: Array, expected_radius: float,
                   expected_half_axis: float, original_face_ids: Dictionary) -> bool:
    clear()
    if (map_name.is_empty() or map_name.get_file() != map_name
        or not map_name.to_lower().ends_with(".gmp")
        or hash.length() != 64 or not hash.is_valid_hex_number()
        or original_face_ids.is_empty()
        or not expected_start.is_finite() or not expected_end.is_finite()
        or expected_start.length() > MAX_POSITION
        or expected_end.length() > MAX_POSITION
        or expected_start.distance_to(expected_end) <= EPS
        or not _number(expected_radius, 0.01, 20.)
        or not _number(expected_half_axis, 0., 20.)
        or data.get("schema") != SCHEMA
        or data.get("source_map") != map_name
        or data.get("source_sha256") != hash
        or data.get("coordinate_system") != COORD
        or data.get("read_only") != true
        or data.get("not_a_native_collision_writer") != true
        or data.get("original_game_assets_modified") != false
        or data.get("havok_runtime_contact_verified") != false
        or data.get("physics_materials_verified") != false
        or data.get("height_direction_original_Level") != "positive Z"
        or data.get("height_offsets_relative_to_baseline") != true
        or data.get("contact_is_not_a_blocking_classifier") != true
        or data.get("no_contact_is_not_proof_of_walkability") != true
        or not _xyz(data.get("baseline_capsule_start_godot_xyz"))
        or not _xyz(data.get("baseline_capsule_end_godot_xyz"))
        or not _number(data.get("capsule_radius_level_units"), .01, 20.)
        or not _number(data.get("capsule_axis_half_length_level_units"), 0., 20.)):
        return _fail("Invalid, stale or unauthenticated height-profile header")
    if (_vec(data["baseline_capsule_start_godot_xyz"]).distance_to(expected_start) > EPS
        or _vec(data["baseline_capsule_end_godot_xyz"]).distance_to(expected_end) > EPS
        or absf(float(data["capsule_radius_level_units"]) - expected_radius) > EPS
        or absf(float(data["capsule_axis_half_length_level_units"]) - expected_half_axis) > EPS):
        return _fail("Profile baseline path or capsule dimensions changed after worker launch")
    var samples: Variant = data.get("profile_samples")
    if (typeof(samples) != TYPE_ARRAY or expected_offsets.size() < 2
        or expected_offsets.size() > 9 or samples.size() != expected_offsets.size()):
        return _fail("Profile sample count differs from authenticated request")
    var accepted: Array[Dictionary] = []
    var previous := -1.0
    for i in samples.size():
        var sample: Variant = samples[i]
        if typeof(sample) != TYPE_DICTIONARY:
            return _fail("Malformed height-profile sample")
        var height: Variant = sample.get("relative_height_level_units")
        var count: Variant = sample.get("geometric_source_triangle_hits")
        var tid: Variant = sample.get("first_hit_original_triangle_id")
        var hit_t: Variant = sample.get("first_contact_path_t")
        var initial: Variant = sample.get("first_contact_initial_overlap")
        var tangent: Variant = sample.get("first_contact_near_tangency")
        if (not _number(expected_offsets[i], 0., 100.)
            or not _number(height, 0., 100.)
            or absf(float(height)-float(expected_offsets[i])) > EPS
            or (i == 0 and absf(float(height)) > EPS)
            or (i > 0 and float(height) - previous < .01 - EPS)
            or not _int(count, 0, original_face_ids.size())):
            return _fail("Profile height or geometric contact count is invalid")
        previous = float(height)
        if int(count) == 0:
            if tid != null or hit_t != null or initial != null or tangent != null:
                return _fail("No-contact row invents an original first hit")
        else:
            if (not _int(tid, 0, 300000)
                or not original_face_ids.has(int(tid))
                or not _number(hit_t, 0., 1.)
                or typeof(initial) != TYPE_BOOL
                or typeof(tangent) != TYPE_BOOL
                or (bool(initial) and absf(float(hit_t)) > EPS)):
                return _fail("Original first-hit triangle ID or timing is not credible")
        accepted.append({
            "offset": float(height),
            "count": int(count),
            "first_id": int(tid) if tid != null else -1,
            "time": float(hit_t) if hit_t != null else -1.,
            "initial_overlap": bool(initial) if initial != null else false,
            "near_tangency": bool(tangent) if tangent != null else false,
        })
    source_map = map_name
    source_sha256 = hash
    start = expected_start
    finish = expected_end
    radius_level = expected_radius
    half_axis_level = expected_half_axis
    profile_rows = accepted
    ready = true
    return true

func description() -> String:
    if not ready:
        return ""
    return ("CAPSULE HEIGHT PATHS: cyan = no static triangle contact, "
        + "amber = contact (may be floor support), pink X = first contact. "
        + "Original Level +Z vertical offsets. NOT Havok clearance, "
        + "controller navigation, collision editing or walkability.")

func _line(mesh: ImmediateMesh, a: Vector3, b: Vector3, color: Color) -> void:
    mesh.surface_set_color(color)
    mesh.surface_add_vertex(a)
    mesh.surface_set_color(color)
    mesh.surface_add_vertex(b)

func make_mesh() -> ImmediateMesh:
    if not ready or profile_rows.is_empty():
        return null
    var mesh := ImmediateMesh.new()
    mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    var tick := maxf(radius_level * 0.04, 0.008)
    var cyan := Color(.1, .92, 1.)
    var amber := Color(1., .68, .14)
    var pink := Color(1., .23, .73)
    for row in profile_rows:
        var delta := Vector3.UP * (float(row["offset"]) / 10.)
        var a: Vector3 = start + delta
        var b: Vector3 = finish + delta
        var ink: Color = cyan if int(row["count"]) == 0 else amber
        _line(mesh, a, b, ink)
        _line(mesh, a - Vector3.UP*tick, a + Vector3.UP*tick, ink)
        _line(mesh, b - Vector3.UP*tick, b + Vector3.UP*tick, ink)
        if int(row["count"]) > 0:
            var first: Vector3 = a.lerp(b, float(row["time"]))
            _line(mesh, first - Vector3.RIGHT*tick, first + Vector3.RIGHT*tick, pink)
            _line(mesh, first - Vector3.BACK*tick, first + Vector3.BACK*tick, pink)
    mesh.surface_end()
    return mesh
