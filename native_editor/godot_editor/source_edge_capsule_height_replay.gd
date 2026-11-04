extends RefCounted
## Read-only one-height detailed replay of a prior SHA-authenticated multi-height
## profile. Reuses PR #46 full-GMP independent oracle, never gameplay physics.
const Contact = preload("res://capsule_contact_preview.gd")
const EPS := 0.00001

var last_error := ""

func _fail(reason: String) -> Dictionary:
    last_error = reason
    return {}

func _point_to_level(p: Vector3) -> PackedStringArray:
    return PackedStringArray([str(p.x * 10.), str(p.z * 10.), str(p.y * 10.)])

func plan(profile: RefCounted, index: int, gmp_path: String,
          output_path: String, current_map: String, current_hash: String,
          exact_chord: Dictionary) -> Dictionary:
    last_error = ""
    if (profile == null or not bool(profile.get("ready"))
        or index < 0 or index >= profile.profile_rows.size()
        or current_map != profile.source_map
        or current_hash != profile.source_sha256
        or current_hash.length() != 64 or not current_hash.is_valid_hex_number()
        or gmp_path.get_file() != current_map
        or gmp_path.get_extension().to_lower() != "gmp"
        or output_path.get_extension().to_lower() != "json"
        or exact_chord.get("schema", "") != "DX2Ed-source-exact-edge-capsule-chord-v1"
        or exact_chord.get("source_map") != current_map
        or exact_chord.get("source_sha256") != current_hash
        or exact_chord.get("source_exact_welded_connectivity") != true
        or not (exact_chord.get("start_godot_xyz") is Vector3)
        or not (exact_chord.get("end_godot_xyz") is Vector3)
        or not (exact_chord["start_godot_xyz"] as Vector3).is_finite()
        or not (exact_chord["end_godot_xyz"] as Vector3).is_finite()
        or (exact_chord["start_godot_xyz"] as Vector3).distance_to(profile.start) > EPS
        or (exact_chord["end_godot_xyz"] as Vector3).distance_to(profile.finish) > EPS
        or absf(float(exact_chord.get("radius_level_units", -1.)) - profile.radius_level) > EPS
        or absf(float(exact_chord.get("axis_half_length_level_units", -1.)) - profile.half_axis_level) > EPS):
        return _fail("Invalid or stale source-exact capsule height replay request")
    var entry: Dictionary = profile.profile_rows[index]
    var offset: float = float(entry["offset"])
    if not is_finite(offset) or offset < 0. or offset > 100.:
        return _fail("Invalid height offset in authenticated profile")
    var rise := Vector3.UP * (offset / 10.)
    var a: Vector3 = profile.start + rise
    var b: Vector3 = profile.finish + rise
    if not a.is_finite() or not b.is_finite() or a.distance_to(b) <= EPS:
        return _fail("Translated source chord is invalid")
    var args := PackedStringArray([
        "--map", gmp_path, "--output", output_path,
        "--expected-sha256", current_hash, "--start"])
    args.append_array(_point_to_level(a))
    args.append("--end")
    args.append_array(_point_to_level(b))
    args.append_array(PackedStringArray([
        "--radius", str(profile.radius_level), "--axis", "0", "0", "1",
        "--axis-half-length", str(profile.half_axis_level)]))
    return {
        "index": index, "source_map": current_map, "source_sha256": current_hash,
        "start_godot_xyz": a, "end_godot_xyz": b,
        "radius_level_units": profile.radius_level,
        "axis_half_length_level_units": profile.half_axis_level,
        "expected_row": entry.duplicate(true),
        "arguments": args,
        "research_only": true,
    }

func verify_replay_document(document: Dictionary, plan_data: Dictionary,
                            face_ids: Dictionary) -> bool:
    last_error = ""
    if (plan_data.is_empty() or face_ids.is_empty()
        or not (plan_data.get("start_godot_xyz") is Vector3)
        or not (plan_data.get("end_godot_xyz") is Vector3)):
        last_error = "Missing authenticated replay plan"
        return false
    var contact = Contact.new()
    if not contact.load_document(document, str(plan_data["source_sha256"]),
                                 str(plan_data["source_map"]), face_ids):
        last_error = "Invalid independent first-contact detail: " + contact.last_error
        return false
    var expected_a: Vector3 = plan_data["start_godot_xyz"]
    var expected_b: Vector3 = plan_data["end_godot_xyz"]
    var row: Dictionary = plan_data["expected_row"]
    if (contact.start.distance_to(expected_a) > EPS
        or contact.finish.distance_to(expected_b) > EPS
        or contact.axis.distance_to(Vector3.UP) > EPS
        or absf(contact.radius * 10. - float(plan_data["radius_level_units"])) > EPS
        or absf(contact.axis_half * 10. - float(plan_data["axis_half_length_level_units"])) > EPS
        or int(document["geometric_source_triangle_hits"]) != int(row["count"])
        or contact.contact_triangle_id != int(row["first_id"])
        or (contact.contact_triangle_id >= 0 and (
            absf(contact.contact_t - float(row["time"])) > 0.00001
            or bool(document["first_hit"]["initial_overlap"]) != (float(row["time"]) == 0.)
        ))):
        last_error = "Detailed replay disagrees with authenticated height-profile geometry"
        return false
    return true
