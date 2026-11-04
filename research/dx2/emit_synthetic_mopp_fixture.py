#!/usr/bin/env python3
"""Generate deliberately SYNTHETIC MOPP-compatible control-flow fixtures.

This is NOT a DX2/Havok collision compiler. Split thresholds (0x80) and
root filter operands (0x00,0xff) are fixed opaque test values. The source-
observed byte grammar, branch displacements, triangle IDs, spatial header
formula, and envelope framing are validated independently by PRs #28/#36.

Never reads, patches or outputs a retail GMP/IBD.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import inspect_level_mopp_triangle_tree as mopp
import inspect_mopp_bytecode_roundtrip as roundtrip

SCHEMA = "DX2SDK-synthetic-MOPP-control-flow-emitter-v1"
MAX_SYNTHETIC_TRIANGLES = 4096
MAX_SYNTHETIC_VERTICES = 3 * MAX_SYNTHETIC_TRIANGLES
ROOT_FILTER = b"\x28\x00\xff"       # known width/opcode, UNKNOWN runtime semantics
SPLIT_OPAQUE_THRESHOLD = 0x80       # no spatial branch test is implemented
SPATIAL_OFFSET_MARGIN = 0.05
SPATIAL_EXTENT_MARGIN = 0.1
SPATIAL_NUMERATOR = 254 * 65536


def _strict_f32(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Synthetic vertex component must be a finite number")
    if abs(value) > 1_000_000:
        raise ValueError("Synthetic vertex exceeds conservative spatial bounds")
    try:
        packed = struct.pack("<f", float(value))
    except (struct.error, OverflowError) as error:
        raise ValueError("Synthetic vertex cannot be represented as f32") from error
    result = struct.unpack("<f", packed)[0]
    if not math.isfinite(result):
        raise ValueError("Synthetic vertex f32 is not finite")
    return result


def _validate_geometry(vertices: object, triangles: object) -> tuple[list[tuple[float,float,float]], list[tuple[int,int,int]], list[int]]:
    """Canonicalize to source-like f32 and exclude exactly degenerate leaves."""
    if (not isinstance(vertices, (list, tuple))
            or not isinstance(triangles, (list, tuple))
            or not 3 <= len(vertices) <= MAX_SYNTHETIC_VERTICES
            or not 1 <= len(triangles) <= MAX_SYNTHETIC_TRIANGLES):
        raise ValueError("Synthetic mesh vertex/triangle count outside fixture limits")
    xyz = []
    for vertex in vertices:
        if not isinstance(vertex, (list, tuple)) or len(vertex) != 3:
            raise ValueError("Synthetic vertex must have exactly three components")
        xyz.append(tuple(_strict_f32(p) for p in vertex))
    ids = []
    valid = []
    for tid, face in enumerate(triangles):
        if (not isinstance(face, (list, tuple)) or len(face) != 3
                or any(type(i) is not int or not 0 <= i < len(xyz) for i in face)):
            raise ValueError("Synthetic triangle requires three valid source vertex indices")
        a, b, c = [xyz[i] for i in face]
        u = [b[k] - a[k] for k in range(3)]
        v = [c[k] - a[k] for k in range(3)]
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2],
                 u[0]*v[1]-u[1]*v[0])
        squared = sum(x*x for x in cross)
        if not math.isfinite(squared):
            raise ValueError("Synthetic triangle area exceeds numeric range")
        if squared > 0:
            valid.append(tid)
        ids.append(tuple(face))
    if not valid:
        raise ValueError("Synthetic geometry has no nonzero-area triangle for MOPP")
    return xyz, ids, valid


def _leaf(triangle_id: int) -> bytes:
    """Original-bytecode leaf encoding, selected by exact integer width."""
    if triangle_id < 32:
        return bytes([0x30 + triangle_id])
    if triangle_id <= 0xff:
        return b"\x50" + triangle_id.to_bytes(1, "big")
    if triangle_id <= 0xffff:
        return b"\x51" + triangle_id.to_bytes(2, "big")
    if triangle_id <= 0xffffff:
        return b"\x52" + triangle_id.to_bytes(3, "big")
    raise ValueError("Synthetic triangle ID exceeds the observed 24-bit leaf width")


def encode_leaf_graph(ids: object, triangle_count: int) -> tuple[bytes, dict]:
    """Encode a balanced ID graph, relocating 8/16-bit second-child offsets.

    This creates structurally decodable bytecode, NOT effective runtime
    spatial filters: the MOPP split condition operands are deliberately opaque.
    """
    if (not isinstance(ids, (tuple, list))
            or not 1 <= len(ids) <= MAX_SYNTHETIC_TRIANGLES
            or type(triangle_count) is not int
            or not 1 <= triangle_count <= mopp.flatcheck.MAX_TRIANGLES):
        raise ValueError("Invalid synthetic graph leaf/triangle count")
    if (any(type(i) is not int or not 0 <= i < triangle_count or i > 0xffffff
            for i in ids)
            or list(ids) != sorted(set(ids))):
        raise ValueError("Synthetic leaf IDs must be sorted, unique and in range")

    def branch(items: list[int]) -> bytes:
        if len(items) == 1:
            return _leaf(items[0])
        mid = len(items)//2
        left = branch(items[:mid])
        right = branch(items[mid:])
        # Source-observed 0x20 uses an 8-bit forward displacement from pc+3.
        # Source-observed 0x23 uses two 16-bit displacements from pc+7.
        if len(left) <= 0xff:
            header = bytes([0x20, SPLIT_OPAQUE_THRESHOLD, len(left)])
        elif len(left) <= 0xffff:
            header = (bytes([0x23, SPLIT_OPAQUE_THRESHOLD,
                             SPLIT_OPAQUE_THRESHOLD])
                      + b"\x00\x00" + len(left).to_bytes(2, "big"))
        else:
            raise ValueError("Synthetic branch relocation exceeds 16-bit offset")
        return header + left + right

    code = ROOT_FILTER + branch(list(ids))
    proof = roundtrip.inspect_code_roundtrip(code, triangle_count)
    if (proof["unvisited_bytes_preserved_opaque"] != 0
            or proof["reachable_instruction_bytes"] != len(code)
            or proof["reachable_triangle_leaves"] != len(ids)):
        raise ValueError("Synthesized control-flow graph lacks complete byte coverage")
    decoded_ids = mopp.trace_mopp_code(code, triangle_count)[
        "reachable_terminal_triangle_ids"]
    if decoded_ids != list(ids):
        raise ValueError("Synthesized leaves do not match intended original IDs")
    return code, proof


def build_synthetic_envelope(vertices: object, triangles: object) -> dict:
    """Build a test-only Level-tail-shaped envelope, with independently checked IDs."""
    xyz, indices, valid_ids = _validate_geometry(vertices, triangles)
    code, proof = encode_leaf_graph(valid_ids, len(indices))
    mins = [min(v[k] for v in xyz) for k in range(3)]
    maxs = [max(v[k] for v in xyz) for k in range(3)]
    extent = max(maxs[k]-mins[k] for k in range(3))
    if not math.isfinite(extent) or extent <= 0:
        raise ValueError("Synthetic spatial extent must be nonzero")
    spatial = struct.pack(
        "<4f", *(minimum-SPATIAL_OFFSET_MARGIN for minimum in mins),
        SPATIAL_NUMERATOR / (extent + SPATIAL_EXTENT_MARGIN))
    envelope = (struct.pack("<I", len(code)+20) + spatial
                + struct.pack("<I", len(code)) + code + bytes(12))
    if len(envelope) != len(code)+36:
        raise ValueError("Synthetic envelope framing failed")
    expected_code = envelope[24:-12]
    if expected_code != code:
        raise ValueError("Synthetic MOPP bytecode not preserved")
    return {
        "schema": SCHEMA, "code": code, "envelope": envelope,
        "vertices_f32": xyz, "triangles": indices,
        "nondegenerate_source_triangle_ids": valid_ids,
        "omitted_zero_area_triangle_ids": sorted(set(range(len(indices)))-set(valid_ids)),
        "report": {
            "schema": SCHEMA,
            "synthetic_only": True,
            "source_gmp_read": False,
            "source_gmp_written": False,
            "runtime_havok_compatible": False,
            "physical_materials_verified": False,
            "actual_spatial_branch_conditions_implemented": False,
            "opaque_root_filter_hex": ROOT_FILTER.hex(),
            "opaque_branch_threshold": SPLIT_OPAQUE_THRESHOLD,
            "source_like_f32_vertex_count": len(xyz),
            "source_triangle_count": len(indices),
            "nonzero_area_triangle_leaf_count": len(valid_ids),
            "skipped_zero_area_triangle_count": len(indices)-len(valid_ids),
            "spatial_formula": "min(xyz)-0.05; scale=254*65536/(max_extent+0.1)",
            "synthetic_code_bytes": len(code),
            "synthetic_envelope_bytes": len(envelope),
            "synthetic_code_sha256": hashlib.sha256(code).hexdigest(),
            "synthetic_envelope_sha256": hashlib.sha256(envelope).hexdigest(),
            "independent_reachable_instruction_count": proof[
                "distinct_decoded_instruction_offsets"],
            "independent_complete_byte_coverage": True,
            "original_source_map_patched": False,
        },
    }


def make_synthetic_level_fixture(vertices: object, triangles: object) -> tuple[bytes, list[dict], dict]:
    """Make a fake Level *export payload*, never a GMP package, for strict tests."""
    result = build_synthetic_envelope(vertices, triangles)
    xyz = result["vertices_f32"]
    indices = result["triangles"]
    nvert, ntri = len(xyz), len(indices)
    # This deliberately fake header is used by older synthetic fixtures only.
    header = (bytes([0xa5])*180
              + struct.pack("<II6I", nvert, ntri, 1, 0, 254, 0, 254, 0)
              + b"SyntheticOnly\x00")
    vertices_raw = b"".join(struct.pack("<3fI", *v, 0) for v in xyz)
    all_indices = [i for face in indices for i in face]
    indices_raw = struct.pack("<" + "I"*len(all_indices), *all_indices)
    level = header + vertices_raw + indices_raw + result["envelope"]
    # Use exact reverse of the source-observed 0.1905 DX2 render→Level scale.
    blocks = [{"vertices": [(tuple(component / 0.1905 for component in v),
                             (0.,0.,1.),(0.,0.)) for v in xyz],
               "sections": [{"material":"SyntheticOnly", "indices":all_indices}]}]
    external = roundtrip.inspect_level_envelope(level, blocks)
    if (not external["envelope_byte_identical"]
            or external["reachable_triangle_leaves"] != len(result[
                "nondegenerate_source_triangle_ids"])):
        raise ValueError("Independent original Level/MOPP validators refused fixture")
    return level, blocks, result["report"]


def _make_disconnected_triangles(count: int) -> tuple[list[tuple[float,float,float]], list[tuple[int,int,int]]]:
    """Deterministic toy triangles; no original commercial geometry involved."""
    if type(count) is not int or not 1 <= count <= MAX_SYNTHETIC_TRIANGLES:
        raise ValueError("Synthetic triangle count must be 1..4096")
    verts, faces = [], []
    for i in range(count):
        x = float(2*i)
        verts.extend([(x,0.,0.),(x+1.,0.,0.),(x,1.,0.)])
        faces.append((3*i,3*i+1,3*i+2))
    return verts, faces


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triangles", type=int, default=4,
                        help="Number of entirely synthetic disjoint triangles, 1..4096")
    parser.add_argument("--output-prefix", type=Path,
                        help="Optional new synthetic .bin and .json outside game directories")
    args = parser.parse_args(argv)
    try:
        vertices, triangles = _make_disconnected_triangles(args.triangles)
        result = build_synthetic_envelope(vertices, triangles)
        if args.output_prefix:
            prefix = args.output_prefix.resolve()
            if (not prefix.name or prefix.suffix.lower() in (".gmp", ".ibd")
                    or any(part.lower() in ("maps", "system")
                           for part in prefix.parent.parts)):
                raise ValueError("Synthetic outputs must not target retail Maps/System or GMP/IBD")
            binpath = prefix.with_name(prefix.name + ".synthetic-mopp.bin")
            jsonpath = prefix.with_name(prefix.name + ".synthetic-mopp.json")
            if binpath.exists() or jsonpath.exists():
                raise ValueError("Synthetic output exists, refusing overwrite")
            prefix.parent.mkdir(parents=True, exist_ok=True)
            with binpath.open("xb") as stream:
                stream.write(result["envelope"])
            with jsonpath.open("x", encoding="utf-8") as stream:
                json.dump(result["report"], stream, indent=2, allow_nan=False)
                stream.write("\n")
            print(json.dumps({"status":"synthetic-only", "binary":str(binpath),
                              "report":str(jsonpath), **result["report"]}))
        else:
            print(json.dumps(result["report"], indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, OverflowError, struct.error) as error:
        print(json.dumps({"status":"refused", "reason":str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
