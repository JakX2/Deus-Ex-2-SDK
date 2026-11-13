#!/usr/bin/env python3
"""Path-anchored DX2Ed v0.97 read-only private OBJ audit CLI adapter.

Receives only a temporary private Box JSON and an existing user-selected
OBJ path; never accepts native map or collision output destinations.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if not (ROOT / "dx2sdk" / "private_brush_obj_audit.py").is_file():
    raise SystemExit("DX2Ed private OBJ audit unavailable in this package")
sys.path.insert(0, str(ROOT))

from dx2sdk.private_brush_obj_audit import main as audit_main


if __name__ == "__main__":
    raise SystemExit(audit_main(sys.argv[1:]))
