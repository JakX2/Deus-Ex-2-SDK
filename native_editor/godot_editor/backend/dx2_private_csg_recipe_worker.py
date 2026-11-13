#!/usr/bin/env python3
"""P103 path-anchored source-private CSG recipe worker.

Uses only private clipped Box/transform JSON and user-selected .dx2csg.json.
No original map loader, native BSP, actor or collision serialization.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if not (ROOT / "dx2sdk" / "private_csg_recipe.py").is_file():
    raise SystemExit("P103 private CSG recipe SDK module missing in package")
sys.path.insert(0, str(ROOT))

from dx2sdk.private_csg_recipe import main as recipe_main


if __name__ == "__main__":
    raise SystemExit(recipe_main(sys.argv[1:]))
