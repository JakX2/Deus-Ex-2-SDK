#!/usr/bin/env python3
"""Read-only DX2 Level -> native world Model linkage and node-prefix audit.

The direct Model link is parsed after four FURL strings, optional URL strings,
port and validity. No native BSP tree, collision or writable package implied.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORTER = PROJECT_ROOT / "map_exporter"
if str(EXPORTER) not in sys.path:
    sys.path.insert(0, str(EXPORTER))
from dx2inspect import Package, Cursor

SCHEMA = "DX2SDK-Level-direct-world-Model-reference-v1"
OBSERVED_LICENSEES = frozenset((65, 67, 68, 69))
MAX_MAP_BYTES = 250 * 1024 * 1024
MAX_MAPS = 64
MAX_LEVEL_ACTORS = 100000
MAX_URL_OPTIONS = 64
MAX_CANDIDATE_NODES = 200000


def _parse_world_model(pkg: Package) -> dict:
    levels = [e for e in pkg.exports if pkg.class_name(e) == "Level" and e["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected exactly one nonempty Level export")
    raw = pkg.payload(levels[0])
    if len(raw) < 32:
        raise ValueError("Level payload shorter than source-observed header")
    r = Cursor(raw, 13)
    count, repeated = r.u32(), r.u32()
    if count != repeated or count > MAX_LEVEL_ACTORS or count > len(raw):
        raise ValueError("Inconsistent or excessive Level actor count")
    actor_refs = []
    for _ in range(count):
        ref = r.ci()
        if ref <= 0 or ref > len(pkg.exports):
            raise ValueError("Invalid export reference in Level actor list")
        actor_refs.append(ref)
    if len(set(actor_refs)) != len(actor_refs):
        raise ValueError("Duplicate export references in Level actor list")

    # FURL: Protocol, Host, Map, Portal, TArray<FString> options,
    # Port (u32), Valid (u32); then native direct Level Model reference.
    url_offset = r.at
    url_values = [r.fstr() for _ in range(4)]
    if not all(len(s) <= 1024 for s in url_values):
        raise ValueError("Unreasonable URL string length")
    option_count = r.ci()
    if not 0 <= option_count <= MAX_URL_OPTIONS:
        raise ValueError("Invalid FURL options array count")
    options = [r.fstr() for _ in range(option_count)]
    if not all(len(s) <= 1024 for s in options):
        raise ValueError("Unreasonable URL option string length")
    port = r.u32()
    valid = r.u32()
    if not (0 < port <= 65535 and valid in (0, 1)):
        raise ValueError("Unexpected URL port or validity indicator")
    world_ref_offset = r.at
    model_ref = r.ci()
    if model_ref <= 0 or model_ref > len(pkg.exports):
        raise ValueError("Invalid direct Level Model export reference")
    model = pkg.exports[model_ref - 1]
    if pkg.class_name(model) != "Model":
        raise ValueError("Direct Level reference does not target a Model export")
    if model_ref in actor_refs:
        raise ValueError("Direct Level Model appears in Level actor list")
    payload = pkg.payload(model)
    if len(payload) < 67:
        raise ValueError("Direct Level Model too short for source-observed prefix")
    zero_prefix9 = payload[:9] == bytes(9)
    bounds = struct.unpack_from("<6f", payload, 9)
    box_valid = payload[33]
    sphere = struct.unpack_from("<4f", payload, 34)
    header_zero_when_invalid = box_valid == 0 and all(v == 0.0 for v in (*bounds, *sphere))
    # Immediately after the 50-byte prefix: Unreal compact integer. In all
    # examined DX2 maps it correlates with number of BSP node-like records.
    # Its real native field name is unverified.
    mr = Cursor(payload, 50)
    candidate_nodes = mr.ci()
    first_candidate_plane_at = mr.at
    if not 0 < candidate_nodes <= MAX_CANDIDATE_NODES:
        raise ValueError("Direct Level Model has invalid compact candidate node count")
    if first_candidate_plane_at + 16 > len(payload):
        raise ValueError("Direct Level Model lacks candidate first node plane")
    first_plane = struct.unpack_from("<4f", payload, first_candidate_plane_at)
    normal = first_plane[:3]
    unit_normal = all(math.isfinite(n) for n in first_plane) and (
        abs(math.sqrt(sum(v*v for v in normal)) - 1.0) <= 1e-3)
    return {
        "level_export": levels[0]["name"], "level_actor_count": count,
        "level_actor_refs_unique": True, "furl_offset_in_level": url_offset,
        "furl": {"protocol": url_values[0], "host": url_values[1],
                 "map": url_values[2], "portal": url_values[3],
                 "options": options, "port": port, "valid": valid},
        "level_model_ref_offset_in_level": world_ref_offset,
        "world_model_export_ref": model_ref,
        "world_model_export_name": model["name"],
        "world_model_payload_bytes": len(payload),
        "world_model_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "world_model_initial_9_zero_bytes": zero_prefix9,
        "world_model_box_valid_byte": box_valid,
        "world_model_zero_bounds_and_sphere": header_zero_when_invalid,
        "world_model_compact_node_count_at_50": candidate_nodes,
        "world_model_candidate_node_count_width": first_candidate_plane_at - 50,
        "world_model_first_candidate_plane_offset": first_candidate_plane_at,
        "world_model_first_plane_normal_unit": unit_normal,
        "world_model_first_candidate_plane_xyz_w": list(first_plane),
        "direct_model_ref_not_in_actor_list": True,
    }


def audit_map(path: Path) -> dict:
    path = Path(path)
    if path.suffix.lower() != ".gmp" or not path.is_file():
        raise ValueError("Expected existing user-owned .gmp")
    if path.stat().st_size > MAX_MAP_BYTES:
        raise ValueError("Input map exceeds 250 MB safety limit")
    pkg = Package(path)
    if pkg.version != 95 or pkg.licensee not in OBSERVED_LICENSEES:
        raise ValueError("Expected source-observed UE95 DX2 licensee 65/67/68/69")
    result = _parse_world_model(pkg)
    candidate_models = []
    for exp in pkg.exports:
        if pkg.class_name(exp) != "Model" or exp["size"] <= 4096:
            continue
        data = pkg.payload(exp)
        if len(data) >= 51 and data[33] == 0:
            candidate_models.append(exp["index"])
    result["large_invalid_box_model_candidates"] = candidate_models
    result["level_model_matches_unique_large_invalid_box_candidate"] = (
        candidate_models == [result["world_model_export_ref"]])
    return {
        "file": path.name, "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
        "source_bytes": len(pkg.data), "unreal_package_version": pkg.version,
        "licensee_version": pkg.licensee, **result,
    }


def audit_maps(paths) -> dict:
    if not paths or len(paths) > MAX_MAPS:
        raise ValueError("Supply between 1 and 64 original DX2 maps")
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Duplicate input map path")
    rows = [audit_map(path) for path in resolved]
    counter = Counter()
    for row in rows:
        counter["maps"] += 1
        counter["direct_world_model_class_matches"] += 1
        counter["world_model_unique_large_invalid_bbox_matches"] += int(
            row["level_model_matches_unique_large_invalid_box_candidate"])
        counter["first_candidate_plane_unit_normals"] += int(
            row["world_model_first_plane_normal_unit"])
        counter["compact_node_count_total"] += row["world_model_compact_node_count_at_50"]
        counter["licensee_"+str(row["licensee_version"])] += 1
    return {
        "schema": SCHEMA, "read_only": True, "source_maps_modified": False,
        "native_world_bsp_nodes_decoded": False, "collision_or_physics_decoded": False,
        "runtime_verified_by_this_audit": False,
        "summary": dict(counter), "maps": rows,
        "limits": [
            "The direct Level link identifies a valid native Model export, distinct from actor ownership.",
            "The compact integer at world Model offset 50 is a node-count hypothesis.",
            "First 4 float32 values after the count are a plane candidate, not full BSP nodes.",
            "Node-to-Level-render-block, collision, leaf, PVS or physics links remain undecoded.",
            "No source package is written, installed or run.",
        ],
    }


def write_report(report: dict, output: Path, sources) -> None:
    output = Path(output).resolve()
    inputs = [Path(p).resolve() for p in sources]
    if output.suffix.casefold() != ".json":
        raise ValueError("Report output must be .json")
    if any(output == src or output.is_relative_to(src.parent) for src in inputs):
        raise ValueError("Write report outside original game map directories")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)
        file.write("\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit_maps(args.maps)
        if args.report:
            write_report(report, args.report, args.maps)
            print(json.dumps({"status": "ok", "report": str(args.report),
                              "summary": report["summary"]}, indent=2))
        else:
            print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, IndexError, KeyError, struct.error, OverflowError) as err:
        print(json.dumps({"status": "error", "reason": str(err)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
