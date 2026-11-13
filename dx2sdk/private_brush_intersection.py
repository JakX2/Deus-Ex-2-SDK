"""Bounded *private* convex intersection, not a DX2 retail BSP/CSG compiler.

The result is a newly computed in-memory convex polyhedron from two
editor-authored, independently validated clipped Boxes with proper rigid
transforms. Its faces retain ONLY private brush provenance. All source
game geometry, GMP/IBD, zones, materials and collision remain untouched.

A strict SAT disjoint/contact classification produces NO volume geometry.
For overlapping solids, the intersection is the halfspace arrangement:
each extreme vertex is a valid triple-plane intersection. The resulting
closed shell must pass directed-edge, Euler, plane, positive volume and
centroid-tetrahedron checks; ambiguous near-degenerate arrangements fail.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import sys
from typing import Any

from .private_brush_boundary import build_private_box_boundary
from .private_brush_obj import _load_private_json
from .private_brush_pair_sat import (
    _dot, _cross, _sub, _rigid, _rotate, inspect_private_box_pair,
)
from .private_brush_preflight import _triple_intersection

SCHEMA = "DX2SDK-private-convex-CSG-intersection-preview-v1"
MAX_PLANES = 28
MAX_VERTICES = 64
MAX_FACES = 28
MAX_EDGES = 100
MAX_TRIANGLES = 100
HALFSPACE_EPS = 1e-7
FACE_EPS = 2e-7
VERTEX_WELD_EPS = 5e-7
VOLUME_EPS = 1e-7
MIN_FACE_AREA = 1e-9


def _unit(v):
    length = math.sqrt(_dot(v, v))
    if not math.isfinite(length) or length < 1e-10:
        raise ValueError("Intersection face has degenerate normal")
    return tuple(x/length for x in v)


def _collect_planes(boundary, frame, anchor, label):
    result = []
    origin = _sub(frame["origin"], anchor)
    for face in boundary["faces"]:
        normal = _unit(_rotate(frame["basis"], face["outward_normal"]))
        distance = float(face["distance"]) + _dot(normal, origin)
        if not math.isfinite(distance):
            raise ValueError("Nonfinite private convex intersection plane")
        result.append({
            "normal": normal,
            "distance": distance,
            "provenance": [{
                "source_private_brush": label,
                "source_private_face_index": face["face_index"],
                "source_private_face_kind": face["kind"],
                "source_private_face_slot": face["slot"],
            }],
        })
    return result


def _combine_same_plane_sources(planes):
    """Merge same-oriented coincident planes, retaining BOTH private sources."""
    unique = []
    for plane in planes:
        for other in unique:
            if (_dot(plane["normal"], other["normal"]) > 1-1e-11
                    and abs(plane["distance"]-other["distance"]) <= 1e-9):
                other["provenance"].extend(plane["provenance"])
                break
        else:
            unique.append(plane)
    if not 4 <= len(unique) <= MAX_PLANES:
        raise ValueError("Private convex intersection plane capacity invalid")
    return unique


def _extreme_vertices(planes):
    vertices = []
    for a, b, c in combinations(planes, 3):
        p = _triple_intersection(
            (a["normal"], a["distance"]),
            (b["normal"], b["distance"]),
            (c["normal"], c["distance"]),
        )
        if p is None:
            continue
        if any(_dot(face["normal"], p)-face["distance"] > HALFSPACE_EPS
               for face in planes):
            continue
        if not any(math.dist(p, old) <= VERTEX_WELD_EPS for old in vertices):
            vertices.append(p)
            if len(vertices) > MAX_VERTICES:
                raise ValueError("Private intersection vertex capacity exceeded")
    if len(vertices) < 4:
        raise ValueError("Private intersection contains no closed 3D volume")
    # Stable order independent of the enumeration of 3-plane combinations.
    return sorted(vertices, key=lambda v: tuple(round(x, 9) for x in v))


def _surface(planes, vertices):
    faces, edge_uses = [], defaultdict(list)
    volume_by_origin = 0.0
    triangles = 0
    for plane in planes:
        normal, distance = plane["normal"], plane["distance"]
        ids = [i for i, p in enumerate(vertices)
               if abs(_dot(normal, p)-distance) <= FACE_EPS]
        if len(ids) < 3:
            continue  # a source plane may be redundant for this intersection
        if len(ids) > 32:
            raise ValueError("Oversized intersection face loop")
        centre = tuple(
            sum(vertices[i][component] for i in ids)/len(ids)
            for component in range(3)
        )
        helper = (0., 1., 0.) if abs(normal[1]) < 0.85 else (1., 0., 0.)
        u = _unit(_cross(helper, normal))
        v = _cross(normal, u)
        ids.sort(key=lambda i: math.atan2(
            _dot(_sub(vertices[i], centre), v),
            _dot(_sub(vertices[i], centre), u)))
        area = 0.0
        for j in range(1, len(ids)-1):
            a, b, c = (vertices[ids[k]] for k in (0, j, j+1))
            area2 = _dot(_cross(_sub(b, a), _sub(c, a)), normal)
            if area2 <= MIN_FACE_AREA:
                raise ValueError("Degenerate or inward private intersection triangle")
            area += area2/2.0
            volume_by_origin += _dot(a, _cross(b, c))/6.0
        if area < MIN_FACE_AREA:
            raise ValueError("Degenerate private intersection face")
        face_number = len(faces)
        triangles += len(ids)-2
        faces.append({
            "face_index": face_number,
            "outward_normal": list(normal),
            "distance_from_anchor_m": distance,
            "vertex_ids": ids,
            "area_m2": area,
            "private_face_sources": plane["provenance"],
        })
        for a, b in zip(ids, ids[1:]+ids[:1]):
            edge_uses[tuple(sorted((a, b)))].append((a, b, face_number))
    if (not 4 <= len(faces) <= MAX_FACES
            or not 4 <= triangles <= MAX_TRIANGLES
            or not 6 <= len(edge_uses) <= MAX_EDGES):
        raise ValueError("Private intersection face/triangle/edge capacity invalid")
    edges = []
    neighbours = {f["face_index"]: {} for f in faces}
    for index, key in enumerate(sorted(edge_uses)):
        entries = edge_uses[key]
        if (len(entries) != 2
                or entries[0][0] != entries[1][1]
                or entries[0][1] != entries[1][0]
                or entries[0][2] == entries[1][2]):
            raise ValueError("Open, duplicated or nonmanifold intersection boundary")
        a, b = entries
        neighbours[a[2]][(a[0], a[1])] = b[2]
        neighbours[b[2]][(b[0], b[1])] = a[2]
        edges.append({
            "edge_index": index,
            "vertex_ids": list(key),
            "adjacent_face_indices": sorted((a[2], b[2])),
        })
    if len(vertices)-len(edges)+len(faces) != 2:
        raise ValueError("Intersection boundary violates convex Euler characteristic")
    for f in faces:
        ids = f["vertex_ids"]
        f["adjacent_face_indices_per_edge"] = [
            neighbours[f["face_index"]][(a, b)]
            for a, b in zip(ids, ids[1:]+ids[:1])
        ]
    if volume_by_origin <= VOLUME_EPS or not math.isfinite(volume_by_origin):
        raise ValueError("Private convex intersection has negligible volume")
    # Cross-check the oriented volume using independent tetrahedra around
    # an interior centroid, avoiding any reliance on the world-space origin.
    centroid = tuple(
        sum(p[component] for p in vertices)/len(vertices)
        for component in range(3)
    )
    inside_volume = 0.0
    for f in faces:
        ids = f["vertex_ids"]
        for j in range(1, len(ids)-1):
            a, b, c = (_sub(vertices[ids[k]], centroid)
                       for k in (0, j, j+1))
            signed = _dot(a, _cross(b, c))/6.0
            if signed <= 0.0:
                raise ValueError("Intersection centroid tetrahedron is inward")
            inside_volume += signed
    if not math.isclose(inside_volume, volume_by_origin,
                        rel_tol=2e-7, abs_tol=1e-7):
        raise ValueError("Independent intersection volume integrals disagree")
    for p in vertices:
        if any(_dot(plane["normal"], p)-plane["distance"] > HALFSPACE_EPS
               for plane in planes):
            raise ValueError("Intersection vertex escapes source halfspace")
    return faces, edges, triangles, volume_by_origin


def intersect_private_boxes(
        private_a: Any, private_b: Any, *,
        transform_a: Any = None, transform_b: Any = None,
        copy_a: str | None = None, copy_b: str | None = None) -> dict:
    """Return ONLY a validated in-memory private convex intersection preview."""
    sat = inspect_private_box_pair(
        private_a, private_b, transform_a=transform_a,
        transform_b=transform_b, copy_a=copy_a, copy_b=copy_b)
    first = build_private_box_boundary(private_a, copy_name=copy_a)
    second = build_private_box_boundary(private_b, copy_name=copy_b)
    frame_a, frame_b = _rigid(transform_a), _rigid(transform_b)
    anchor = tuple(frame_a["origin"])
    base = {
        "schema": SCHEMA,
        "coordinate_system": "Godot-preview-metres-Y-up",
        "sat_contact_classification": sat["classification"],
        "source_private_geometry_sha256_a": first["private_geometry_sha256"],
        "source_private_geometry_sha256_b": second["private_geometry_sha256"],
        "source_private_topology_sha256_a": first["boundary_topology_sha256"],
        "source_private_topology_sha256_b": second["boundary_topology_sha256"],
        "source_private_transform_sha256_a": sat["private_transform_sha256_a"],
        "source_private_transform_sha256_b": sat["private_transform_sha256_b"],
        "native_BSP_or_CSG_writer_enabled": False,
        "native_collision_generated": False,
        "original_gmp_or_ibd_modified": False,
        "retail_game_runtime_verified": False,
    }
    if sat["classification"] != "interior-overlap":
        return {
            **base, "status": "no-3D-private-intersection-volume",
            "has_volume": False, "volume_m3": 0.0,
            "vertex_count": 0, "edge_count": 0, "face_count": 0,
            "triangle_count": 0, "vertices": [], "edges": [], "faces": [],
        }
    planes = _combine_same_plane_sources(
        _collect_planes(first, frame_a, anchor, "a")
        + _collect_planes(second, frame_b, anchor, "b"))
    vertices = _extreme_vertices(planes)
    faces, edges, triangles, volume = _surface(planes, vertices)
    if volume > min(first["enclosed_volume_m3"],
                    second["enclosed_volume_m3"])+1e-5:
        raise ValueError("Intersection exceeds either original private volume")
    result_vertices = [[x+anchor[j] for j, x in enumerate(v)] for v in vertices]
    geometry = {"vertices": result_vertices, "faces": faces, "edges": edges}
    digest = hashlib.sha256(json.dumps(
        geometry, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest()
    return {
        **base,
        "status": "closed-source-private-convex-intersection-preview",
        "has_volume": True,
        "volume_m3": volume,
        "surface_area_m2": sum(f["area_m2"] for f in faces),
        "vertex_count": len(vertices),
        "edge_count": len(edges),
        "face_count": len(faces),
        "triangle_count": triangles,
        "euler_characteristic": 2,
        "all_edges_two_opposite_face_uses": True,
        "intersection_geometry_sha256": digest,
        "local_calculation_anchor_m": list(anchor),
        **geometry,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Source-private convex Box intersection preview; NO native BSP")
    parser.add_argument("private_a", type=Path)
    parser.add_argument("private_b", type=Path)
    parser.add_argument("--copy-a")
    parser.add_argument("--copy-b")
    parser.add_argument("--transform-a", type=Path)
    parser.add_argument("--transform-b", type=Path)
    args = parser.parse_args(argv)
    try:
        left, right = _load_private_json(args.private_a), _load_private_json(
            args.private_b)
        for raw, name in ((left, args.copy_a), (right, args.copy_b)):
            if (type(raw) is dict and raw.get("schema") == "DX2Ed-prop-draft-v1"
                    and name is None):
                raise ValueError("A private draft requires exact --copy-a/b selection")
        result = intersect_private_boxes(
            left, right, copy_a=args.copy_a, copy_b=args.copy_b,
            transform_a=(_load_private_json(args.transform_a)
                         if args.transform_a else None),
            transform_b=(_load_private_json(args.transform_b)
                         if args.transform_b else None))
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print("Source-private CSG intersection REFUSED: " + str(exc),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
