#!/usr/bin/env python3
"""Compare owner-original mission IBD and Kernel_TSDALL IBD TriggerScripts.

Reads an exact source GMP / actors.json / original TriggerScript.zip trio and
two original IBD bundles. Writes a new *private* JSON report, never game files.
Two different comparisons are retained: IBD vs original standalone TSD, and
mission IBD vs kernel IBD. Also counts original GameSys-92 name-table
candidates by status, explicitly WITHOUT asserting actor runtime execution.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile, BadZipFile

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_TOOLS = ROOT / "tools" / "scripts"
if str(SCRIPT_TOOLS) not in sys.path:
    sys.path.insert(0, str(SCRIPT_TOOLS))
from dx2_script_bundle_probe import parse_tsd_resources
from dx2_gameplay_catalog import hash_path
from dx2_script_ibd_provenance import build_evidence

SCHEMA = "DX2Ed-original-mission-kernel-TSD-comparison-v1"
MAX_IBD = 512 * 1024 * 1024
MAX_RESOURCES = 6000
CATEGORIES = ("absent", "exact_payload", "different_payload", "not_in_original_zip")


def _hash(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def byte_difference(a: bytes, b: bytes) -> dict:
    """Metadata-only binary comparison with no original byte excerpts."""
    first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    prefix = min(len(a), len(b)) if first is None else first
    if first is None and len(a) != len(b):
        first = prefix
    overlap = min(len(a), len(b))
    mismatch = 0
    runs = 0
    inside = False
    for x, y in zip(a, b):
        unequal = x != y
        mismatch += int(unequal)
        if unequal and not inside:
            runs += 1
        inside = unequal
    tail = 0
    while (tail < overlap - prefix and a[len(a) - 1 - tail] ==
           b[len(b) - 1 - tail]):
        tail += 1
    return {
        "byte_equal": a == b,
        "left_size": len(a),
        "right_size": len(b),
        "same_size": len(a) == len(b),
        "first_difference_offset": first,
        "common_prefix_bytes": prefix,
        "common_suffix_bytes": tail if a != b else len(a),
        "overlapping_different_bytes": mismatch,
        "different_byte_runs_in_overlap": runs,
        "size_difference_bytes": len(b) - len(a),
    }


def _source_script_rows(evidence: dict) -> dict[str, dict]:
    rows = {r["script_id"].casefold(): r for r in evidence["entries"]}
    if len(rows) != len(evidence["entries"]):
        raise ValueError("Duplicate original bundle script identifiers")
    return rows


def _unpack_bundle(path: Path, evidence: dict) -> tuple[bytes, dict]:
    if path.stat().st_size > MAX_IBD:
        raise ValueError("IBD exceeds safety size")
    blob = path.read_bytes()
    if _hash(blob) != evidence["ibd_sha256"]:
        raise ValueError("Original IBD changed during comparison")
    meta, rows = parse_tsd_resources(blob, bundle_name=path.name)
    if len(rows) > MAX_RESOURCES or meta["trigger_scripts"] != len(rows):
        raise ValueError("Invalid original IBD script resource count")
    return blob, rows


def _extract(blob: bytes, record: dict) -> bytes:
    start, size = record["offset"], record["size"]
    if (type(start) is not int or type(size) is not int
            or start < 0 or size <= 0 or start + size > len(blob)):
        raise ValueError("Original IBD script payload extent invalid")
    return blob[start:start + size]


def _status(row: dict | None) -> str:
    return row["status"] if row is not None else "absent"


def _actor_reference_summary(first: dict, second: dict,
                             mission: dict, kernel: dict) -> dict:
    """Count *possible* direct GMP name-slot references without claiming links."""
    common = {
        "status": "source_actor_name_slots_unavailable",
        "native_actor_script_semantics_verified": False,
        "original_actor_script_runtime_links_verified": False,
        "raw_name_slot_candidate_occurrences": 0,
        "actors_with_verified_numeric_arrays": 0,
        "transition_counts": {},
    }
    if (first.get("status") != "original_package_name_slots_inspected"
            or second.get("status") != "original_package_name_slots_inspected"):
        return common
    left, right = first.get("actors"), second.get("actors")
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
        return common
    counts = Counter()
    references = 0
    verified = 0
    for a, b in zip(left, right):
        if ((a.get("actor"), a.get("class"), a.get("export"), a.get("status")) !=
                (b.get("actor"), b.get("class"), b.get("export"), b.get("status"))):
            return common
        if (a.get("native_game_property_92_verified") is not True
                or a.get("status") != "numeric_array_redecoded"):
            continue
        aa, bb = a.get("candidates", []), b.get("candidates", [])
        if len(aa) != len(bb):
            return common
        verified += 1
        for x, y in zip(aa, bb):
            if (x.get("raw_compact_integer") != y.get("raw_compact_integer")
                    or x.get("name_at_same_numeric_slot") !=
                    y.get("name_at_same_numeric_slot")
                    or x.get("actor_runtime_link_verified") is not False
                    or y.get("actor_runtime_link_verified") is not False):
                return common
            if (x.get("same_name_in_original_tsd_archive") is not True
                    or not x.get("slot_in_package_name_table")):
                continue
            name = x["name_at_same_numeric_slot"]
            if not isinstance(name, str):
                return common
            key = name.casefold()
            # Validate every counted status against the independent source
            # IBD resource evidence, NOT labels from untrusted actor rows.
            mstatus, kstatus = _status(mission.get(key)), _status(kernel.get(key))
            if (x.get("ibd_resource_payload_status") != mstatus
                    or y.get("ibd_resource_payload_status") != kstatus):
                return common
            counts[f"{mstatus}_to_{kstatus}"] += 1
            references += 1
    common.update({
        "status": "verified_original_name_slot_candidates_not_runtime_bindings",
        "raw_name_slot_candidate_occurrences": references,
        "actors_with_verified_numeric_arrays": verified,
        "transition_counts": dict(sorted(counts.items())),
    })
    return common


def build_comparison(map_file: Path, actors_file: Path, script_zip: Path,
                     mission_ibd: Path, kernel_ibd: Path) -> dict:
    paths = [Path(p).expanduser().resolve(strict=True)
             for p in (map_file, actors_file, script_zip, mission_ibd, kernel_ibd)]
    map_file, actors_file, script_zip, mission_ibd, kernel_ibd = paths
    if (mission_ibd == kernel_ibd or
            kernel_ibd.name.casefold() != "kernel_tsdall.ibd" or
            mission_ibd.name.casefold() == "kernel_tsdall.ibd" or
            mission_ibd.suffix.casefold() != ".ibd" or
            not 0 < mission_ibd.stat().st_size <= MAX_IBD or
            not 0 < kernel_ibd.stat().st_size <= MAX_IBD):
        raise ValueError("Choose separate original mission and Kernel_TSDALL IBDs")
    # Both independent original resource builders recheck SHA-bound GMP/actor
    # cache, entire original ZIP and individual IBD tables.
    mission = build_evidence(map_file, actors_file, script_zip, mission_ibd)
    kernel = build_evidence(map_file, actors_file, script_zip, kernel_ibd)
    for key in ("source_map", "source_map_sha256", "script_archive_sha256"):
        if mission[key] != kernel[key]:
            raise ValueError("Original source identity changed between IBD checks")
    left = _source_script_rows(mission)
    right = _source_script_rows(kernel)
    m_blob, m_records = _unpack_bundle(mission_ibd, mission)
    k_blob, k_records = _unpack_bundle(kernel_ibd, kernel)
    if set(left) != set(m_records) or set(right) != set(k_records):
        raise ValueError("Original IBD resource tables inconsistent")
    source_counts = Counter()
    shared_equal = 0
    shared_different = 0
    rows = []
    for key in sorted(set(left) | set(right)):
        lm, lk = left.get(key), right.get(key)
        mstatus, kstatus = _status(lm), _status(lk)
        if mstatus not in CATEGORIES or kstatus not in CATEGORIES:
            raise ValueError("Original standalone script classification invalid")
        source_counts[f"{mstatus}_to_{kstatus}"] += 1
        row = {
            "script_id": (lm or lk)["script_id"],
            "mission_original_tsd_status": mstatus,
            "kernel_original_tsd_status": kstatus,
            "mission_resource_index": lm["ibd_resource_index"] if lm else None,
            "kernel_resource_index": lk["ibd_resource_index"] if lk else None,
            "mission_vs_kernel": None,
            "mission_vs_standalone": None,
            "kernel_vs_standalone": None,
        }
        def source_profile(entry, blob, resource):
            if entry is None or entry["status"] != "different_payload":
                return None
            # It is not sufficient to know SHA equality: collect size and
            # changed-byte-run metadata, but never sample original bytes.
            if "source_payload_size" not in entry:
                return None
            return {
                "source_payload_size": entry["source_payload_size"],
                "ibd_payload_size": entry["ibd_payload_size"],
                "same_size": (entry["source_payload_size"] ==
                              entry["ibd_payload_size"]),
                "size_difference_bytes": (entry["ibd_payload_size"] -
                                         entry["source_payload_size"]),
            }
        row["mission_vs_standalone"] = source_profile(lm, m_blob, m_records.get(key))
        row["kernel_vs_standalone"] = source_profile(lk, k_blob, k_records.get(key))
        if lm is not None and lk is not None:
            difference = byte_difference(
                _extract(m_blob, m_records[key]),
                _extract(k_blob, k_records[key]))
            row["mission_vs_kernel"] = difference
            shared_equal += int(difference["byte_equal"])
            shared_different += int(not difference["byte_equal"])
        rows.append(row)
    # Source hashes, not just cached metadata, must still match real files
    # after all reads. No result is valid if originals drift during analysis.
    if (hash_path(map_file) != mission["source_map_sha256"]
            or hash_path(script_zip) != mission["script_archive_sha256"]
            or hash_path(mission_ibd) != mission["ibd_sha256"]
            or hash_path(kernel_ibd) != kernel["ibd_sha256"]):
        raise ValueError("Original source drifted while comparing mission and kernel")
    actor_summary = _actor_reference_summary(
        mission.get("original_actor_name_slot_probe", {}),
        kernel.get("original_actor_name_slot_probe", {}), left, right)
    return {
        "schema": SCHEMA,
        "read_only": True,
        "source_map": mission["source_map"],
        "source_map_sha256": mission["source_map_sha256"],
        "script_archive_name": mission["script_archive_name"],
        "script_archive_sha256": mission["script_archive_sha256"],
        "mission_ibd_name": mission_ibd.name,
        "mission_ibd_sha256": mission["ibd_sha256"],
        "kernel_ibd_name": kernel_ibd.name,
        "kernel_ibd_sha256": kernel["ibd_sha256"],
        "counts": {
            "mission_script_resources": len(left),
            "kernel_script_resources": len(right),
            "shared_script_ids": shared_equal + shared_different,
            "shared_payload_exact": shared_equal,
            "shared_payload_different": shared_different,
            "mission_only": len(set(left) - set(right)),
            "kernel_only": len(set(right) - set(left)),
            "mission_vs_standalone_exact": mission["counts"]["exact_payload"],
            "mission_vs_standalone_different": mission["counts"]["different_payload"],
            "kernel_vs_standalone_exact": kernel["counts"]["exact_payload"],
            "kernel_vs_standalone_different": kernel["counts"]["different_payload"],
        },
        "source_status_transitions": dict(sorted(source_counts.items())),
        "actor_name_slot_candidates": actor_summary,
        "script_rows": rows,  # private local detail; not rendered in sanitized UI
        "original_game_assets_modified": False,
        "native_actor_script_indices_resolved": False,
        "runtime_actor_script_binding_verified": False,
        "native_script_writer_enabled": False,
        "gameplay_runtime_verified": False,
        "warnings": [
            "A difference from standalone TSD does not identify a compiler or header cause.",
            "Per-name resource comparisons are separate from raw actor index occurrences.",
            "Original actor name-table slot references remain candidates, not verified runtime bindings.",
            "Source bundle and game files are read-only; no native scripts were rewritten.",
        ],
    }


def write_private_comparison(map_file: Path, actors_file: Path, script_zip: Path,
                             mission_ibd: Path, kernel_ibd: Path,
                             output: Path) -> dict:
    inputs = [Path(p).expanduser().resolve(strict=True) for p in
              (map_file, actors_file, script_zip, mission_ibd, kernel_ibd)]
    target = Path(output).expanduser().resolve()
    protected = [inputs[i].parent for i in (0, 2, 3, 4)]
    if (target.suffix.casefold() != ".json" or target.exists()
            or any(target == p for p in inputs)
            or any(root == target.parent or root in target.parents or
                   target.parent in root.parents for root in protected)):
        raise ValueError("Private report must not be under original retail folders")
    report = build_comparison(*inputs)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=True, allow_nan=False)
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--map", type=Path, required=True)
    p.add_argument("--actors", type=Path, required=True)
    p.add_argument("--scripts", type=Path, required=True)
    p.add_argument("--mission-ibd", type=Path, required=True)
    p.add_argument("--kernel-ibd", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        report = write_private_comparison(
            args.map, args.actors, args.scripts, args.mission_ibd,
            args.kernel_ibd, args.output)
    except (OSError, ValueError, KeyError, TypeError, BadZipFile):
        print(json.dumps({"status": "refused", "code": "source_or_bundle_mismatch"}))
        return 2
    print(json.dumps({
        "status": "ok", "schema": SCHEMA, "read_only": True,
        "counts": report["counts"], "native_script_writer_enabled": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
