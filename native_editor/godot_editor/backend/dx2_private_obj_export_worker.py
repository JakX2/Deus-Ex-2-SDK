#!/usr/bin/env python3
"""Tiny path-anchored adapter to the *existing* private v0.93 OBJ exporter.

Arguments are provided by the Godot editor as a temporary user:// private
JSON Box spec and a user-chosen NEW .obj destination. Never opens DX2
original GMP/IBD, never overwrites, never shells out.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if not (ROOT / "dx2sdk" / "private_brush_obj.py").is_file():
    raise SystemExit("DX2Ed private OBJ exporter unavailable in this package")
sys.path.insert(0, str(ROOT))

from dx2sdk.private_brush_obj import main as private_obj_main


if __name__ == "__main__":
    raise SystemExit(private_obj_main(sys.argv[1:]))
