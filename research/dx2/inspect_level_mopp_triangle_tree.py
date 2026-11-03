#!/usr/bin/env python3
"""Read-only DX2 Level candidate Havok MOPP stream and triangle-leaf audit.

Reuses strict PR27 Level render/flat geometry cross-reference. Traverses all
conditional MOPP paths *symbolically*: this is NOT runtime collision testing,
contact generation, physics integration, or a writable MOPP compiler.
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

import inspect_level_flattened_mesh_crossref as flatcheck

SCHEMA = "DX2SDK-Level-candidate-Havok-MOPP-triangle-tree-v1"
MOPP_OFFSET_EXPANSION = 0.05
MOPP_SCALE_EXPANSION = 0.1
MOPP_SCALE_NUMERATOR = 254 * 65536
MAX_OFFSET_ERROR = 0.001
MAX_SCALE_RELATIVE_ERROR = 0.000002
MAX_MOPP_CODE_BYTES = 4_000_000
MAX_INSTRUCTION_STATES = 1_000_000
MOPP_TRAILER = bytes(12)


def trace_mopp_code(code: bytes, triangle_count: int) -> dict:
    """Enumerate all reachable leaf IDs using source-corroborated MOPP grammar.

    Branch conditions are intentionally ignored so both paths are explored.
    Operands and jump distances are big-endian, unlike Level u32 framing.
    State is (byte offset, output base); both are bounded and explicit.
    """
    if (not isinstance(code, bytes) or not 3 <= len(code) <= MAX_MOPP_CODE_BYTES
            or type(triangle_count) is not int or not 1 <= triangle_count <= flatcheck.MAX_TRIANGLES):
        raise ValueError("Invalid candidate MOPP code/triangle bounds")
    if code[0] not in (0x26, 0x27, 0x28):
        raise ValueError("Candidate MOPP code lacks expected root axis filter")
    todo = [(0, 0)]
    visited = set()
    leaves = []
    opcodes = Counter()
    max_base = 0
    while todo:
        pc, base = todo.pop()
        if (pc, base) in visited:
            continue
        if not 0 <= pc < len(code):
            raise ValueError(f"MOPP instruction pointer outside bytecode at {pc}")
        if len(visited) >= MAX_INSTRUCTION_STATES:
            raise ValueError("MOPP instruction-state count safety limit")
        visited.add((pc, base))
        op = code[pc]
        opcodes[f"0x{op:02x}"] += 1

        def operand_width(n: int) -> None:
            if pc + n > len(code):
                raise ValueError(f"Truncated MOPP opcode 0x{op:02x} at {pc}")

        def integer(at: int, size: int) -> int:
            return int.from_bytes(code[at:at+size], "big")

        def path(target: int, new_base: int = base) -> None:
            if not pc < target < len(code):
                raise ValueError(f"Invalid MOPP jump target {target} from {pc}")
            if new_base < 0 or new_base > 0xffffffff:
                raise ValueError("MOPP output base outside u32 range")
            todo.append((target, new_base))

        if 0x01 <= op <= 0x04:
            operand_width(4)
            path(pc + 4)
        elif op == 0x05:
            operand_width(2)
            path(pc + 2 + integer(pc+1, 1))
        elif op == 0x06:
            operand_width(3)
            path(pc + 3 + integer(pc+1, 2))
        elif op == 0x09:
            operand_width(2)
            path(pc + 2, base + integer(pc+1, 1))
        elif op == 0x0a:
            operand_width(3)
            path(pc + 3, base + integer(pc+1, 2))
        elif op == 0x0b:
            operand_width(5)
            path(pc + 5, integer(pc+1, 4))
        elif 0x10 <= op <= 0x1c:
            operand_width(4)
            path(pc + 4)
            path(pc + 4 + integer(pc+3, 1))
        elif 0x20 <= op <= 0x22:
            operand_width(3)
            path(pc + 3)
            path(pc + 3 + integer(pc+2, 1))
        elif 0x23 <= op <= 0x25:
            operand_width(7)
            path(pc + 7 + integer(pc+3, 2))
            path(pc + 7 + integer(pc+5, 2))
        elif 0x26 <= op <= 0x28:
            operand_width(3)
            path(pc + 3)
        elif 0x29 <= op <= 0x2b:
            operand_width(7)
            path(pc + 7)
        elif 0x30 <= op <= 0x4f:
            leaves.append(base + op - 0x30)
        elif 0x50 <= op <= 0x52:
            n = op - 0x50 + 1
            operand_width(1+n)
            leaves.append(base + integer(pc+1, n))
        else:
            raise ValueError(f"Unknown reachable MOPP opcode 0x{op:02x} at {pc}")
        max_base = max(max_base, base)
    if not leaves:
        raise ValueError("No reachable MOPP terminal triangle leaves")
    if any(type(i) is not int or i < 0 or i >= triangle_count for i in leaves):
        raise ValueError("MOPP terminal triangle ID out of flattened geometry range")
    if len(leaves) != len(set(leaves)):
        raise ValueError("Repeated terminal triangle ID in MOPP tree")
    return {
        "reachable_instruction_states": len(visited),
        "reachable_distinct_instruction_offsets": len({p for p, _ in visited}),
        "reachable_terminal_triangle_ids": sorted(leaves),
        "terminal_leaf_count": len(leaves),
        "highest_output_base": max_base,
        "reachable_opcode_histogram": dict(sorted(opcodes.items())),
        "unsupported_reachable_opcodes": 0,
        "jump_outside_bytecode": 0,
    }


def inspect_mopp_link(level: bytes, blocks: list[dict]) -> dict:
    """Check exact packed-render ↔ flat-mesh ↔ MOPP triangle consistency."""
    flat = flatcheck.inspect_level_flattened_mesh(level, blocks)
    end = flat["level_flat_index_array_end"]
    nverts = flat["render_and_flat_vertex_count"]
    ntri = flat["render_and_flat_triangle_count"]
    tail = level[end:]
    if len(tail) < 39:
        raise ValueError("Level lacks candidate MOPP envelope and 12-byte trailer")
    outer_bytes = struct.unpack_from("<I", tail, 0)[0]
    origin_scale = struct.unpack_from("<4f", tail, 4)
    code_bytes = struct.unpack_from("<I", tail, 20)[0]
    if (code_bytes < 3 or code_bytes > MAX_MOPP_CODE_BYTES or
            outer_bytes != code_bytes + 20 or
            len(tail) != code_bytes + 36 or
            tail[-12:] != MOPP_TRAILER):
        raise ValueError("Candidate MOPP envelope length/trailer mismatch")
    if (not all(math.isfinite(x) for x in origin_scale)
            or origin_scale[3] <= 0):
        raise ValueError("Candidate MOPP origin/scale invalid")

    vertices_at = flat["level_flat_vertex_array_offset"]
    indices_at = flat["level_flat_index_array_offset"]
    mins = [math.inf] * 3
    maxs = [-math.inf] * 3
    vertices = []
    for i in range(nverts):
        xyz = struct.unpack_from("<3f", level, vertices_at + i*16)
        vertices.append(xyz)
        for axis in range(3):
            mins[axis] = min(mins[axis], xyz[axis])
            maxs[axis] = max(maxs[axis], xyz[axis])
    max_offset_error = max(abs(mins[i] - MOPP_OFFSET_EXPANSION - origin_scale[i])
                           for i in range(3))
    extent = max(maxs[i]-mins[i] for i in range(3))
    if extent <= 0:
        raise ValueError("Invalid flattened-geometry bounds")
    expected_scale = MOPP_SCALE_NUMERATOR / (extent + MOPP_SCALE_EXPANSION)
    scale_relative_error = abs(origin_scale[3] - expected_scale) / expected_scale
    if max_offset_error > MAX_OFFSET_ERROR or scale_relative_error > MAX_SCALE_RELATIVE_ERROR:
        raise ValueError("MOPP spatial origin/scale does not match flattened geometry")

    traced = trace_mopp_code(tail[24:-12], ntri)
    leaf_ids = set(traced.pop("reachable_terminal_triangle_ids"))
    ids = struct.unpack_from("<" + str(ntri * 3) + "I", level, indices_at)
    if any(i >= nverts for i in ids):
        raise ValueError("Flattened geometry references vertex outside pool")
    zero_area = set()
    for tri in range(ntri):
        a, b, c = (vertices[ids[j]] for j in (3*tri,3*tri+1,3*tri+2))
        u = tuple(b[k]-a[k] for k in range(3))
        v = tuple(c[k]-a[k] for k in range(3))
        normal = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2],
                  u[0]*v[1]-u[1]*v[0])
        if sum(x*x for x in normal) == 0.0:
            zero_area.add(tri)
    missing = set(range(ntri)) - leaf_ids
    if missing != zero_area:
        raise ValueError("MOPP leaves disagree with nonzero-area triangle coverage")
    return {
        "status": "candidate_Havok_MOPP_tree_matches_every_nondegenerate_triangle",
        "render_blocks_prevalidated": flat["validated_render_blocks"],
        "flat_vertices_prevalidated": nverts,
        "flat_triangles_prevalidated": ntri,
        "mopp_outer_length_field": outer_bytes,
        "mopp_code_bytes": code_bytes,
        "mopp_code_start_in_level": end + 24,
        "mopp_code_end_in_level": end + 24 + code_bytes,
        "mopp_trailer_zero_bytes": 12,
        "observed_mopp_origin_expansion": MOPP_OFFSET_EXPANSION,
        "observed_mopp_scale_numerator": MOPP_SCALE_NUMERATOR,
        "observed_mopp_largest_extent_expansion": MOPP_SCALE_EXPANSION,
        "max_origin_component_error": max_offset_error,
        "scale_relative_error": scale_relative_error,
        "zero_area_triangle_count": len(zero_area),
        "omitted_zero_area_triangle_ids": sorted(zero_area),
        "unique_valid_mopp_triangle_leaves": len(leaf_ids),
        **traced,
        "all_nondegenerate_triangle_ids_have_exactly_one_reachable_leaf": True,
        "world_model_vertex_pool_recovered": False,
        "runtime_Havok_shape_instantiated": False,
        "writable_collision_tree_compiler": False,
    }


def audit_map(path: Path) -> dict:
    path = Path(path)
    if (path.suffix.casefold() != ".gmp" or not path.is_file() or
            path.stat().st_size > flatcheck.MAX_MAP_BYTES):
        raise ValueError("Expected existing user-owned DX2 GMP within size limit")
    project = Path(__file__).resolve().parents[2]
    exporter = project / "map_exporter"
    if str(exporter) not in sys.path:
        sys.path.insert(0, str(exporter))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg = Package(path)
    if pkg.version != 95 or pkg.licensee not in flatcheck.OBSERVED_LICENSEES:
        raise ValueError("Expected source-observed DX2 UE95 licensees 65/67/68/69")
    levels = [e for e in pkg.exports if pkg.class_name(e) == "Level" and e["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected exactly one Level export")
    level = pkg.payload(levels[0])
    result = inspect_mopp_link(level, find_bsp(pkg))
    return {"file": path.name, "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
            "licensee": pkg.licensee, **result}


def audit_maps(paths) -> dict:
    if not 1 <= len(paths) <= flatcheck.MAX_MAPS:
        raise ValueError("Supply 1..64 original user-owned DX2 GMPs")
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Duplicate original maps")
    rows = [audit_map(p) for p in resolved]
    totals = Counter()
    for row in rows:
        totals["maps"] += 1
        totals["flat_vertices"] += row["flat_vertices_prevalidated"]
        totals["triangles"] += row["flat_triangles_prevalidated"]
        totals["candidate_mopp_bytes"] += row["mopp_code_bytes"]
        totals["reachable_instruction_states"] += row["reachable_instruction_states"]
        totals["verified_collision_leaf_ids"] += row["unique_valid_mopp_triangle_leaves"]
        totals["omitted_zero_area_triangles"] += row["zero_area_triangle_count"]
    return {
        "schema": SCHEMA, "read_only": True, "native_files_written": False,
        "runtime_Havok_collision_verified": False,
        "native_collision_writer_available": False,
        "summary": dict(totals), "maps": rows,
        "limits": [
            "Havok-MOPP-compatible grammar and unique triangle ownership verified on retail serialization.",
            "Graph traversal explores all bytecode branches without testing runtime spatial queries.",
            "Only exactly zero-area triangles are allowed to lack MOPP terminal leaves.",
            "Full Havok runtime shape binding, collision material flags and a writable MOPP builder remain unverified.",
            "Compiled-world BSP Model vertex pool and native CSG compiler remain unrecovered.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path, help="New JSON report outside original game-map directories")
    args = parser.parse_args(argv)
    try:
        result = audit_maps(args.maps)
        if args.report:
            dest = args.report.resolve()
            inputs = [p.resolve() for p in args.maps]
            if (dest.suffix.casefold() != ".json" or
                    any(dest == p or dest.is_relative_to(p.parent) for p in inputs)):
                raise ValueError("Refuse report path inside original game-map directories")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("x", encoding="utf-8") as f:
                json.dump(result, f, indent=2, allow_nan=False)
                f.write("\n")
            print(json.dumps({"status": "ok", "report": str(dest),
                              "summary": result["summary"]}, indent=2))
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, IndexError, KeyError, OverflowError, struct.error) as ex:
        print(json.dumps({"status": "refused", "reason": str(ex)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
