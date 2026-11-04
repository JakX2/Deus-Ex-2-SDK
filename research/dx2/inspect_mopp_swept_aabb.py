#!/usr/bin/env python3
"""Research-only translating AABB vs original Level triangles and MOPP candidates.

Continuous 13-axis SAT for a translated, non-rotating AABB against static,
original Level-space triangles. All geometry calculations are independent of
MOPP control flow and use explicit numeric tolerances. No Havok runtime,
game-compatible shape cooking, physical materials, or original map writes.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

from inspect_mopp_point_triangle_oracle import LevelPointTriangleOracle, _point, _sub, _dot, _cross
import inspect_mopp_axis_point_candidates as spatial

SCHEMA = "DX2SDK-Level-moving-AABB-triangle-SAT-v1"
MAX_HITS = 300000
MAX_STATES = 200000


def _half_extents(xyz):
    h = _point(xyz, label="Swept AABB half extents")
    if any(v < 0 or v > 1000 for v in h):
        raise ValueError("AABB half extents must be nonnegative and bounded")
    return h


def _segment_expanded_box_intersects(lo, hi, start, direction, half, tolerance):
    """Reject a moving box against a BVH AABB expanded by its half extents."""
    t_min, t_max = 0., 1.
    for k in range(3):
        low = lo[k] - half[k] - tolerance
        high = hi[k] + half[k] + tolerance
        if direction[k] == 0.:
            if not low <= start[k] <= high:
                return False
        else:
            a = (low - start[k])/direction[k]
            b = (high - start[k])/direction[k]
            t_min = max(t_min, min(a,b))
            t_max = min(t_max, max(a,b))
            if t_min > t_max:
                return False
    return True


def _sat_interval(tri, start, end, half, tolerance):
    """Continuous SAT across 3 box axes, 1 triangle normal, 9 edge-cross axes."""
    a,b,c = tri.a,tri.b,tri.c
    edges = (_sub(b,a), _sub(c,b), _sub(a,c))
    unitbox = ((1.,0.,0.), (0.,1.,0.), (0.,0.,1.))
    axes = [*unitbox, tri.normal]
    axes.extend(_cross(e,u) for e in edges for u in unitbox)
    motion = _sub(end,start)
    start_t, end_t = 0.,1.
    valid_axes = 0
    for axis in axes:
        norm = math.hypot(*axis)
        if norm == 0.:
            continue
        if not math.isfinite(norm):
            raise ValueError("Unrepresentable swept triangle SAT axis")
        n = tuple(x/norm for x in axis)
        q = [_dot(v,n) for v in (a,b,c)]
        radius = sum(half[k]*abs(n[k]) for k in range(3))
        low = min(q)-radius-tolerance
        high = max(q)+radius+tolerance
        offset = _dot(start,n)
        speed = _dot(motion,n)
        valid_axes += 1
        if speed == 0.:
            if not low <= offset <= high:
                return None
        else:
            t0 = (low-offset)/speed
            t1 = (high-offset)/speed
            start_t = max(start_t,min(t0,t1))
            end_t = min(end_t,max(t0,t1))
            if start_t > end_t:
                return None
    if valid_axes < 4:
        raise ValueError("Triangle SAT produced too few axes")
    if not 0 <= start_t <= end_t <= 1:
        raise ValueError("Swept SAT time interval escaped finite segment")
    return start_t, end_t


@dataclass(frozen=True)
class SweptAABBHit:
    original_triangle_id: int
    t_enter: float
    t_exit: float
    initial_overlap: bool


def swept_aabb_triangle_hits(oracle, start, end, half_extents, *, tolerance=1e-7):
    """Find all translated AABB↔triangle overlaps and their normalized time ranges."""
    if not isinstance(oracle, LevelPointTriangleOracle):
        raise ValueError("Expected independent original Level source geometry")
    a = _point(start,label="Moving box center start")
    b = _point(end,label="Moving box center end")
    h = _half_extents(half_extents)
    if (type(tolerance) not in (int,float) or not math.isfinite(tolerance)
            or not 0 <= tolerance <= .01):
        raise ValueError("Invalid source-Level swept SAT tolerance")
    direction = _sub(b,a)
    if not math.isfinite(math.hypot(*direction)):
        raise ValueError("Moving box trajectory overflows numeric range")
    hits = []
    todo = [oracle.root]
    nodes = 0
    while todo:
        lo,hi,left,right,ids = oracle.nodes[todo.pop()]
        if not _segment_expanded_box_intersects(lo,hi,a,direction,h,tolerance):
            continue
        nodes += 1
        if ids:
            for tid in ids:
                tri = oracle.tris[tid]
                if not _segment_expanded_box_intersects(
                        tri.box_lo,tri.box_hi,a,direction,h,tolerance):
                    continue
                times = _sat_interval(tri,a,b,h,tolerance)
                if times is not None:
                    lo_t,hi_t = times
                    hits.append(SweptAABBHit(tid,lo_t,hi_t,lo_t==0.))
                    if len(hits)>MAX_HITS:
                        raise ValueError("Swept AABB hit safety bound exceeded")
        else:
            todo.extend((left,right))
    hits.sort(key=lambda hit:(hit.t_enter,hit.original_triangle_id))
    return {
        "schema": SCHEMA,
        "hits": hits,
        "original_triangle_hit_ids": sorted(hit.original_triangle_id for hit in hits),
        "bvh_nodes_visited": nodes,
        "half_extents_level_xyz": list(h),
        "tolerance_level_units": float(tolerance),
        "moving_box_rotation_supported": False,
        "runtime_havok_contact_verified": False,
        "game_source_files_modified": False,
    }


def swept_aabb_mopp_candidates(walker, start, end, half_extents, *,
                               diagonal_mode="conservative", tolerance_units=1.0):
    """Source MOPP *point* branch overapproximation over a moving-box footprint.

    A rescaled, quantized AABB at each endpoint bounds all intermediate
    swept points under the linear instruction hypotheses. Diagonal research
    bounds all 16 spatiotemporal box corners; unknown diagonals explore BOTH.
    It is not a Havok swept-shape implementation.
    """
    if not isinstance(walker,spatial.ConservativeMoppPointCandidates):
        raise ValueError("Expected source-validated MOPP code and Level origin")
    a = _point(start,label="Swept MOPP center start")
    b = _point(end,label="Swept MOPP center end")
    h = _half_extents(half_extents)
    if (diagonal_mode not in spatial.DIAGONAL_MODES or
            type(tolerance_units) not in (int,float) or
            not math.isfinite(tolerance_units) or not 0 <= tolerance_units <= 4):
        raise ValueError("Invalid MOPP swept AABB research options")
    scale = walker.scale/65536.
    first = tuple((a[k]-walker.origin[k])*scale for k in range(3))
    last = tuple((b[k]-walker.origin[k])*scale for k in range(3))
    half = tuple(h[k]*scale for k in range(3))
    if any(not math.isfinite(v) or abs(v)>1e15 for xyz in (first,last,half) for v in xyz):
        raise ValueError("Swept AABB quantization not representable")
    todo = [(0,0,first,last,half)]
    seen = set()
    leaves = set()
    diagonal_ambiguous = 0
    diagonal_hypothesized = 0
    code = walker.code
    margin = float(tolerance_units)
    while todo:
        pc,base,c0,c1,extent = todo.pop()
        state = (pc,base,c0,c1,extent)
        if state in seen:
            continue
        if len(seen) >= MAX_STATES:
            raise ValueError("Exceeded MOPP swept box state safety bound")
        seen.add(state)
        if not 0 <= pc < len(code):
            raise ValueError("MOPP swept box instruction outside validated bytecode")
        op = code[pc]
        def num(at,width):
            return int.from_bytes(code[at:at+width],"big")
        def route(target,new_base=None,first_=None,last_=None,extent_=None):
            bb = base if new_base is None else new_base
            f = c0 if first_ is None else first_
            l = c1 if last_ is None else last_
            e = extent if extent_ is None else extent_
            if (not pc < target < len(code) or not 0 <= bb <= 0xffffffff or
                    any(not math.isfinite(x) or abs(x)>1e15 for v in (f,l,e) for x in v)):
                raise ValueError("MOPP moving AABB branch escaped source bytecode")
            todo.append((target,bb,f,l,e))
        def axis_span(axis):
            return (min(c0[axis],c1[axis])-extent[axis],
                    max(c0[axis],c1[axis])+extent[axis])
        if 0x01 <= op <= 0x04:
            operand=code[pc+1:pc+4]
            fac=1<<op
            route(pc+4,
                  first_=tuple((c0[k]-operand[k])*fac for k in range(3)),
                  last_=tuple((c1[k]-operand[k])*fac for k in range(3)),
                  extent_=tuple(extent[k]*fac for k in range(3)))
        elif op == 0x05:
            route(pc+2+num(pc+1,1))
        elif op == 0x06:
            route(pc+3+num(pc+1,2))
        elif op == 0x09:
            route(pc+2,new_base=base+num(pc+1,1))
        elif op == 0x0a:
            route(pc+3,new_base=base+num(pc+1,2))
        elif op == 0x0b:
            route(pc+5,new_base=num(pc+1,4))
        elif 0x10 <= op <= 0x1c:
            lo,hi,offset=code[pc+1:pc+4]
            if op <= 0x12:
                lower,upper=axis_span(op-0x10)
            elif diagonal_mode=="conservative":
                route(pc+4)
                route(pc+4+offset)
                diagonal_ambiguous+=1
                continue
            else:
                values=[]
                for mid in (c0,c1):
                    for mask in range(8):
                        corner=tuple(mid[k]+(extent[k] if (mask>>k)&1 else -extent[k])
                                     for k in range(3))
                        projection=spatial._diagonal_projection(op,corner)
                        if projection is None:
                            values=[]
                            break
                        values.append(projection)
                    if not values:
                        break
                if not values:
                    route(pc+4)
                    route(pc+4+offset)
                    diagonal_ambiguous+=1
                    continue
                lower,upper=min(values),max(values)
                diagonal_hypothesized+=1
            if lower < lo+margin:
                route(pc+4)
            if upper >= hi-margin:
                route(pc+4+offset)
        elif 0x20 <= op <= 0x22:
            low,high=axis_span(op-0x20)
            threshold,delta=code[pc+1:pc+3]
            if low < threshold+margin:
                route(pc+3)
            if high >= threshold-margin:
                route(pc+3+delta)
        elif 0x23 <= op <= 0x25:
            low,high=axis_span(op-0x23)
            lo,hi=code[pc+1:pc+3]
            if low < lo+margin:
                route(pc+7+num(pc+3,2))
            if high >= hi-margin:
                route(pc+7+num(pc+5,2))
        elif 0x26 <= op <= 0x28:
            low,high=axis_span(op-0x26)
            lo,hi=code[pc+1:pc+3]
            if low < hi+margin and high >= lo-margin:
                route(pc+3)
        elif 0x29 <= op <= 0x2b:
            low,high=axis_span(op-0x29)
            lo,hi=num(pc+1,3),num(pc+4,3)
            if low*65536.<hi+margin*65536. and high*65536.>=lo-margin*65536.:
                route(pc+7)
        elif 0x30 <= op <= 0x4f:
            leaves.add(base+op-0x30)
        elif 0x50 <= op <= 0x52:
            leaves.add(base+num(pc+1,op-0x50+1))
        else:
            raise ValueError(f"Unknown MOPP swept AABB opcode 0x{op:02x}")
    if not leaves <= walker.complete_leaf_set:
        raise ValueError("Swept AABB candidate escapes source-authenticated MOPP leaves")
    return {
        "schema": "DX2SDK-MOPP-swept-AABB-overapproximated-point-branches-v1",
        "candidate_original_triangle_ids": sorted(leaves),
        "candidate_count": len(leaves),
        "source_mopp_states_checked": len(seen),
        "unknown_diagonals_explored_both": diagonal_ambiguous,
        "experimental_diagonal_projections": diagonal_hypothesized,
        "diagonal_mode": diagonal_mode,
        "full_swept_box_footprint_examined": True,
        "actual_havok_swept_shape_traversal": False,
        "shape_rotation_supported": False,
    }


def compare_swept_aabb(oracle,walker,start,end,half_extents,*,
                       diagonal_mode="conservative",tolerance_units=1.):
    truth=swept_aabb_triangle_hits(oracle,start,end,half_extents)
    broad=swept_aabb_mopp_candidates(walker,start,end,half_extents,
                                      diagonal_mode=diagonal_mode,
                                      tolerance_units=tolerance_units)
    actual=set(truth["original_triangle_hit_ids"])
    candidates=set(broad["candidate_original_triangle_ids"])
    return {"schema":"DX2SDK-original-Level-swept-AABB-all-geometric-hits-v1",
            "swept_geometric_original_triangle_ids":sorted(actual),
            "swept_mopp_candidates":sorted(candidates),
            "missed_geometrically_intersected_original_ids":sorted(actual-candidates),
            "geometric_triangle_hits":len(actual),
            "candidate_count":len(candidates),
            "extra_broadphase_candidates":len(candidates-actual),
            "all_geometric_swept_AABB_hits_retained":actual<=candidates,
            "runtime_havok_verified":False}
