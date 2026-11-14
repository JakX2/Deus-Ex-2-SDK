#!/usr/bin/env python3
"""Read-only candidate discovery for original DX2 doors and vending machines.

Matches are based on text *observed* in original GMP actor names, classes and
mesh resource names. A match is not proof of a functional device or a safe
cloning template. This module never writes a GMP, IBD, actor or script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
ACTOR_EXPLORER = ROOT / "actor_explorer"
if str(ACTOR_EXPLORER) not in sys.path:
    sys.path.insert(0, str(ACTOR_EXPLORER))
from dx2_actor_explorer import actor_records

SCHEMA = "DX2Ed-interactive-original-candidates-v1"
MAX_MAP_BYTES = 256 * 1024 * 1024
MAX_ACTORS = 30000
MAX_RESULTS = 250
NEARBY_RADIUS_UNREAL = 512.0
NEARBY_LIMIT = 5
TOKENS = {
    "door": ("door", "hatch", "airlock", "bulkhead", "gate"),
    "vending": ("vend", "dispenser", "sodamachine", "snackmachine", "soda_machine", "snack_machine"),
}


def _sha256(source: Path) -> str:
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _location(actor: dict) -> list[float] | None:
    value = actor.get("location")
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    if any(type(n) not in (int, float) or not math.isfinite(n) or abs(n) > 1e9 for n in value):
        return None
    return [float(n) for n in value]


def _matches(actor: dict, kind: str) -> list[dict]:
    fields = (("original_actor_name", actor.get("name")),
              ("original_actor_class", actor.get("class")),
              ("original_mesh_name", actor.get("mesh")))
    categories = ("door", "vending") if kind == "both" else (kind,)
    evidence = []
    for category in categories:
        for field, value in fields:
            if not isinstance(value, str):
                continue
            for token in TOKENS[category]:
                if token in value.casefold():
                    evidence.append({"category": category, "source_field": field,
                                     "matched_token": token})
    return evidence


def _nearby(actor: dict, originals: list[dict]) -> list[dict]:
    point = _location(actor)
    if point is None:
        return []
    hits = []
    radius_sq = NEARBY_RADIUS_UNREAL * NEARBY_RADIUS_UNREAL
    for other in originals:
        if other is actor:
            continue
        position = _location(other)
        export = other.get("export")
        if position is None or type(export) is not int or export <= 0:
            continue
        distance_sq = sum((a - b) ** 2 for a, b in zip(point, position))
        if distance_sq <= radius_sq:
            hits.append((distance_sq, export, other))
    hits.sort(key=lambda item: (item[0], item[1]))
    return [
        {"name": original.get("name"), "class": original.get("class"),
         "export": export, "distance_unreal_units": round(math.sqrt(dist), 3)}
        for dist, export, original in hits[:NEARBY_LIMIT]
    ]


def _property_summary(actor: dict) -> tuple[list[int], list[str]]:
    properties = actor.get("game_properties", [])
    if not isinstance(properties, list):
        return [], []
    identifiers = set()
    names = set()
    for prop in properties:
        if not isinstance(prop, dict):
            continue
        number = prop.get("id")
        if type(number) is int and 0 <= number <= 65535:
            identifiers.add(number)
        name = prop.get("name")
        if isinstance(name, str) and 0 < len(name) <= 128:
            names.add(name)
    return sorted(identifiers)[:128], sorted(names)[:128]


def find_candidates(originals: list[dict], *, kind: str = "both",
                    limit: int = 100) -> tuple[list[dict], int]:
    """Classify observations, not object behavior or native spawn eligibility."""
    if kind not in ("door", "vending", "both") or not 1 <= limit <= MAX_RESULTS:
        raise ValueError("Unsupported category or result limit")
    if not isinstance(originals, list) or len(originals) > MAX_ACTORS:
        raise ValueError("Too many actor records")
    seen = set()
    found = []
    total = 0
    for original in originals:
        if not isinstance(original, dict):
            raise ValueError("Malformed source actor")
        export = original.get("export")
        if type(export) is not int or export <= 0 or export in seen:
            raise ValueError("Duplicate or malformed source export")
        seen.add(export)
        evidence = _matches(original, kind)
        if not evidence:
            continue
        total += 1
        if len(found) >= limit:
            continue
        ids, names = _property_summary(original)
        found.append({
            "source_actor_name": original.get("name"),
            "source_export": export,
            "source_class": original.get("class"),
            "source_mesh": original.get("mesh"),
            "location_unreal_xyz": _location(original),
            "matching_source_fields": evidence,
            "original_gamesys_property_ids": ids,
            "original_gamesys_property_names": names,
            "raw_trigger_script_field_present": original.get(
                "trigger_script_serialized") is not None,
            "nearby_source_actors_spatial_only": _nearby(original, originals),
            "functional_interaction_verified": False,
            "actor_script_binding_verified": False,
            "native_clone_eligible": False,
        })
    return found, total


def audit(map_path: Path, *, system_path: Path | None = None,
          kind: str = "both", limit: int = 100) -> dict:
    source = Path(map_path).expanduser().resolve(strict=True)
    if (source.suffix.casefold() != ".gmp" or not source.is_file()
            or not 0 < source.stat().st_size <= MAX_MAP_BYTES):
        raise ValueError("Expected an existing original GMP within the file-size limit")
    if system_path is not None:
        system_path = Path(system_path).expanduser().resolve(strict=True)
        if not system_path.exists():
            raise ValueError("System source not found")
    before = _sha256(source)
    meta, originals = actor_records(source, system_path)
    if (not isinstance(meta, dict)
            or meta.get("map_sha256") != before
            or str(meta.get("map", "")).casefold() != source.name.casefold()):
        raise ValueError("GMP or actor catalog source identity mismatch")
    found, count = find_candidates(originals, kind=kind, limit=limit)
    if _sha256(source) != before:
        raise ValueError("Original GMP changed while it was being inspected")
    return {
        "schema": SCHEMA,
        "source_map": source.name,
        "source_sha256": before,
        "source_actor_count": len(originals),
        "category": kind,
        "candidate_count": count,
        "returned_count": len(found),
        "truncated": count > len(found),
        "original_actor_parse_failures": len(meta.get("scene_parse_failures", [])),
        "original_property_decode_failures": len(meta.get("game_property_decode_errors", [])),
        "candidates": found,
        "read_only": True,
        "source_gmp_modified": False,
        "functional_interactions_verified": False,
        "native_interactive_clone_supported": False,
        "actor_links_verified": False,
        "game_runtime_verified": False,
        "warnings": [
            "Name, class or mesh substring matches are discovery hints, never actor-type proof.",
            "Nearby actors are spatial neighbors, NOT decoded switches, scripts, links or dependencies.",
            "GameSys IDs and names are observed source fields; opaque and array values are not writable.",
            "Existing StaticMeshActor clone success does NOT establish door/vending behavior.",
            "No native map, IBD, actor, collision, script or GameSys output is generated.",
        ],
    }


def _output(report: dict, output: Path, source: Path) -> Path:
    destination = output.expanduser().resolve()
    if destination.suffix.casefold() != ".json":
        raise ValueError("Output must be JSON")
    if (destination == source or destination == source.parent
            or destination.is_relative_to(source.parent)):
        raise ValueError("Private reports must stay outside the original Maps directory")
    if not destination.parent.is_dir():
        raise ValueError("Private output directory must already exist")
    with destination.open("x", encoding="utf8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=True, allow_nan=False)
        handle.write("\n")
    return destination


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", required=True, type=Path, help="Original local DX2 GMP")
    parser.add_argument("--system", type=Path, help="Optional original System directory/ZIP")
    parser.add_argument("--kind", choices=("door", "vending", "both"), default="both")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", type=Path, help="New private JSON outside the Maps folder")
    args = parser.parse_args(argv)
    try:
        source = args.map.expanduser().resolve(strict=True)
        report = audit(source, system_path=args.system, kind=args.kind,
                       limit=args.limit)
        if _sha256(source) != report["source_sha256"]:
            raise ValueError("Original GMP changed after source audit")
        if args.output is None:
            print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))
        else:
            destination = _output(report, args.output, source)
            print(json.dumps({"status": "ok", "output": str(destination),
                              "candidate_count": report["candidate_count"],
                              "read_only": True}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        print(json.dumps({"status": "refused", "error": str(error)[:220],
                          "read_only": True}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
