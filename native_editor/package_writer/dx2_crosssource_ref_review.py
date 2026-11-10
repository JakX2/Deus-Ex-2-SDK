#!/usr/bin/env python3
"""DX2Ed v0.63 read-only cross-source unplace risk review.

Compare CONFIRMED original GMP explicit incoming actor references with
independently validated original TriggerScript ZIP -> IBD resource identity.

The original GameSys 92 actor-to-script binding remains UNKNOWN: a matching
TSD/IBD resource is NOT proof that any particular GMP actor executes it.
This is only an evidence overlay for choosing safe research candidates.
It never writes/edits game files, scripts, maps or mod recipes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "godot_editor" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from dx2_incoming_ref_audit import audit_original
from dx2_script_ibd_provenance import build_evidence

SCHEMA = "DX2Ed-original-cross-source-unplace-evidence-v1"
MAX_REPORT_SIZE = 1_048_576


def review_original(
    map_file: Path, *, source_sha256: str, actor_export: int,
    actor_name: str, actors_file: Path, scripts_file: Path, ibd_file: Path,
) -> dict:
    """Read original owned resources and report independently provable facts."""
    map_file = Path(map_file).expanduser().resolve(strict=True)
    actors_file = Path(actors_file).expanduser().resolve(strict=True)
    scripts_file = Path(scripts_file).expanduser().resolve(strict=True)
    ibd_file = Path(ibd_file).expanduser().resolve(strict=True)

    incoming = audit_original(
        map_file, source_sha256=source_sha256,
        actor_export=actor_export, actor_name=actor_name)
    evidence = build_evidence(
        map_file, actors_file, scripts_file, ibd_file)
    if (evidence.get("source_map_sha256") != incoming["source_sha256"]
            or evidence.get("source_map", "").casefold() !=
               incoming["source_name"].casefold()
            or evidence.get("original_game_assets_modified") is not False
            or evidence.get("actor_to_script_binding_verified") is not False
            or evidence.get("native_actor_script_indices_resolved") is not False
            or evidence.get("native_script_writer_enabled") is not False
            or evidence.get("gameplay_runtime_verified") is not False):
        raise ValueError("Script IBD provenance disagrees with original GMP or its evidence boundary")

    probe = evidence.get("original_actor_name_slot_probe")
    if not isinstance(probe, dict):
        raise ValueError("Original native actor name-slot evidence is malformed")
    rows = probe.get("actors", [])
    if not isinstance(rows, list):
        raise ValueError("Original actor script name-slot list is malformed")
    target_rows = [row for row in rows if isinstance(row, dict) and
                   row.get("export") == actor_export]
    if len(target_rows) > 1 or (target_rows and target_rows[0].get("actor") != actor_name):
        raise ValueError("Ambiguous or mismatched original native script actor identity")
    target = target_rows[0] if target_rows else None
    native_status = (
        target.get("status", "unverified_native_actor")
        if target else "not_in_verified_script_actor_rows")
    native_verified = bool(
        target and target.get("native_game_property_92_verified") is True)
    candidate_count = len(target.get("candidates", [])) if target else 0
    if candidate_count > 256:
        raise ValueError("Unsupported original target script candidate count")

    # Intentionally never turn numeric name-table coincidences into actor
    # dependencies. We expose only conservative aggregate provenance.
    resource_counts = evidence.get("counts")
    if not isinstance(resource_counts, dict) or any(
        type(resource_counts.get(key)) is not int or resource_counts[key] < 0
        for key in (
            "exact_payload", "different_payload",
            "not_in_original_zip", "source_definitions_not_in_ibd")
    ):
        raise ValueError("Original IBD resource counters are malformed")
    if (incoming.get("incoming_references_verified") is not False
            or incoming.get("safe_to_unplace_claimed") is not False
            or incoming.get("runtime_game_verified") is not False):
        raise ValueError("GMP incoming-reference audit must not claim full safety")

    return {
        "schema": SCHEMA,
        "status": ("known-explicit-incoming-reference"
                   if incoming["explicit_incoming_blocker"]
                   else "no-known-incoming-reference-but-unresolved-script-links"),
        "read_only": True,
        "source_map": incoming["source_name"],
        "source_map_sha256": incoming["source_sha256"],
        "target_actor": actor_name,
        "target_export": actor_export,
        "target_location": incoming["source_location"],
        "gmp_explicit_incoming_references": incoming["confirmed_incoming_references"],
        "gmp_explicit_incoming_count": incoming["confirmed_incoming_count"],
        "gmp_reference_list_truncated": incoming["hit_list_truncated"],
        "gmp_opaque_or_untyped_scopes": incoming["opaque_or_untyped_scopes"],
        "gmp_scanned_actor_exports": incoming["scanned_actor_exports"],
        "trigger_script_archive_name": evidence["script_archive_name"],
        "trigger_script_archive_sha256": evidence["script_archive_sha256"],
        "original_ibd_name": evidence["ibd_name"],
        "original_ibd_sha256": evidence["ibd_sha256"],
        "original_ibd_script_resource_counts": {
            key: resource_counts[key] for key in (
                "exact_payload", "different_payload",
                "not_in_original_zip", "source_definitions_not_in_ibd")},
        "source_script_actors_with_raw_fields":
            probe.get("counts", {}).get("source_script_actors", 0),
        "target_game_property_92_status": native_status,
        "target_game_property_92_redecoded": native_verified,
        "target_numeric_script_name_slot_candidates": candidate_count,
        "target_actor_to_script_binding_verified": False,
        "incoming_script_links_verified": False,
        "full_incoming_reference_graph_verified": False,
        "native_script_writer_enabled": False,
        "gameplay_runtime_verified": False,
        "source_gmp_modified": False,
        "source_ibd_modified": False,
        "source_script_archive_modified": False,
        "safe_to_unplace_claimed": False,
        "warnings": [
            "Verified TSD-to-IBD byte identity is NOT an actor-to-script binding.",
            "GameSys 92 raw integers may resemble name-table slots; their runtime meaning is unresolved.",
            "IBD/TriggerScript actors could still affect this target even with zero typed GMP incoming hits.",
            "This source-only review cannot verify runtime loading, removal, collision or save/reload.",
        ],
    }


def export_private_report(
    map_file: Path, actors_file: Path, scripts_file: Path,
    ibd_file: Path, output: Path, *, source_sha256: str,
    actor_export: int, actor_name: str,
) -> dict:
    sources = [
        Path(p).expanduser().resolve(strict=True)
        for p in (map_file, actors_file, scripts_file, ibd_file)]
    target = Path(output).expanduser().resolve()
    protected_folders = (
        sources[0].parent, sources[2].parent, sources[3].parent)
    if (target.suffix.casefold() != ".json" or target.exists()
            or any(target == p for p in sources)
            or any(folder == target.parent or folder in target.parents
                   or target.parent in folder.parents
                   for folder in protected_folders)):
        raise ValueError("Private review must be a new JSON outside the original game resource hierarchy")
    report = review_original(
        sources[0], source_sha256=source_sha256,
        actor_export=actor_export, actor_name=actor_name,
        actors_file=sources[1], scripts_file=sources[2],
        ibd_file=sources[3])
    encoded = json.dumps(
        report, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    if len(encoded.encode("utf-8")) > MAX_REPORT_SIZE:
        raise ValueError("Cross-source review report exceeds source-only size cap")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--map", required=True, type=Path)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--actor-export", required=True, type=int)
    p.add_argument("--actor-name", required=True)
    p.add_argument("--actors", required=True, type=Path)
    p.add_argument("--scripts", required=True, type=Path)
    p.add_argument("--ibd", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    try:
        kw = {
            "source_sha256": args.source_sha256,
            "actor_export": args.actor_export,
            "actor_name": args.actor_name,
            "actors_file": args.actors,
            "scripts_file": args.scripts,
            "ibd_file": args.ibd,
        }
        if args.output is None:
            doc = review_original(args.map, **kw)
        else:
            doc = export_private_report(
                args.map, args.actors, args.scripts,
                args.ibd, args.output,
                source_sha256=args.source_sha256,
                actor_export=args.actor_export,
                actor_name=args.actor_name)
        result = {
            "schema": SCHEMA, "status": doc["status"],
            "read_only": True, "source_map_sha256": doc["source_map_sha256"],
            "target_actor": doc["target_actor"], "target_export": doc["target_export"],
            "confirmed_gmp_incoming": doc["gmp_explicit_incoming_count"],
            "original_ibd_script_resource_counts":
                doc["original_ibd_script_resource_counts"],
            "actor_to_script_binding_verified": False,
            "safe_to_unplace_claimed": False,
            "gameplay_runtime_verified": False,
            "output_written": args.output is not None,
        }
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        # Deliberately avoid reproducing owner-local file paths, TSD bytes,
        # or original map content in failure messages.
        print(json.dumps({
            "schema": SCHEMA, "status": "refused",
            "reason": type(exc).__name__,
            "read_only": True, "output_written": False}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
