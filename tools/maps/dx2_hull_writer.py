#!/usr/bin/env python3
"""Experimental DX2 type-5 convex physics-hull writer.

Only the observed four-part point-cloud layout is supported. The two
uninterpreted prefix fields are preserved verbatim. Coordinates are explicit
native PHYSICS coordinates, not render coordinates. No automatic collision
registration, mass/inertia or retail runtime claim.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from itertools import combinations, product
import json
import math
from pathlib import Path
import re
import struct

from dx2_ibd_integrity import read_bounded, verify_bundle, sha256
from dx2_ibd_repack import rebuild_canonical

MAX_POINTS=64
MAX_COORD=1000000
MAX_JSON=65536
KNOWN_PREFIXES={0,2,8,32}


@dataclass(frozen=True)
class Hull:
    parts: tuple
    points: tuple


def select_hull(bundle,name):
    found=[r for r in bundle.resources if r.typ==5 and r.name.casefold()==name.casefold()]
    if len(found)!=1:
        raise ValueError("Expected exactly one existing physics hull with that name")
    return found[0]


def _vector(point):
    if type(point) not in (tuple,list) or len(point)!=3:
        raise ValueError("Expected three native physics coordinates")
    out=[]
    for x in point:
        if type(x) not in (float,int) or not math.isfinite(x) or abs(x)>=MAX_COORD:
            raise ValueError("Nonfinite or out-of-range physics coordinate")
        out.append(struct.unpack("<f",struct.pack("<f",x))[0])
    return tuple(out)


def sub(a,b):
    return tuple(x-y for x,y in zip(a,b))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def validate_points(points):
    """Validate all points are extreme vertices of a full-dimensional hull.

    Use exact integer predicates on the float32-quantized coordinates.
    For each supporting plane, intersect its incident vertex set for each
    vertex. An extreme vertex is uniquely isolated by incident planes.
    Points interior to a face, edge, or volume cannot satisfy that test.
    This is deliberately bounded; it is not a Havok tolerance model.
    """
    if type(points) not in (list,tuple) or not 4<=len(points)<=MAX_POINTS:
        raise ValueError("Hull requires 4 to 64 points")
    result=tuple(_vector(p) for p in points)
    if len(set(result))!=len(result):
        raise ValueError("Duplicate float32 hull point")
    # Every float32 is an exact binary rational. All denominators divide
    # the largest denominator, so all orientation tests can use integers.
    ratios=[[x.as_integer_ratio() for x in p] for p in result]
    den=max(d for row in ratios for _,d in row)
    pts=[tuple(n*(den//d) for n,d in row) for row in ratios]
    # Test affine rank before support-plane enumeration.
    origin=pts[0]
    vectors=[sub(p,origin) for p in pts[1:]]
    a=next((v for v in vectors if any(v)),None)
    normal=next((cross(a,v) for v in vectors if any(cross(a,v))),None)
    if normal is None or not any(dot(normal,v) for v in vectors):
        raise ValueError("Hull is not full-dimensional")
    n=len(pts)
    all_mask=(1<<n)-1
    incident=[all_mask]*n
    for i,j,k in combinations(range(n),3):
        plane=cross(sub(pts[j],pts[i]),sub(pts[k],pts[i]))
        if not any(plane):
            continue
        positive=negative=False
        mask=0
        for m,p in enumerate(pts):
            value=dot(plane,sub(p,pts[i]))
            if value>0:positive=True
            elif value<0:negative=True
            else:mask|=1<<m
            if positive and negative:break
        if positive and negative:continue
        for m in range(n):
            if mask&(1<<m):incident[m]&=mask
    if any(mask!=1<<i for i,mask in enumerate(incident)):
        raise ValueError("Hull includes a non-extreme point")
    return result


def inspect_hull(bundle,resource):
    if resource.typ!=5:raise ValueError("Not a physics hull")
    parts=tuple(bundle.parts(resource))
    if len(parts)!=4 or tuple(map(len,parts[:3]))!=(4,1,4):
        raise ValueError("Unsupported physics hull part layout")
    prefix=struct.unpack("<I",parts[0])[0]
    n=struct.unpack("<I",parts[2])[0]
    if prefix not in KNOWN_PREFIXES or parts[1]!=b"\0":
        raise ValueError("Unsupported physics hull prefix")
    if not 4<=n<=MAX_POINTS or len(parts[3])!=16*n:
        raise ValueError("Physics hull count/size mismatch")
    rows=list(struct.iter_unpack("<4f",parts[3]))
    if any(parts[3][16*i+12:16*i+16]!=b"\0"*4 for i in range(n)):
        raise ValueError("Unsupported fourth coordinate")
    return Hull(parts,validate_points([row[:3] for row in rows]))


def box_points(lower,upper):
    lo,hi=_vector(lower),_vector(upper)
    if not all(a<b for a,b in zip(lo,hi)):
        raise ValueError("Box must have positive extent on all axes")
    return validate_points(list(product(*zip(lo,hi))))


def replace_hull(raw,name,points):
    b=verify_bundle(raw)
    r=select_hull(b,name)
    old=inspect_hull(b,r)
    pts=validate_points(points)
    payload=b"".join(struct.pack("<4f",*p,0.0) for p in pts)
    parts=[*old.parts[:2],struct.pack("<I",len(pts)),payload]
    candidate=rebuild_canonical(raw,{r.index:parts})
    after=verify_bundle(candidate)
    parsed=inspect_hull(after,select_hull(after,name))
    if parsed.parts!=tuple(parts) or parsed.points!=pts:
        raise ValueError("Reparsed hull differs from requested points")
    if len(after.resources)!=len(b.resources):
        raise ValueError("Resource count changed")
    for before,new in zip(b.resources,after.resources):
        if (before.name,before.typ,before.index,before.part_count)!=(new.name,new.typ,new.index,new.part_count):
            raise ValueError("Resource identity changed")
        if before.index!=r.index and b.raw(before)!=after.raw(new):
            raise ValueError("Unrelated resource changed")
    if rebuild_canonical(candidate,{r.index:list(old.parts)})!=raw:
        raise ValueError("Inverse collision serialization did not restore source")
    return candidate


def read_geometry(path):
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=MAX_JSON:
        raise ValueError("Invalid or oversized physics JSON")
    with path.open("rb") as stream:raw=stream.read(MAX_JSON+1)
    if len(raw)>MAX_JSON:raise ValueError("Physics JSON exceeds limit")
    doc=json.loads(raw)
    if type(doc) is not dict:raise ValueError("Expected physics geometry object")
    if set(doc)=={"points"}:return validate_points(doc["points"])
    if set(doc)=={"min","max"}:return box_points(doc["min"],doc["max"])
    raise ValueError("Expected explicit native physics points or box min/max")


def write_candidate(source,output,pin,name,geometry):
    if not re.fullmatch(r"[0-9a-f]{64}",pin):raise ValueError("Expected lowercase source SHA-256")
    if source.is_symlink() or output.is_symlink():raise ValueError("Symlink input or output refused")
    source=source.resolve(strict=True);output=output.resolve()
    if (source.suffix.lower()!=".ibd" or output.name!=source.name or output.exists()
            or source.parent==output.parent or source.parent in output.parents):
        raise ValueError("Output must retain original filename in a new isolated directory")
    raw=read_bounded(source)
    if sha256(raw)!=pin:raise ValueError("Source SHA-256 mismatch")
    pts=read_geometry(geometry)
    candidate=replace_hull(raw,name,pts)
    if sha256(read_bounded(source))!=pin:raise ValueError("Source changed during preparation")
    output.parent.mkdir(parents=True,exist_ok=True)
    created=False
    try:
        with output.open("xb") as stream:
            created=True
            stream.write(candidate)
        actual=read_bounded(output)
        if actual!=candidate or sha256(read_bounded(source))!=pin:
            raise ValueError("Candidate or source changed")
        verify_bundle(actual)
    except Exception:
        if created:output.unlink(missing_ok=True)
        raise
    return {"schema":"DX2-PhysicsHullCandidate-v1","hull":name,"point_count":len(pts),
            "source_sha256":pin,"candidate_sha256":sha256(candidate),
            "inverse_byte_identical":True,"runtime_verified":False,
            "physics_registration_verified":False,"source_modified":False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    inspect=sub.add_parser("inspect")
    inspect.add_argument("source",type=Path);inspect.add_argument("--hull",required=True)
    edit=sub.add_parser("replace")
    edit.add_argument("source",type=Path);edit.add_argument("--hull",required=True)
    edit.add_argument("--geometry",required=True,type=Path)
    edit.add_argument("--source-sha256",required=True);edit.add_argument("--output",required=True,type=Path)
    a=p.parse_args(argv)
    try:
        if a.command=="inspect":
            raw=read_bounded(a.source);b=verify_bundle(raw);h=inspect_hull(b,select_hull(b,a.hull))
            result={"source_sha256":sha256(raw),"hull":a.hull,"point_count":len(h.points),
                    "points":h.points,"prefix":struct.unpack("<I",h.parts[0])[0],
                    "runtime_verified":False}
        else:result=write_candidate(a.source,a.output,a.source_sha256,a.hull,a.geometry)
        print(json.dumps(result,sort_keys=True,indent=2))
        return 0
    except (OSError,ValueError,IndexError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":raise SystemExit(main())
