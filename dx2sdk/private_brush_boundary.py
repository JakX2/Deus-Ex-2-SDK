"""Closed source-private convex boundary graph and segment/solid queries.

Builds an oriented boundary representation from independently preflighted
editor-authored clipped Box metadata. The model contains source-private
face/edge/vertex IDs only. It is NOT DX2 native World BSP, a CSG compiler,
a Havok/MOPP collision cooker, a map writer or retail runtime proof.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

from .private_brush_obj import _load_private_json
from .private_brush_preflight import (
    PLANE_TOLERANCE, inspect_private_box_convex, inspect_private_draft_copy,
)

SCHEMA = "DX2SDK-private-Box-oriented-boundary-v1"
SEGMENT_SCHEMA = "DX2SDK-private-Box-convex-segment-query-v1"
MAX_QUERY_COORD = 1_000_000.0
BOUNDARY_TOLERANCE = 1e-7
INTERSECTION_TOLERANCE = 1e-9


def _vec3(value: Any) -> tuple[float, float, float]:
    if (not isinstance(value, (list, tuple)) or len(value) != 3
            or any(type(x) not in (float, int) or not math.isfinite(x)
                   or abs(x) > MAX_QUERY_COORD for x in value)):
        raise ValueError("Expected three bounded finite local coordinates")
    return tuple(float(x) for x in value)


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _point_state(faces: list[dict], p: tuple[float, float, float]) -> str:
    signed = [_dot(f["outward_normal"], p)-f["distance"]
              for f in faces]
    largest = max(signed)
    if largest > BOUNDARY_TOLERANCE:
        return "outside"
    if largest >= -BOUNDARY_TOLERANCE:
        return "boundary"
    return "inside"


def build_private_box_boundary(raw: Any, *, copy_name: str | None = None) -> dict:
    """Create an in-memory, face/edge/vertex closed B-rep from a private Box.

    Every vertex has exactly one private index; each boundary edge must have
    exactly two oppositely oriented face incidences. Plane and volume proofs
    are independent of any original game source objects.
    """
    report = (inspect_private_box_convex(raw) if copy_name is None
              else inspect_private_draft_copy(raw, copy_name))
    rows = report["local_faces_not_native_bsp"]
    vertices: list[list[float] | None] = [None] * report["vertex_count"]
    incidences: dict[tuple[int, int], list[dict]] = defaultdict(list)
    faces = []
    seen_slots: set[tuple[str, int]] = set()
    volume = 0.0
    for face_index, face in enumerate(rows):
        ids = face["vertex_ids"]
        positions = face["vertices"]
        normal = _vec3(face["normal"])
        distance = float(face["distance"])
        slot = face["slot"]
        kind = face["kind"]
        if (kind not in ("private_box_side", "private_cut_cap")
                or type(slot) is not int or not 0 <= slot <= 8
                or (kind, slot) in seen_slots
                or not 3 <= len(ids) <= 16
                or len(ids) != len(positions)
                or len(set(ids)) != len(ids)
                or not math.isfinite(distance)
                or not math.isclose(_dot(normal, normal), 1.0,
                                    rel_tol=0.0, abs_tol=1e-4)):
            raise ValueError("Malformed or ambiguous private boundary face")
        seen_slots.add((kind, slot))
        for vertex_id, raw_point in zip(ids, positions):
            if type(vertex_id) is not int or not 0 <= vertex_id < len(vertices):
                raise ValueError("Private face references invalid vertex index")
            point = _vec3(raw_point)
            if abs(_dot(normal, point)-distance) > PLANE_TOLERANCE:
                raise ValueError("Private polygon vertex does not lie on face plane")
            old = vertices[vertex_id]
            if old is not None and math.dist(old, point) > 1e-5:
                raise ValueError("Private faces disagree on shared vertex position")
            vertices[vertex_id] = list(point)
        face_area = 0.0
        a = _vec3(positions[0])
        for j in range(1, len(positions)-1):
            b, c = _vec3(positions[j]), _vec3(positions[j+1])
            oriented_area2 = _dot(_cross(_sub(b, a), _sub(c, a)), normal)
            if oriented_area2 <= 1e-10:
                raise ValueError("Private face has inward or degenerate triangle")
            face_area += oriented_area2/2.0
            volume += _dot(a, _cross(b, c))/6.0
        for a_id, b_id in zip(ids, ids[1:] + ids[:1]):
            if a_id == b_id:
                raise ValueError("Private boundary has zero-length edge")
            incidences[tuple(sorted((a_id, b_id)))].append({
                "face_index": face_index,
                "oriented_vertex_ids": [a_id, b_id],
            })
        faces.append({
            "face_index": face_index,
            "kind": kind,
            "slot": slot,
            "outward_normal": list(normal),
            "distance": distance,
            "vertex_ids": list(ids),
            "area_m2": face_area,
        })
    if any(point is None for point in vertices):
        raise ValueError("Unreferenced private boundary vertex")
    full_vertices = [point for point in vertices if point is not None]
    for point in full_vertices:
        for face in faces:
            if (_dot(face["outward_normal"], point) - face["distance"]
                    > PLANE_TOLERANCE):
                raise ValueError("Private vertex escapes another boundary halfspace")
    edges = []
    face_neighbours: list[dict[tuple[int, int], int]] = [
        {} for _ in faces]
    for edge_id, key in enumerate(sorted(incidences)):
        uses = incidences[key]
        if (len(uses) != 2
                or uses[0]["oriented_vertex_ids"]
                    != list(reversed(uses[1]["oriented_vertex_ids"]))
                or uses[0]["face_index"] == uses[1]["face_index"]):
            raise ValueError("Nonmanifold, open or inconsistently wound private edge")
        a_face, b_face = (use["face_index"] for use in uses)
        for use, other in ((uses[0], b_face), (uses[1], a_face)):
            start, end = use["oriented_vertex_ids"]
            face_neighbours[use["face_index"]][(start, end)] = other
        edges.append({
            "edge_index": edge_id,
            "vertex_ids": list(key),
            "adjacent_face_indices": sorted((a_face, b_face)),
            "oriented_face_uses": uses,
        })
    if (len(edges) != report["edge_count"]
            or len(full_vertices)-len(edges)+len(faces) != 2
            or not math.isclose(volume, report["enclosed_private_volume_m3"],
                                rel_tol=1e-7, abs_tol=1e-8)):
        raise ValueError("Private boundary census, Euler or volume disagrees")
    for face in faces:
        ids = face["vertex_ids"]
        neighbours = face_neighbours[face["face_index"]]
        face["adjacent_face_indices_per_edge"] = [
            neighbours[(a_id, b_id)]
            for a_id, b_id in zip(ids, ids[1:] + ids[:1])]
    surface_area = sum(face["area_m2"] for face in faces)
    if surface_area <= 0 or not math.isfinite(surface_area):
        raise ValueError("Private convex boundary surface area invalid")
    geometry = {
        "vertices": full_vertices,
        "faces": faces,
        "edges": edges,
    }
    digest = hashlib.sha256(json.dumps(
        geometry, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    return {
        "schema": SCHEMA,
        "status": "source-private-convex-boundary-verified",
        "coordinate_system": "Godot-local-metres-Y-up",
        "source_private_spec_sha256": report["private_brush_spec_sha256"],
        "private_geometry_sha256": report[
            "private_geometry_sha256_quantized_1e-6m"],
        "boundary_topology_sha256": digest,
        "vertex_count": len(full_vertices),
        "face_count": len(faces),
        "edge_count": len(edges),
        "euler_characteristic": 2,
        "enclosed_volume_m3": volume,
        "surface_area_m2": surface_area,
        **geometry,
        "all_edges_two_opposite_face_uses": True,
        "native_bsp_surface_ids_known": False,
        "native_BSP_or_CSG_writer_enabled": False,
        "native_collision_generated": False,
        "source_gmp_or_ibd_modified": False,
        "retail_game_runtime_verified": False,
    }


def query_private_box_segment(
        raw: Any, start: Any, end: Any, *,
        copy_name: str | None = None) -> dict:
    """Clip a bounded source-private segment against the convex halfspaces.

    Classifies solid interior crossings, coplanar boundary travel and a
    single tangent point separately. No DX2 Havok/MOPP or original BSP query.
    """
    boundary = build_private_box_boundary(raw, copy_name=copy_name)
    faces = boundary["faces"]
    a, b = _vec3(start), _vec3(end)
    delta = _sub(b, a)
    start_state, end_state = (_point_state(faces, a), _point_state(faces, b))
    lo, hi = 0.0, 1.0
    rejected = False
    for face in faces:
        n, d = face["outward_normal"], face["distance"]
        signed_at_start = _dot(n, a)-d
        directional = _dot(n, delta)
        if abs(directional) <= 1e-12:
            if signed_at_start > BOUNDARY_TOLERANCE:
                rejected = True
                break
            continue
        intersection_t = -signed_at_start / directional
        if directional < 0:
            lo = max(lo, intersection_t)
        else:
            hi = min(hi, intersection_t)
        if lo > hi+INTERSECTION_TOLERANCE:
            rejected = True
            break
    base = {
        "schema": SEGMENT_SCHEMA,
        "boundary_topology_sha256": boundary["boundary_topology_sha256"],
        "private_geometry_sha256": boundary["private_geometry_sha256"],
        "start_classification": start_state,
        "end_classification": end_state,
        "native_collision_generated": False,
        "retail_game_runtime_verified": False,
        "source_gmp_or_ibd_modified": False,
    }
    if rejected or hi < -INTERSECTION_TOLERANCE or lo > 1+INTERSECTION_TOLERANCE:
        return {**base, "intersects": False, "contact_kind": "miss",
                "entry_t": None, "exit_t": None,
                "entry_face_indices": [], "exit_face_indices": []}
    lo, hi = max(0.0, lo), min(1.0, hi)
    if lo > hi+INTERSECTION_TOLERANCE:
        return {**base, "intersects": False, "contact_kind": "miss",
                "entry_t": None, "exit_t": None,
                "entry_face_indices": [], "exit_face_indices": []}
    if lo > hi:
        lo = hi = (lo+hi)/2.0
    p_enter = tuple(a[i]+lo*delta[i] for i in range(3))
    p_exit = tuple(a[i]+hi*delta[i] for i in range(3))
    def touching(point):
        return [
            face["face_index"] for face in faces
            if abs(_dot(face["outward_normal"], point)-face["distance"])
               <= 2*BOUNDARY_TOLERANCE
        ]
    stationary = all(value == 0.0 for value in delta)
    if stationary:
        kind = ("stationary-inside" if start_state == "inside"
                else "stationary-boundary")
    elif hi-lo <= INTERSECTION_TOLERANCE:
        kind = "tangent-point"
    else:
        centre = tuple((p_enter[i]+p_exit[i])/2 for i in range(3))
        kind = ("interior-interval" if _point_state(faces, centre) == "inside"
                else "boundary-only-interval")
    return {
        **base,
        "intersects": True,
        "contact_kind": kind,
        "crosses_strict_interior": kind in (
            "interior-interval", "stationary-inside"),
        "entry_t": lo, "exit_t": hi,
        "entry_point": list(p_enter), "exit_point": list(p_exit),
        "entry_face_indices": touching(p_enter),
        "exit_face_indices": touching(p_exit),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only source-private convex Box boundary and segment query")
    parser.add_argument("private_json", type=Path)
    parser.add_argument("--copy", dest="copy_name",
                        help="Exact private DraftProp_N selection for sidecar")
    parser.add_argument("--start", nargs=3, type=float, metavar=("X", "Y", "Z"))
    parser.add_argument("--end", nargs=3, type=float, metavar=("X", "Y", "Z"))
    args = parser.parse_args(argv)
    try:
        if (args.start is None) != (args.end is None):
            raise ValueError("Specify both --start and --end for segment query")
        raw = _load_private_json(args.private_json)
        if (args.copy_name is None and type(raw) is dict
                and raw.get("schema") == "DX2Ed-prop-draft-v1"):
            raise ValueError("Saved private drafts require --copy DraftProp_N")
        result = (build_private_box_boundary(raw, copy_name=args.copy_name)
                  if args.start is None else query_private_box_segment(
                      raw, args.start, args.end, copy_name=args.copy_name))
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print("Source-private convex boundary REFUSED: " + str(exc),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
