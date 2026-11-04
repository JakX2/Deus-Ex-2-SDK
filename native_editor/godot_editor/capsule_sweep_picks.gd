extends RefCounted
## Original Level capsule sweep PICK STATE only. No Havok contact and no GMP writes.
## Supports two source-authenticated viewport triangle picks with optional signed
## offsets along the source triangle's winding-dependent geometric normal.

const SCHEMA := "DX2Ed-interactive-source-capsule-research-picks-v1"
const MAX_LEVEL_OFFSET := 1000.0
const MAX_LEVEL_SHAPE := 1000.0
const MIN_SEGMENT_PREVIEW := 0.00000001

var source_map := ""
var source_sha256 := ""
var picking := 0  # 0 idle; 1 start; 2 end
var start_set := false
var end_set := false
var start_preview := Vector3.ZERO
var end_preview := Vector3.ZERO
var start_triangle_id := -1
var end_triangle_id := -1
var last_error := ""

func clear() -> void:
    source_map = ""
    source_sha256 = ""
    picking = 0
    start_set = false
    end_set = false
    start_preview = Vector3.ZERO
    end_preview = Vector3.ZERO
    start_triangle_id = -1
    end_triangle_id = -1
    last_error = ""

func _identity(map_name: String, sha: String) -> bool:
    return (not map_name.is_empty() and map_name.get_file() == map_name
        and map_name.to_lower().ends_with(".gmp")
        and sha.length() == 64 and sha.is_valid_hex_number())

func begin_pick(which: int, map_name: String, sha: String) -> bool:
    last_error = ""
    if which not in [1, 2] or not _identity(map_name, sha):
        last_error = "Source map or capsule point choice is invalid"
        return false
    if source_map != map_name or source_sha256 != sha:
        clear()
        source_map = map_name
        source_sha256 = sha
    picking = which
    return true

func capture_hit(hit: Dictionary, face_ids: Dictionary, map_name: String,
                 sha: String, offset_level: float) -> bool:
    last_error = ""
    if (picking not in [1, 2] or map_name != source_map
        or sha != source_sha256 or face_ids.is_empty()
        or not is_finite(offset_level) or absf(offset_level) > MAX_LEVEL_OFFSET
        or not bool(hit.get("selection_is_ray_hit", false))
        or typeof(hit.get("original_level_triangle_id")) != TYPE_INT
        or not face_ids.has(int(hit["original_level_triangle_id"]))
        or not (hit.get("point_godot") is Vector3)
        or not (hit.get("normal_godot") is Vector3)):
        last_error = "Expected original source-hash-matched triangle ray hit"
        return false
    var point: Vector3 = hit["point_godot"]
    var normal: Vector3 = hit["normal_godot"]
    if (not point.is_finite() or not normal.is_finite()
        or normal.length() < 0.0000001
        or absf(normal.length() - 1.0) > 0.001):
        last_error = "Source collision point or geometric normal is invalid"
        return false
    var adjusted: Vector3 = point + normal.normalized() * (offset_level / 10.0)
    if not adjusted.is_finite() or adjusted.length() > 100000.0:
        last_error = "Offset source position exceeded safe preview bounds"
        return false
    if picking == 1:
        start_preview = adjusted
        start_triangle_id = int(hit["original_level_triangle_id"])
        start_set = true
    else:
        end_preview = adjusted
        end_triangle_id = int(hit["original_level_triangle_id"])
        end_set = true
    picking = 0
    return true

func can_run() -> bool:
    return (start_set and end_set and picking == 0
        and _identity(source_map, source_sha256)
        and start_preview.is_finite() and end_preview.is_finite()
        and start_preview.distance_to(end_preview) > MIN_SEGMENT_PREVIEW)

func level_xyz(godot_xyz: Vector3) -> PackedStringArray:
    # Inverse of original source Level XYZ -> (x/10,z/10,y/10).
    return PackedStringArray([
        str(godot_xyz.x * 10.0), str(godot_xyz.z * 10.0),
        str(godot_xyz.y * 10.0)])

func export_arguments(original_gmp: String, output_json: String,
                      radius_level: float, axis_half_level: float) -> PackedStringArray:
    last_error = ""
    if not can_run():
        last_error = "Pick two distinct original source collision points first"
        return PackedStringArray()
    if (not is_finite(radius_level) or radius_level < 0.0
        or radius_level > MAX_LEVEL_SHAPE
        or not is_finite(axis_half_level) or axis_half_level < 0.0
        or axis_half_level > MAX_LEVEL_SHAPE
        or original_gmp.get_file() != source_map
        or original_gmp.get_extension().to_lower() != "gmp"
        or output_json.get_extension().to_lower() != "json"
        or original_gmp.simplify_path() == output_json.simplify_path()):
        last_error = "Invalid shape, original GMP, or private research output"
        return PackedStringArray()
    var args := PackedStringArray([
        "--map", original_gmp, "--output", output_json,
        "--expected-sha256", source_sha256, "--start"])
    args.append_array(level_xyz(start_preview))
    args.append("--end")
    args.append_array(level_xyz(end_preview))
    args.append_array(PackedStringArray([
        "--radius", str(radius_level),
        "--axis", "0", "0", "1",
        "--axis-half-length", str(axis_half_level)]))
    return args

func description() -> String:
    var result := "INTERACTIVE CAPSULE SWEEP | GEOMETRIC RESEARCH ONLY\n"
    result += "Pick two original Level collision faces with the left mouse button.\n"
    result += "Signed offsets follow triangle WINDING normal, not verified game gravity.\n"
    if start_set:
        result += "Start, triangle #%d: %s (Godot)\n" % [start_triangle_id, str(start_preview)]
    else:
        result += "Start: not selected\n"
    if end_set:
        result += "End, triangle #%d: %s (Godot)\n" % [end_triangle_id, str(end_preview)]
    else:
        result += "End: not selected\n"
    if picking != 0:
        result += "Waiting for %s surface click.\n" % ("START" if picking == 1 else "END")
    if start_set and end_set and not can_run():
        result += "Choose different points or offsets: the current trajectory is too short.\n"
    result += "Native Havok collision, character movement and writable maps NOT verified."
    return result
