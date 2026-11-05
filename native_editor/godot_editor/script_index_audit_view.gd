extends RefCounted
## Safe presentation of the optional map-wide GameSys 92 offset comparison.
## This must NEVER select a winning offset or imply actual actor script links.
const SCHEMA := "DX2Ed-original-GameSys92-name-index-hypothesis-audit-v1"
const DELTAS := [-2, -1, 0, 1, 2]
const MAX_ACTORS := 30000
const MAX_RAW := 30000 * 256

static func _int_in(value: Variant, limit: int) -> bool:
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value))
        and float(value) >= 0.0
        and float(value) <= float(limit)
        and float(int(value)) == float(value))

static func _counts_ok(c: Dictionary) -> bool:
    for key in ["actors_considered", "verified_numeric_array_actors",
                "distinct_raw_values", "raw_value_occurrences",
                "actors_skipped_unverified_or_opaque"]:
        if not _int_in(c.get(key), MAX_RAW):
            return false
    return (
        int(c["actors_considered"]) <= MAX_ACTORS
        and int(c["verified_numeric_array_actors"]) <= int(c["actors_considered"])
        and int(c["verified_numeric_array_actors"])
            + int(c["actors_skipped_unverified_or_opaque"])
            == int(c["actors_considered"])
        and int(c["distinct_raw_values"]) <= int(c["raw_value_occurrences"]))

static func format_audit(doc: Variant) -> String:
    if typeof(doc) != TYPE_DICTIONARY:
        return ""
    if (doc.get("schema") != SCHEMA
        or doc.get("read_only") != true
        or doc.get("name_table_integer_semantics_verified") != false
        or doc.get("runtime_actor_script_binding_verified") != false
        or doc.get("native_script_writer_enabled") != false
        or doc.get("preferred_index_offset") != null
        or typeof(doc.get("counts")) != TYPE_DICTIONARY
        or typeof(doc.get("offsets")) != TYPE_ARRAY
        or not _counts_ok(doc["counts"])):
        return ""
    var counts: Dictionary = doc["counts"]
    var state := str(doc.get("status", ""))
    var no_evidence := state in [
        "source_package_unavailable", "source_evidence_inconsistent",
        "no_independently_verified_numeric_arrays"]
    if no_evidence:
        if (doc.get("source_actor_values_redecoded") != false
            or not doc["offsets"].is_empty()):
            return ""
        return (
            "MAP-WIDE ORIGINAL GAMEPROPERTY 92 INDEX AUDIT\n"
            + "Status: " + state + "\n"
            + "No verified numeric-array hypotheses could be computed.\n"
            + "Actor-to-script runtime bindings remain UNRESOLVED."
        )
    if (state not in [
        "original_name_offset_controls_computed",
        "partial_original_actor_verification"]
        or doc.get("source_actor_values_redecoded") != true
        or doc["offsets"].size() != DELTAS.size()):
        return ""
    var entries: Array = doc["offsets"]
    var seen: Dictionary = {}
    for entry in entries:
        if typeof(entry) != TYPE_DICTIONARY:
            return ""
        var raw_delta: Variant = entry.get("name_table_index_delta")
        if (typeof(raw_delta) not in [TYPE_INT, TYPE_FLOAT]
            or not is_finite(float(raw_delta))
            or float(int(raw_delta)) != float(raw_delta)):
            return ""
        var delta := int(raw_delta)
        if delta not in DELTAS or seen.has(delta):
            return ""
        seen[delta] = true
        if (entry.get("name_table_mapping_proven") != false
            or entry.get("actor_script_runtime_binding_proven") != false):
            return ""
        for key in [
            "source_numeric_values", "positions_with_nonempty_names",
            "original_zip_script_name_hits", "distinct_original_zip_scripts",
            "original_ibd_exact_payload_name_hits",
            "distinct_original_ibd_exact_scripts",
            "original_ibd_different_payload_name_hits",
            "actors_with_zip_script_name_hits",
            "actors_with_ibd_exact_script_hits",
            "repeated_name_slot_occurrences"]:
            if not _int_in(entry.get(key), MAX_RAW):
                return ""
        if (int(entry["source_numeric_values"]) != int(counts["raw_value_occurrences"])
            or int(entry["positions_with_nonempty_names"])
                > int(entry["source_numeric_values"])
            or int(entry["original_zip_script_name_hits"])
                > int(entry["positions_with_nonempty_names"])
            or int(entry["original_ibd_exact_payload_name_hits"])
                + int(entry["original_ibd_different_payload_name_hits"])
                > int(entry["original_zip_script_name_hits"])
            or int(entry["distinct_original_zip_scripts"])
                > int(entry["original_zip_script_name_hits"])
            or int(entry["distinct_original_ibd_exact_scripts"])
                > int(entry["original_ibd_exact_payload_name_hits"])
            or int(entry["actors_with_zip_script_name_hits"])
                > int(counts["verified_numeric_array_actors"])
            or int(entry["actors_with_ibd_exact_script_hits"])
                > int(counts["verified_numeric_array_actors"])):
            return ""
    var lines := PackedStringArray([
        "MAP-WIDE ORIGINAL GAMEPROPERTY 92 INDEX AUDIT | READ ONLY",
        "Source state: " + state,
        "Original actors considered: " + str(counts["actors_considered"]),
        "Verified native numeric-array actors: "
            + str(counts["verified_numeric_array_actors"]),
        "Unverified/opaque actors excluded: "
            + str(counts["actors_skipped_unverified_or_opaque"]),
        "Raw numeric values: " + str(counts["raw_value_occurrences"]),
        "Distinct raw values: " + str(counts["distinct_raw_values"]),
        "",
        "OFFSET | NONEMPTY NAME SLOTS | ZIP SCRIPT HITS | IBD EXACT | IBD DIFFERS",
    ])
    for delta in DELTAS:
        for entry in entries:
            if int(entry["name_table_index_delta"]) != delta:
                continue
            lines.append("%d | %d | %d | %d | %d" % [
                delta, int(entry["positions_with_nonempty_names"]),
                int(entry["original_zip_script_name_hits"]),
                int(entry["original_ibd_exact_payload_name_hits"]),
                int(entry["original_ibd_different_payload_name_hits"]),
            ])
    lines.append("")
    lines.append("These offsets are exploratory name-table POSITION CONTROLS.")
    lines.append("More ZIP/IBD matches do NOT prove the GameSys array stores FName indices.")
    lines.append("No preferred offset is chosen. No actor runtime link is verified.")
    lines.append("Native TriggerScript editing and game-file writes remain disabled.")
    return "\n".join(lines)
