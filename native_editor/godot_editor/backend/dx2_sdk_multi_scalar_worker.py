#!/usr/bin/env python3
"""DX2Ed v0.15: 2..8 original UE95 tagged scalar fields, one isolated GMP.

This bridge reuses the v0.3 DX2SDK native scalar writer and v0.14 source-
verified actor/field inspector. Only existing positioned StaticMeshActors,
existing unique top-level 4-byte IntProperty/FloatProperty, GMP and source-
bound actors.json SHA pins. Preview cannot write. Confirmed apply writes a
fresh isolated same-basename GMP + scalar manifest and verifies every byte.
No new actor, GameSys, BSP/CSG, scripts, collision or gameplay validation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dx2_sdk_scalar_worker import (  # noqa: E402
    _original, _fields, _request, _unique_pairs,
    perform as single_perform,
)
from dx2sdk.api import _safe_output  # noqa: E402
from dx2sdk.scalars import _encode, SCHEMA  # noqa: E402

BRIDGE_SCHEMA = "DX2Ed-GUI-original-multi-native-scalar-worker-v1"
MIN_FIELDS = 2
MAX_FIELDS = 8
MAX_REQUEST_BYTES = 16 * 1024


def _strict_rows(payload: object) -> list[dict]:
    if (type(payload) is not str or
            not 0 < len(payload.encode("utf8")) <= MAX_REQUEST_BYTES):
        raise ValueError("Native scalar batch request must be bounded JSON")
    parsed = json.loads(
        payload,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError("Native scalar batches cannot contain nonfinite JSON")),
        object_pairs_hook=_unique_pairs,
    )
    if not isinstance(parsed, list) or not MIN_FIELDS <= len(parsed) <= MAX_FIELDS:
        raise ValueError("Native scalar batch must contain 2..8 unique original fields")
    rows = []
    seen = set()
    actor_exports = {}
    export_actors = {}
    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError("Native scalar batch contains non-object edit")
        # Reuse the exact strict one-property source-preserving request schema.
        row = _request(json.dumps(item, allow_nan=False))
        key = (row["actor"], row["property"])
        if key in seen:
            raise ValueError("Native scalar batch cannot edit a field twice")
        seen.add(key)
        if (row["actor"] in actor_exports and
                actor_exports[row["actor"]] != row["export"]):
            raise ValueError("Original actor name changed export within one batch")
        if (row["export"] in export_actors and
                export_actors[row["export"]] != row["actor"]):
            raise ValueError("Original export assigned to different source actors")
        actor_exports[row["actor"]] = row["export"]
        export_actors[row["export"]] = row["actor"]
        rows.append(row)
    # Deterministic request order, independent of UI staging order.
    return sorted(rows, key=lambda r: (r["export"], r["property"]))


def _validate_against_source(world, rows: list[dict]) -> tuple[dict, list[dict]]:
    changes = {}
    validated = []
    by_actor = {}
    for row in rows:
        if row["actor"] not in by_actor:
            origin = _fields(world, row["actor"], row["export"])
            by_actor[row["actor"]] = {
                field["property"]: field for field in origin["fields"]
            }
        candidate = by_actor[row["actor"]].get(row["property"])
        if (candidate is None or
                candidate["type"] != row["type"] or
                candidate["source_value"] != row["expected"]):
            raise ValueError("Original source native field/type/value changed from batch preview")
        kind = 2 if row["type"] == "int32" else 4
        _encode(row["expected"], kind)
        new_value, changed = _encode(row["replacement"], kind)
        _, before = _encode(candidate["source_value"], kind)
        if before == changed:
            raise ValueError("Original native batch cannot contain a no-op scalar edit")
        changes.setdefault(row["actor"], {})[row["property"]] = row["replacement"]
        validated.append({
            **row, "replacement": new_value,
        })
    world._check_original_unchanged()
    return changes, validated


def _audit_report(world, report: dict, rows: list[dict], output: Path) -> None:
    if (report.get("schema") != SCHEMA or
            report.get("source") != str(world.source) or
            report.get("output") != str(output) or
            report.get("source_sha256") != world.source_sha256 or
            report.get("source_actor_cache_sha256") != world._actor_cache_sha256 or
            report.get("original_size") != len(world._package.data) or
            report.get("edited_field_count") != len(rows) or
            type(report.get("changed_byte_count")) is not int or
            not 1 <= report["changed_byte_count"] <= 4 * len(rows) or
            report.get("runtime_game_verified") is not False or
            report.get("source_original_modified") is not False or
            report.get("native_script_writer_enabled") is not False or
            report.get("bsp_collision_rebuild_enabled") is not False or
            not isinstance(report.get("edits"), list) or
            len(report["edits"]) != len(rows)):
        raise ValueError("Native scalar batch serializer returned unsupported report")
    native = {(item["actor"], item["property"]): item for item in report["edits"]}
    if len(native) != len(rows):
        raise ValueError("Native scalar batch source report contains duplicate properties")
    for row in rows:
        source = native.get((row["actor"], row["property"]))
        expected_kind = 2 if row["type"] == "int32" else 4
        if (source is None or source.get("export") != row["export"] or
                source.get("actor_class") != "StaticMeshActor" or
                source.get("native_kind") != expected_kind or
                source.get("before_value") != row["expected"] or
                source.get("after_value") != row["replacement"]):
            raise ValueError("Native scalar batch field lost source actor/export/type/value identity")


def perform(args: argparse.Namespace) -> dict:
    if args.action in ("list", "fields"):
        single = single_perform(args)
        return {**single, "bridge_schema": BRIDGE_SCHEMA}
    if args.action not in ("preview", "apply") or not args.output:
        raise ValueError("Native scalar batch requires explicit preview or apply output")
    world = _original(args)
    rows = _strict_rows(args.rows_json)
    changes, original_rows = _validate_against_source(world, rows)
    target = _safe_output(world.source, args.output)
    manifest = target.with_suffix(".dx2sdk-scalar.json")
    if manifest.exists():
        raise ValueError("Existing scalar copy manifest cannot be overwritten")

    # The original GMP no-op serialization proof and bounded byte patch are
    # performed in the existing public SDK writer. Preview is no-write.
    saved = world.save_as_scalar_changes(
        changes, target, write=args.action == "apply")
    _audit_report(world, saved, original_rows, target)
    if args.action == "preview":
        if (saved.get("status") != "dry-run" or
                saved.get("independent_byte_validation") is not False or
                target.exists() or manifest.exists()):
            raise ValueError("Native scalar batch preview unexpectedly wrote output")
        return {
            "bridge_schema": BRIDGE_SCHEMA, "schema": SCHEMA,
            "status": "dry-run", "action": "preview",
            "source_map": world.source.name,
            "source_sha256": world.source_sha256,
            "actors_sha256": world._actor_cache_sha256,
            "rows": original_rows, "requested_rows": rows,
            "edited_field_count": len(rows),
            "changed_byte_count": saved["changed_byte_count"],
            "output": str(target),
            "original_source_noop_T3SDK_parity_verified": True,
            "edited_package_written": False,
            "saved_binary_structure_verified": False,
            "source_original_modified": False,
            "runtime_game_verified": False,
            "native_gamesys_or_script_writer_enabled": False,
            "native_new_actor_creation_enabled": False,
            "bsp_collision_rebuild_enabled": False,
        }
    if (saved.get("status") != "written-unverified-gameplay" or
            saved.get("independent_byte_validation") is not True):
        raise ValueError("Original scalar batch writer did not verify its isolated GMP")
    verification = world.verify_saved_scalar_changes(target)
    if (verification.get("verified_binary_structure") is not True or
            verification.get("changed_fields") != len(rows) or
            verification.get("changed_bytes") != saved["changed_byte_count"] or
            verification.get("unapproved_bytes") != 0 or
            verification.get("source_map") != world.source.name or
            verification.get("runtime_game_verified") is not False or
            verification.get("source_original_modified") is not False):
        raise ValueError("Native scalar batch saved GMP failed full independent source replay")
    world._check_original_unchanged()
    return {
        "bridge_schema": BRIDGE_SCHEMA, "schema": SCHEMA,
        "status": "isolated-multi-native-scalars-verified-runtime-unverified",
        "action": "apply", "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "actors_sha256": world._actor_cache_sha256,
        "rows": original_rows, "requested_rows": rows,
            "edited_field_count": len(rows),
        "changed_byte_count": saved["changed_byte_count"],
        "output": str(target),
        "original_source_noop_T3SDK_parity_verified": True,
        "edited_package_written": True,
        "saved_binary_structure_verified": True,
        "independent_saved_whole_GMP_byte_verification": True,
        "source_original_modified": False,
        "runtime_game_verified": False,
        "native_gamesys_or_script_writer_enabled": False,
        "native_new_actor_creation_enabled": False,
        "bsp_collision_rebuild_enabled": False,
    }


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=("list", "fields", "preview", "apply"))
    cli.add_argument("--map", required=True)
    cli.add_argument("--actors", required=True)
    cli.add_argument("--source-sha256", required=True)
    cli.add_argument("--actors-sha256", required=True)
    cli.add_argument("--actor", help="Exact source actor name for fields action")
    cli.add_argument("--export", type=int, help="Original export number for fields")
    cli.add_argument("--rows-json", help="2..8 distinct original numeric field edits")
    cli.add_argument("--output", help="Fresh isolated GMP retaining original basename")
    return cli


def main(argv=None) -> int:
    try:
        args = parser().parse_args(argv)
        result = perform(args)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
        print(json.dumps({
            "bridge_schema": BRIDGE_SCHEMA, "status": "refused",
            "reason": str(exc)[:390],
            "source_original_modified": False,
            "runtime_game_verified": False,
            "native_new_actor_creation_enabled": False,
            "native_gamesys_or_script_writer_enabled": False,
        }, sort_keys=True, allow_nan=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
