extends RefCounted
## Private original-file report formatter, with aggregate-only clipboard output.
## Original script IDs may appear in detail view ONLY, not summary/clipboard.
const SCHEMA := "DX2Ed-original-mission-kernel-TSD-comparison-v1"
const STATES := ["absent", "exact_payload", "different_payload", "not_in_original_zip"]
const LIMIT := 6000

static func _count(v: Variant, max_value: int = 12000) -> bool:
    return (typeof(v) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(v))
        and float(v) >= 0.0 and float(v) <= float(max_value)
        and float(int(v)) == float(v))

static func valid(doc: Variant) -> bool:
    if typeof(doc) != TYPE_DICTIONARY:
        return false
    if (doc.get("schema") != SCHEMA
        or doc.get("read_only") != true
        or doc.get("native_script_writer_enabled") != false
        or doc.get("runtime_actor_script_binding_verified") != false
        or doc.get("native_actor_script_indices_resolved") != false
        or doc.get("original_game_assets_modified") != false
        or doc.get("gameplay_runtime_verified") != false
        or str(doc.get("kernel_ibd_name", "")).to_lower() != "kernel_tsdall.ibd"
        or typeof(doc.get("counts")) != TYPE_DICTIONARY
        or typeof(doc.get("script_rows")) != TYPE_ARRAY
        or doc["script_rows"].size() > LIMIT * 2
        or typeof(doc.get("source_status_transitions")) != TYPE_DICTIONARY
        or typeof(doc.get("actor_name_slot_candidates")) != TYPE_DICTIONARY):
        return false
    var c: Dictionary = doc["counts"]
    for key in [
        "mission_script_resources", "kernel_script_resources",
        "shared_script_ids", "shared_payload_exact",
        "shared_payload_different", "mission_only", "kernel_only",
        "mission_vs_standalone_exact", "mission_vs_standalone_different",
        "kernel_vs_standalone_exact", "kernel_vs_standalone_different"]:
        if not _count(c.get(key), LIMIT):
            return false
    if (int(c["shared_script_ids"]) != int(c["shared_payload_exact"]) +
            int(c["shared_payload_different"])
        or int(c["mission_script_resources"]) != int(c["shared_script_ids"]) +
            int(c["mission_only"])
        or int(c["kernel_script_resources"]) != int(c["shared_script_ids"]) +
            int(c["kernel_only"])
        or int(c["mission_vs_standalone_exact"]) +
            int(c["mission_vs_standalone_different"]) >
            int(c["mission_script_resources"])
        or int(c["kernel_vs_standalone_exact"]) +
            int(c["kernel_vs_standalone_different"]) >
            int(c["kernel_script_resources"])
        or doc["script_rows"].size() != int(c["shared_script_ids"]) +
            int(c["mission_only"]) + int(c["kernel_only"])):
        return false
    var transitions: Dictionary = doc["source_status_transitions"]
    var sum := 0
    for key in transitions:
        var pair := str(key).split("_to_", false, 1)
        if (pair.size() != 2 or pair[0] not in STATES or pair[1] not in STATES
            or not _count(transitions[key], LIMIT * 2)):
            return false
        sum += int(transitions[key])
    if sum != doc["script_rows"].size():
        return false
    var actor: Dictionary = doc["actor_name_slot_candidates"]
    if (actor.get("native_actor_script_semantics_verified") != false
        or actor.get("original_actor_script_runtime_links_verified") != false
        or actor.get("status") not in [
            "source_actor_name_slots_unavailable",
            "verified_original_name_slot_candidates_not_runtime_bindings"]
        or not _count(actor.get("raw_name_slot_candidate_occurrences"), LIMIT * 256)
        or not _count(actor.get("actors_with_verified_numeric_arrays"), 30000)
        or typeof(actor.get("transition_counts")) != TYPE_DICTIONARY):
        return false
    var actor_sum := 0
    for key in actor["transition_counts"]:
        var pair := str(key).split("_to_", false, 1)
        if (pair.size() != 2 or pair[0] not in STATES or pair[1] not in STATES
            or not _count(actor["transition_counts"][key], LIMIT * 256)):
            return false
        actor_sum += int(actor["transition_counts"][key])
    if actor_sum != int(actor["raw_name_slot_candidate_occurrences"]):
        return false
    return true

static func _histogram(doc: Dictionary, key: String) -> Array:
    var counts: Dictionary = {}
    var different := 0
    var changed_size := 0
    for r in doc["script_rows"]:
        if typeof(r) != TYPE_DICTIONARY:
            continue
        var diff: Variant = r.get(key)
        if (typeof(diff) != TYPE_DICTIONARY
            or diff.get("byte_equal") != false):
            continue
        different += 1
        if diff.get("same_size") == false:
            changed_size += 1
        var index: Variant = diff.get("first_difference_offset")
        if not _count(index, 512 * 1024 * 1024):
            continue
        var slot := int(index)
        counts[slot] = int(counts.get(slot, 0)) + 1
    var ordered: Array = []
    for offset in counts:
        ordered.append({"offset": int(offset), "count": int(counts[offset])})
    ordered.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
        if a["count"] != b["count"]:
            return a["count"] > b["count"]
        return a["offset"] < b["offset"])
    return [different, changed_size, ordered.slice(0, 5)]

## Byte offsets 4..7 may form a 4-byte field. These bins do not
## interpret its contents as any native checksum, length or reference.
static func _word4_control(doc: Dictionary, key: String) -> Array:
    var field_only := 0
    var field_and_other := 0
    var other_only := 0
    var too_short := 0
    for r in doc["script_rows"]:
        if typeof(r) != TYPE_DICTIONARY:
            continue
        var d: Variant = r.get(key)
        if typeof(d) != TYPE_DICTIONARY or d.get("byte_equal") != false:
            continue
        if d.get("candidate_word4_4byte_slot_comparable") != true:
            too_short += 1
        elif d.get("candidate_word4_only_difference") == true:
            field_only += 1
        elif d.get("candidate_word4_and_other_changes") == true:
            field_and_other += 1
        else:
            other_only += 1
    return [field_only, field_and_other, other_only, too_short]


static func summary(doc: Variant) -> String:
    if not valid(doc):
        return ""
    var c: Dictionary = doc["counts"]
    var lines := PackedStringArray([
        "ORIGINAL CLUB / KERNEL TRIGGERSCRIPT COMPARISON | READ ONLY",
        "Mission vs Kernel_TSDALL.ibd | source-hash-verified inputs",
        "",
        "Original mission IBD script resources: " + str(c["mission_script_resources"]),
        "Original Kernel IBD script resources: " + str(c["kernel_script_resources"]),
        "IDs present in both: " + str(c["shared_script_ids"]),
        "Shared scripts with byte-identical mission/kernel payloads: "
            + str(c["shared_payload_exact"]),
        "Shared scripts with different mission/kernel payloads: "
            + str(c["shared_payload_different"]),
        "Only in mission IBD: " + str(c["mission_only"]),
        "Only in Kernel IBD: " + str(c["kernel_only"]),
        "",
        "MISSION VERSUS STANDALONE TSD:",
        "  Exact payloads: " + str(c["mission_vs_standalone_exact"]),
        "  Different payloads: " + str(c["mission_vs_standalone_different"]),
        "KERNEL VERSUS STANDALONE TSD:",
        "  Exact payloads: " + str(c["kernel_vs_standalone_exact"]),
        "  Different payloads: " + str(c["kernel_vs_standalone_different"]),
    ])
    for group in [
        ["MISSION / TSD", "mission_vs_standalone"],
        ["KERNEL / TSD", "kernel_vs_standalone"],
        ["MISSION / KERNEL", "mission_vs_kernel"]
    ]:
        var hist := _histogram(doc, str(group[1]))
        lines.append("")
        lines.append(str(group[0]) + " | differing script resources: "
            + str(hist[0]) + "; different lengths: " + str(hist[1]))
        lines.append("  Most common first differing byte offsets (relative to payload):")
        var offsets: Array = hist[2]
        if offsets.is_empty():
            lines.append("  none")
        else:
            for entry in offsets:
                lines.append("  byte " + str(entry["offset"]) + ": "
                    + str(entry["count"]) + " scripts")
        var word4 := _word4_control(doc, str(group[1]))
        lines.append("  Candidate bytes 4..7 only changed: " + str(word4[0]))
        lines.append("  Bytes 4..7 and other bytes/length changed: " + str(word4[1]))
        lines.append("  Other changes without bytes 4..7 changing: " + str(word4[2]))
        lines.append("  Too short to inspect candidate bytes 4..7: " + str(word4[3]))
    var actor: Dictionary = doc["actor_name_slot_candidates"]
    lines.append("")
    lines.append("ACTOR NAME-SLOT CANDIDATES (not executable bindings):")
    if actor["status"] == "source_actor_name_slots_unavailable":
        lines.append("  No independently verified source actor name-slot data.")
    else:
        lines.append("  Source-verified actors with compact arrays: "
            + str(actor["actors_with_verified_numeric_arrays"]))
        lines.append("  Original raw-index name candidates: "
            + str(actor["raw_name_slot_candidate_occurrences"]))
        for transition in actor["transition_counts"]:
            lines.append("  " + str(transition).replace("_", " ") + ": "
                + str(actor["transition_counts"][transition]))
    lines.append("")
    lines.append("Original TSD differences in candidate bytes 4..7 do NOT establish")
    lines.append("a checksum, header field, version, size or runtime reference.")
    lines.append("Original TSD mismatches may be a size/layout change, a version")
    lines.append("difference, or mission-specific data. No cause is assumed.")
    lines.append("These figures count distinct IBD resources, except actor name-slot")
    lines.append("candidate occurrences above, which may repeat a script ID.")
    lines.append("Runtime actor-to-script bindings remain UNVERIFIED.")
    lines.append("No original game assets were modified. No native writer enabled.")
    return "\n".join(lines)

static func script_details(doc: Variant, script_id: String) -> String:
    if not valid(doc) or script_id.is_empty():
        return ""
    for r in doc["script_rows"]:
        if (typeof(r) != TYPE_DICTIONARY
            or str(r.get("script_id", "")).to_lower() !=
                script_id.to_lower()):
            continue
        var lines := PackedStringArray([
            "ORIGINAL SCRIPT PAYLOAD PROVENANCE | READ ONLY",
            "Script ID: " + str(r.get("script_id", "")),
            "Mission status vs standalone TSD: "
                + str(r.get("mission_original_tsd_status", "?")),
            "Kernel status vs standalone TSD: "
                + str(r.get("kernel_original_tsd_status", "?")),
        ])
        for group in [
            ["MISSION vs STANDALONE TSD", "mission_vs_standalone"],
            ["KERNEL vs STANDALONE TSD", "kernel_vs_standalone"],
            ["MISSION vs KERNEL", "mission_vs_kernel"],
        ]:
            lines.append("")
            lines.append(str(group[0]) + ":")
            var diff: Variant = r.get(str(group[1]))
            if typeof(diff) != TYPE_DICTIONARY:
                lines.append("  No comparison: resource absent or not in original ZIP.")
                continue
            lines.append("  Byte-identical: " + str(diff.get("byte_equal", false)))
            lines.append("  Left/right payload sizes: "
                + str(diff.get("left_size", "?")) + " / "
                + str(diff.get("right_size", "?")))
            lines.append("  First differing payload byte: "
                + str(diff.get("first_difference_offset", "none")))
            lines.append("  Different overlapping bytes: "
                + str(diff.get("overlapping_different_bytes", "?")))
            lines.append("  Different-byte runs: "
                + str(diff.get("different_byte_runs_in_overlap", "?")))
            lines.append("  Common prefix/suffix bytes: "
                + str(diff.get("common_prefix_bytes", "?")) + " / "
                + str(diff.get("common_suffix_bytes", "?")))
            lines.append("  Only candidate bytes 4..7 differ: "
                + str(diff.get("candidate_word4_only_difference", false)))
            lines.append("  Candidate bytes 4..7 plus other differences: "
                + str(diff.get("candidate_word4_and_other_changes", false)))
        lines.append("")
        lines.append("Byte positions are metadata only; no retail byte values are displayed.")
        lines.append("Matching script names do NOT prove runtime actor bindings.")
        return "\n".join(lines)
    return "Selected standalone script is not present in either selected original IBD."
