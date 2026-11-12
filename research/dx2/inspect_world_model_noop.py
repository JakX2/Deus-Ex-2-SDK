#!/usr/bin/env python3
"""DX2 original World Model native structural no-op reassembly preflight.

Read-only. Requires original source GMP and exact SHA-256. The only optional
file write is a fresh JSON report *outside* source retail map directories.
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
from inspect_bsp_mopp_plane_impact import _private_output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_gmp", type=Path)
    parser.add_argument("--source-sha256", required=True,
                        help="Exact 64-hex SHA-256 of user-owned original GMP")
    parser.add_argument("--report", type=Path,
                        help="Fresh private JSON outside retail game Maps")
    args = parser.parse_args(argv)
    try:
        if re.fullmatch(r"[0-9a-fA-F]{64}", args.source_sha256) is None:
            raise ValueError("Original GMP SHA-256 must be exactly 64 hex digits")
        world = DX2Map.open(args.original_gmp)
        if world.source_sha256 != args.source_sha256.lower():
            raise ValueError("Original source GMP SHA-256 does not match")
        report = world.inspect_original_world_model_noop()
        if report["source_gmp_sha256"] != args.source_sha256.lower():
            raise ValueError("Independent Model no-op source SHA-256 mismatch")
        if not report["model_reassembled_byte_identical"]:
            raise ValueError("Original Model failed byte-exact in-memory reassembly")
        if args.report is not None:
            target = _private_output(world.source, args.report)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf8") as stream:
                json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
                stream.write("\n")
            print(json.dumps({
                "status": report["status"], "report": str(target),
                "source_sha256": world.source_sha256,
                "source_node_count": report["source_node_count"],
                "source_zone_count": report["source_zone_count"],
                "model_reassembled_byte_identical": True,
                "native_modified_model_writer_enabled": False,
            }, sort_keys=True))
        else:
            print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError, OverflowError) as exc:
        print(json.dumps({
            "status": "refused", "reason": str(exc),
            "original_game_package_modified": False,
            "native_modified_model_writer_enabled": False,
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
