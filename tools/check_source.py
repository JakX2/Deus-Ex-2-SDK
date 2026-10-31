#!/usr/bin/env python3
"""Asset-free Python syntax check for the current DX2Ed checkout."""
from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
files = sorted(p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts)
for path in files:
    py_compile.compile(str(path), doraise=True)
print(f"PASS: {len(files)} Python source files compile")
