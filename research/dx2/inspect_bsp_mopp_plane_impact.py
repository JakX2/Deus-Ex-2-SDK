#!/usr/bin/env python3
"""Source-pinned read-only DX2 BSP plane candidate → Level/MOPP triangle IDs.

Does not modify game files, write BSP/CSG or compile Havok collision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dx2sdk import DX2Map


def _private_output(original: Path, report: Path) -> Path:
    if report.is_symlink():
        raise ValueError("Report path cannot be a symlink")
    target = report.expanduser().resolve()
    parts = tuple(p.casefold() for p in target.parent.parts)
    if (target.suffix.casefold() != ".json" or target.exists()
            or target.parent == original.parent
            or original.parent in target.parents
            or any(parts[i:i+3] == ("content", "dx2", "maps")
                   for i in range(max(0, len(parts)-2)))):
        raise ValueError("Report must be a fresh private JSON outside game/source Maps")
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_gmp", type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--node", type=int, required=True)
    parser.add_argument("--plane", type=float, nargs=4, required=True,
                        metavar=("A", "B", "C", "W"))
    parser.add_argument("--report", type=Path,
                        help="Fresh private JSON outside original game/source Maps")
    args = parser.parse_args(argv)
    try:
        if not re.fullmatch("[a-fA-F0-9]{64}", args.source_sha256):
            raise ValueError("Require the pinned 64-character original GMP SHA-256")
        world = DX2Map.open(args.original_gmp)
        if world.source_sha256 != args.source_sha256.lower():
            raise ValueError("Original GMP does not match supplied source SHA-256")
        result = world.inspect_bsp_plane_mopp_candidates(
            node=args.node, replacement=args.plane)
        if args.report is not None:
            target = _private_output(world.source, args.report)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf8") as stream:
                json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
                stream.write("\n")
            print(json.dumps({
                "status": result["status"], "report": str(target),
                "source_sha256": world.source_sha256,
                "lost_candidate_original_mopp_leaf_count":
                    result["lost_candidate_original_mopp_leaf_count"],
                "gained_candidate_original_mopp_leaf_count":
                    result["gained_candidate_original_mopp_leaf_count"],
                "retail_runtime_verified": False,
            }, indent=2))
        else:
            print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, IndexError, OverflowError, struct.error, TypeError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc),
                          "original_gmp_modified": False,
                          "retail_runtime_verified": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
