"""Read-only CSG difference of two source-private clipped convex Box previews.

A minus B is decomposed into an ordered set of non-overlapping-interior
convex shell pieces: at each B plane, emit the current remainder outside
that plane, then continue with the inside remainder. This can represent a
non-convex RESULT without falsely claiming that it is one convex Box.

All shell construction uses the independently validated private v1.00
intersection halfspace and manifold checks. It does not compile original
DX2 World BSP, create native BSP surfaces, rebuild Havok/MOPP, change
GMP/IBD data, or prove a playable mission.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

from .private_brush_boundary import build_private_box_boundary
from .private_brush_intersection import (
    _collect_planes, _combine_same_plane_sources, _extreme_vertices,
    _surface, intersect_private_boxes,
)
from .private_brush_obj import _load_private_json
from .private_brush_pair_sat import _dot, _rigid, inspect_private_box_pair

SCHEMA = "DX2SDK-source-private-convex-CSG-difference-decomposition-v1"
SPLIT_EPS = 1e-7
VOLUME_ABS_EPS = 2e-6
VOLUME_REL_EPS = 2e-6
MAX_PIECES = 14


def _make_piece(planes: list[dict], anchor: tuple[float, float, float]) -> dict:
    """Independent bounded manifold/volume reconstruction for one convex part."""
    # The plane merger adds provenance to coincident constraints. Never
    # mutate the B-plane list or another piece's provenance while doing so.
    canonical = _combine_same_plane_sources(deepcopy(planes))
    local_vertices = _extreme_vertices(canonical)
    faces, edges, triangle_count, volume = _surface(canonical, local_vertices)
    vertices = [[v[i] + anchor[i] for i in range(3)]
                for v in local_vertices]
    shell = {
        "vertices": vertices,
        "faces": faces,
        "edges": edges,
        "vertex_count": len(vertices),
        "face_count": len(faces),
        "edge_count": len(edges),
        "triangle_count": triangle_count,
        "volume_m3": volume,
        "surface_area_m2": sum(face["area_m2"] for face in faces),
        "euler_characteristic": 2,
        "all_edges_two_opposite_face_uses": True,
    }
    shell["private_shell_sha256"] = hashlib.sha256(json.dumps(
        shell, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    return {"planes": canonical, "local_vertices": local_vertices,
            "shell": shell}


def _volume_close(left: float, right: float) -> bool:
    return math.isclose(left, right, abs_tol=VOLUME_ABS_EPS,
                        rel_tol=VOLUME_REL_EPS)


def subtract_private_boxes(
    private_a: Any, private_b: Any, *,
    transform_a: Any = None, transform_b: Any = None,
    copy_a: str | None = None, copy_b: str | None = None,
) -> dict:
    """Construct a bounded, certified private convex-piece A\\B preview.

    Pieces share boundary faces but have no shared strict interior volume.
    Each piece has its own independently closed, oriented convex shell.
    No native or private on-disk geometry artifact is written.
    """
    sat = inspect_private_box_pair(
        private_a, private_b, transform_a=transform_a,
        transform_b=transform_b, copy_a=copy_a, copy_b=copy_b)
    first = build_private_box_boundary(private_a, copy_name=copy_a)
    second = build_private_box_boundary(private_b, copy_name=copy_b)
    frame_a, frame_b = _rigid(transform_a), _rigid(transform_b)
    anchor = tuple(frame_a["origin"])
    a_planes = _collect_planes(first, frame_a, anchor, "a")
    b_planes = _collect_planes(second, frame_b, anchor, "b")
    original = _make_piece(a_planes, anchor)
    a_volume = original["shell"]["volume_m3"]
    if not _volume_close(a_volume, first["enclosed_volume_m3"]):
        raise ValueError("Private source A volume changes under its rigid transform")
    intersection = intersect_private_boxes(
        private_a, private_b, transform_a=transform_a,
        transform_b=transform_b, copy_a=copy_a, copy_b=copy_b)
    removed = intersection["volume_m3"]
    if not 0 <= removed <= a_volume+VOLUME_ABS_EPS:
        raise ValueError("CSG intersection volume cannot exceed source A")
    common = {
        "schema": SCHEMA,
        "status": "closed-source-private-convex-piece-subtraction-preview",
        "coordinate_system": "Godot-preview-metres-Y-up",
        "operation": "a-minus-b",
        "sat_contact_classification": sat["classification"],
        "source_a_volume_m3": a_volume,
        "removed_intersection_volume_m3": removed,
        "source_private_geometry_sha256_a": first["private_geometry_sha256"],
        "source_private_geometry_sha256_b": second["private_geometry_sha256"],
        "source_private_transform_sha256_a": sat["private_transform_sha256_a"],
        "source_private_transform_sha256_b": sat["private_transform_sha256_b"],
        "local_calculation_anchor_m": list(anchor),
        "native_bsp_or_csg_writer_enabled": False,
        "native_havok_or_mopp_cooker_enabled": False,
        "original_gmp_or_ibd_modified": False,
        "retail_game_runtime_verified": False,
    }
    # The SAT classification guarantees no strict volume overlap for
    # disjoint and boundary-only pairs. Preserve A as a single closed piece.
    if not intersection["has_volume"]:
        shell = {**original["shell"], "piece_index": 0,
                 "emitted_at_b_face_index": None,
                 "emission": "unchanged-source-a"}
        return {
            **common, "piece_count": 1, "pieces": [shell],
            "remaining_volume_m3": a_volume,
            "volume_partition_verified": True,
            "all_pieces_individually_closed": True,
        }
    pieces = []
    remaining: dict | None = original
    for b_face in b_planes:
        if remaining is None:
            break
        normal, distance = b_face["normal"], b_face["distance"]
        signs = [_dot(normal, v)-distance
                 for v in remaining["local_vertices"]]
        low, high = min(signs), max(signs)
        if low >= -SPLIT_EPS and high <= SPLIT_EPS:
            raise ValueError("Ambiguous nearly coplanar CSG remainder")
        if high <= SPLIT_EPS:
            # This entire remainder satisfies the current B halfspace.
            continue
        if low >= -SPLIT_EPS:
            # The entire remainder lies on the OTHER side of this B plane.
            pieces.append((remaining, b_face, "unclipped-outside"))
            remaining = None
            break
        # Split strictly into two positive-volume convex parts. Both must
        # pass the independent complete closed-manifold/volume validator.
        inside_plane = deepcopy(b_face)
        inside_plane["provenance"] = [
            {**entry, "private_boolean_side": "inside-b-halfspace"}
            for entry in b_face["provenance"]
        ]
        outside_plane = {
            "normal": tuple(-x for x in normal),
            "distance": -distance,
            "provenance": [
                {**entry, "private_boolean_side": "outside-b-halfspace-cap"}
                for entry in b_face["provenance"]
            ],
        }
        outside = _make_piece(remaining["planes"]+[outside_plane], anchor)
        inside = _make_piece(remaining["planes"]+[inside_plane], anchor)
        if not _volume_close(
                remaining["shell"]["volume_m3"],
                outside["shell"]["volume_m3"]+inside["shell"]["volume_m3"]):
            raise ValueError("Private CSG partition lost or duplicated volume")
        pieces.append((outside, b_face, "split-outside"))
        if len(pieces) > MAX_PIECES:
            raise ValueError("Private subtraction exceeds bounded piece count")
        remaining = inside
    # The last inside remainder is precisely A intersect B and is removed.
    inside_volume = 0.0 if remaining is None else remaining["shell"]["volume_m3"]
    if not _volume_close(inside_volume, removed):
        raise ValueError("Private subtraction inside volume disagrees with intersection")
    emitted = []
    for i, (piece, b_face, emission) in enumerate(pieces):
        source_face = b_face["provenance"][0]
        emitted.append({
            **piece["shell"], "piece_index": i,
            "emission": emission,
            "emitted_at_b_face_index": source_face["source_private_face_index"],
        })
    total = math.fsum(piece["volume_m3"] for piece in emitted)
    if not _volume_close(total+removed, a_volume):
        raise ValueError("Private subtraction violates source A volume conservation")
    if total < 0 or total > a_volume+VOLUME_ABS_EPS:
        raise ValueError("Private subtraction volume outside allowable range")
    return {
        **common,
        "piece_count": len(emitted),
        "pieces": emitted,
        "remaining_volume_m3": total,
        "volume_partition_verified": True,
        "all_pieces_individually_closed": True,
        "inside_remainder_volume_m3": inside_volume,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Source-private Box difference into closed convex pieces, no native BSP")
    parser.add_argument("private_a", type=Path)
    parser.add_argument("private_b", type=Path)
    parser.add_argument("--copy-a")
    parser.add_argument("--copy-b")
    parser.add_argument("--transform-a", type=Path)
    parser.add_argument("--transform-b", type=Path)
    args = parser.parse_args(argv)
    try:
        left = _load_private_json(args.private_a)
        right = _load_private_json(args.private_b)
        for raw, name in ((left, args.copy_a), (right, args.copy_b)):
            if (type(raw) is dict and raw.get("schema") == "DX2Ed-prop-draft-v1"
                    and name is None):
                raise ValueError("Private draft requires exact --copy-a or --copy-b")
        result = subtract_private_boxes(
            left, right, copy_a=args.copy_a, copy_b=args.copy_b,
            transform_a=(_load_private_json(args.transform_a)
                         if args.transform_a else None),
            transform_b=(_load_private_json(args.transform_b)
                         if args.transform_b else None))
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print("Source-private convex subtraction REFUSED: " + str(exc),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
