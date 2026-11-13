#!/usr/bin/env python3
"""DX2Ed P102: only private Box CSG shell JSON to stdout.

Four small, temporary source-private JSON files are passed by the editor.
No native GMP, IBD, BSP, original actor, GameSys or collision input allowed.
This process never writes files.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if not (ROOT / "dx2sdk" / "private_brush_subtraction.py").is_file():
    raise SystemExit("Source-private CSG preview module missing in package")
sys.path.insert(0, str(ROOT))

from dx2sdk.private_brush_obj import _load_private_json
from dx2sdk.private_brush_intersection import intersect_private_boxes
from dx2sdk.private_brush_subtraction import subtract_private_boxes


def main(argv: list[str]) -> int:
    if len(argv) != 5 or argv[0] not in ("intersection", "subtraction"):
        print("Expected source-private CSG operation and four JSON files",
              file=sys.stderr)
        return 2
    try:
        left, right, transform_a, transform_b = (
            _load_private_json(Path(name)) for name in argv[1:]
        )
        operation = argv[0]
        report = (
            intersect_private_boxes(left, right, transform_a=transform_a,
                                    transform_b=transform_b)
            if operation == "intersection" else
            subtract_private_boxes(left, right, transform_a=transform_a,
                                   transform_b=transform_b)
        )
        # Never print proprietary source metadata; all inputs are only
        # editor-private Box specs and numeric proper-rigid preview placements.
        print(json.dumps(report, sort_keys=True, allow_nan=False,
                         separators=(",", ":")))
        return 0
    except (OSError, TypeError, ValueError, KeyError, UnicodeError) as exc:
        print("Private CSG preview REFUSED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
