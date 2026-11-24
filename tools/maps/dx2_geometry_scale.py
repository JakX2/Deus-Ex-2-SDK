#!/usr/bin/env python3
"""Offline, coordinated uniform scaling of named render mesh and hull copies.

Only the observed 64-byte render vertices, position+rotation hardpoints,
16-byte auxiliary vertices and type-5 hulls are supported. The same scale
is applied in each resource's own coordinate system. Name matching is not
proof of runtime binding. No mass, inertia, actor, BSP or registry edits.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import struct

from dx2bundles import Parts, parse_mesh
from dx2_ibd_integrity import MAX_BUNDLE_BYTES, verify_bundle, sha256, read_bounded
from dx2_ibd_repack import rebuild_canonical
from dx2_hull_writer import inspect_hull
from dx2_material_audit import members
from dx2_custom_texture_import import _zip_pin, _portable_parts, _actual_member_names

MAX_SELECTED_BYTES=256*1024*1024


def scale_word(data, offset, exponent):
    old=data[offset:offset+4]
    x=struct.unpack("<f",old)[0]
    y=math.ldexp(x,exponent)
    if not math.isfinite(y) or abs(y)>=1000000:
        raise ValueError("Scaled position outside supported range")
    word=struct.pack("<f",y)
    # Refuse underflow/rounding which would prevent exact inverse.
    if struct.pack("<f",math.ldexp(struct.unpack("<f",word)[0],-exponent))!=old:
        raise ValueError("Position scaling is not exactly reversible")
    data[offset:offset+4]=word


def _rotation_ok(values):
    rows=[values[i:i+3] for i in (0,3,6)]
    if not all(math.isfinite(x) for x in values):return False
    if any(abs(sum(x*y for x,y in zip(a,b))-(i==j))>1e-3
           for i,a in enumerate(rows) for j,b in enumerate(rows)):return False
    a,b,c=rows
    det=a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
    return abs(det-1)<1e-3


def _scale_render_parts(bundle,resource,exponent):
    mesh=parse_mesh(bundle,resource)
    parts=list(bundle.parts(resource))
    p=Parts(parts)
    for _ in range(p.u32()):
        p.string()
        for _ in range(p.u32()):p.string()
    for _ in range(p.u32()):p.u32()
    p.u32()
    nh=p.u32()
    if nh!=len(mesh.hardpoints):raise ValueError("Hardpoint readers disagree")
    for h in mesh.hardpoints:
        slot=p.pos
        matrix=p.take(48)
        if not _rotation_ok(struct.unpack("<12f",matrix)[3:]):
            raise ValueError("Unrecognized hardpoint rotation")
        changed=bytearray(matrix)
        for off in (0,4,8):scale_word(changed,off,exponent)
        parts[slot]=bytes(changed)
        if p.string()!=h["name"]:raise ValueError("Hardpoint name readers disagree")
    size=p.u32()
    at=p.pos
    payload=p.take(size)
    p.end()
    data=bytearray(payload)
    nv,ni,nt,ns,nsi,nst,nsv,u1,stride,u2=struct.unpack_from("<10I",data,40)
    if (stride,u1,u2)!=(64,1,0) or nt!=ni//3 or nsi!=3*nst or bool(nsi)!=bool(nsv):
        raise ValueError("Unsupported render/auxiliary layout")
    lo=[min(v[i] for v in mesh.positions) for i in range(3)]
    hi=[max(v[i] for v in mesh.positions) for i in range(3)]
    if list(mesh.bounds)!=lo+hi:raise ValueError("Original render bounds disagree")
    expected=[math.dist(lo,hi)/2]+[(a+b)/2 for a,b in zip(lo,hi)]
    if not all(math.isclose(x,y,rel_tol=1e-5,abs_tol=1e-5)
               for x,y in zip(struct.unpack_from("<4f",data,24),expected)):
        raise ValueError("Unknown bounding sphere fields")
    shadow=80+nv*64
    shadow_index=shadow+nsv*16
    if shadow_index+nsi*2>len(data):raise ValueError("Truncated auxiliary geometry")
    if nsi and max(struct.unpack_from("<%dH"%nsi,data,shadow_index))>=nsv:
        raise ValueError("Auxiliary index outside vertex range")
    # Every non-position vertex field, index and unknown word stays intact.
    for offset in range(0,40,4):scale_word(data,offset,exponent)
    for i in range(nv):
        for offset in (0,4,8):scale_word(data,80+i*64+offset,exponent)
    for i in range(nsv):
        for offset in (0,4,8):scale_word(data,shadow+i*16+offset,exponent)
    parts[at]=bytes(data)
    return parts


def _scale_hull_parts(bundle,resource,exponent):
    h=inspect_hull(bundle,resource)
    data=bytearray(h.parts[3])
    for i in range(len(h.points)):
        for off in (0,4,8):scale_word(data,16*i+off,exponent)
    return [*h.parts[:3],bytes(data)]


def _parts_for(bundle,resource,exponent):
    if exponent not in (-1,1):raise ValueError("Scale exponent must be -1 or 1")
    if resource.typ==4:return _scale_render_parts(bundle,resource,exponent)
    if resource.typ==5:return _scale_hull_parts(bundle,resource,exponent)
    raise ValueError("Unsupported resource type")


def scale_archive(raw,indices,exponent):
    b=verify_bundle(raw)
    if not indices or len(set(indices))!=len(indices) or any(type(i)!=int or not 0<=i<len(b.resources) for i in indices):
        raise ValueError("Invalid resource selection")
    edits={i:_parts_for(b,b.resources[i],exponent) for i in indices}
    candidate=rebuild_canonical(raw,edits)
    after=verify_bundle(candidate)
    if len(candidate)!=len(raw) or len(after.resources)!=len(b.resources):
        raise ValueError("Uniform scale changed archive geometry")
    inverse={}
    for a,c in zip(b.resources,after.resources):
        if (a.name,a.typ,a.index,a.offset,a.size,a.part_count)!=(c.name,c.typ,c.index,c.offset,c.size,c.part_count):
            raise ValueError("Resource identity or extent changed")
        if a.index not in edits:
            if b.raw(a)!=after.raw(c):raise ValueError("Unrelated resource changed")
            continue
        if list(after.parts(c))!=edits[a.index]:raise ValueError("Scaled resource differs from plan")
        inverse[a.index]=_parts_for(after,c,-exponent)
        if inverse[a.index]!=list(b.parts(a)):
            raise ValueError("Scaled resource inverse differs from original")
    if rebuild_canonical(candidate,inverse)!=raw:
        raise ValueError("Inverse archive reconstruction differs")
    return candidate


def collect(zip_path,pin,name):
    if not name or len(name)>96 or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*",name):
        raise ValueError("Invalid existing mesh base name")
    _zip_pin(zip_path,pin)
    actual=_actual_member_names(zip_path)
    selected=[];seen=set();total=0;meshes=hulls=0;groups=set()
    hull_pattern=re.compile(re.escape(name.casefold())+r"--(0|[1-9][0-9]{0,3})$")
    for path,raw in members(zip_path,".ibd",MAX_BUNDLE_BYTES):
        b=verify_bundle(raw)
        indices=[];names=set()
        for r in b.resources:
            key=r.name.casefold()
            match=hull_pattern.fullmatch(key) if r.typ==5 else None
            if not (r.typ==4 and key==name.casefold()) and match is None:continue
            if (r.typ,key) in names:raise ValueError("Ambiguous resource copy within bundle")
            names.add((r.typ,key));indices.append(r.index)
            if r.typ==4:meshes+=1
            else:hulls+=1;groups.add(int(match[1]))
        if indices:
            filename=PurePosixPath(actual[path]).name
            _portable_parts((filename,))
            if filename.casefold() in seen:raise ValueError("Ambiguous destination filename")
            seen.add(filename.casefold());total+=len(raw)
            if total>MAX_SELECTED_BYTES:raise ValueError("Selected corpus exceeds memory limit")
            selected.append((filename,raw,indices))
    if not meshes or not hulls or groups!=set(range(max(groups)+1)):
        raise ValueError("Expected render copies and contiguous named hull group")
    _zip_pin(zip_path,pin)
    return selected,meshes,hulls


def prepare(zip_path,pin,name,exponent,expected_meshes,expected_hulls,output):
    if output.is_symlink() or output.exists():raise ValueError("Output must be a new isolated directory")
    output=output.resolve()
    if output.exists():raise ValueError("Output must be a new isolated directory")
    selected,meshes,hulls=collect(zip_path,pin,name)
    if (meshes,hulls)!=(expected_meshes,expected_hulls):
        raise ValueError("Resource counts differ from explicit expected counts")
    candidates=[(filename,raw,scale_archive(raw,indices,exponent)) for filename,raw,indices in selected]
    _zip_pin(zip_path,pin)
    output.mkdir(parents=True,exist_ok=False)
    try:
        maps=output/"Maps";maps.mkdir()
        receipt={"schema":"DX2-CoordinatedScale-v1","mesh_name":name,
                 "source_zip_sha256":pin,"scale":math.ldexp(1.,exponent),
                 "render_records":meshes,"hull_records":hulls,"files":[],
                 "inverse_byte_identical":True,"runtime_verified":False,
                 "physics_binding_verified":False,"mass_inertia_updated":False,
                 "source_modified":False,"game_installation_modified":False}
        for filename,raw,data in candidates:
            path=maps/filename
            with path.open("xb") as stream:stream.write(data)
            if read_bounded(path)!=data:raise ValueError("Candidate write verification failed")
            receipt["files"].append({"relative_path":"Maps/"+filename,
                                     "source_sha256":sha256(raw),"candidate_sha256":sha256(data)})
        with (output/"trial.json").open("x",encoding="utf-8") as stream:
            json.dump(receipt,stream,indent=2,sort_keys=True)
        _zip_pin(zip_path,pin)
    except Exception:
        shutil.rmtree(output)
        raise
    return receipt


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip",required=True,type=Path)
    p.add_argument("--source-sha256",required=True)
    p.add_argument("--mesh",required=True)
    p.add_argument("--exponent",required=True,type=int,choices=(-1,1))
    p.add_argument("--expected-meshes",required=True,type=int)
    p.add_argument("--expected-hulls",required=True,type=int)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args(argv)
    try:
        report=prepare(a.source_zip,a.source_sha256,a.mesh,a.exponent,a.expected_meshes,a.expected_hulls,a.output)
        print(json.dumps(report,sort_keys=True,indent=2));return 0
    except (OSError,ValueError,IndexError,OverflowError,struct.error) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}));return 2


if __name__=="__main__":raise SystemExit(main())
