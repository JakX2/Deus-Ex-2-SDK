#!/usr/bin/env python3
"""Independent original-Level finite-segment/triangle crossing oracle.

Transverse geometric crossings only. Coplanar/near-parallel segment cases
are explicitly unresolved and counted, not silently considered collision-free.
No runtime Havok calls, MOPP segment traversal, or game asset writes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from inspect_mopp_point_triangle_oracle import (
    LevelPointTriangleOracle, _point, _sub, _dot, compare_point_to_mopp,
)

SCHEMA = "DX2SDK-Level-segment-transverse-triangle-oracle-v1"
MAX_HITS = 300_000


@dataclass(frozen=True)
class SegmentCrossing:
    original_triangle_id: int
    t: float
    point: tuple[float, float, float]
    barycentric: tuple[float, float, float]


def _slab_segment_intersects(lo, hi, origin, direction, pad):
    """Slab BVH rejection for the CLOSED finite segment, not an infinite ray."""
    t_lo, t_hi = 0., 1.
    for axis in range(3):
        minv, maxv = lo[axis]-pad, hi[axis]+pad
        if direction[axis] == 0.:
            if not minv <= origin[axis] <= maxv:
                return False
        else:
            t0 = (minv-origin[axis])/direction[axis]
            t1 = (maxv-origin[axis])/direction[axis]
            t_lo = max(t_lo, min(t0,t1))
            t_hi = min(t_hi, max(t0,t1))
            if t_hi < t_lo:
                return False
    return True


def segment_crossings(oracle: LevelPointTriangleOracle, start, end, *,
                      plane_tolerance=1e-5, barycentric_tolerance=1e-8):
    """Find source Level triangle crossings, ordered by t and original ID.

    Plane-parallel/near-parallel candidates are recorded separately. A
    coplanar overlap is NOT considered a verified nonintersection.
    """
    if not isinstance(oracle, LevelPointTriangleOracle):
        raise ValueError("Expected independent original Level oracle")
    a, b = _point(start, label="Segment start"), _point(end, label="Segment end")
    if (type(plane_tolerance) not in (float,int)
            or type(barycentric_tolerance) not in (float,int)
            or not math.isfinite(plane_tolerance)
            or not math.isfinite(barycentric_tolerance)
            or not 0 <= plane_tolerance <= 0.1
            or not 0 <= barycentric_tolerance <= 0.01):
        raise ValueError("Invalid segment geometric tolerance")
    direction = _sub(b,a)
    span = math.hypot(*direction)
    if not math.isfinite(span) or span <= 1e-12:
        raise ValueError("Segment must have nonzero finite length")
    hits = []
    parallel = []
    visited = 0
    todo = [oracle.root]
    while todo:
        lo,hi,left,right,ids = oracle.nodes[todo.pop()]
        if not _slab_segment_intersects(lo,hi,a,direction,plane_tolerance):
            continue
        visited += 1
        if ids:
            for tid in ids:
                tri = oracle.tris[tid]
                if not _slab_segment_intersects(tri.box_lo,tri.box_hi,a,direction,
                                                plane_tolerance):
                    continue
                den = _dot(tri.normal,direction)
                if abs(den) <= 1e-12 * tri.normal_len * span:
                    parallel.append(tid)
                    continue
                t = _dot(tri.normal,_sub(tri.a,a))/den
                t_pad = plane_tolerance/span
                if t < -t_pad or t > 1+t_pad:
                    continue
                t = max(0.,min(1.,t))
                p = tuple(a[k]+t*direction[k] for k in range(3))
                if not oracle._contains(tri,p,plane_tolerance,barycentric_tolerance):
                    continue
                axes = tuple(k for k in range(3) if k != tri.dominant)
                u,v,w,q = (tuple(pt[k] for k in axes)
                            for pt in (tri.a,tri.b,tri.c,p))
                def orient(x,y,z):
                    return ((y[0]-x[0])*(z[1]-x[1])
                            -(y[1]-x[1])*(z[0]-x[0]))
                det = orient(u,v,w)
                if det == 0:
                    raise ValueError("Projected triangle degenerated unexpectedly")
                bary = (orient(v,w,q)/det,orient(w,u,q)/det,orient(u,v,q)/det)
                hits.append(SegmentCrossing(tid,t,p,bary))
                if len(hits)>MAX_HITS:
                    raise ValueError("Segment hit safety limit exceeded")
        else:
            todo.extend((left,right))
    hits.sort(key=lambda h:(h.t,h.original_triangle_id))
    return {
        "schema":SCHEMA,"hits":hits,
        "parallel_or_coplanar_triangle_ids":sorted(set(parallel)),
        "bvh_nodes_visited":visited,
        "segment_length_level_units":span,
        "coplanar_overlap_fully_supported":False,
        "runtime_havok_collision_verified":False,
        "game_files_modified":False,
    }


def compare_segment_crossings(oracle, walker, start, end, *,
                              diagonal_mode="conservative", tolerance_units=1.0,
                              plane_tolerance=1e-5):
    """At each independently located transverse hit, test MOPP POINT candidates.

    This does not implement MOPP line-segment or ray traversal. It explicitly
    checks ALL triangle geometry hits at each calculated segment intersection.
    """
    scan = segment_crossings(oracle,start,end,plane_tolerance=plane_tolerance)
    checks = []
    missing = set()
    for hit in scan["hits"]:
        result = compare_point_to_mopp(
            oracle,walker,hit.point,
            diagonal_mode=diagonal_mode,tolerance_units=tolerance_units)
        if hit.original_triangle_id not in result[
                "geometric_hit_original_triangle_ids"]:
            raise ValueError("Geometry point oracle disagrees with transverse hit")
        missing.update(result[
            "geometrically_intersecting_triangles_missing_from_mopp"])
        checks.append({
            "seed_triangle_id":hit.original_triangle_id,
            "t":hit.t,
            "geometric_hits":result["geometric_hit_count"],
            "mopp_candidates":result["candidate_count"],
            "missing_triangle_ids":result[
                "geometrically_intersecting_triangles_missing_from_mopp"],
        })
    return {
        "schema":SCHEMA,
        "transverse_crossings":len(scan["hits"]),
        "intersection_point_mopp_comparisons":len(checks),
        "intersection_checks":checks,
        "missing_geometric_ids":sorted(missing),
        "all_transverse_geometric_hits_retained":not missing,
        "parallel_or_coplanar_triangle_count":len(scan[
            "parallel_or_coplanar_triangle_ids"]),
        "mopp_full_segment_traversal_performed":False,
        "diagonal_mode":diagonal_mode,
        "runtime_havok_contact_verified":False,
    }
