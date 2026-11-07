#!/usr/bin/env python3
"""DX2Ed v0.13: GUI JSON worker for 2..8 original LightColor actors.

The single original source is SHA-pinned by the UI. Preview is memory only:
the v0.8 multi-LightColor serializer must match exact independent original
source byte patches across an ENTIRE GMP. Apply creates a fresh private
source-bound plan, one isolated same-basename GMP and its verified manifest.
There is no creation of native Lights or runtime lighting test.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dx2sdk import DX2Map  # noqa: E402
from dx2sdk.light_colors import SCHEMA as ONE_SCHEMA  # noqa: E402
from dx2sdk.multi_light_colors import (  # noqa: E402
    MAX_COPIES, SCHEMA, PLAN_SCHEMA, _proof,
)
from dx2sdk.lights import _safe_copy_path  # noqa: E402

BRIDGE_SCHEMA = "DX2Ed-GUI-source-multi-LightColor-worker-v1"
MAX_REQUEST = 16 * 1024


def _sha_pin(value: str) -> str:
    if (not isinstance(value, str) or len(value) != 64 or
            any(ch not in "0123456789abcdef" for ch in value)):
        raise ValueError("GUI original SHA-256 must be 64 lowercase hexadecimal characters")
    return value


def _source(path: str, sha: str) -> DX2Map:
    world = DX2Map.open(path)
    if world.source_sha256 != _sha_pin(sha):
        raise ValueError("Original GMP changed since the GUI source audit")
    return world


def _rows(value: str) -> list[dict]:
    if not isinstance(value, str) or not 0 < len(value.encode("utf8")) <= MAX_REQUEST:
        raise ValueError("Batch GUI request must be a bounded JSON string")
    data = json.loads(value)
    if (not isinstance(data, list) or not 2 <= len(data) <= MAX_COPIES):
        raise ValueError("Batch GUI requires 2..8 different original actors")
    # Reject duplicate JSON keys via an independently strict key-set check
    # below. The SDK rechecks all original source actor IDs and byte values.
    exports = set()
    for item in data:
        if not isinstance(item, dict) or set(item) != {
                "actor", "export", "expected", "changes"}:
            raise ValueError("Each GUI batch row must contain only actor/export/expected/changes")
        export = item["export"]
        if (type(export) is not int or export < 1 or export in exports
                or not isinstance(item["actor"], str) or not item["actor"]
                or not isinstance(item["expected"], list) or len(item["expected"]) != 3
                or any(type(x) is not int or not 0 <= x <= 255 for x in item["expected"])
                or not isinstance(item["changes"], dict)
                or not 1 <= len(item["changes"]) <= 3
                or any(k not in ("brightness", "hue", "saturation") or
                       type(v) is not int or not 0 <= v <= 255
                       for k, v in item["changes"].items())):
            raise ValueError("GUI actor source byte pins or requested changes are invalid")
        exports.add(export)
    return data


def _path_for_plan(output: str) -> Path:
    # The v0.8 original SDK's path guards are authoritative. This deterministic
    # adjacent private filename also stays tied to the verified output GMP.
    return Path(output).expanduser().resolve().with_suffix(
        ".dx2sdk-multi-lightcolor-plan.json")


def perform(args: argparse.Namespace) -> dict:
    world = _source(args.map, args.source_sha256)
    if args.action == "list":
        data = world.original_light_colors(limit=1000)
        if (data.get("schema") != ONE_SCHEMA or
                data.get("source_sha256") != world.source_sha256 or
                data.get("status") != "read-only-source-verified" or
                data.get("read_only") is not True or
                data.get("native_new_light_actor_creation_enabled") is not False or
                data.get("gameplay_runtime_verified") is not False):
            raise ValueError("Original GUI LightColor list failed source validation")
        return {"bridge_schema": BRIDGE_SCHEMA, "action": "list", **data}
    if args.action not in ("preview", "apply") or not args.output:
        raise ValueError("Batch preview/apply needs a fresh isolated GMP target")
    records = _rows(args.rows_json)
    target = _safe_copy_path(world, args.output, exists=False)
    plan_path = _path_for_plan(str(target))
    # Disallow both preexisting plan and output/manifest so a later Save As
    # cannot overwrite or silently reuse a previous private research record.
    if (plan_path.exists() or
            target.with_suffix(".dx2sdk-multi-lightcolor.json").exists()):
        raise ValueError("Batch output or private plan/manifest already exists")
    dry, _ = _proof(world, records)
    if (dry.get("schema") != SCHEMA or dry.get("status") != "dry-run"
            or dry.get("source_sha256") != world.source_sha256
            or dry.get("independent_full_package_byte_match") is not True
            or dry.get("source_original_modified") is not False
            or dry.get("native_light_spawn_enabled") is not False
            or dry.get("native_bsp_or_zone_rebuild_enabled") is not False
            or dry.get("gameplay_runtime_verified") is not False
            or dry.get("edited_actor_count") != len(records)):
        raise ValueError("Original multi-LightColor dual-writer parity proof failed")
    if args.action == "preview":
        return {
            "bridge_schema": BRIDGE_SCHEMA, "action": "preview",
            **dry, "edited_package_written": False,
            "plan_created": False, "output": str(target),
        }

    # A real apply is an explicit user-confirmed action. The worker must still
    # validate ALL original data again, not trust a previous preview response.
    created_plan = False
    try:
        plan = world.write_lightcolor_plan(records, plan_path)
        created_plan = True
        if (plan.get("schema") != PLAN_SCHEMA or
                plan.get("source_sha256") != world.source_sha256 or
                plan.get("source_only_plan") is not True or
                plan.get("native_light_spawn_enabled") is not False or
                plan.get("gameplay_runtime_verified") is not False or
                plan.get("actors") != dry["actors"]):
            raise ValueError("Fresh private batch LightColor plan disagrees with original")
        saved = world.apply_lightcolor_plan(plan_path, target, write=True)
        if (saved.get("schema") != SCHEMA or
                saved.get("status") != "isolated-GMP-written-runtime-unverified" or
                saved.get("source_sha256") != world.source_sha256 or
                saved.get("edited_actor_count") != len(records) or
                saved.get("changed_bytes") != dry["changed_bytes"] or
                saved.get("output_sha256") != dry["output_sha256"] or
                saved.get("independent_full_package_byte_match") is not True or
                saved.get("verified_binary_structure") is not True or
                saved.get("source_original_modified") is not False or
                saved.get("gameplay_runtime_verified") is not False or
                saved.get("native_light_spawn_enabled") is not False):
            raise ValueError("Isolated original LightColor group failed source-byte proof")
        final = world.verify_saved_multi_lightcolor(target)
        if (final.get("schema") != SCHEMA
                or final.get("verified_binary_structure") is not True
                or final.get("edited_actor_count") != len(records)
                or final.get("changed_bytes") != dry["changed_bytes"]
                or final.get("unapproved_bytes") != 0
                or final.get("source_map") != world.source.name
                or final.get("source_original_modified") is not False
                or final.get("gameplay_runtime_verified") is not False):
            raise ValueError("Saved LightColor batch failed independent full-package verification")
        return {
            "bridge_schema": BRIDGE_SCHEMA, "action": "apply",
            "schema": SCHEMA,
            "status": "isolated-multi-LightColor-verified-runtime-unverified",
            "source_map": world.source.name,
            "source_sha256": world.source_sha256,
            "actors": dry["actors"],
            "edited_actor_count": len(records),
            "changed_bytes": dry["changed_bytes"],
            "output": str(target),
            "private_plan": str(plan_path),
            "independent_full_package_byte_match": True,
            "verified_binary_structure": True,
            "source_original_modified": False,
            "gameplay_runtime_verified": False,
            "native_light_spawn_enabled": False,
            "native_bsp_or_zone_rebuild_enabled": False,
        }
    except Exception:
        # Clean up only a new plan we created if no GMP was created. Once a
        # native GMP exists, retain the plan to allow independent verification
        # and user investigation. Never delete unrelated preexisting files.
        if created_plan and not target.exists():
            plan_path.unlink(missing_ok=True)
        raise


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=("list", "preview", "apply"))
    cli.add_argument("--map", required=True)
    cli.add_argument("--source-sha256", required=True)
    cli.add_argument("--rows-json", help="2..8 exact existing Actor LightColor edits, source locked")
    cli.add_argument("--output", help="NEW isolated same-basename .gmp; private plan kept")
    return cli


def main(argv=None) -> int:
    try:
        args = parser().parse_args(argv)
        result = perform(args)
        print(json.dumps(result, allow_nan=False, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        print(json.dumps({
            "bridge_schema": BRIDGE_SCHEMA,
            "status": "refused",
            "reason": str(exc)[:380],
            "native_light_spawn_enabled": False,
            "source_original_modified": False,
        }, allow_nan=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
