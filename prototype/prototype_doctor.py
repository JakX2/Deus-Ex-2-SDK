#!/usr/bin/env python3
"""Offline, read-only preflight for the packaged Windows DX2Ed prototype.

No original retail game assets are required for the self-test. This script
reads only bundled files, creates no output and does not access the network.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SCHEMA = "DX2Ed-Windows-source-prototype-bundle-v1"
GODOT = ("Godot_v4.3-stable_win64.exe",
         "Godot_v4.3-stable_win64_console.exe")
REQUIRED = (
    "dx2sdk/__init__.py",
    "dx2sdk/api.py",
    "dx2sdk/catalog.py",
    "dx2sdk/scalars.py",
    "dx2sdk/clones.py",
    "dx2sdk/multi_clones.py",
    "dx2sdk/projects.py",
    "dx2sdk/__main__.py",
    "dx2sdk/README.md",
    "DX2SDK_CONSOLE.cmd",
    "native_editor/godot_editor/project.godot",
    "native_editor/godot_editor/main.tscn",
    "native_editor/godot_editor/main.gd",
    "native_editor/godot_editor/backend/dx2_native_backend.py",
    "native_editor/godot_editor/backend/dx2_collision_selection_cache.py",
    "native_editor/godot_editor/backend/dx2_script_ibd_provenance.py",
    "native_editor/godot_editor/backend/dx2_mission_kernel_script_diff.py",
    "native_editor/godot_editor/mission_kernel_script_view.gd",
    "native_editor/godot_editor/tests/smoke_mission_kernel_script_view.gd",
    "native_editor/godot_editor/backend/dx2_actor_script_name_candidates.py",
    "native_editor/godot_editor/backend/dx2_script_index_hypothesis_audit.py",
    "native_editor/godot_editor/script_index_audit_view.gd",
    "native_editor/godot_editor/tests/smoke_script_index_hypothesis_audit.gd",
    "native_editor/godot_editor/tests/smoke_original_script_ibd_provenance.gd",
    "tools/scripts/dx2_script_bundle_probe.py",
    "native_editor/godot_editor/capsule_sweep_panel.gd",
    "native_editor/godot_editor/source_edge_capsule_height_replay.gd",
    "native_editor/godot_editor/python_runtime.gd",
    "native_editor/godot_editor/startup_route.gd",
    "native_editor/godot_editor/mission_logic_draft.gd",
    "native_editor/godot_editor/tests/smoke_mission_logic_draft.gd",
    "native_editor/godot_editor/dialogue_design_draft.gd",
    "native_editor/godot_editor/tests/smoke_dialogue_design_draft.gd",
    "native_editor/godot_editor/demo/scene.glb",
    "native_editor/godot_editor/demo/actors.json",
    "native_editor/package_writer/dx2_actor_clone_probe.py",
    "map_exporter/dx2_map_exporter.py",
    "actor_explorer/dx2_actor_explorer.py",
    "research/dx2/export_capsule_first_contact_preview.py",
    "research/dx2/audit_private_capsule_height_profiles.py",
    "third_party/t3sdk_assets/LICENSE",
    "GODOT_LICENSE.txt",
    "prototype-manifest.json",
    "DIAGNOSE_GMP.cmd",
    "map_import_preflight.py",
)
# Run these actual Python entry points with --help, not just AST.parse.
# stdlib-only imports should work on a clean machine without any DX2 game
# assets. The -B flag prevents __pycache__ writes in the extracted ZIP.
PREFLIGHT_WORKERS = (
    "native_editor/godot_editor/backend/dx2_native_backend.py",
    "native_editor/godot_editor/backend/dx2_zip_stage.py",
    "native_editor/godot_editor/backend/dx2_script_ibd_provenance.py",
    "native_editor/godot_editor/backend/dx2_mission_kernel_script_diff.py",
    "map_import_preflight.py",
    "native_editor/godot_editor/backend/dx2_collision_selection_cache.py",
    "research/dx2/export_capsule_first_contact_preview.py",
    "native_editor/package_writer/dx2_actor_clone_probe.py",
)

RETAIL_EXT = {".gmp", ".ibd", ".d2u", ".t3u", ".ibt", ".pak", ".dds",
              ".mp3", ".wav", ".bik", ".tsd"}


def examine(root: Path) -> list[str]:
    root = Path(root).resolve()
    issues: list[str] = []
    if sys.version_info < (3, 11):
        issues.append("python_3_11_or_newer_required")
    for rel in REQUIRED:
        if not (root / rel).is_file():
            issues.append("missing:" + rel)
    if issues:
        return issues
    try:
        manifest = json.loads((root / "prototype-manifest.json").read_text("utf-8"))
        if (manifest.get("schema") != SCHEMA
                or manifest.get("engine") != "Godot 4.3 stable Standard Windows x86_64"
                or manifest.get("includes_original_dx2_assets") is not False
                or manifest.get("includes_havok_runtime") is not False
                or manifest.get("gameplay_physics_or_walkability_verified") is not False
                or manifest.get("public_dx2sdk_api_version") != "0.8.0"
                or manifest.get("public_dx2sdk_cli_included") is not True
                or manifest.get("public_dx2sdk_gameplay_runtime_verified") is not False):
            issues.append("invalid_prototype_manifest")
    except (OSError, ValueError, TypeError):
        return ["invalid_prototype_manifest"]
    try:
        glb = root / "native_editor/godot_editor/demo/scene.glb"
        if glb.read_bytes()[:4] != b"glTF" or glb.stat().st_size < 100:
            issues.append("synthetic_demo_glb_invalid")
        demo = json.loads(
            (root / "native_editor/godot_editor/demo/actors.json").read_text("utf-8"))
        if len(demo.get("actors", [])) != 2:
            issues.append("synthetic_demo_actors_invalid")
    except (OSError, ValueError, TypeError):
        issues.append("synthetic_demo_missing")
    for name in GODOT:
        binary = root / "runtime" / name
        minimum = 50_000 if name.endswith("_console.exe") else 1_000_000
        if not binary.is_file() or binary.stat().st_size < minimum:
            issues.append("godot_runtime_missing_or_invalid:" + name)
            continue
        with binary.open("rb") as handle:
            if handle.read(2) != b"MZ":
                issues.append("godot_runtime_missing_or_invalid:" + name)
                continue
            handle.seek(0)
            digest = hashlib.sha256()
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != manifest.get("runtime_sha256", {}).get(name):
            issues.append("godot_runtime_checksum_mismatch:" + name)
    try:
        for script in root.rglob("*.py"):
            if ".godot" not in script.parts and "__pycache__" not in script.parts:
                ast.parse(script.read_text("utf-8"), filename=script.name)
    except (SyntaxError, OSError, UnicodeError):
        issues.append("bundled_python_syntax_invalid")
    try:
        if not (root / "GODOT_LICENSE.txt").read_text("utf-8").find(
                "Permission is hereby granted") >= 0:
            issues.append("godot_license_notice_missing")
    except (OSError, UnicodeError):
        issues.append("godot_license_notice_missing")
    # A source file can pass syntax validation while its imports fail at
    # runtime (wrong relative layout, missing source worker, unbundled module).
    # Capture/suppress private exception text; report a fixed relative filename.
    for relative in PREFLIGHT_WORKERS:
        try:
            process = subprocess.run(
                [sys.executable, "-B", str(root / relative), "--help"],
                cwd=root, capture_output=True, timeout=20, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            issues.append("worker_import_failed:" + relative)
            continue
        if process.returncode != 0:
            issues.append("worker_import_failed:" + relative)

    # The SDK is a Python package, not a standalone script: --help must
    # import all its dependencies from THIS extracted source-only ZIP.
    try:
        process = subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", "--help"],
            cwd=root, capture_output=True, timeout=20, check=False,
        )
        if (process.returncode != 0
                or b"Deus Ex: Invisible War" not in process.stdout
                or b"move" not in process.stdout):
            issues.append("public_dx2sdk_cli_import_failed")
    except (OSError, subprocess.TimeoutExpired):
        issues.append("public_dx2sdk_cli_import_failed")

    # Refuse accidental copied map files inside the distribution. This check
    # is deliberately read-only and does not enumerate outside the prototype.
    for file in root.rglob("*"):
        if file.is_file() and file.suffix.lower() in RETAIL_EXT:
            issues.append("retail_game_asset_detected")
            break
    return issues


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    issues = examine(args.root)
    if issues:
        for issue in issues:
            print("DX2Ed prototype FAILED: " + issue, file=sys.stderr)
        return 1
    print("DX2Ed prototype preflight: PASS")
    print("Python OK; Godot 4.3 verified; source parsers present; synthetic demo ready.")
    print("No packaged retail game files found. Original maps are owner-provided only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
