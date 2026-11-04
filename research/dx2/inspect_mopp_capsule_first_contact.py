#!/usr/bin/env python3
"""Research: tolerance-bounded first contact of a fixed-axis translating capsule.

A geometric closest-segment/triangle oracle is used at each trial time.
Golden-section search finds the convex distance minimum; bisection brackets
first entry into a sphere-radius-expanded distance threshold. This is an
OFFLINE geometric estimate, not an exact Havok time of impact, controller,
contact manifold, material/filter query or runtime-compatible shape serializer.
Original Level-space source IDs are preserved. Source data are never edited.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import math

from inspect_mopp_point_triangle_oracle import LevelPointTriangleOracle, _point
from inspect_mopp_swept_capsule import (
    _shape, _add, _sub, _mul, _dot, _cross, _sq, _clamp,
    _segment_expanded_box_intersects, swept_capsule_triangle_hits,
    swept_capsule_mopp_candidates,
)

SCHEMA = "DX2SDK-Level-capsule-tolerance-bracketed-first-contact-v1"
MAX_GOLDEN_STEPS = 88
MAX_ROOT_STEPS = 66
MAX_CANDIDATES = 150_000


def _closest_point_triangle(p,a,b,c):
    """Closest point on a nondegenerate closed 3D triangle (Ericson regions)."""
    ab=_sub(b,a);ac=_sub(c,a);ap=_sub(p,a)
    d1=_dot(ab,ap);d2=_dot(ac,ap)
    if d1<=0 and d2<=0:return a
    bp=_sub(p,b);d3=_dot(ab,bp);d4=_dot(ac,bp)
    if d3>=0 and d4<=d3:return b
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0:
        return _add(a,_mul(ab,d1/(d1-d3)))
    cp=_sub(p,c);d5=_dot(ab,cp);d6=_dot(ac,cp)
    if d6>=0 and d5<=d6:return c
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0:
        return _add(a,_mul(ac,d2/(d2-d6)))
    va=d3*d6-d5*d4
    if va<=0 and (d4-d3)>=0 and (d5-d6)>=0:
        return _add(b,_mul(_sub(c,b),(d4-d3)/((d4-d3)+(d5-d6))))
    det=va+vb+vc
    if det<=0:raise ValueError("Degenerate source triangle closest-point denominator")
    return _add(a,_add(_mul(ab,vb/det),_mul(ac,vc/det)))


def _closest_segment_segment(a,b,c,d):
    """Return closest XYZ pair on two closed segments, including points."""
    u=_sub(b,a);v=_sub(d,c);w=_sub(a,c)
    aa=_sq(u);ee=_sq(v);ff=_dot(v,w)
    if aa<=1e-30 and ee<=1e-30:return a,c
    if aa<=1e-30:s=0.;t=_clamp(ff/ee)
    else:
        cc=_dot(u,w)
        if ee<=1e-30:t=0.;s=_clamp(-cc/aa)
        else:
            bb=_dot(u,v);den=aa*ee-bb*bb
            s=_clamp((bb*ff-cc*ee)/den) if den>1e-30 else 0.
            t=(bb*s+ff)/ee
            if t<0:t=0.;s=_clamp(-cc/aa)
            elif t>1:t=1.;s=_clamp((bb-cc)/aa)
    return _add(a,_mul(u,s)),_add(c,_mul(v,t))


def _closest_axis_triangle(a,b,tri):
    """Return closest point pair (capsule axis, source triangle) and d^2.

    Tests true face penetration independently of edge/vertex candidates.
    Does not derive positions from source MOPP code or binary leaves.
    """
    p,q,r=tri
    n=_cross(_sub(q,p),_sub(r,p));normal=math.hypot(*n)
    if normal<=0 or not math.isfinite(normal):
        raise ValueError("Original triangle must have finite nonzero geometric area")
    candidates=[]
    def offer(x,y):
        d=_sq(_sub(x,y))
        if not math.isfinite(d):raise ValueError("Unrepresentable triangle distance")
        candidates.append((d,x,y))

    for x in (a,b):offer(x,_closest_point_triangle(x,p,q,r))
    for x,y in ((p,q),(q,r),(r,p)):
        cx,cy=_closest_segment_segment(a,b,x,y)
        offer(cx,cy)
    motion=_sub(b,a)
    denominator=_dot(n,motion)
    if abs(denominator)>1e-14*normal*math.hypot(*motion):
        t=_dot(n,_sub(p,a))/denominator
        if 0<=t<=1:
            x=_add(a,_mul(motion,t))
            y=_closest_point_triangle(x,p,q,r)
            if _sq(_sub(x,y))<=1e-20:
                offer(x,y)
    if not candidates:raise ValueError("No closest-feature candidates")
    return min(candidates,key=lambda val:val[0])


def _capsule_axis_at(start,end,unit,half,t):
    center=tuple(start[k]+(end[k]-start[k])*t for k in range(3))
    scale=_mul(unit,half)
    return _sub(center,scale),_add(center,scale)


def _normal_from_pair(axis_point,triangle_point):
    delta=_sub(axis_point,triangle_point)
    length=math.hypot(*delta)
    if not math.isfinite(length):raise ValueError("Invalid closest-point normal")
    return None if length<=1e-12 else tuple(x/length for x in delta)


@dataclass(frozen=True)
class CapsuleContact:
    original_triangle_id:int
    t_first_inside:float
    t_last_outside:float|None
    signed_gap_at_contact:float
    triangle_point_xyz:tuple[float,float,float]
    capsule_axis_point_xyz:tuple[float,float,float]
    contact_normal_from_triangle_to_capsule:tuple[float,float,float]|None
    contact_normal_resolved:bool
    initial_overlap:bool
    near_tangency:bool
    numerical_contact_only:bool


def _first_contact_one(start,end,radius,unit,half,source_tri,*,
                       distance_tolerance=1e-7,time_tolerance=1e-8):
    """Solve a convex distance-to-closed-triangle path with bounded searches.

    First entry into d(t)<=radius+distance_tolerance. For tangency, the
    boundary may be isolated and is flagged. We return a bounding bracket
    [t_last_outside,t_first_inside] rather than claim exact engine time.
    """
    def measure(t):
        aa,bb=_capsule_axis_at(start,end,unit,half,t)
        return _closest_axis_triangle(aa,bb,source_tri)
    eps=radius+distance_tolerance
    first=measure(0.)
    if first[0]<=eps*eps:
        norm=_normal_from_pair(first[1],first[2])
        return CapsuleContact(-1,0.,None,math.sqrt(first[0])-radius,
                              first[2],first[1],norm,norm is not None,
                              True,False,first[0]>radius*radius)

    left=0.;right=1.;ratio=(math.sqrt(5.)-1.)/2.
    c=right-ratio*(right-left);d=left+ratio*(right-left)
    fc=measure(c)[0];fd=measure(d)[0]
    for _ in range(MAX_GOLDEN_STEPS):
        if fc<=fd:
            right=d;d=c;fd=fc;c=right-ratio*(right-left);fc=measure(c)[0]
        else:
            left=c;c=d;fc=fd;d=left+ratio*(right-left);fd=measure(d)[0]
    tmin=(left+right)*.5
    probes=[(0.,first),(tmin,measure(tmin)),(1.,measure(1.))]
    tmin,found=min(probes,key=lambda pair:pair[1][0])
    if found[0]>eps*eps:
        return None
    near_tangent=abs(math.sqrt(found[0])-radius)<=max(4*distance_tolerance,1e-11)
    if tmin==0:
        raise ValueError("Unexpected minimum at start after noncontact check")
    low=0.;high=tmin
    for _ in range(MAX_ROOT_STEPS):
        if high-low<=time_tolerance:break
        midpoint=(low+high)*.5
        if measure(midpoint)[0]<=eps*eps:high=midpoint
        else:low=midpoint
    candidate=measure(high)
    if candidate[0]>eps*eps*(1+1e-8):
        raise ValueError("First-contact numerical bracket inconsistent")
    norm=_normal_from_pair(candidate[1],candidate[2])
    return CapsuleContact(-1,high,low,math.sqrt(candidate[0])-radius,
                          candidate[2],candidate[1],norm,norm is not None,
                          False,near_tangent,candidate[0]>radius*radius)


def first_capsule_triangle_contacts(oracle,start,end,radius,
                                    axis=(0.,0.,1.),axis_half_length=.5,*,
                                    distance_tolerance=1e-7,time_tolerance=1e-8,
                                    max_hits=10000):
    """Return first-entry estimates per triangle, ordered by time, not contacts.

    Does NOT compute a manifold, resolve penetration, or choose a physics body.
    """
    if not isinstance(oracle,LevelPointTriangleOracle):
        raise ValueError("Expected original Level-space triangle oracle")
    a=_point(start,label="Contact segment start")
    b=_point(end,label="Contact segment end")
    r,unit,half=_shape(radius,axis,axis_half_length)
    if (type(distance_tolerance) not in (int,float) or
            not math.isfinite(distance_tolerance) or
            not 0<=distance_tolerance<=1e-3 or
            type(time_tolerance) not in (int,float) or
            not math.isfinite(time_tolerance) or
            not 1e-11<=time_tolerance<=1e-3 or
            type(max_hits) is not int or not 1<=max_hits<=MAX_CANDIDATES):
        raise ValueError("Invalid capsule time-of-impact research tolerances")
    h=tuple(r+half*abs(unit[k]) for k in range(3))
    motion=_sub(b,a)
    todo=[oracle.root];hits=[];considered=0
    while todo:
        lo,hi,left,right,ids=oracle.nodes[todo.pop()]
        if not _segment_expanded_box_intersects(lo,hi,a,motion,h,distance_tolerance):
            continue
        if ids:
            for tid in ids:
                tri=oracle.tris[tid]
                if not _segment_expanded_box_intersects(tri.box_lo,tri.box_hi,
                        a,motion,h,distance_tolerance):
                    continue
                considered+=1
                if considered>MAX_CANDIDATES:
                    raise ValueError("First-contact triangle candidate cap exceeded")
                result=_first_contact_one(a,b,r,unit,half,(tri.a,tri.b,tri.c),
                       distance_tolerance=distance_tolerance,
                       time_tolerance=time_tolerance)
                if result is not None:
                    hits.append(replace(result,original_triangle_id=tid))
                    if len(hits)>max_hits:
                        raise ValueError("First-contact hit cap exceeded")
        else:
            todo.extend((left,right))
    hits.sort(key=lambda x:(x.t_first_inside,x.original_triangle_id))
    return {"schema":SCHEMA,"contacts":hits,
            "original_triangle_contact_ids":sorted(h.original_triangle_id for h in hits),
            "first_contact":hits[0] if hits else None,
            "triangles_considered_after_BVH":considered,
            "distance_tolerance_level_units":float(distance_tolerance),
            "time_parameter_bracket_tolerance":float(time_tolerance),
            "returned_time_is_tolerance_expanded_first_entry":True,
            "normal_from_geometry_not_havok":True,
            "contact_manifold_or_response_computed":False,
            "authentic_havok_runtime_queried":False,
            "source_gmp_modified":False}


def compare_first_contact_with_full_sweep(oracle,start,end,radius,
                                         axis=(0.,0.,1.),axis_half_length=.5,*,
                                         distance_tolerance=1e-7):
    """Fail closed if the new first-contact oracle loses PR #45 full-sweep IDs."""
    contacts=first_capsule_triangle_contacts(
        oracle,start,end,radius,axis,axis_half_length,
        distance_tolerance=distance_tolerance)
    independent=swept_capsule_triangle_hits(
        oracle,start,end,radius,axis,axis_half_length,tolerance=distance_tolerance)
    older=set(independent["original_triangle_hit_ids"])
    newer=set(contacts["original_triangle_contact_ids"])
    return {"schema":SCHEMA,"full_sweep_original_triangle_ids":sorted(older),
            "contact_original_triangle_ids":sorted(newer),
            "contacts_missing_old_full_sweep_ids":sorted(older-newer),
            "new_contacts_absent_from_old_full_sweep":sorted(newer-older),
            "matching_original_triangle_id_sets":older==newer,
            "first_contact":contacts["first_contact"],
            "havok_runtime_verified":False}
