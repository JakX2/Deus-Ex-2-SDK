#!/usr/bin/env python3
"""Read-only comparison of two native T3Ed .unr build-stage snapshots.

This is NOT a map compiler. Input files are never modified.
Both snapshots must be from the same Unreal package version/licensee branch.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import compare_editor_cooked as core

SCHEMA = "DX2SDK-T3Ed-Flesh-BSP-stage-audit-v1"


def _profile(pkg):
    """Summarize only validated packed render blocks; opaque bytes stay opaque."""
    info, hashes, spans = core._flesh_bsp(pkg)
    blocks = core.find_bsp(pkg)
    if len(blocks) != len(spans):
        raise ValueError("Inconsistent packed render-block scan")
    detailed = []
    material_triangles = Counter()
    total_vertices = total_indices = total_bytes = 0
    for index, (block, (start, end, digest)) in enumerate(zip(blocks, spans)):
        if (block["offset"], block["end"]) != (start, end):
            raise ValueError("Render-block offsets changed between scans")
        vertices = block["vertices"]
        if not vertices:
            raise ValueError("Empty validated render block")
        positions = [v[0] for v in vertices]
        bounds = {
            "min": [min(p[axis] for p in positions) for axis in range(3)],
            "max": [max(p[axis] for p in positions) for axis in range(3)],
        }
        mats = Counter()
        indices = 0
        for section in block["sections"]:
            n = len(section["indices"])
            if n % 3:
                raise ValueError("Invalid triangle index count")
            indices += n
            mats[section["material"]] += n // 3
            material_triangles[section["material"]] += n // 3
        total_vertices += len(vertices)
        total_indices += indices
        total_bytes += end - start
        detailed.append({
            "index": index, "level_offset": start, "bytes": end - start,
            "sha256": digest, "block_id": block["id"],
            "vertices": len(vertices), "indices": indices,
            "triangles": indices // 3, "bounds_unreal_units": bounds,
            "material_triangles": dict(sorted(mats.items())),
        })
    info.update({
        "render_vertices": total_vertices,
        "render_indices": total_indices,
        "render_block_bytes": total_bytes,
        "triangles_by_material": dict(sorted(material_triangles.items())),
    })
    return info, hashes, detailed


def _match_unchanged_blocks(before, after):
    """Match whole-block bytes one-to-one, preserving duplicate multiplicity."""
    positions = defaultdict(list)
    for block in after:
        positions[block["sha256"]].append(block["index"])
    match = []
    for block in before:
        candidates = positions[block["sha256"]]
        if candidates:
            match.append({"before_index": block["index"], "after_index": candidates.pop(0),
                          "sha256": block["sha256"]})
    used_before = {item["before_index"] for item in match}
    used_after = {item["after_index"] for item in match}
    return {
        "byte_identical_block_matches": match,
        "before_only_block_indices": [b["index"] for b in before if b["index"] not in used_before],
        "after_only_block_indices": [b["index"] for b in after if b["index"] not in used_after],
        "method": "whole validated block SHA256, one-to-one with duplicate counts",
        "spatial_lineage_proven": False,
    }


def audit_stages(before_path: Path, after_path: Path) -> dict:
    before_path, after_path = Path(before_path), Path(after_path)
    if before_path.resolve() == after_path.resolve():
        raise ValueError("Snapshots must be different files")
    if before_path.suffix.lower() != ".unr" or after_path.suffix.lower() != ".unr":
        raise ValueError("Expected two .unr source-map snapshots")
    if before_path.stem.casefold() != after_path.stem.casefold():
        raise ValueError("Snapshot basenames must match")
    before, before_info = core._package(before_path)
    after, after_info = core._package(after_path)
    if before.version != after.version or before.licensee != after.licensee:
        raise ValueError("Snapshot package version/licensee mismatch")
    b_info, b_hashes, b_blocks = _profile(before)
    a_info, a_hashes, a_blocks = _profile(after)
    same = b_hashes & a_hashes
    lineage = _match_unchanged_blocks(b_blocks, a_blocks)
    level_delta = a_info["level_payload_bytes"] - b_info["level_payload_bytes"]
    render_delta = a_info["render_block_bytes"] - b_info["render_block_bytes"]
    return {
        "schema": SCHEMA, "read_only": True,
        "build_commands_observed_by_tool": False,
        "game_runtime_verified": False,
        "input_stage_labels": {
            "before": "user-designated After_Unreal_BSP",
            "after": "user-designated After_Flesh_BSP",
        },
        "before": {**before_info, "render": b_info},
        "after": {**after_info, "render": a_info},
        "deltas": {
            "file_bytes": after_info["bytes"] - before_info["bytes"],
            "level_payload_bytes": level_delta,
            "render_blocks": a_info["validated_render_blocks"] - b_info["validated_render_blocks"],
            "render_vertices": a_info["render_vertices"] - b_info["render_vertices"],
            "render_indices": a_info["render_indices"] - b_info["render_indices"],
            "render_triangles": a_info["render_triangles"] - b_info["render_triangles"],
            "validated_render_block_bytes": render_delta,
            "level_bytes_outside_validated_render_blocks": level_delta - render_delta,
        },
        "render_block_correspondence": lineage,
        "render_block_byte_matches": {
            "unchanged": sum(same.values()),
            "before_only": sum((b_hashes - same).values()),
            "after_only": sum((a_hashes - same).values()),
        },
        "before_render_blocks": b_blocks,
        "after_render_blocks": a_blocks,
        "exports": core._diff_exports(before, after),
        "limitations": [
            "Input labels describe the user's Windows build sequence, not commands observed by this tool.",
            "A before/after difference does not prove exclusive causality if other edits occurred.",
            "Unmatched blocks have no inferred one-to-one or one-to-many spatial lineage.",
            "Unknown Level bytes are not decoded as collision, PVS, Havok, AI or lighting.",
            "No native .gmp export, .ibt cooking or in-game validation is performed.",
            "T3 licensee 133 does not establish DX2 licensee 68 compatibility.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path, help="Saved .unr after Unreal BSP")
    parser.add_argument("after", type=Path, help="Saved .unr after Flesh BSP")
    parser.add_argument("--report", type=Path, help="JSON output, outside map directories")
    args = parser.parse_args(argv)
    try:
        result = audit_stages(args.before, args.after)
        if args.report:
            core._write_report(result, args.report, [args.before, args.after])
            print(json.dumps({"status": "ok", "report": str(args.report), "deltas": result["deltas"],
                              "render_block_byte_matches": result["render_block_byte_matches"]}, indent=2))
        else:
            print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, IndexError, KeyError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
