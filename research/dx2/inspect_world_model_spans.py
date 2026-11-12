#!/usr/bin/env python3
"""Original DX2 compiled World Model complete read-only byte-span ledger.

Inspect user-owned original GMP by exact SHA-256. Bounded source node samples
are metadata and hashes only. No copied game model data, map writes, native
surface assignments, collision updates or playable mission output.
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_gmp", type=Path)
    p.add_argument("--source-sha256", required=True,
                   help="64 hexadecimal characters of original source GMP SHA-256")
    p.add_argument("--node", type=int, action="append", default=[],
                   help="Original BSP node ordinal for exact source offsets, repeat <=12")
    p.add_argument("--report", type=Path,
                   help="Exclusive-create private JSON outside original game Maps")
    args = p.parse_args(argv)
    try:
        if re.fullmatch(r"[0-9a-fA-F]{64}", args.source_sha256) is None:
            raise ValueError("Require exact 64-hex original GMP SHA-256")
        if len(args.node) > 12 or len(set(args.node)) != len(args.node):
            raise ValueError("Select at most 12 distinct original BSP nodes")
        world = DX2Map.open(args.original_gmp)
        if world.source_sha256 != args.source_sha256.lower():
            raise ValueError("Original GMP source SHA-256 does not match pinned input")
        report = world.inspect_original_model_byte_spans(node_indices=args.node)
        if (report["original_gmp_sha256"] != world.source_sha256
                or not report["original_model_noop_reassembled_byte_identical"]
                or not report.get("model_byte_ledger_fully_contiguous_nonoverlapping", True)):
            raise ValueError("Original World Model byte ledger could not be source-verified")
        if args.report is not None:
            dest = _private_output(world.source, args.report)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("x", encoding="utf8") as stream:
                json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
                stream.write("\n")
            print(json.dumps({
                "status": report["status"],
                "report": str(dest),
                "source_gmp_sha256": world.source_sha256,
                "selected_original_node_ordinals":
                    report["selected_original_node_ordinals"],
                "original_model_noop_reassembled_byte_identical": True,
                "native_edited_BSP_or_MOPP_writer_enabled": False,
            }, sort_keys=True))
        else:
            print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError, OverflowError) as exc:
        print(json.dumps({
            "status": "refused",
            "reason": str(exc),
            "source_gmp_modified": False,
            "native_edited_BSP_or_MOPP_writer_enabled": False,
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
