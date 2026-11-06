#!/usr/bin/env python3
"""DX2Ed v0.12 GUI bridge for one existing, authored LightColor.

Runs only from the bundled open-source DX2SDK Python distribution.
Original GMP SHA must match the UI-provided source anchor. Listing reads
the original, preview performs a dual-writer full-byte dry run, and apply
requires the explicit action plus private isolated same-basename output.
No native Light creation, BSP zone editing, or game runtime acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from dx2sdk import DX2Map  # noqa: E402
from dx2sdk.light_colors import SCHEMA  # noqa: E402

SCHEMA_GUI = "DX2Ed-GUI-original-LightColor-worker-v1"


def _pin(value: str) -> str:
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)):
        raise ValueError("Original GMP requires a lowercase SHA-256 identity")
    return value


def _original(path: str, source_sha256: str) -> DX2Map:
    expected = _pin(source_sha256)
    world = DX2Map.open(path)
    if world.source_sha256 != expected:
        raise ValueError("Original GMP has changed since the DX2Ed source scan")
    return world


def _changes(args) -> dict[str, int]:
    values = {field: getattr(args, field) for field in
              ("brightness", "hue", "saturation")}
    result = {k: v for k, v in values.items() if v is not None}
    if not 1 <= len(result) <= 3 or any(type(v) is not int or not 0 <= v <= 255
                                         for v in result.values()):
        raise ValueError("1..3 original LightColor byte edits must be 0..255")
    return result


def perform(args) -> dict:
    world = _original(args.map, args.source_sha256)
    if args.action == "list":
        listed = world.original_light_colors(limit=args.limit)
        if (listed.get("schema") != SCHEMA
                or listed.get("status") != "read-only-source-verified"
                or listed.get("source_sha256") != world.source_sha256
                or listed.get("read_only") is not True
                or listed.get("native_new_light_actor_creation_enabled") is not False):
            raise ValueError("Original source LightColor inventory is not strict")
        return {"bridge_schema": SCHEMA_GUI, "action": "list", **listed}
    if (args.action not in ("preview", "apply")
            or type(args.actor) is not str or not args.actor
            or type(args.export) is not int or args.export < 1
            or not isinstance(args.expect, list) or len(args.expect) != 3
            or any(type(v) is not int or not 0 <= v <= 255 for v in args.expect)
            or type(args.output) is not str or not args.output):
        raise ValueError("Exact source actor, export, pinned bytes and isolated path required")
    edited = _changes(args)
    changed = world.set_existing_light_color(
        export=args.export,
        actor=args.actor,
        expected=tuple(args.expect),
        changes=edited,
        output=args.output,
        write=args.action == "apply")
    if (changed.get("schema") != SCHEMA
            or changed.get("source_sha256") != world.source_sha256
            or changed.get("actor_export") != args.export
            or changed.get("actor") != args.actor
            or changed.get("gameplay_runtime_verified") is not False
            or changed.get("new_light_actor_created") is not False
            or changed.get("original_map_modified") is not False
            or changed.get("dual_serializer_full_package_match") is not True
            or changed.get("changed_bytes") != len(edited)):
        raise ValueError("Source LightColor native writer failed independent parity")
    if args.action == "preview":
        if changed.get("status") != "dry-run" or changed.get("edited_package_written") is not False:
            raise ValueError("Dry-run unexpectedly reported a native GMP write")
        return {"bridge_schema": SCHEMA_GUI, "action": "preview", **changed}
    if (changed.get("status") != "isolated-GMP-written-runtime-unverified"
            or changed.get("verified_binary_structure") is not True
            or changed.get("edited_package_written") is not True):
        raise ValueError("Isolated LightColor output was not independently verified")
    verification = world.verify_saved_light_color(args.output)
    if (verification.get("verified_binary_structure") is not True
            or verification.get("source_sha256") != world.source_sha256):
        raise ValueError("Saved LightColor GMP failed final source-independent replay")
    return {
        "bridge_schema": SCHEMA_GUI,
        "action": "apply",
        "schema": SCHEMA,
        "status": "isolated-verified-runtime-unverified",
        "actor": args.actor,
        "actor_export": args.export,
        "changed_bytes": len(edited),
        "source_sha256": world.source_sha256,
        "output": str(Path(args.output).expanduser().resolve()),
        "dual_serializer_full_package_match": True,
        "verified_binary_structure": True,
        "original_map_modified": False,
        "new_light_actor_created": False,
        "gameplay_runtime_verified": False,
    }


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("list", "preview", "apply"))
    p.add_argument("--map", required=True, help="Owner original .gmp")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--limit", type=int, default=1000)
    p.add_argument("--export", type=int)
    p.add_argument("--actor")
    p.add_argument("--expect", type=int, nargs=3)
    p.add_argument("--brightness", type=int)
    p.add_argument("--hue", type=int)
    p.add_argument("--saturation", type=int)
    p.add_argument("--output", help="Fresh isolated same-basename private .gmp")
    return p


def main(argv=None) -> int:
    try:
        args = make_parser().parse_args(argv)
        response = perform(args)
        print(json.dumps(response, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        print(json.dumps({
            "bridge_schema": SCHEMA_GUI,
            "status": "refused",
            "reason": str(exc)[:360],
            "original_map_modified": False,
            "native_new_light_actor_creation_enabled": False,
        }, allow_nan=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
