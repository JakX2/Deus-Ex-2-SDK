#!/usr/bin/env python3
"""Original DX2 GameSys-92 raw-index hypotheses, aggregated across a map.

The only valid input is an independently re-decoded, original GMP actor
GameSys 92 array, cross-checked against source-hashed actor cache by
dx2_actor_script_name_candidates. This module compares five name-table
*offset hypotheses* and reports their evidence counts, without selecting a
winner or claiming runtime FName/script semantics. Read-only source research.
"""
from __future__ import annotations

from collections import Counter

SCHEMA = "DX2Ed-original-GameSys92-name-index-hypothesis-audit-v1"
OFFSETS = (-2, -1, 0, 1, 2)
MAX_NAME_TABLE = 3_000_000
MAX_ACTORS = 30_000
MAX_INDICES_PER_ACTOR = 256


def unavailable(reason: str = "no_independently_verified_numeric_arrays") -> dict:
    return {
        "schema": SCHEMA,
        "status": reason,
        "read_only": True,
        "source_actor_values_redecoded": False,
        "name_table_integer_semantics_verified": False,
        "runtime_actor_script_binding_verified": False,
        "preferred_index_offset": None,
        "native_script_writer_enabled": False,
        "counts": {
            "actors_considered": 0,
            "verified_numeric_array_actors": 0,
            "distinct_raw_values": 0,
            "raw_value_occurrences": 0,
            "actors_skipped_unverified_or_opaque": 0,
        },
        "offsets": [],
        "warning": (
            "These are relative name-table position hypotheses, not decoded "
            "GameSys array element semantics or an in-game script binding."
        ),
    }


def _unique_casefolded(rows: list[dict], field: str) -> set[str]:
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed original script evidence")
        name = row.get(field)
        if not isinstance(name, str) or not name:
            raise ValueError("Invalid original script identity")
        folded = name.casefold()
        if folded in seen:
            raise ValueError("Ambiguous source script identities")
        seen.add(folded)
    return seen


def audit_name_offset_hypotheses(
    name_table: list[str],
    native_actor_probe: list[dict],
    original_definitions: list[dict],
    original_ibd_entries: list[dict],
) -> dict:
    """Count source ZIP/IBD matches under offset hypotheses [-2..2].

    Every input actor must already carry the independent GMP-native check
    result. We *only* use a row if that check verified the original GameSys
    property 92, and its raw values are an unambiguously redecoded compact
    integer array. All other actors are excluded and counted.
    """
    if (not isinstance(name_table, list)
            or len(name_table) > MAX_NAME_TABLE
            or not all(isinstance(x, str) for x in name_table)
            or not isinstance(native_actor_probe, list)
            or len(native_actor_probe) > MAX_ACTORS):
        raise ValueError("Unsupported or oversized original GMP source")
    zip_names = _unique_casefolded(original_definitions, "id")
    ibd_names = _unique_casefolded(original_ibd_entries, "script_id")
    ibd_status = {row["script_id"].casefold(): row.get("status")
                  for row in original_ibd_entries}
    if not all(value in (
        "exact_payload", "different_payload", "not_in_original_zip")
            for value in ibd_status.values()):
        raise ValueError("Invalid source IBD identity status")

    probe = unavailable()
    observed: list[tuple[int, list[int]]] = []
    skipped = 0
    for actor in native_actor_probe:
        if not isinstance(actor, dict):
            raise ValueError("Malformed native actor evidence")
        if (actor.get("native_game_property_92_verified") is not True
                or actor.get("numeric_slots_are_name_references_verified") is not False
                or actor.get("status") != "numeric_array_redecoded"):
            skipped += 1
            continue
        candidates = actor.get("candidates")
        if (not isinstance(candidates, list)
                or len(candidates) > MAX_INDICES_PER_ACTOR):
            raise ValueError("Malformed source-verified compact array")
        ids = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("Malformed original script name-slot candidate")
            number = candidate.get("raw_compact_integer")
            if type(number) is not int:
                raise ValueError("A raw GameSys compact index must be an integer")
            # Fail closed on forged precomputed direct-slot candidates.
            expected = (name_table[number]
                        if 0 <= number < len(name_table) and
                        name_table[number] else None)
            if (candidate.get("name_at_same_numeric_slot") != expected
                    or candidate.get("slot_in_package_name_table") is not
                       (expected is not None)
                    or candidate.get("same_name_in_original_tsd_archive") is not
                       (expected is not None and
                        expected.casefold() in zip_names)
                    or candidate.get("ibd_resource_payload_status") !=
                       (ibd_status.get(expected.casefold(), "not_found")
                        if expected is not None else "not_found")
                    or candidate.get("actor_runtime_link_verified") is not False):
                raise ValueError("Forged original package-name-slot evidence")
            ids.append(number)
        export = actor.get("export")
        if type(export) is not int or export < 1:
            raise ValueError("Missing original actor native export")
        observed.append((export, ids))

    if not observed:
        probe["counts"]["actors_considered"] = len(native_actor_probe)
        probe["counts"]["actors_skipped_unverified_or_opaque"] = skipped
        return probe

    probe["status"] = (
        "original_name_offset_controls_computed"
        if skipped == 0 else "partial_original_actor_verification"
    )
    probe["source_actor_values_redecoded"] = True
    total_raw = [n for _, values in observed for n in values]
    probe["counts"] = {
        "actors_considered": len(native_actor_probe),
        "verified_numeric_array_actors": len(observed),
        "distinct_raw_values": len(set(total_raw)),
        "raw_value_occurrences": len(total_raw),
        "actors_skipped_unverified_or_opaque": skipped,
    }
    offsets = []
    for delta in OFFSETS:
        slot_count = 0
        tsd_hit_count = 0
        exact_count = 0
        differing_count = 0
        actors_tsd = 0
        actors_exact = 0
        unique_tsd = set()
        unique_exact = set()
        duplicate_values = Counter()
        for _export, raw_values in observed:
            actor_has_tsd = False
            actor_has_exact = False
            for n in raw_values:
                shifted = n + delta
                if not 0 <= shifted < len(name_table):
                    continue
                name = name_table[shifted]
                if not name:
                    continue
                slot_count += 1
                folded = name.casefold()
                duplicate_values[folded] += 1
                if folded in zip_names:
                    tsd_hit_count += 1
                    unique_tsd.add(folded)
                    actor_has_tsd = True
                    if ibd_status.get(folded) == "exact_payload":
                        exact_count += 1
                        unique_exact.add(folded)
                        actor_has_exact = True
                    elif ibd_status.get(folded) == "different_payload":
                        differing_count += 1
            actors_tsd += int(actor_has_tsd)
            actors_exact += int(actor_has_exact)
        offsets.append({
            "name_table_index_delta": delta,
            "source_numeric_values": len(total_raw),
            "positions_with_nonempty_names": slot_count,
            "original_zip_script_name_hits": tsd_hit_count,
            "distinct_original_zip_scripts": len(unique_tsd),
            "original_ibd_exact_payload_name_hits": exact_count,
            "distinct_original_ibd_exact_scripts": len(unique_exact),
            "original_ibd_different_payload_name_hits": differing_count,
            "actors_with_zip_script_name_hits": actors_tsd,
            "actors_with_ibd_exact_script_hits": actors_exact,
            "repeated_name_slot_occurrences": sum(
                count - 1 for count in duplicate_values.values()
                if count > 1),
            "name_table_mapping_proven": False,
            "actor_script_runtime_binding_proven": False,
        })
    probe["offsets"] = offsets
    return probe
