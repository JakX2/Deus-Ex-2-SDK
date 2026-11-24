#!/usr/bin/env python3
"""Experimental native DX2 static mesh topology replacement.

Only verified single-section, single-material, 64-byte vertex templates
without hardpoints or auxiliary shadow geometry are accepted. Input is an
explicit native-coordinate indexed triangle mesh in JSON, not an arbitrary
OBJ/glTF importer. No collision, BSP, shadow or runtime compatibility claim.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import struct

from dx2bundles import parse_mesh
from dx2_ibd_integrity import read_bounded, verify_bundle, sha256
from dx2_ibd_repack import rebuild_canonical

MAX_VERTICES = 65536
MAX_INDICES = 300000
MAX_JSON_BYTES = 32*1024*1024
EPS = 1e-8


@dataclass(frozen=True)
class Template:
    mesh: object
    parts: tuple
    section_name: bytes
    header: bytes


def select_mesh(bundle,name):
    matches=[r for r in bundle.resources if r.typ==4 and r.name.casefold()==name.casefold()]
    if len(matches)!=1:
        raise ValueError("Expected exactly one existing static mesh with that name")
    return matches[0]


def inspect_template(bundle,resource):
    mesh=parse_mesh(bundle,resource)
    parts=tuple(bundle.parts(resource))
    if len(parts)<2 or len(parts[-2])!=4 or struct.unpack("<I",parts[-2])[0]!=len(parts[-1]):
        raise ValueError("Unknown render payload prefix")
    data=parts[-1]
    nv,ni,nt,ns,nsi,nst,nsv,u1,stride,u2=struct.unpack_from("<10I",data,40)
    if (stride!=64 or (nsi,nst,nsv,u1,u2)!=(0,0,0,1,0)
            or ns!=1 or nt!=ni//3 or nv>MAX_VERTICES or mesh.hardpoints
            or len(mesh.skins)!=1 or len(mesh.skins[0]["materials"])!=1):
        raise ValueError("Only one-section 64-byte meshes without hardpoints or auxiliary geometry")
    if mesh.sections[0]["vertex_count"]!=nv or mesh.sections[0]["index_count"]!=ni:
        raise ValueError("Section must cover the complete mesh")
    at=80+nv*64+ni*2
    n=data[at]
    name=data[at+1:at+1+n]
    if not name.endswith(b"\0") or b"\0" in name[:-1]:
        raise ValueError("Unknown section string encoding")
    if struct.unpack_from("<6I",data,at+1+n)!=(ni//3,0,nv,0,ni,0):
        raise ValueError("Unknown section record geometry")
    for i in range(nv):
        p=80+i*64
        if not (data[p+24:p+32]==data[p+44:p+52]==data[p+52:p+60]
                and data[p+60:p+64]==b"\xff"*4):
            raise ValueError("Template has nonduplicated UV channels or nonwhite color")
    # Independently validate the original bounding fields.
    lo=[min(p[i] for p in mesh.positions) for i in range(3)]
    hi=[max(p[i] for p in mesh.positions) for i in range(3)]
    if list(mesh.bounds)!=lo+hi:
        raise ValueError("Original AABB does not match decoded vertices")
    rad,*center=struct.unpack_from("<4f",data,24)
    expected=[math.dist(lo,hi)/2]+[(a+b)/2 for a,b in zip(lo,hi)]
    if not all(math.isclose(a,b,rel_tol=1e-5,abs_tol=1e-5) for a,b in zip([rad,*center],expected)):
        raise ValueError("Unrecognized bounding sphere fields")
    return Template(mesh,parts,name,data[:80])


def f32(value):
    if type(value) not in (int,float) or not math.isfinite(value) or abs(value)>=1e6:
        raise ValueError("Nonfinite or out-of-range vertex component")
    return struct.unpack("<f",struct.pack("<f",value))[0]


def vector(value,count):
    if type(value) not in (list,tuple) or len(value)!=count:
        raise ValueError("Incorrect vector dimension")
    return tuple(f32(x) for x in value)


def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def unit(a):
    n=math.sqrt(dot(a,a))
    if not math.isfinite(n) or n<EPS:
        raise ValueError("Degenerate direction")
    return tuple(x/n for x in a)


def parse_geometry(doc):
    """Accept native coordinates, explicit vertex normals and one UV per vertex."""
    if type(doc) is not dict or set(doc)!={"positions","normals","uv","indices"}:
        raise ValueError("Expected positions, normals, uv and indices only")
    if any(type(doc[k]) is not list for k in doc):
        raise ValueError("Geometry arrays required")
    nv=len(doc["positions"]);ni=len(doc["indices"])
    if not 3<=nv<=MAX_VERTICES or not 3<=ni<=MAX_INDICES or ni%3:
        raise ValueError("Unsupported vertex or triangle count")
    if len(doc["normals"])!=nv or len(doc["uv"])!=nv:
        raise ValueError("Vertex attributes must have matching counts")
    pos=[vector(v,3) for v in doc["positions"]]
    normals=[tuple(f32(c) for c in unit(vector(v,3))) for v in doc["normals"]]
    uv=[vector(v,2) for v in doc["uv"]]
    indices=doc["indices"]
    if any(type(i) is not int or not 0<=i<nv for i in indices) or len(set(indices))!=nv:
        raise ValueError("Indices must be uint16 and reference every vertex")
    accum=[[0.,0.,0.] for _ in pos]
    signs=[set() for _ in pos]
    for k in range(0,ni,3):
        a,b,c=indices[k:k+3]
        if len({a,b,c})!=3:
            raise ValueError("Repeated triangle vertex")
        e1,e2=sub(pos[b],pos[a]),sub(pos[c],pos[a])
        face=unit(cross(e1,e2))
        du1,dv1=sub(uv[b],uv[a]);du2,dv2=sub(uv[c],uv[a])
        det=du1*dv2-du2*dv1
        if abs(det)<EPS:
            raise ValueError("Degenerate triangle UV mapping")
        tangent=unit(tuple((x*dv2-y*dv1)/det for x,y in zip(e1,e2)))
        for i in (a,b,c):
            # All 6,990 triangle corners in the 32 eligible source
            # templates have positive dot products with their face normals.
            if dot(face,normals[i])<=EPS:
                raise ValueError("Native triangle winding disagrees with vertex normal")
            signs[i].add(det>0)
            for j in range(3):accum[i][j]+=tangent[j]
    if any(len(s)!=1 for s in signs):
        raise ValueError("Split vertices at mirrored UV seams")
    tangents=[]
    for n,t in zip(normals,accum):
        orth=tuple(x-dot(n,t)*y for x,y in zip(t,n))
        tangents.append(tuple(f32(x) for x in unit(orth)))
    return pos,normals,uv,tuple(indices),tangents


def build_payload(template,doc):
    pos,normals,uv,indices,tangents=parse_geometry(doc)
    lo=[min(p[i] for p in pos) for i in range(3)]
    hi=[max(p[i] for p in pos) for i in range(3)]
    sphere=[f32(math.dist(lo,hi)/2)]+[f32((a+b)/2) for a,b in zip(lo,hi)]
    nv,ni=len(pos),len(indices)
    header=bytearray(template.header)
    struct.pack_into("<10f",header,0,*(lo+hi+sphere))
    struct.pack_into("<4I",header,40,nv,ni,ni//3,1)
    vertices=bytearray()
    for xyz,n,tex,t in zip(pos,normals,uv,tangents):
        vertices.extend(struct.pack("<15fI",*xyz,*n,*tex,*t,*tex,*tex,0xffffffff))
    section=bytes([len(template.section_name)])+template.section_name+struct.pack(
        "<6I",ni//3,0,nv,0,ni,0)
    data=bytes(header)+bytes(vertices)+struct.pack("<%dH"%ni,*indices)+section
    return data,(pos,normals,uv,indices,tangents)


def replace_geometry(raw,name,doc):
    bundle=verify_bundle(raw)
    resource=select_mesh(bundle,name)
    template=inspect_template(bundle,resource)
    payload,expected=build_payload(template,doc)
    parts=list(template.parts)
    parts[-2:]=[struct.pack("<I",len(payload)),payload]
    candidate=rebuild_canonical(raw,{resource.index:parts})
    after=verify_bundle(candidate)
    result=inspect_template(after,select_mesh(after,name))
    pos,normals,uv,indices,tangents=expected
    if (result.parts!=tuple(parts) or result.parts[:-2]!=template.parts[:-2]
            or result.mesh.positions!=pos or result.mesh.normals!=normals
            or result.mesh.uv!=uv or tuple(result.mesh.indices)!=indices
            or result.mesh.skins!=template.mesh.skins or result.mesh.flags!=template.mesh.flags):
        raise ValueError("Reparsed mesh differs from geometry plan")
    for old,new in zip(bundle.resources,after.resources):
        if (old.name,old.typ,old.index,old.part_count)!=(new.name,new.typ,new.index,new.part_count):
            raise ValueError("Resource identity changed")
        if old.index!=resource.index and bundle.raw(old)!=after.raw(new):
            raise ValueError("Unrelated resource changed")
    # Rebuild from original render parts, rather than copying the original
    # archive over the candidate, to establish exact inverse serialization.
    if rebuild_canonical(candidate,{resource.index:list(template.parts)})!=raw:
        raise ValueError("Inverse geometry serialization did not restore source")
    return candidate


def write_candidate(source,output,pin,name,geometry):
    if not re.fullmatch(r"[0-9a-f]{64}",pin):
        raise ValueError("Expected lowercase source SHA-256")
    if source.is_symlink() or output.is_symlink():
        raise ValueError("Symlink input or output refused")
    source=source.resolve(strict=True);output=output.resolve()
    if (source.suffix.lower()!=".ibd" or output.name!=source.name or output.exists()
            or output.parent==source.parent or source.parent in output.parents):
        raise ValueError("Output must retain original filename in a new isolated directory")
    raw=read_bounded(source)
    if sha256(raw)!=pin:
        raise ValueError("Source SHA-256 mismatch")
    if geometry.is_symlink() or not geometry.is_file() or not 0<geometry.stat().st_size<=MAX_JSON_BYTES:
        raise ValueError("Invalid or oversized geometry JSON")
    doc=json.loads(geometry.read_text(encoding="utf-8"))
    candidate=replace_geometry(raw,name,doc)
    if sha256(read_bounded(source))!=pin:
        raise ValueError("Source changed during preparation")
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
    return {"schema":"DX2-StaticMeshGeometryCandidate-v1","mesh":name,
            "source_sha256":pin,"candidate_sha256":sha256(candidate),
            "vertex_count":len(doc["positions"]),"triangle_count":len(doc["indices"])//3,
            "inverse_byte_identical":True,"runtime_verified":False,
            "collision_generated":False,"source_modified":False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    inspect=sub.add_parser("inspect")
    inspect.add_argument("source",type=Path);inspect.add_argument("--mesh",required=True)
    edit=sub.add_parser("replace-geometry")
    edit.add_argument("source",type=Path);edit.add_argument("--mesh",required=True)
    edit.add_argument("--geometry",required=True,type=Path)
    edit.add_argument("--source-sha256",required=True);edit.add_argument("--output",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=="inspect":
            raw=read_bounded(args.source)
            b=verify_bundle(raw)
            m=inspect_template(b,select_mesh(b,args.mesh)).mesh
            result={"source_sha256":sha256(raw),"mesh":m.name,"vertices":len(m.positions),
                    "triangles":len(m.indices)//3,"material":m.skins[0]["materials"][0],
                    "runtime_verified":False}
        else:
            result=write_candidate(args.source,args.output,args.source_sha256,args.mesh,args.geometry)
        print(json.dumps(result,sort_keys=True,indent=2))
        return 0
    except (OSError,ValueError,IndexError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
