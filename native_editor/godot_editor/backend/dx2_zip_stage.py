#!/usr/bin/env python3
"""Safely stage DX2 Seattle Club source archives for the read-only native viewer.

Accepts club, maps, and optionally System ZIPs. Copies only needed game-data
formats to a private local cache. Never writes to the ZIPs or publishes assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import zipfile

VERSION = "DX2Ed-zip-stage-v1"
MAP_NAME = "M1_Seattle_Club.gmp"
MISSION_NAME = "m1_club.ibd"
REQUIRED_SHARED = {"kernel_gfxall.ibd", "mainmenu_gfxall.ibd"}
SYSTEM_SUFFIXES = {".d2u", ".ini", ".int"}
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 768 * 1024 * 1024
MAX_MEMBERS = 20000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    components = normalized.split("/")
    if (not normalized or normalized.startswith("/") or
        "\x00" in normalized or any(p in ("", ".", "..") for p in components) or
        re.match(r"^[A-Za-z]:", components[0])):
        raise ValueError("Unsafe ZIP member path: " + repr(name))
    return normalized


def members(path: Path) -> list[tuple[zipfile.ZipInfo, str]]:
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_MEMBERS:
            raise ValueError(f"ZIP has too many entries: {path}")
        result = []
        for info in entries:
            if info.is_dir():
                continue
            normalized = validate_name(info.filename)
            if info.flag_bits & 1:
                raise ValueError("Encrypted ZIP entry: " + normalized)
            # Unix symlinks do not belong in an asset staging archive.
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ZIP symbolic link forbidden: " + normalized)
            result.append((info, normalized))
        return result


def select_files(club: Path, maps: Path, system: Path | None,
                 map_name: str, mission_name: str):
    selection: list[tuple[Path, zipfile.ZipInfo, Path]] = []
    base_names = {map_name.casefold(), mission_name.casefold()}
    club_matches = [
        (info, name) for info, name in members(club)
        if PurePosixPath(name).name.casefold() in base_names
    ]
    for expected in sorted(base_names):
        matches = [(info, name) for info, name in club_matches
                   if PurePosixPath(name).name.casefold() == expected]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {expected} in {club.name}; found {len(matches)}")
        info, name = matches[0]
        selection.append((club, info, Path("Maps") / PurePosixPath(name).name))

    shared_names: set[str] = set()
    for info, name in members(maps):
        base = PurePosixPath(name).name
        if PurePosixPath(base).suffix.casefold() != ".ibd":
            continue
        key = base.casefold()
        if key in shared_names:
            raise ValueError("Duplicate map-bundle basename: " + base)
        shared_names.add(key)
        selection.append((maps, info, Path("Maps") / base))
    missing = REQUIRED_SHARED - shared_names
    if missing:
        raise ValueError("Missing required shared bundles: " + ", ".join(sorted(missing)))

    if system is not None:
        destinations: set[str] = set()
        for info, name in members(system):
            path = PurePosixPath(name)
            if path.suffix.casefold() not in SYSTEM_SUFFIXES:
                continue
            # Preserve directories within System rather than flattening
            # potentially duplicate filenames such as UseBlockLoading.ini.
            parts = path.parts
            if parts and parts[0].casefold() == "system":
                parts = parts[1:]
            if not parts:
                continue
            relative = Path("System", *parts)
            key = relative.as_posix().casefold()
            if key in destinations:
                raise ValueError("Duplicate System path: " + relative.as_posix())
            destinations.add(key)
            selection.append((system, info, relative))

    seen: set[str] = set()
    total = 0
    for _archive, info, relative in selection:
        key = relative.as_posix().casefold()
        if key in seen:
            raise ValueError("Duplicate output path: " + relative.as_posix())
        seen.add(key)
        if info.file_size > MAX_FILE_BYTES:
            raise ValueError("Single ZIP entry exceeds staging size limit: " + info.filename)
        total += info.file_size
    if total > MAX_TOTAL_BYTES:
        raise ValueError("Selected files exceed the staging size limit")
    return selection


def _verified_cache(stage: Path, key: str) -> bool:
    manifest = stage / "source_manifest.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("version") != VERSION or data.get("cache_key") != key:
            return False
        records = data.get("files")
        if not isinstance(records, list) or not records:
            return False
        for record in records:
            relative = Path(record["path"])
            if relative.is_absolute() or ".." in relative.parts:
                return False
            output = stage / relative
            if not output.is_file() or output.stat().st_size != record["size"]:
                return False
            if sha256(output) != record["sha256"]:
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def prepare(club: Path, maps: Path, output_root: Path,
            system: Path | None = None, map_name: str = MAP_NAME,
            mission_name: str = MISSION_NAME) -> dict:
    club, maps = club.expanduser().resolve(), maps.expanduser().resolve()
    system = system.expanduser().resolve() if system is not None else None
    archives = [club, maps] + ([system] if system is not None else [])
    if len(set(archives)) != len(archives):
        raise ValueError("Club, maps and System archives must be distinct")
    for source in archives:
        if not source.is_file():
            raise FileNotFoundError(source)
    selection = select_files(club, maps, system, map_name, mission_name)

    # Role-based keys avoid collisions if different directories both contain
    # a generic filename such as resources.zip.
    source_hashes = {"club": sha256(club), "maps": sha256(maps)}
    if system is not None:
        source_hashes["system"] = sha256(system)
    key_input = json.dumps({"version": VERSION, "sources": sorted(source_hashes.items()),
                            "map": map_name, "mission": mission_name}, sort_keys=True)
    key = hashlib.sha256(key_input.encode("utf-8")).hexdigest()[:20]
    root = output_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    stage = root / ("Seattle_Club_" + key)
    if stage.exists():
        if not _verified_cache(stage, key):
            raise ValueError("Staged cache exists but verification failed: " + str(stage))
        return _result(stage, map_name, mission_name, True)

    temporary = Path(tempfile.mkdtemp(prefix=".dx2stage_", dir=root))
    try:
        records = []
        # Open archives one by one; never extract into the game's installation.
        for source in archives:
            with zipfile.ZipFile(source) as archive:
                for archive_path, info, relative in selection:
                    if archive_path != source:
                        continue
                    target = temporary / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    digest = hashlib.sha256()
                    written = 0
                    with archive.open(info) as src, target.open("xb") as dst:
                        while True:
                            block = src.read(1024 * 1024)
                            if not block:
                                break
                            written += len(block)
                            if written > MAX_FILE_BYTES or written > info.file_size:
                                raise ValueError("ZIP expansion exceeded declared size: " + info.filename)
                            dst.write(block)
                            digest.update(block)
                    if written != info.file_size:
                        raise ValueError("ZIP member has unexpected size: " + info.filename)
                    records.append({"path": relative.as_posix(), "size": written,
                                    "sha256": digest.hexdigest(), "source_archive": source.name})
        manifest = {"version": VERSION, "cache_key": key,
                    "source_archives_sha256": source_hashes, "files": records,
                    "note": "Private local game-owned asset cache; never publish."}
        (temporary / "source_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, stage)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return _result(stage, map_name, mission_name, False)


def _result(stage: Path, map_name: str, mission_name: str, cached: bool) -> dict:
    return {
        "status": "ok", "cached": cached, "read_only_source_archives": True,
        "staging_directory": str(stage),
        "map": str(stage / "Maps" / map_name),
        "mission_bundle": str(stage / "Maps" / mission_name),
        "system": str(stage / "System") if (stage / "System").is_dir() else None,
        "manifest": str(stage / "source_manifest.json"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--club", required=True, type=Path)
    parser.add_argument("--maps", required=True, type=Path)
    parser.add_argument("--system", type=Path, help="Optional System archive")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--map-name", default=MAP_NAME)
    parser.add_argument("--mission-name", default=MISSION_NAME)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.club, args.maps, args.output_root,
                                 args.system, args.map_name, args.mission_name)))
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile,
            zipfile.LargeZipFile, NotImplementedError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
