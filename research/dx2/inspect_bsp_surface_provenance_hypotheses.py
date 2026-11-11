#!/usr/bin/env python3
"""Source-SHA-pinned original DX2 BSP field2 / Level provenance hypothesis audit.

Requires user-owned UE95 DX2 GMP, supported by DX2Map. Read-only.
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
    p.add_argument("--source-sha256", required=True, help="Exact original source GMP SHA-256")
    p.add_argument("--field2-plane-coherence", action="store_true",
                   help="Audit same raw BSP field2 IDs against source Model planes without Level triangle guessing")
    p.add_argument("--report", type=Path, help="Fresh private JSON outside the retail Maps folder")
    args = p.parse_args(argv)
    try:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", args.source_sha256):
            raise ValueError("Require exactly one pinned original 64-digit GMP SHA-256")
        world = DX2Map.open(args.original_gmp)
        if world.source_sha256 != args.source_sha256.lower():
            raise ValueError("Original GMP SHA-256 does not match requested source")
        method = (world.inspect_bsp_surface_plane_coherence
                  if args.field2_plane_coherence
                  else world.inspect_bsp_surface_provenance_hypotheses)
        result = method()
        if args.report is not None:
            dest = _private_output(world.source, args.report)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("x", encoding="utf8") as stream:
                json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
                stream.write("\n")
            summary = {
                "status": result["status"], "report": str(dest),
                "source_sha256": result["source_sha256"],
                "retail_runtime_verified": False,
            }
            if args.field2_plane_coherence:
                summary.update({
                    "source_reused_field2_groups": result["source_reused_field2_groups"],
                    "source_field2_is_authenticated_surface_index": False,
                })
            else:
                summary.update({
                    "unique_geometric_node_candidates":
                        result["unique_geometric_node_candidates"],
                    "field2_is_engine_authenticated_surface_index": False,
                })
            print(json.dumps(summary, sort_keys=True))
        else:
            print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError, OverflowError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc),
                          "original_gmp_modified": False,
                          "retail_runtime_verified": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
