"""DX2SDK v0.1 versioned source-locked multi-actor position plans.

Project plans are authoring JSON, NOT native GMP patches. The only writer
is DX2Map.save_as_translations, with the original SHA and binary checks.
No executable scripts, transforms other than Location X/Y/Z, or game folder
outputs are supported.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

from .api import DX2Map, _finite_xyz, _safe_output, MAX_MOVES
from dx2_gameplay_catalog import hash_path

SCHEMA = "DX2SDK-position-plan-v1"
MAX_PLAN_BYTES = 2_000_000


def _require_cache(world: DX2Map) -> dict:
    world._check_original_unchanged()
    if world.actors_file is None or world._cache is None:
        raise ValueError("DX2SDK plans require a source-matched original actors.json")
    return world._cache


def build_position_plan(
    world: DX2Map, positions: Mapping[str, Sequence[float]],
) -> dict:
    """Construct private editable plan data for existing source actors."""
    cache = _require_cache(world)
    if (not isinstance(positions, Mapping)
            or not 1 <= len(positions) <= MAX_MOVES):
        raise ValueError("Position plan requires 1..10000 native source actor moves")
    source = {}
    for a in cache["actors"]:
        name = a.get("name")
        if type(name) is not str or name in source:
            raise ValueError("Source actor names must be unique")
        source[name] = a
    moves = []
    for name, xyz in positions.items():
        if type(name) is not str or name not in source:
            raise ValueError("Plan references unknown original actor")
        original = source[name]
        if original.get("class") != "StaticMeshActor" or not original.get("mesh"):
            raise ValueError("Only existing rendered StaticMeshActors can be planned")
        target = _finite_xyz(xyz)
        before = _finite_xyz(original.get("location", []))
        if all(abs(a-b) < 0.00001 for a, b in zip(before, target)):
            raise ValueError("Plan must specify meaningful native position changes")
        idx = original.get("export")
        if type(idx) is not int or idx < 1:
            raise ValueError("Original actor export must be a positive integer")
        moves.append({
            "actor": name,
            "source_actor_export": idx,
            "source_actor_class": "StaticMeshActor",
            "source_native_location": list(before),
            "new_native_location": list(target),
        })
    moves.sort(key=lambda r: r["source_actor_export"])
    return {
        "schema": SCHEMA,
        "source_map": world.source.name,
        "source_map_sha256": world.source_sha256,
        "source_actor_cache_sha256": hash_path(world.actors_file),
        "moves": moves,
        "output_is_gameplay_verified": False,
        "native_script_edits_enabled": False,
        "native_bsp_collision_writer_enabled": False,
        "read_only_source": True,
    }


def write_position_plan(
    world: DX2Map, positions: Mapping[str, Sequence[float]],
    path: str | Path,
) -> dict:
    """Write a NEW private planning JSON. Refuses original game folders."""
    plan = build_position_plan(world, positions)
    dest = Path(path).expanduser().resolve()
    if dest.suffix.casefold() != ".json" or dest.exists():
        raise ValueError("New private plan requires unused .json path")
    if (dest.parent == world.source.parent or
            world.source.parent in dest.parents):
        raise ValueError("Position plan may not be written under original game maps")
    parts = tuple(p.casefold() for p in dest.parent.parts)
    if any(parts[i:i+3] == ("content", "dx2", "maps")
           for i in range(max(0, len(parts) - 2))):
        raise ValueError("Position plan cannot be placed inside game Content/DX2/Maps")
    blob = (json.dumps(plan, ensure_ascii=True, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf8")
    if len(blob) > MAX_PLAN_BYTES:
        raise ValueError("Position plan exceeds supported safety size")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("xb") as stream:
        stream.write(blob)
    return plan


def load_position_plan(world: DX2Map, path: str | Path) -> dict[str, list[float]]:
    """Revalidate every original source identity before returning positions.

    This method never assumes an untrusted plan's native actor class, export
    or original location is authoritative. It checks all fields against
    current source-matched actors.json and the GMP file before use.
    """
    cache = _require_cache(world)
    file = Path(path).expanduser().resolve(strict=True)
    if file.suffix.casefold() != ".json" or not 0 < file.stat().st_size <= MAX_PLAN_BYTES:
        raise ValueError("Invalid position plan size or extension")
    doc = json.loads(file.read_text(encoding="utf8"))
    if (not isinstance(doc, dict) or doc.get("schema") != SCHEMA
            or doc.get("source_map") != world.source.name
            or doc.get("source_map_sha256") != world.source_sha256
            or doc.get("source_actor_cache_sha256") != hash_path(world.actors_file)
            or doc.get("output_is_gameplay_verified") is not False
            or doc.get("native_script_edits_enabled") is not False
            or doc.get("native_bsp_collision_writer_enabled") is not False
            or doc.get("read_only_source") is not True):
        raise ValueError("Position plan source or binary capability mismatch")
    rows = doc.get("moves")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_MOVES:
        raise ValueError("Invalid position plan actor list")
    actors = {a["name"]: a for a in cache["actors"]}
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed position plan actor record")
        name = row.get("actor")
        if type(name) is not str or name in result or name not in actors:
            raise ValueError("Duplicate or unknown source actor in position plan")
        original = actors[name]
        if (original.get("class") != "StaticMeshActor"
                or not original.get("mesh")
                or type(row.get("source_actor_export")) is not int
                or row["source_actor_export"] != original.get("export")
                or row.get("source_actor_class") != "StaticMeshActor"
                or list(_finite_xyz(row.get("source_native_location"))) !=
                    list(_finite_xyz(original.get("location")))):
            raise ValueError("Position plan actor identity no longer matches original GMP")
        target = _finite_xyz(row.get("new_native_location"))
        if all(abs(a-b) < 0.00001 for a, b in zip(
                target, _finite_xyz(original["location"]))):
            raise ValueError("Original and planned actor positions are identical")
        result[name] = list(target)
    return result


def apply_position_plan(
    world: DX2Map, plan: str | Path, output: str | Path,
    *, write: bool = False,
) -> dict:
    """Dry run by default; optional fully verified new isolated GMP copy."""
    moves = load_position_plan(world, plan)
    _safe_output(world.source, output)
    return world.save_as_translations(moves, output, write=write)
