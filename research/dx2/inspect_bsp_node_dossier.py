#!/usr/bin/env python3
"""Inspect a single source-original DX2 World Model BSP node, read-only.

The source GMP SHA-256 is mandatory; never reads mutable private drafts,
serializes a modified Model or writes any native game artifact.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dx2sdk import DX2Map


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gmp", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--node", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if re.fullmatch(r"[0-9a-fA-F]{64}", args.source_sha256) is None:
            raise ValueError("Original GMP SHA-256 must be exactly 64 hex chars")
        if args.gmp.suffix.lower() != ".gmp":
            raise ValueError("Only an original .gmp World Model is accepted")
        if type(args.node) is not int or not 0 <= args.node < 20_000:
            raise ValueError("Select an original node ordinal from 0..19999")
        world = DX2Map.open(args.gmp)
        if world.source_sha256 != args.source_sha256.lower():
            raise ValueError("Original GMP content SHA-256 no longer matches")
        report = world.inspect_original_bsp_node_dossier(args.node)
        if (report["source_gmp_sha256"] != world.source_sha256
            or report["original_source_gmp_modified"] is not False
            or report["native_BSP_or_Havok_collision_writer_enabled"] is not False
            or report["original_model_full_span_ledger_verified"] is not True):
            raise ValueError("Source-original BSP node dossier validation failed")
        print(json.dumps(report, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            OverflowError, UnicodeError) as exc:
        print(json.dumps({
            "status": "refused", "reason": str(exc),
            "original_source_gmp_modified": False,
            "native_BSP_or_Havok_collision_writer_enabled": False,
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
