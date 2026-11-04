#!/usr/bin/env python3
"""Research: fixed-axis translating capsule against original DX2 Level triangles.

Independent geometry uses the Minkowski sum of the swept axis segment patch
and a sphere. Source MOPP candidate generation separately reuses a fully
enclosing swept AABB. Not Havok capsule/raycast behavior; never writes GMP.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from inspect_mopp_point_triangle_oracle import LevelPointTriangleOracle, _point
from inspect_mopp_swept_aabb import (_segment_expanded_box_intersects,
                                    swept_aabb_mopp_candidates)

SCHEMA = "DX2SDK-source-Level-translating-capsule-triangle-distance-v1"
MAX_HITS = 300000


def _sub(a, b): return tuple(a[k] - b[k] for k in range(3))
def _add(a, b): return tuple(a[k] + b[k] for k in range(3))
def _mul(a, s): return tuple(x*s for x in a)
def _dot(a, b): return sum(a[k]*b[k] for k in range(3))
def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])
def _sq(a): return _dot(a, a)
def _clamp(x, a=0., b=1.): return max(a, min(b, x))


def _point_triangle_distance_sq(p, a, b, c):
    """Independent closest point on triangle, including edge and vertex zones."""
    ab=_sub(b,a);ac=_sub(c,a);ap=_sub(p,a)
    d1=_dot(ab,ap);d2=_dot(ac,ap)
    if d1<=0 and d2<=0: return _sq(ap)
    bp=_sub(p,b);d3=_dot(ab,bp);d4=_dot(ac,bp)
    if d3>=0 and d4<=d3: return _sq(bp)
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0:
        v=d1/(d1-d3)
        return _sq(_sub(p,_add(a,_mul(ab,v))))
    cp=_sub(p,c);d5=_dot(ab,cp);d6=_dot(ac,cp)
    if d6>=0 and d5<=d6: return _sq(cp)
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0:
        w=d2/(d2-d6)
        return _sq(_sub(p,_add(a,_mul(ac,w))))
    va=d3*d6-d5*d4
    if va<=0 and (d4-d3)>=0 and (d5-d6)>=0:
        w=(d4-d3)/((d4-d3)+(d5-d6))
        return _sq(_sub(p,_add(b,_mul(_sub(c,b),w))))
    denom=va+vb+vc
    if denom<=0: raise ValueError("Source triangle has degenerate closest-point denominator")
    v=vb/denom;w=vc/denom
    return _sq(_sub(p,_add(a,_add(_mul(ab,v),_mul(ac,w)))))


def _segment_segment_distance_sq(a,b,c,d):
    """Distance between two closed 3D segments, including degenerate segments."""
    u=_sub(b,a);v=_sub(d,c);w=_sub(a,c)
    aa=_sq(u);ee=_sq(v);ff=_dot(v,w)
    if aa<=1e-30 and ee<=1e-30: return _sq(w)
    if aa<=1e-30:
        s=0.;t=_clamp(ff/ee)
    else:
        cc=_dot(u,w)
        if ee<=1e-30:
            t=0.;s=_clamp(-cc/aa)
        else:
            bb=_dot(u,v);den=aa*ee-bb*bb
            s=_clamp((bb*ff-cc*ee)/den) if den>1e-30 else 0.
            t=(bb*s+ff)/ee
            if t<0:
                t=0.;s=_clamp(-cc/aa)
            elif t>1:
                t=1.;s=_clamp((bb-cc)/aa)
    return _sq(_sub(_add(a,_mul(u,s)),_add(c,_mul(v,t))))


def _segment_triangle_distance_sq(p,q,tri):
    """Closed segment vs source triangle: face crossing, endpoints, and all edges."""
    a,b,c=tri
    n=_cross(_sub(b,a),_sub(c,a));length=math.sqrt(_sq(n))
    if length==0: raise ValueError("Degenerate triangle in segment distance")
    motion=_sub(q,p);den=_dot(n,motion)
    if abs(den)>1e-14*length*math.sqrt(_sq(motion)):
        t=_dot(n,_sub(a,p))/den
        if 0<=t<=1:
            x=_add(p,_mul(motion,t))
            u=_sub(b,a);v=_sub(c,a);z=_sub(x,a)
            d00=_dot(u,u);d01=_dot(u,v);d11=_dot(v,v)
            d20=_dot(z,u);d21=_dot(z,v);det=d00*d11-d01*d01
            if det<=0: raise ValueError("Degenerate source triangle geometry")
            wb=(d11*d20-d01*d21)/det;wc=(d00*d21-d01*d20)/det
            if min(wb,wc,1-wb-wc)>=-1e-12:return 0.
    best=min(_point_triangle_distance_sq(p,a,b,c),
             _point_triangle_distance_sq(q,a,b,c))
    for x,y in ((a,b),(b,c),(c,a)):
        best=min(best,_segment_segment_distance_sq(p,q,x,y))
    return max(0.,best)


def _triangle_triangle_distance_sq(one,two):
    a,b,c=one;p,q,r=two
    best=float("inf")
    for x,y in ((a,b),(b,c),(c,a)):
        best=min(best,_segment_triangle_distance_sq(x,y,two))
        if best==0:return 0.
    for x,y in ((p,q),(q,r),(r,p)):
        best=min(best,_segment_triangle_distance_sq(x,y,one))
        if best==0:return 0.
    return best


def _shape(radius,axis,axis_half_length):
    if (type(radius) not in (float,int) or not math.isfinite(radius)
            or not 0<=radius<=1000):
        raise ValueError("Capsule radius must be finite and nonnegative")
    if (type(axis_half_length) not in (int,float) or
            not math.isfinite(axis_half_length) or
            not 0<=axis_half_length<=1000):
        raise ValueError("Capsule half-axis length must be finite and nonnegative")
    axis=_point(axis,label="Fixed capsule centerline axis")
    length=math.sqrt(_sq(axis))
    if not 1e-10<=length<=1e6:
        raise ValueError("Capsule axis must be a finite nonzero direction")
    return float(radius),tuple(x/length for x in axis),float(axis_half_length)


@dataclass(frozen=True)
class SweptCapsuleHit:
    original_triangle_id:int
    axis_patch_distance:float
    capsule_radius:float


def swept_capsule_triangle_hits(oracle,start,end,radius,axis=(0.,0.,1.),
                                axis_half_length=.5,*,tolerance=1e-7):
    """Classify any-time overlap, not time of impact nor collision response."""
    if not isinstance(oracle,LevelPointTriangleOracle):
        raise ValueError("Expected independent original Level source triangle BVH")
    start=_point(start,label="Capsule start");end=_point(end,label="Capsule end")
    r,unit,half=_shape(radius,axis,axis_half_length)
    if (type(tolerance) not in (int,float) or not math.isfinite(tolerance)
            or not 0<=tolerance<=.01):
        raise ValueError("Invalid capsule geometry tolerance")
    scale=_mul(unit,half)
    a=_sub(start,scale);b=_add(start,scale)
    c=_add(end,scale);d=_sub(end,scale)
    corners=(a,b,c,d)
    motion=_sub(end,start);axis_segment=_sub(b,a)
    patch_normal=_cross(axis_segment,motion)
    collapsed=_sq(patch_normal)<=1e-24*max(1.,_sq(axis_segment)*_sq(motion))
    if collapsed:
        pair=max(((i,j) for i in range(4) for j in range(i+1,4)),
                 key=lambda ij:_sq(_sub(corners[ij[0]],corners[ij[1]])))
        patch_segment=(corners[pair[0]],corners[pair[1]])
        patches=()
    else:
        patches=((a,b,c),(a,c,d))
    extent=tuple(abs(unit[k])*half+r for k in range(3))
    pending=[oracle.root];hits=[]
    distance_threshold=(r+float(tolerance))**2
    while pending:
        lo,hi,left,right,ids=oracle.nodes[pending.pop()]
        if not _segment_expanded_box_intersects(lo,hi,start,motion,extent,tolerance):
            continue
        if not ids:
            pending.extend((left,right));continue
        for tid in ids:
            tri=oracle.tris[tid]
            if not _segment_expanded_box_intersects(
                    tri.box_lo,tri.box_hi,start,motion,extent,tolerance):
                continue
            source=(tri.a,tri.b,tri.c)
            if collapsed:
                sqdist=_segment_triangle_distance_sq(*patch_segment,source)
            else:
                sqdist=min(_triangle_triangle_distance_sq(source,part) for part in patches)
            if sqdist<=distance_threshold:
                hits.append(SweptCapsuleHit(tid,math.sqrt(max(0.,sqdist)),r))
                if len(hits)>MAX_HITS:raise ValueError("Capsule oracle hit safety cap")
    hits.sort(key=lambda x:x.original_triangle_id)
    return {"schema":SCHEMA,"hits":hits,
            "original_triangle_hit_ids":[x.original_triangle_id for x in hits],
            "radius_level_units":r,"axis_unit_xyz":list(unit),
            "axis_half_length_level_units":half,
            "distance_tolerance_level_units":float(tolerance),
            "swept_axis_patch_collapsed_to_segment":collapsed,
            "time_of_impact_solved":False,"native_havok_capsule_contact_verified":False,
            "retail_game_files_modified":False}


def swept_capsule_mopp_candidates(walker,start,end,radius,axis=(0.,0.,1.),
                                  axis_half_length=.5,*,diagonal_mode="conservative",
                                  tolerance_units=1.):
    """Swept box enclosing the capsule, NOT actual Havok capsule traversal."""
    r,unit,half=_shape(radius,axis,axis_half_length)
    extents=tuple(r+half*abs(unit[k]) for k in range(3))
    result=swept_aabb_mopp_candidates(walker,start,end,extents,
                                      diagonal_mode=diagonal_mode,
                                      tolerance_units=tolerance_units)
    return {**result,"schema":"DX2SDK-MOPP-capsule-via-enclosing-AABB-candidates-v1",
            "capsule_enclosing_AABB_half_extents_level_xyz":list(extents),
            "capsule_geometry_mode":"fixed_axis_translating_capsule",
            "capsule_is_exact_havok_shape_query":False,
            "candidate_overapproximation":True}


def compare_swept_capsule(oracle,walker,start,end,radius,axis=(0.,0.,1.),
                          axis_half_length=.5,*,diagonal_mode="conservative",
                          tolerance_units=1.):
    truth=swept_capsule_triangle_hits(oracle,start,end,radius,axis,axis_half_length)
    broad=swept_capsule_mopp_candidates(walker,start,end,radius,axis,
                                        axis_half_length,diagonal_mode=diagonal_mode,
                                        tolerance_units=tolerance_units)
    actual=set(truth["original_triangle_hit_ids"])
    candidates=set(broad["candidate_original_triangle_ids"])
    return {"schema":"DX2SDK-Level-swept-capsule-vs-MOPP-candidates-v1",
            "geometric_original_triangle_hit_ids":sorted(actual),
            "candidate_original_triangle_ids":sorted(candidates),
            "missing_original_triangle_ids":sorted(actual-candidates),
            "geometric_hit_count":len(actual),"candidate_count":len(candidates),
            "extra_broadphase_candidates":len(candidates-actual),
            "all_geometric_hits_retained":actual<=candidates,
            "capsule_and_havok_runtime_equivalent":False,
            "gmp_source_written":False}
