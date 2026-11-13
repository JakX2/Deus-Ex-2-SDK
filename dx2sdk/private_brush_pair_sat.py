"""Source-private convex Box pair separation via complete 3D SAT axes.

Checks two *independently validated* editor-authored clipped Boxes under
bounded, proper-rigid local-to-preview transforms. Face normals and every
nonparallel cross product of convex boundary edges are separating axes.

This is an exact-geometry-motivated, floating-point read-only preview
classification, NOT a DX2 native BSP/CSG builder, Havok/MOPP collider,
native Actor writer or retail gameplay collision certificate.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

from .private_brush_boundary import build_private_box_boundary, _vec3
from .private_brush_obj import _load_private_json

SCHEMA = "DX2SDK-source-private-convex-pair-SAT-v1"
MAX_ORIGIN_COORD = 1_000_000.0
AXIS_PARALLEL_THRESHOLD_SQ = 1e-18
CONTACT_TOLERANCE = 1e-7
IDENTITY = [[1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]]


def _dot(a, b):
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def _sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _unit(v):
    norm = math.sqrt(_dot(v, v))
    if not math.isfinite(norm) or norm*norm <= AXIS_PARALLEL_THRESHOLD_SQ:
        return None
    return tuple(x/norm for x in v)


def _rigid(raw: Any) -> dict:
    """Validate a proper (not reflected/scaled/skewed) rigid preview transform."""
    if raw is None:
        raw = {"basis": IDENTITY, "origin": [0., 0., 0.]}
    if type(raw) is not dict or set(raw) != {"basis", "origin"}:
        raise ValueError("Private preview transform needs basis and origin")
    rows = raw["basis"]
    if type(rows) is not list or len(rows) != 3:
        raise ValueError("Private preview transform requires 3x3 basis")
    basis = []
    for row in rows:
        if type(row) is not list:
            raise ValueError("Preview basis rows must be local numeric triples")
        basis.append(_vec3(row))
    origin = _vec3(raw["origin"])
    if any(abs(x) > MAX_ORIGIN_COORD for x in origin):
        raise ValueError("Private preview placement origin exceeds 1e6 metres")
    for i in range(3):
        if not math.isclose(_dot(basis[i], basis[i]), 1.0,
                            rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("Preview basis must be orthonormal, not scaled")
        for j in range(i):
            if abs(_dot(basis[i], basis[j])) > 1e-6:
                raise ValueError("Preview basis rows are not orthogonal")
    determinant = _dot(basis[0], _cross(basis[1], basis[2]))
    if abs(determinant-1.0) > 1e-6:
        raise ValueError("Preview basis must have proper right-handed rotation")
    return {"basis": [list(row) for row in basis], "origin": list(origin)}


def _rotate(basis, vector):
    return tuple(_dot(row, vector) for row in basis)


def _point(transform, local):
    rotated = _rotate(transform["basis"], local)
    return tuple(rotated[i]+transform["origin"][i] for i in range(3))


def _axis_key(axis):
    # SAT is insensitive to axis sign; normalize for repeatable comparisons.
    normal = _unit(axis)
    if normal is None:
        return None
    for component in normal:
        if abs(component) > 1e-9:
            if component < 0:
                normal = tuple(-x for x in normal)
            break
    return tuple(round(x, 9) for x in normal)


def _world_geometry(boundary, transform):
    points = [_point(transform, v) for v in boundary["vertices"]]
    if any(not all(math.isfinite(x) for x in p) for p in points):
        raise ValueError("Private world-space preview vertices are not finite")
    face_axes = [_rotate(transform["basis"], face["outward_normal"])
                 for face in boundary["faces"]]
    edge_directions = [
        _sub(points[edge["vertex_ids"][1]],
             points[edge["vertex_ids"][0]])
        for edge in boundary["edges"]
    ]
    return points, face_axes, edge_directions


def inspect_private_box_pair(
    private_a: Any, private_b: Any, *,
    transform_a: Any = None, transform_b: Any = None,
    copy_a: str | None = None, copy_b: str | None = None,
) -> dict:
    """Read-only SAT contact classification for two authored private solids.

    A strict separation proves disjointness for these two convex preview
    solids. Overlap/contact is subject to fixed numerical tolerances.
    Neither the result nor its witness axis is a native game collision hit.
    """
    first = build_private_box_boundary(private_a, copy_name=copy_a)
    second = build_private_box_boundary(private_b, copy_name=copy_b)
    frame_a, frame_b = _rigid(transform_a), _rigid(transform_b)
    a_points, a_faces, a_edges = _world_geometry(first, frame_a)
    b_points, b_faces, b_edges = _world_geometry(second, frame_b)
    axis_records = []
    seen = set()
    type_counts = Counter()
    def add_axis(vector, kind, first_index, second_index=None):
        key = _axis_key(vector)
        if key is None or key in seen:
            return
        seen.add(key)
        # Never use rounded numbers as the actual projection axis.
        normal = _unit(vector)
        if normal is None:
            return
        if _dot(normal, key) < 0:
            normal = tuple(-x for x in normal)
        axis_records.append({
            "axis": normal, "kind": kind,
            "source_index_a": first_index if kind != "face-b" else None,
            "source_index_b": second_index if kind == "edge-cross"
                else first_index if kind == "face-b" else None,
        })
        type_counts[kind] += 1
    for i, normal in enumerate(a_faces):
        add_axis(normal, "face-a", i)
    for j, normal in enumerate(b_faces):
        add_axis(normal, "face-b", j)
    for i, a_direction in enumerate(a_edges):
        for j, b_direction in enumerate(b_edges):
            add_axis(_cross(a_direction, b_direction), "edge-cross", i, j)
    if not axis_records or len(axis_records) > 1324:
        raise ValueError("Private convex pair SAT axis capacity invalid")
    separated = None
    smallest_overlap = None
    for record in axis_records:
        axis = record["axis"]
        left = [_dot(axis, p) for p in a_points]
        right = [_dot(axis, p) for p in b_points]
        a_min, a_max = min(left), max(left)
        b_min, b_max = min(right), max(right)
        gap_ab = b_min-a_max
        gap_ba = a_min-b_max
        gap = max(gap_ab, gap_ba)
        overlap = min(a_max, b_max)-max(a_min, b_min)
        if gap > CONTACT_TOLERANCE:
            if separated is None or gap > separated["projected_gap_m"]:
                separated = {
                    **record,
                    "projected_gap_m": gap,
                    "interval_a": [a_min, a_max],
                    "interval_b": [b_min, b_max],
                }
        else:
            if (smallest_overlap is None
                    or overlap < smallest_overlap["interval_overlap_m"]):
                smallest_overlap = {
                    **record,
                    "interval_overlap_m": overlap,
                    "interval_a": [a_min, a_max],
                    "interval_b": [b_min, b_max],
                }
    if separated is not None:
        result, intersects, interior = "disjoint", False, False
        witness = separated
    elif smallest_overlap is not None:
        interior = smallest_overlap["interval_overlap_m"] > CONTACT_TOLERANCE
        result = "interior-overlap" if interior else "boundary-contact"
        intersects, witness = True, smallest_overlap
    else:
        raise ValueError("Incomplete private convex SAT axis evaluation")
    return {
        "schema": SCHEMA,
        "status": "source-private-convex-pair-SAT-checked",
        "classification": result,
        "intersects_or_touches_within_tolerance": intersects,
        "has_strict_volume_overlap": interior,
        "contact_tolerance_m": CONTACT_TOLERANCE,
        "tested_unique_sat_axis_count": len(axis_records),
        "tested_sat_axis_types": dict(sorted(type_counts.items())),
        "witness_axis": list(witness["axis"]),
        "witness_kind": witness["kind"],
        "witness_private_index_a": witness["source_index_a"],
        "witness_private_index_b": witness["source_index_b"],
        "witness_interval_a_m": witness["interval_a"],
        "witness_interval_b_m": witness["interval_b"],
        "witness_axis_gap_m": witness.get("projected_gap_m"),
        "minimum_tested_interval_overlap_m": witness.get("interval_overlap_m"),
        "boundary_topology_sha256_a": first["boundary_topology_sha256"],
        "boundary_topology_sha256_b": second["boundary_topology_sha256"],
        "private_geometry_sha256_a": first["private_geometry_sha256"],
        "private_geometry_sha256_b": second["private_geometry_sha256"],
        "private_transform_sha256_a": hashlib.sha256(json.dumps(
            frame_a, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "private_transform_sha256_b": hashlib.sha256(json.dumps(
            frame_b, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "native_bsp_compilation_enabled": False,
        "native_havok_mopp_collision_enabled": False,
        "source_original_gmp_or_ibd_modified": False,
        "retail_game_runtime_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only SAT of two source-private convex Box previews")
    parser.add_argument("private_a", type=Path)
    parser.add_argument("private_b", type=Path)
    parser.add_argument("--copy-a")
    parser.add_argument("--copy-b")
    parser.add_argument("--transform-a", type=Path,
                        help="Optional private rigid transform JSON for A")
    parser.add_argument("--transform-b", type=Path,
                        help="Optional private rigid transform JSON for B")
    args = parser.parse_args(argv)
    try:
        raw_a, raw_b = _load_private_json(args.private_a), _load_private_json(
            args.private_b)
        for raw, name in ((raw_a, args.copy_a), (raw_b, args.copy_b)):
            if (name is None and type(raw) is dict
                    and raw.get("schema") == "DX2Ed-prop-draft-v1"):
                raise ValueError("Each private draft requires its exact --copy-a/b")
        def load_transform(path):
            return _load_private_json(path) if path is not None else None
        result = inspect_private_box_pair(
            raw_a, raw_b,
            transform_a=load_transform(args.transform_a),
            transform_b=load_transform(args.transform_b),
            copy_a=args.copy_a, copy_b=args.copy_b)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        print("Private convex pair SAT REFUSED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
