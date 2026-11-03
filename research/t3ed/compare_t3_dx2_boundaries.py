#!/usr/bin/env python3
"""Compare a user-owned T3 GMP and DX2 GMP at validated serialization boundaries.

Read only. The shared packed Flesh *render* layout is a necessary research
clue, NOT proof that package exports, collision, PVS, Havok or scripts transfer.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys

import compare_editor_cooked as core

SCHEMA = "DX2SDK-T3-DX2-cross-licensee-render-boundary-v1"
MARKER = struct.pack("<IiI", 1, -32, 0)
MAX_FILE_BYTES = 200 * 1024 * 1024


def _snapshot(path: Path) -> dict:
    if path.suffix.casefold() != ".gmp":
        raise ValueError("Both map inputs must be .gmp")
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Missing or oversized map input")
    package, meta = core._package(path)
    render, _hashes, spans = core._flesh_bsp(package)
    if not spans:
        raise ValueError("No validated packed Flesh BSP render blocks")
    level_exports = [e for e in package.exports if package.class_name(e) == "Level" and e["size"] > 0]
    if len(level_exports) != 1:
        raise ValueError("Expected exactly one serialized Level")
    level = package.payload(level_exports[0])
    if render["level_payload_bytes"] != len(level):
        raise ValueError("Inconsistent Level byte count")
    preceding_end = 0
    gap_sizes = Counter()
    for start, end, digest in spans:
        if not (0 <= preceding_end <= start < end <= len(level)):
            raise ValueError("Overlapping/invalid block ranges")
        gap_sizes[start - preceding_end] += 1
        if level[start + 0x44:start + 0x50] != MARKER:
            raise ValueError("Render block marker missing from validated span")
        if end - start < 80:
            raise ValueError("Render block shorter than validated header")
        header = struct.unpack_from("<10I", level, start + 0x28)
        if header[7:] != (1, 0xFFFFFFE0, 0):
            raise ValueError("Unexpected render-block structural flags")
        preceding_end = end
    render_bytes = sum(end - start for start, end, _ in spans)
    first = spans[0][0]
    between = sum(spans[i + 1][0] - spans[i][1] for i in range(len(spans)-1))
    tail = len(level) - spans[-1][1]
    if first + between + render_bytes + tail != len(level):
        raise ValueError("Level-region byte partition does not add up")
    classes = Counter(package.class_name(e) for e in package.exports)
    return {
        "package": meta,
        "render": render,
        "structural_render_header": {
            "marker_hex": MARKER.hex(),
            "header_bytes": 80,
            "vertex_stride_bytes": 32,
            "unknown_header_u32_7": 1,
            "stride_field_u32_8": 0xFFFFFFE0,
            "unknown_header_u32_9": 0,
            "validated_block_count": len(spans),
            "all_validated_blocks_match": True,
        },
        "level_regions_bytes": {
            "prefix_before_first_render_block": first,
            "between_render_blocks": between,
            "validated_render_blocks": render_bytes,
            "suffix_after_last_render_block": tail,
            "opaque_total_outside_validated_blocks": first + between + tail,
        },
        "between_block_gap_histogram": dict(sorted(Counter(
            spans[i + 1][0] - spans[i][1] for i in range(len(spans)-1)
        ).items())),
        "export_classes": dict(sorted(classes.items())),
    }


def audit(t3_path: Path, dx2_path: Path) -> dict:
    t3_path, dx2_path = Path(t3_path), Path(dx2_path)
    if t3_path.resolve() == dx2_path.resolve():
        raise ValueError("T3 and DX2 inputs must be different files")
    t3 = _snapshot(t3_path)
    dx2 = _snapshot(dx2_path)
    v1, v2 = t3["package"]["unreal_package_version"], dx2["package"]["unreal_package_version"]
    if v1 != 95 or v2 != 95:
        raise ValueError("Expected two Unreal v95 packages")
    lv1, lv2 = t3["package"]["licensee_version"], dx2["package"]["licensee_version"]
    a, b = t3["export_classes"], dx2["export_classes"]
    classes_common = sorted(set(a) & set(b))
    return {
        "schema": SCHEMA, "read_only": True,
        "t3": t3, "dx2": dx2,
        "comparison": {
            "shared_ue_version_95": True,
            "same_licensee_version": lv1 == lv2,
            "licensee_versions": {"t3": lv1, "dx2": lv2},
            "validated_render_header_layout_compatible": (
                t3["structural_render_header"]["all_validated_blocks_match"]
                and dx2["structural_render_header"]["all_validated_blocks_match"]
            ),
            "shared_export_classes": classes_common,
            "t3_only_export_classes": sorted(set(a)-set(b)),
            "dx2_only_export_classes": sorted(set(b)-set(a)),
            "flesh_bsp_native_writer_interchangeable": False,
            "collision_parity_proven": False,
            "pvs_havok_ai_light_script_parity_proven": False,
        },
        "notes": [
            "Inputs are named T3/DX2 by the caller; this tool does not authenticate game provenance.",
            "The 80-byte packed render header and 32-byte vertices are validated in both inputs.",
            "Material names, geometric triangles and shared class names are NOT serialized writer compatibility.",
            "Offsets outside validated render blocks are opaque and may mix unrelated native data.",
            "The T3 and DX2 licencee revisions are different for these supplied samples.",
            "No native writer, collision decoder, .ibt cooker, level compiler or game runtime is run.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t3", required=True, type=Path, help="User-owned T3 game-ready GMP")
    parser.add_argument("--dx2", required=True, type=Path, help="User-owned Invisible War GMP")
    parser.add_argument("--report", type=Path, help="New JSON file outside input map directories")
    args = parser.parse_args(argv)
    try:
        result = audit(args.t3, args.dx2)
        if args.report:
            core._write_report(result, args.report, [args.t3, args.dx2])
            print(json.dumps({
                "status": "ok", "report": str(args.report),
                "licensees": result["comparison"]["licensee_versions"],
                "shared_render_header": result["comparison"]["validated_render_header_layout_compatible"],
                "native_writer_interchangeable": False,
            }, indent=2))
        else:
            print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, IndexError, struct.error) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
