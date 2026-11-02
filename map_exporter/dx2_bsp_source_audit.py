#!/usr/bin/env python3
"""Audit original DX2 BSP render blocks against a cached DX2Ed report.

Read-only. Requires the user's original .gmp and the scene.report.json
from DX2Ed. The game files are never modified or committed.

Usage:
    python map_exporter/dx2_bsp_source_audit.py \
       M1_Seattle_Hub_WTOterminal.gmp scene.report.json \
       --target-ue 0 -272 396 --output bsp_source_audit.json

The marker count alone is not proof of BSP completeness: native BSP/model
content not represented by the understood render-block format remains
outside the scope of this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

from dx2scene import Package, find_bsp, MARKER

SCHEMA = "DX2Ed-bsp-source-audit-v1"


def box_distance_ue(lo, hi, p):
    return math.sqrt(sum(max(lo[i] - p[i], p[i] - hi[i], 0.0) ** 2
                         for i in range(3)))


def describe_blocks(blocks, target_ue=None):
    entries = []
    for number, block in enumerate(blocks):
        section_summary = [
            {"material": s["material"], "triangles": len(s["indices"]) // 3,
             "hidden_bf": s["material"].casefold() == "bf"}
            for s in block["sections"]
        ]
        lo = [min(v[0][axis] for v in block["vertices"]) for axis in range(3)]
        hi = [max(v[0][axis] for v in block["vertices"]) for axis in range(3)]
        visible_triangles = sum(s["triangles"] for s in section_summary
                                if not s["hidden_bf"])
        entry = {
            "index": number,
            "source_level_offset": block["offset"],
            "id": block["id"],
            "source_vertex_bounds_ue": [lo, hi],
            "sections": section_summary,
            "visible_triangles": visible_triangles,
            "all_bf_hidden": visible_triangles == 0,
        }
        if target_ue is not None:
            entry["target_to_vertex_aabb_ue"] = round(
                box_distance_ue(lo, hi, target_ue), 4)
        entries.append(entry)
    return entries


def compare_bsp_data(blocks, marker_hits, source_name, source_hash, report, target_ue=None):
    if not isinstance(report, dict):
        raise ValueError("scene.report.json must be a JSON object")
    if target_ue is not None and (
        len(target_ue) != 3 or any(not math.isfinite(x) for x in target_ue)
    ):
        raise ValueError("target_ue must contain three finite numeric coordinates")
    entries = describe_blocks(blocks, target_ue)
    visible = sum(x["visible_triangles"] for x in entries)
    all_triangles = sum(sum(s["triangles"] for s in x["sections"]) for x in entries)
    hidden = all_triangles - visible
    expected_hash = report.get("source_map_sha256")
    expected_triangles = report.get("visible_bsp_triangles")
    source_match = expected_hash == source_hash
    parity = source_match and isinstance(expected_triangles, int) and visible == expected_triangles
    nearest = sorted((e for e in entries if e["visible_triangles"])
                     , key=lambda e: e.get("target_to_vertex_aabb_ue", float("inf")))[:12] if target_ue is not None else []
    return {
        "schema": SCHEMA, "read_only": True, "game_rendering_verified": False,
        "source_map": source_name, "source_sha256": source_hash,
        "report_source_hash_matches": source_match,
        "marker_hits": marker_hits, "validated_nonoverlapping_render_blocks": len(entries),
        "render_block_section_count": sum(len(e["sections"]) for e in entries),
        "visible_bsp_triangles": visible, "bf_hidden_triangles": hidden,
        "bf_only_hidden_blocks": sum(e["all_bf_hidden"] for e in entries),
        "previous_cache_report_visible_triangles": expected_triangles,
        "visible_triangles_match_matching_cache_report": parity,
        "target_ue": list(target_ue) if target_ue is not None else None,
        "nearest_source_render_blocks": nearest, "blocks": entries,
        "caveats": [
            "Marker hits and render-block counts do not prove all engine geometry is understood.",
            "The preview intentionally suppresses BF sections; BF is treated as a native no-draw material.",
            "Actor source/pivot problems, shader approximations and mesh visibility require separate checks.",
            "The proximity numbers measure AABB distance only, not a polygon-to-polygon gap.",
        ],
    }


def audit_original(map_path: Path, report_path: Path, target_ue=None):
    pkg = Package(map_path)
    if pkg.version != 95:
        raise ValueError("Expected Ion Storm Unreal package version 95")
    level = next((e for e in pkg.exports if pkg.class_name(e) == "Level" and e["size"] > 0), None)
    if not level:
        raise ValueError("GMP contains no Level export")
    markers = pkg.payload(level).count(MARKER)
    blocks = find_bsp(pkg)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return compare_bsp_data(blocks, markers, map_path.name,
                            hashlib.sha256(pkg.data).hexdigest(),
                            report, target_ue)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gmp", type=Path)
    parser.add_argument("scene_report_json", type=Path)
    parser.add_argument("--target-ue", nargs=3, type=float, metavar=("X","Y","Z"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.output and args.output.resolve() in (
            args.gmp.resolve(), args.scene_report_json.resolve()):
        parser.error("Refusing to overwrite original source or scene report")
    try:
        result = audit_original(args.gmp, args.scene_report_json, args.target_ue)
        encoded = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
            print(json.dumps({"saved": str(args.output),
                              "matching_cache": result["report_source_hash_matches"],
                              "visible_triangles_match": result["visible_triangles_match_matching_cache_report"]}))
        else:
            print(encoded, end="")
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
