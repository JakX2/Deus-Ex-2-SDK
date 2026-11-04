#!/usr/bin/env python3
"""Research-only finite-segment MOPP candidate superset + coplanar geometry.

Interval traversal applies each source-observed branch condition to the full
continuous segment (using both endpoint coordinate states), instead of only
sampling its endpoints. Diagonal semantics remain hypotheses; default uses
BOTH branches. A full Havok shape/ray traversal is NOT implemented.

Coplanar overlap is independently derived from original Level triangles
using barycentric segment clipping; no MOPP code is used for geometry truth.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct

import inspect_mopp_axis_point_candidates as spatial
from inspect_mopp_point_triangle_oracle import (
    LevelPointTriangleOracle, _point, _sub, _dot,
)
from inspect_mopp_segment_geometry_oracle import (
    segment_crossings, _slab_segment_intersects,
)

SCHEMA = "DX2SDK-Level-segment-interval-MOPP-candidates-v1"
MAX_QUERY_STATES = 200_000
MAX_HITS = 300_000


def _orient(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


@dataclass(frozen=True)
class CoplanarOverlap:
    original_triangle_id: int
    t_enter: float
    t_exit: float
    entry_xyz: tuple[float, float, float]
    exit_xyz: tuple[float, float, float]


def coplanar_segment_overlaps(oracle: LevelPointTriangleOracle, start, end, *,
                              plane_tolerance=1e-5, barycentric_tolerance=1e-8):
    """Find complete same-plane segment spans within original source triangles.

    Includes an overlap touching only a vertex (t_enter == t_exit). This is
    a geometric tolerance model, not Havok's collision/contact threshold.
    Near-parallel segments with endpoints outside the plane tolerance remain
    unresolved here and must be handled by the transverse oracle separately.
    """
    if not isinstance(oracle, LevelPointTriangleOracle):
        raise ValueError("Expected independent original Level geometry oracle")
    a = _point(start, label="Coplanar segment start")
    b = _point(end, label="Coplanar segment end")
    if (type(plane_tolerance) not in (int, float)
            or type(barycentric_tolerance) not in (int, float)
            or not math.isfinite(plane_tolerance)
            or not math.isfinite(barycentric_tolerance)
            or not 0 <= plane_tolerance <= .1
            or not 0 <= barycentric_tolerance <= .01):
        raise ValueError("Invalid coplanar geometric tolerance")
    direction = _sub(b, a)
    if not math.isfinite(math.hypot(*direction)) or math.hypot(*direction) <= 1e-12:
        raise ValueError("Coplanar segment must be finite and nonzero")

    results = []
    pending = [oracle.root]
    while pending:
        lo, hi, left, right, tri_ids = oracle.nodes[pending.pop()]
        if not _slab_segment_intersects(lo, hi, a, direction, plane_tolerance):
            continue
        if not tri_ids:
            pending.extend((left, right))
            continue
        for tid in tri_ids:
            tri = oracle.tris[tid]
            if not _slab_segment_intersects(tri.box_lo, tri.box_hi,
                                           a, direction, plane_tolerance):
                continue
            signed_a = _dot(tri.normal, _sub(a, tri.a)) / tri.normal_len
            signed_b = _dot(tri.normal, _sub(b, tri.a)) / tri.normal_len
            if abs(signed_a) > plane_tolerance or abs(signed_b) > plane_tolerance:
                continue
            axes = tuple(k for k in range(3) if k != tri.dominant)
            p, q, r, a2, b2 = (
                tuple(pt[k] for k in axes)
                for pt in (tri.a, tri.b, tri.c, a, b)
            )
            denominator = _orient(p, q, r)
            if denominator == 0.:
                raise ValueError("Source triangle collapsed after 2D projection")
            weights_a = (
                _orient(q, r, a2) / denominator,
                _orient(r, p, a2) / denominator,
                _orient(p, q, a2) / denominator,
            )
            weights_b = (
                _orient(q, r, b2) / denominator,
                _orient(r, p, b2) / denominator,
                _orient(p, q, b2) / denominator,
            )
            # Clip barycentric coordinate functions wi(t)>= -eps on [0,1].
            enter, exit_ = 0., 1.
            valid = True
            for w0, w1 in zip(weights_a, weights_b):
                slope = w1 - w0
                if slope == 0.:
                    if w0 < -barycentric_tolerance:
                        valid = False
                        break
                else:
                    crossing = (-barycentric_tolerance - w0) / slope
                    if slope > 0.:
                        enter = max(enter, crossing)
                    else:
                        exit_ = min(exit_, crossing)
                if enter > exit_ + 1e-12:
                    valid = False
                    break
            if not valid or exit_ < 0. or enter > 1.:
                continue
            enter, exit_ = max(0., enter), min(1., exit_)
            if enter > exit_:
                if enter - exit_ > 1e-12:
                    continue
                enter = exit_ = (enter + exit_) / 2
            xyz0 = tuple(a[k] + enter * direction[k] for k in range(3))
            xyz1 = tuple(a[k] + exit_ * direction[k] for k in range(3))
            results.append(CoplanarOverlap(tid, enter, exit_, xyz0, xyz1))
            if len(results) > MAX_HITS:
                raise ValueError("Coplanar overlap count exceeds safety limit")
    return sorted(results, key=lambda result:
                  (result.t_enter, result.t_exit, result.original_triangle_id))


def segment_candidate_triangle_ids(walker, start, end, *,
                                   diagonal_mode="conservative",
                                   tolerance_units=1.0):
    """Overapproximate all MOPP point routes on a finite continuous segment.

    Every branch is taken if ANY point of the segment could pass its test,
    using endpoint extrema of each linear rescaled coordinate or projection.
    We deliberately do not restrict endpoints to previously selected subranges:
    this can return extra candidates but avoids a false-negative caused by
    pruning too aggressively at branch boundaries.
    """
    if not isinstance(walker, spatial.ConservativeMoppPointCandidates):
        raise ValueError("Expected fully source-validated MOPP point interpreter")
    a = _point(start, label="MOPP segment start")
    b = _point(end, label="MOPP segment end")
    if a == b or math.hypot(*_sub(b, a)) <= 1e-12:
        raise ValueError("MOPP segment must have nonzero length")
    if (diagonal_mode not in spatial.DIAGONAL_MODES
            or type(tolerance_units) not in (int, float)
            or not math.isfinite(tolerance_units)
            or not 0 <= tolerance_units <= 4):
        raise ValueError("Invalid experimental MOPP segment query options")
    margin = float(tolerance_units)
    ends = tuple(tuple((p[k] - walker.origin[k]) * walker.scale / 65536.
                       for k in range(3)) for p in (a, b))
    if any(not math.isfinite(x) or abs(x) > 1e15 for p in ends for x in p):
        raise ValueError("Unrepresentable quantized finite segment")
    code = walker.code
    pending = [(0, 0, ends[0], ends[1])]
    visited = set()
    candidates = set()
    diagonal_guesses = unknown_diagonals = 0
    while pending:
        pc, base, first, last = pending.pop()
        state = (pc, base, first, last)
        if state in visited:
            continue
        if len(visited) >= MAX_QUERY_STATES:
            raise ValueError("MOPP segment query state cap exceeded")
        visited.add(state)
        if not 0 <= pc < len(code):
            raise ValueError("MOPP segment instruction pointer out of bounds")
        op = code[pc]

        def num(at, width):
            return int.from_bytes(code[at:at+width], "big")

        def route(target, next_base=None, coord_a=None, coord_b=None):
            if next_base is None:
                next_base = base
            if coord_a is None:
                coord_a = first
            if coord_b is None:
                coord_b = last
            if (not pc < target < len(code) or not 0 <= next_base <= 0xffffffff
                    or any(not math.isfinite(x) or abs(x) > 1e15
                           for p in (coord_a, coord_b) for x in p)):
                raise ValueError("MOPP segment branch escaped validated code")
            pending.append((target, next_base, coord_a, coord_b))

        def span(axis):
            return min(first[axis], last[axis]), max(first[axis], last[axis])

        if 0x01 <= op <= 0x04:
            vals = code[pc+1:pc+4]
            power = 1 << op
            new_a = tuple((first[k]-vals[k])*power for k in range(3))
            new_b = tuple((last[k]-vals[k])*power for k in range(3))
            route(pc+4, coord_a=new_a, coord_b=new_b)
        elif op == 0x05:
            route(pc+2+num(pc+1,1))
        elif op == 0x06:
            route(pc+3+num(pc+1,2))
        elif op == 0x09:
            route(pc+2, next_base=base+num(pc+1,1))
        elif op == 0x0a:
            route(pc+3, next_base=base+num(pc+1,2))
        elif op == 0x0b:
            route(pc+5, next_base=num(pc+1,4))
        elif 0x10 <= op <= 0x1c:
            lo, hi, delta = code[pc+1:pc+4]
            if op <= 0x12:
                lower, upper = span(op-0x10)
            else:
                projection = getattr(spatial, "_diagonal_projection", None)
                v0 = (projection(op,first) if diagonal_mode == "derived_diagonals"
                      and projection is not None else None)
                v1 = (projection(op,last) if diagonal_mode == "derived_diagonals"
                      and projection is not None else None)
                if v0 is None or v1 is None:
                    route(pc+4)
                    route(pc+4+delta)
                    unknown_diagonals += 1
                    continue
                lower, upper = min(v0, v1), max(v0, v1)
                diagonal_guesses += 1
            if lower < lo+margin:
                route(pc+4)
            if upper >= hi-margin:
                route(pc+4+delta)
        elif 0x20 <= op <= 0x22:
            threshold, delta = code[pc+1:pc+3]
            lower,upper = span(op-0x20)
            if lower < threshold+margin:
                route(pc+3)
            if upper >= threshold-margin:
                route(pc+3+delta)
        elif 0x23 <= op <= 0x25:
            lo,hi=code[pc+1:pc+3]
            lower,upper=span(op-0x23)
            if lower < lo+margin:
                route(pc+7+num(pc+3,2))
            if upper >= hi-margin:
                route(pc+7+num(pc+5,2))
        elif 0x26 <= op <= 0x28:
            lo,hi=code[pc+1:pc+3]
            lower,upper=span(op-0x26)
            if lower < hi+margin and upper >= lo-margin:
                route(pc+3)
        elif 0x29 <= op <= 0x2b:
            lo,hi=num(pc+1,3),num(pc+4,3)
            lower,upper=span(op-0x29)
            if (lower*65536. < hi+margin*65536. and
                    upper*65536. >= lo-margin*65536.):
                route(pc+7)
        elif 0x30 <= op <= 0x4f:
            candidates.add(base+op-0x30)
        elif 0x50 <= op <= 0x52:
            candidates.add(base+num(pc+1,op-0x50+1))
        else:
            raise ValueError(f"Unknown MOPP instruction 0x{op:02x}")
    if not candidates <= walker.complete_leaf_set:
        raise ValueError("Generated segment candidate escaped original MOPP leaves")
    return {
        "schema": SCHEMA,
        "candidate_original_triangle_ids": sorted(candidates),
        "candidate_count": len(candidates),
        "reachable_segment_query_states": len(visited),
        "unknown_diagonal_branches_explored_both": unknown_diagonals,
        "experimental_diagonal_projections_used": diagonal_guesses,
        "diagonal_mode": diagonal_mode,
        "tolerance_quantization_units": margin,
        "entire_finite_segment_interval_considered": True,
        "mopp_havok_runtime_segment_query": False,
        "runtime_collision_contacts_verified": False,
    }


def verify_segment_against_geometry(oracle, walker, start, end, *,
                                    diagonal_mode="conservative",
                                    tolerance_units=1.):
    """Compare independent transverse and coplanar geometry hits to MOPP intervals."""
    transverse = segment_crossings(oracle,start,end)
    coplanar = coplanar_segment_overlaps(oracle,start,end)
    actual = {hit.original_triangle_id for hit in transverse["hits"]}
    actual.update(hit.original_triangle_id for hit in coplanar)
    for hit in transverse["hits"]:
        actual.update(oracle.containing_triangle_ids(hit.point))
    for hit in coplanar:
        mid = tuple((x+y)*.5 for x,y in zip(hit.entry_xyz,hit.exit_xyz))
        actual.update(oracle.containing_triangle_ids(mid))
    answer=segment_candidate_triangle_ids(
        walker,start,end,diagonal_mode=diagonal_mode,
        tolerance_units=tolerance_units)
    missing=sorted(actual-set(answer["candidate_original_triangle_ids"]))
    return {
        "schema":SCHEMA,
        "transverse_crossing_events":len(transverse["hits"]),
        "coplanar_overlap_events":len(coplanar),
        "unresolved_parallel_triangle_candidates":len(transverse[
            "parallel_or_coplanar_triangle_ids"]),
        "geometric_triangle_ids_intersecting_segment":sorted(actual),
        "candidate_original_triangle_ids":answer["candidate_original_triangle_ids"],
        "missing_geometric_original_triangle_ids":missing,
        "all_classified_geometric_hits_retained":not missing,
        "runtime_havok_segment_query":False,
        "near_parallel_offplane_behavior_fully_proven":False,
    }
