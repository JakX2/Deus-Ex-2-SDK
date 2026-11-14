#!/usr/bin/env python3
"""Godot packaged read-only original World BSP node dossier command."""
from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if not (ROOT / "research" / "dx2" / "inspect_bsp_node_dossier.py").is_file():
    raise SystemExit("DX2 original BSP node dossier unavailable in package")
sys.path.insert(0, str(ROOT / "research" / "dx2"))
from inspect_bsp_node_dossier import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
