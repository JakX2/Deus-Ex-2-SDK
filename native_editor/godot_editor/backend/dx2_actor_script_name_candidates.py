#!/usr/bin/env python3
"""Source-constrained, read-only actor TriggerScripts *candidate* name lookup.

The existing DX2 GameSys parser can decode array fields as compact integer
indices, and the GMP has an original Unreal name table. This module checks
what *name happens to reside at each integer position*. It DOES NOT establish
that the original native TriggerScripts array stores Unreal FName indices.

A candidate that also names a TSD definition and an exactly matching IBD
resource is stronger cross-source evidence, but still NOT a verified
actor->script runtime binding. This module never emits native write plans.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
MAP_EXPORTER = ROOT / "map_exporter"
if str(MAP_EXPORTER) not in sys.path:
    sys.path.insert(0, str(MAP_EXPORTER))

from dx2inspect import Package
from dx2scene import decode_full_actor

MAX_NAME_TABLE = 3_000_000
MAX_ACTORS = 30_000
MAX_ITEMS_PER_ACTOR = 256


def _int(value: object) -> bool:
    return type(value) is int


def inspect_name_candidates(
    package: object,
    source_actor_rows: list[dict],
    definitions: list[dict],
    ibd_entries: list[dict],
    *,
    decoder=decode_full_actor,
) -> dict:
    """Check native GameSys 92 bytes and compare numeric slots with names.

    The caller already validated source file SHA, original actor cache, ZIP
    and IBD provenance. This function independently decodes original GMP
    actor blocks, refusing forged cached raw properties or export identity.
    """
    unavailable = {
        "status": "source_package_unavailable",
        "read_only": True,
        "actor_to_script_binding_verified": False,
        "name_table_indices_semantics_verified": False,
        "native_script_writer_enabled": False,
        "actors": [],
        "counts": {
            "source_script_actors": len(source_actor_rows),
            "native_property_verified": 0,
            "candidate_name_slots": 0,
            "source_tsd_name_candidates": 0,
            "ibd_exact_name_candidates": 0,
            "source_actor_unverified": len(source_actor_rows),
        },
    }
    if (len(source_actor_rows) > MAX_ACTORS
            or not isinstance(getattr(package, "names", None), list)
            or len(package.names) > MAX_NAME_TABLE
            or not isinstance(getattr(package, "exports", None), list)
            or package.version != 95 or package.licensee not in (68, 69)):
        return unavailable

    zip_ids = {str(r["id"]).casefold() for r in definitions}
    ibd_by_name = {
        str(r["script_id"]).casefold(): r["status"]
        for r in ibd_entries
    }
    actors = []
    counts = dict(unavailable["counts"])
    for cache in source_actor_rows:
        row = {
            "actor": cache.get("actor"),
            "class": cache.get("class"),
            "export": cache.get("export"),
            "native_game_property_92_verified": False,
            "numeric_slots_are_name_references_verified": False,
            "status": "unverified_native_actor",
            "candidates": [],
        }
        actors.append(row)
        index = cache.get("export")
        if not _int(index) or index < 1 or index > len(package.exports):
            continue
        original = package.exports[index - 1]
        if (original.get("index") != index
                or original.get("name") != cache.get("actor")
                or package.class_name(original) != cache.get("class")):
            continue
        try:
            _tagged, blocks = decoder(package, original, {})
        except (ValueError, IndexError, KeyError, TypeError, OverflowError):
            continue
        props = [b for b in blocks
                 if type(b) is dict and b.get("id") == 92]
        if len(props) != 1 or props[0].get("value") != cache.get("raw_property"):
            row["status"] = "native_cache_property_mismatch"
            continue

        row["native_game_property_92_verified"] = True
        counts["native_property_verified"] += 1
        counts["source_actor_unverified"] -= 1
        value = props[0]["value"]
        if (type(value) is not dict
                or value.get("interpretation") != "index"
                or type(value.get("items")) is not list
                or len(value["items"]) > MAX_ITEMS_PER_ACTOR):
            row["status"] = "opaque_native_array"
            continue

        row["status"] = "numeric_array_redecoded"
        for n in value["items"]:
            candidate = {
                "raw_compact_integer": n,
                "name_at_same_numeric_slot": None,
                "slot_in_package_name_table": False,
                "same_name_in_original_tsd_archive": False,
                "ibd_resource_payload_status": "not_found",
                "actor_runtime_link_verified": False,
            }
            if (_int(n) and 0 <= n < len(package.names)
                    and isinstance(package.names[n], str)
                    and package.names[n]):
                name = package.names[n]
                name_key = name.casefold()
                candidate["name_at_same_numeric_slot"] = name
                candidate["slot_in_package_name_table"] = True
                candidate["same_name_in_original_tsd_archive"] = name_key in zip_ids
                candidate["ibd_resource_payload_status"] = ibd_by_name.get(
                    name_key, "not_found")
                counts["candidate_name_slots"] += 1
                if candidate["same_name_in_original_tsd_archive"]:
                    counts["source_tsd_name_candidates"] += 1
                    if candidate["ibd_resource_payload_status"] == "exact_payload":
                        counts["ibd_exact_name_candidates"] += 1
            row["candidates"].append(candidate)

    unavailable["status"] = "original_package_name_slots_inspected"
    unavailable["actors"] = actors
    unavailable["counts"] = counts
    return unavailable


def inspect_original_package(
    map_path: Path, source_actor_rows: list[dict],
    definitions: list[dict], ibd_entries: list[dict],
) -> dict:
    """Best-effort independent native source decode; never fail IBD proof.

    Failed original GMP decoding yields no speculative actor bindings while
    preserving the separately verified original TSD<->IBD results.
    """
    try:
        package = Package(Path(map_path))
        return inspect_name_candidates(
            package, source_actor_rows, definitions, ibd_entries)
    except Exception:
        # Optional research must never make previously verified original
        # TSD/IBD resource comparisons fail. A malformed or unfamiliar GMP
        # actor encoding therefore yields *no* candidate links.
        return inspect_name_candidates(
            None, source_actor_rows, definitions, ibd_entries)
