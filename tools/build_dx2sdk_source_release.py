#!/usr/bin/env python3
"""Build a Python-only, original-game-file-free DX2SDK v0.1 source ZIP.

No Godot 4.3 binary or interpreter bundled. All imports are local,
standard-library + the existing audited DX2Ed / MIT T3SDK sources.
Original DX2 maps, IBDs, TSDs, textures and any game runtime are forbidden.
Usage: python tools/build_dx2sdk_source_release.py --output NEW.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = "DX2SDK_Python_0.3.0"
SCHEMA = "DX2SDK-source-only-Python-portable-v0.1"
DATE = (2026, 11, 5, 0, 0, 0)

ALLOWED = {
    "dx2sdk": {".py", ".md"},
    "actor_explorer": {".py"},
    "map_exporter": {".py"},
    "native_editor/godot_editor/backend": {".py"},
    "native_editor/package_writer": {".py"},
    "third_party/t3sdk_assets": {".py"},
    "tools/scripts": {".py"},
}
REQUIRED = (
    "dx2sdk/__init__.py",
    "dx2sdk/__main__.py",
    "dx2sdk/api.py",
    "dx2sdk/catalog.py",
    "dx2sdk/scalars.py",
    "dx2sdk/projects.py",
    "actor_explorer/dx2_actor_explorer.py",
    "actor_explorer/dx2catalog.py",
    "dx2sdk/README.md",
    "dx2sdk/RUN_SDK_STANDALONE.cmd",
    "map_exporter/dx2inspect.py",
    "map_exporter/dx2level.py",
    "native_editor/godot_editor/backend/dx2_native_save_as.py",
    "native_editor/godot_editor/backend/dx2_gameplay_catalog.py",
    "native_editor/godot_editor/backend/dx2_script_ibd_provenance.py",
    "native_editor/godot_editor/backend/dx2_mission_kernel_script_diff.py",
    "native_editor/package_writer/dx2_package_roundtrip.py",
    "third_party/t3sdk_assets/upkg.py",
    "third_party/t3sdk_assets/upkgwrite.py",
    "third_party/t3sdk_assets/LICENSE",
    "third_party/t3sdk_assets/formats.json",
    "tools/scripts/dx2_script_bundle_probe.py",
)
RETAIL_EXT = {
    ".gmp", ".ibd", ".ibt", ".d2u", ".t3u", ".pak", ".dds", ".glb",
    ".tsd", ".wav", ".mp3", ".bik", ".exe", ".dll", ".zip", ".lbd",
    ".psk", ".psa", ".ski", ".ogg",
}


def _info(path: str) -> ZipInfo:
    entry = ZipInfo(f"{ARCHIVE}/{path}", DATE)
    entry.compress_type = ZIP_DEFLATED
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    return entry


def _sources(root: Path) -> dict[str, bytes]:
    if any(not (root / rel).is_file() or (root / rel).is_symlink()
           for rel in REQUIRED):
        raise ValueError("One or more required SDK source files are missing")
    files: dict[str, bytes] = {}
    for folder, suffixes in ALLOWED.items():
        base = root / folder
        if not base.is_dir():
            raise ValueError("Missing required SDK source directory")
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            parts = path.relative_to(base).parts
            if any(part.startswith(".") or part == "__pycache__"
                   for part in parts):
                continue
            if path.suffix.lower() in suffixes:
                files[rel] = path.read_bytes()
    files["third_party/t3sdk_assets/LICENSE"] = (
        root / "third_party/t3sdk_assets/LICENSE").read_bytes()
    # The MIT T3SDK t3common.py imports this code/data format table at
    # module import time. No other original/sample asset JSON is bundled.
    files["third_party/t3sdk_assets/formats.json"] = (
        root / "third_party/t3sdk_assets/formats.json").read_bytes()
    # The only CMD script shipped is source-owned and remapped to archive root.
    files["RUN_DX2SDK.cmd"] = (
        root / "dx2sdk/RUN_SDK_STANDALONE.cmd").read_bytes()
    if any(rel not in files for rel in REQUIRED
           if rel != "dx2sdk/RUN_SDK_STANDALONE.cmd"):
        raise ValueError("Required SDK dependency omitted by source-only allowlist")
    if any(Path(rel).suffix.lower() in RETAIL_EXT for rel in files):
        raise ValueError("Unexpected retail or binary resource in source archive")
    if any(len(data) > 4 * 1024 * 1024 for data in files.values()):
        raise ValueError("Source file exceeds safe SDK release size")
    return files


def build(source_root: Path, output: Path) -> dict:
    root = source_root.expanduser().resolve(strict=True)
    target = output.expanduser().resolve()
    if (target.suffix.lower() != ".zip" or target.exists()
            or not target.parent.is_dir() or root in target.parents
            or target == root):
        raise ValueError("Output requires a new SDK ZIP outside source repository")
    files = _sources(root)
    # A manifest maps exact file paths to their public-source checksums.
    # It never embeds source system or user game paths or proprietary bytes.
    manifest = {
        "schema": SCHEMA,
        "version": "0.3.0",
        "python_minimum": "3.11",
        "requires_godot": False,
        "includes_original_dx2_assets": False,
        "retail_game_runtime_tested": False,
        "native_writer_scope": "existing_StaticMeshActor_Location_only",
        "native_writer_requires_explicit_write": True,
        "bsp_mopp_or_native_script_writer": False,
        "third_party_t3sdk_license": "third_party/t3sdk_assets/LICENSE",
        "source_sha256": {
            name: hashlib.sha256(data).hexdigest()
            for name, data in sorted(files.items())
        },
    }
    with ZipFile(target, "x", compression=ZIP_DEFLATED, compresslevel=9,
                 allowZip64=False) as archive:
        for rel, data in sorted(files.items()):
            archive.writestr(_info(rel), data)
        archive.writestr(_info("sdk-manifest.json"),
                         (json.dumps(manifest, indent=2, sort_keys=True)
                          + "\n").encode("utf8"))
    with ZipFile(target) as archive:
        if archive.testzip() is not None:
            target.unlink(missing_ok=True)
            raise ValueError("Created SDK ZIP checksum test failed")
        entries = archive.namelist()
        if len(entries) != len(set(entries)):
            target.unlink(missing_ok=True)
            raise ValueError("Created SDK ZIP has duplicate archive entries")
    return {
        "schema": SCHEMA,
        "version": "0.3.0",
        "file_count": len(files),
        "zip_bytes": target.stat().st_size,
        "includes_original_dx2_assets": False,
        "gameplay_runtime_verified": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        report = build(args.source_root, args.output)
    except (OSError, ValueError, TypeError):
        print(json.dumps({"status": "refused", "code": "unsafe_or_incomplete_source_package"}))
        return 2
    print(json.dumps({"status": "ok", **report}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
