#!/usr/bin/env python3
"""Read-only catalog of original DX2 SkeletalMeshes *.ski descriptors.

This parses *metadata*, NOT the geometry in .pro, rig weights, animation
frames, NPC archetypes or character appearance. No source files are edited.
The v2-v5 descriptor grammar is validated conservatively; unsafe/unrecognized
members cause an error rather than invented animation links.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import zipfile

SCHEMA = "DX2Ed-original-skeletal-ski-inventory-v1"
VERSIONS = {"v2", "v3", "v4", "v5"}
MAX_SKI = 16384
MAX_FILES = 2000
MAX_LINKS = 64


def _integer(value: str, low: int = 0, high: int = MAX_LINKS) -> int:
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError("Expected unsigned integer in SKI")
    n = int(value)
    if n < low or n > high:
        raise ValueError("SKI count outside supported limits")
    return n


def _finite_numbers(text: str, count: int) -> list[float]:
    values = text.split()
    if len(values) != count:
        raise ValueError("Wrong number of numeric SKI values")
    try:
        numbers = [float(x) for x in values]
    except ValueError as e:
        raise ValueError("Bad numeric SKI value") from e
    if any(not math.isfinite(v) or abs(v) > 1e6 for v in numbers):
        raise ValueError("Non-finite/out-of-bounds SKI number")
    return numbers


def parse_ski(raw: bytes, member: str) -> dict:
    if len(raw) == 0 or len(raw) > MAX_SKI:
        raise ValueError("Missing or oversized SKI descriptor")
    path = PurePosixPath(member)
    if path.suffix.casefold() != ".ski" or any(s in ("", "..") for s in path.parts):
        raise ValueError("Unsafe SKI member path")
    try:
        lines = [line.strip() for line in raw.decode("utf-8-sig").splitlines()
                 if line.strip()]
    except UnicodeDecodeError as e:
        raise ValueError("Non-text SKI descriptor") from e
    if len(lines) < 9 or len(lines) > 200 or lines[0].lower() not in VERSIONS:
        raise ValueError("Unrecognized SKI version or malformed descriptor")
    name = lines[1]
    if (not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", name)
        or name.casefold() != path.stem.casefold()):
        raise ValueError("SKI mesh identity does not match filename")
    position = _finite_numbers(lines[2], 3)
    rotation = _finite_numbers(lines[3], 3)
    scale = _finite_numbers(lines[4], 3)
    if any(abs(v) < 1e-9 for v in scale):
        raise ValueError("Unsupported zero SKI scale")
    # Two upstream editor configuration lines, not interpreted as animation.
    _finite_numbers(lines[5], 4)
    _finite_numbers(lines[6], 5)
    i = 7
    flags = ""
    if lines[i].startswith("MeshFlags="):
        flags = lines[i].split("=", 1)[1]
        if not re.fullmatch(r"[A-Za-z0-9_]{0,32}", flags):
            raise ValueError("Bad SKI MeshFlags value")
        i += 1
    thresholds: list[float] = []
    if lines[0].lower() == "v5":
        count = _integer(lines[i], 0, 16)
        i += 1
        if i + count > len(lines):
            raise ValueError("Truncated v5 SKI thresholds")
        thresholds = [_finite_numbers(lines[i + j], 1)[0] for j in range(count)]
        i += count
    if i >= len(lines):
        raise ValueError("Missing SKI animation count")
    n = _integer(lines[i], 0, 64)
    i += 1
    animation_sets = []
    for _ in range(n):
        if i >= len(lines):
            raise ValueError("Truncated SKI animation links")
        value = lines[i].replace("\\", "/")
        if not re.fullmatch(r"[A-Za-z0-9_./-]{1,256}", value):
            raise ValueError("Bad SKI animation link")
        animation_sets.append(PurePosixPath(value).name)
        i += 1
        if i < len(lines) and lines[i].startswith("Flags="):
            i += 1
    if i != len(lines) - 1 or lines[i] != "0":
        raise ValueError("Unsupported SKI trailer or animation layout")
    return {"name": name, "version": lines[0].lower(), "mesh_flags": flags,
            "position": position, "rotation": rotation, "scale": scale,
            "lod_thresholds": thresholds,
            "animation_sets": animation_sets,
            "read_only": True, "geometry_decoded": False,
            "npc_class_mapping_verified": False}


def catalog_from_zip(path: Path) -> dict:
    path = Path(path)
    if not path.is_file() or not zipfile.is_zipfile(path):
        raise ValueError("Expected existing SkeletalMeshes.zip")
    with zipfile.ZipFile(path) as archive:
        infos = [i for i in archive.infolist() if not i.is_dir()]
        if len(infos) > MAX_FILES:
            raise ValueError("Too many skeletal archive members")
        pro_names = set()
        seen = set()
        for info in infos:
            member = PurePosixPath(info.filename.replace("\\", "/"))
            if member.is_absolute() or ".." in member.parts:
                raise ValueError("Unsafe skeletal ZIP member")
            if member.suffix.casefold() == ".pro":
                pro_names.add(member.stem.casefold())
        records = []
        for info in infos:
            if not info.filename.casefold().endswith(".ski"):
                continue
            if info.file_size > MAX_SKI:
                raise ValueError("Oversized skeletal descriptor")
            record = parse_ski(archive.read(info), info.filename)
            key = record["name"].casefold()
            if key in seen:
                raise ValueError("Duplicate case-insensitive skeletal mesh name")
            seen.add(key)
            record["pro_present"] = key in pro_names
            records.append(record)
    records.sort(key=lambda x: x["name"].casefold())
    return {"schema": SCHEMA, "read_only": True,
            "source_archive": path.name,
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "geometry_decoded": False, "npc_spawn_enabled": False,
            "record_count": len(records), "pro_count": len(pro_names),
            "versions": dict(sorted(Counter(x["version"] for x in records).items())),
            "records": records}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)
    catalog = catalog_from_zip(args.archive)
    if args.output is not None:
        output = args.output.resolve()
        if output.suffix.casefold() != ".json" or output == args.archive.resolve():
            ap.error("Output must be separate, new JSON")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(catalog, stream, indent=2)
        print(json.dumps({"status": "ok", "output": str(output),
                          "skeletal_descriptors": catalog["record_count"],
                          "read_only": True}))
    else:
        print(json.dumps(catalog, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
