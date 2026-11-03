#!/usr/bin/env python3
"""Read-only cross-check of DX2 Level flattened mesh against Flesh render blocks.

The second Level representation has scaled f32 XYZ + zero u32 per vertex,
then globally indexed u32 triangle triplets. This is NOT identified as Havok,
collision, PVS, or the compiled-world BSP Model vertex pool. No native writes.
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

SCHEMA = "DX2SDK-Level-flattened-Flesh-mesh-crossreference-v1"
SCALE = 0.1905
MAX_COMPONENT_ERROR = 0.0002
MAX_VERTICES = 300_000
MAX_TRIANGLES = 300_000
MAX_BLOCKS = 5_000
MAX_HEADER_SEARCH_BYTES = 128
MAX_MAPS = 64
MAX_MAP_BYTES = 250 * 1024 * 1024
OBSERVED_LICENSEES = frozenset((65, 67, 68, 69))


def _flatten_render_blocks(blocks: list[dict]):
    if not 1 <= len(blocks) <= MAX_BLOCKS:
        raise ValueError("Missing or excessive validated Flesh render blocks")
    coords = []
    global_indices = []
    base = 0
    for bi, block in enumerate(blocks):
        vertices = block.get("vertices")
        sections = block.get("sections")
        if not isinstance(vertices, list) or not isinstance(sections, list):
            raise ValueError(f"Block {bi} lacks vertices or sections")
        if not vertices or not sections:
            raise ValueError(f"Block {bi} has empty vertices or sections")
        for entry in vertices:
            if not isinstance(entry, (tuple, list)) or not entry:
                raise ValueError(f"Block {bi} invalid vertex shape")
            xyz = entry[0]
            if (not isinstance(xyz, (tuple, list)) or len(xyz) != 3 or
                    any(type(x) not in (float, int) or not math.isfinite(x) or
                        abs(x) > 1_000_000 for x in xyz)):
                raise ValueError(f"Block {bi} invalid XYZ coordinates")
            coords.append(tuple(xyz))
        for si, section in enumerate(sections):
            indices = section.get("indices")
            if not isinstance(indices, (tuple, list)) or len(indices) % 3:
                raise ValueError(f"Block {bi} section {si} index triples malformed")
            for idx in indices:
                if type(idx) is not int or not 0 <= idx < len(vertices):
                    raise ValueError(f"Block {bi} section {si} index out of range")
                global_indices.append(base + idx)
        base += len(vertices)
        if base > MAX_VERTICES or len(global_indices) > 3 * MAX_TRIANGLES:
            raise ValueError("Validated render corpus exceeds safe maximum")
    if len(coords) < 3 or not global_indices:
        raise ValueError("Insufficient Flesh render geometry")
    return coords, global_indices


def _find_all(haystack: bytes, needle: bytes, *, stop_at: int = 3) -> list[int]:
    if not needle:
        raise ValueError("Empty signature")
    positions = []
    offset = 0
    while len(positions) < stop_at:
        i = haystack.find(needle, offset)
        if i < 0:
            break
        positions.append(i)
        offset = i + 1
    return positions


def inspect_level_flattened_mesh(level: bytes, blocks: list[dict]) -> dict:
    """Require one full index sequence, bounded preceding counts, scaled XYZ."""
    if not isinstance(level, bytes) or len(level) < 100:
        raise ValueError("Level payload too short or not immutable bytes")
    coords, indices = _flatten_render_blocks(blocks)
    nverts = len(coords)
    ntri = len(indices) // 3
    index_blob = struct.pack("<" + str(len(indices)) + "I", *indices)
    matches = _find_all(level, index_blob)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one full flattened index array; found {len(matches)}")
    index_start = matches[0]
    vertex_start = index_start - nverts * 16
    if vertex_start < MAX_HEADER_SEARCH_BYTES or index_start + len(index_blob) > len(level):
        raise ValueError("Flattened vertex/index arrays outside bounded Level payload")
    count_blob = struct.pack("<II", nverts, ntri)
    count_matches = [p for p in _find_all(level, count_blob)
                     if vertex_start - MAX_HEADER_SEARCH_BYTES <= p <= vertex_start - 8]
    if len(count_matches) != 1:
        raise ValueError("Missing or ambiguous preceding vertex/triangle count pair")
    max_error = 0.0
    scaled_components = 0
    for i, raw in enumerate(coords):
        x, y, z, padding = struct.unpack_from("<3fI", level, vertex_start + i * 16)
        if padding != 0:
            raise ValueError(f"Flattened vertex {i} has nonzero padding word")
        for actual, original in zip((x, y, z), raw):
            if not math.isfinite(actual):
                raise ValueError(f"Flattened vertex {i} has nonfinite XYZ")
            error = abs(actual - original * SCALE)
            max_error = max(max_error, error)
            if error > MAX_COMPONENT_ERROR:
                raise ValueError(f"Flattened vertex {i} differs from expected scaled render position")
            scaled_components += 1
    if scaled_components != nverts * 3:
        raise ValueError("Incomplete scaled XYZ verification")
    return {
        "status": "exact_global_triangle_indices_and_scaled_vertex_xyz",
        "validated_render_blocks": len(blocks),
        "render_and_flat_vertex_count": nverts,
        "render_and_flat_triangle_count": ntri,
        "verified_global_u32_triangle_indices": len(indices),
        "verified_scaled_float_components": scaled_components,
        "flattened_vertex_record_bytes": 16,
        "flattened_index_width_bytes": 4,
        "flattened_vertex_fourth_u32_all_zero": True,
        "render_to_flat_xyz_scale_observed": SCALE,
        "max_abs_coordinate_component_error": max_error,
        "level_vertex_count_pair_offset": count_matches[0],
        "level_flat_vertex_array_offset": vertex_start,
        "level_flat_index_array_offset": index_start,
        "level_flat_index_array_end": index_start + len(index_blob),
        "level_remaining_bytes_after_flat_index_array": len(level) - (index_start + len(index_blob)),
        "collision_semantics_verified": False,
        "native_world_model_vertex_pool_link_verified": False,
    }


def audit_map(path: Path) -> dict:
    path = Path(path)
    if (path.suffix.casefold() != ".gmp" or not path.is_file() or
            path.stat().st_size > MAX_MAP_BYTES):
        raise ValueError("Expected existing user-owned DX2 GMP within size limit")
    root = Path(__file__).resolve().parents[2]
    exporter = root / "map_exporter"
    if str(exporter) not in sys.path:
        sys.path.insert(0, str(exporter))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg = Package(path)
    if pkg.version != 95 or pkg.licensee not in OBSERVED_LICENSEES:
        raise ValueError("Expected DX2 UE95 licensee 65/67/68/69")
    levels = [e for e in pkg.exports if pkg.class_name(e) == "Level" and e["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected one nonempty Level export")
    level = pkg.payload(levels[0])
    blocks = find_bsp(pkg)
    result = inspect_level_flattened_mesh(level, blocks)
    return {
        "file": path.name,
        "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
        "level_sha256": hashlib.sha256(level).hexdigest(),
        "licensee": pkg.licensee,
        **result,
    }


def audit_maps(paths) -> dict:
    if not 1 <= len(paths) <= MAX_MAPS:
        raise ValueError("Provide 1 to 64 original user-owned GMPs")
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Duplicate original map paths")
    rows = [audit_map(p) for p in resolved]
    totals = Counter()
    for row in rows:
        totals["maps"] += 1
        totals["render_blocks"] += row["validated_render_blocks"]
        totals["flattened_vertices"] += row["render_and_flat_vertex_count"]
        totals["flattened_triangles"] += row["render_and_flat_triangle_count"]
        totals["verified_indices"] += row["verified_global_u32_triangle_indices"]
        totals["verified_scaled_xyz_components"] += row["verified_scaled_float_components"]
    return {
        "schema": SCHEMA, "read_only": True, "native_game_files_written": False,
        "runtime_collision_verified": False,
        "native_bsp_model_vertex_pool_decoded": False,
        "summary": dict(totals), "maps": rows,
        "limitations": [
            "This second Level representation is not proven to be runtime collision or Havok.",
            "World Model compact-field-1 vertex-pool domain is not linked to these flattened vertices.",
            "XYZ agree with packed render positions times 0.1905 within corpus-checked f32 tolerance, not byte-identically.",
            "Render-block sections and global indices are checked in source order.",
            "No native level writer, geometry compiler, PVS decoder or DX2 runtime test is claimed.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path,
                        help="Write new JSON outside source game-map directories")
    args = parser.parse_args(argv)
    try:
        report = audit_maps(args.maps)
        if args.report:
            dest = args.report.resolve()
            sources = [p.resolve() for p in args.maps]
            if dest.suffix.casefold() != ".json" or any(
                    dest == src or dest.is_relative_to(src.parent) for src in sources):
                raise ValueError("JSON report must be outside all source map directories")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("x", encoding="utf-8") as f:
                json.dump(report, f, indent=2, allow_nan=False)
                f.write("\n")
            print(json.dumps({"status": "ok", "report": str(dest),
                              "summary": report["summary"]}, indent=2))
        else:
            print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, IndexError, KeyError, OverflowError, struct.error) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
