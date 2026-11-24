#!/usr/bin/env python3
"""Original polygon primary UV basis and packed tangent-like word evidence.

This is read-only. A direction match is not an exact packed tangent encoder
or proof of the fourth-byte/final-word engine semantics.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

from experimental_polygon_uv import _read_context, MAX_GMP
import inspect_level_world_model as world

SCHEMA="DX2SDK-original-polygon-primary-UV-basis-v1"
UV_PREVIEW_TOL=.0001
POSITION_TOL=.15
MAX_FACE_VERTICES=64


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def sub(a,b):
    return tuple(x-y for x,y in zip(a,b))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def unit(a):
    length=math.sqrt(dot(a,a))
    return tuple(x/length for x in a) if length>1e-10 else None


def _finite_rows(rows,width):
    return all(len(v)==width and all(type(x) in (int,float) and
               math.isfinite(x) and abs(x)<1e8 for x in v) for v in rows)


def fit_affine_uv(xyz,uv):
    """Fit the actual source material patch using a well-conditioned triangle.

    Return an affine world-space projection and max residuals at all original
    vertices. A nearly collinear or malformed face is refused. The fit may be
    used only with the caller's explicit residual and planarity gates.
    """
    n=len(xyz)
    if (not 3<=n<=MAX_FACE_VERTICES or len(uv)!=n or not _finite_rows(xyz,3)
            or not _finite_rows(uv,2)):
        raise ValueError("Malformed source polygon XYZ/UV inventory")
    p,q=max(((a,b) for a in range(n) for b in range(a+1,n)),
            key=lambda ab:math.dist(xyz[ab[0]],xyz[ab[1]]))
    origin=xyz[p]
    u=sub(xyz[q],origin)
    r=max(range(n),key=lambda i:dot(cross(u,sub(xyz[i],origin)),
                                  cross(u,sub(xyz[i],origin))))
    v=sub(xyz[r],origin)
    uu,uvdot,vv=dot(u,u),dot(u,v),dot(v,v)
    den=uu*vv-uvdot*uvdot
    if den<=1e-10 or den<=1e-14*uu*vv:
        raise ValueError("Degenerate source polygon UV basis")
    uv0=uv[p]
    du,dv=sub(uv[q],uv0),sub(uv[r],uv0)
    grads=[]
    for j in range(2):
        a=(du[j]*vv-dv[j]*uvdot)/den
        b=(dv[j]*uu-du[j]*uvdot)/den
        grads.append(tuple(a*x+b*y for x,y in zip(u,v)))
    plane_normal=unit(cross(u,v))
    if plane_normal is None:
        raise ValueError("Degenerate source polygon plane")
    det=du[0]*dv[1]-du[1]*dv[0]
    tangent=unit(tuple((dv[1]*x-du[1]*y)/det for x,y in zip(u,v))) if abs(det)>1e-10 else None
    fit={"origin":origin,"uv_origin":uv0,"gradients":tuple(grads),
         "normal":plane_normal,"tangent_direction":tangent}
    fit["max_uv_error"]=max(abs(a-b) for x,t in zip(xyz,uv)
                            for a,b in zip(evaluate_uv(fit,x),t))
    fit["max_plane_error"]=max(abs(dot(sub(x,origin),plane_normal)) for x in xyz)
    return fit


def evaluate_uv(fit,xyz):
    if not _finite_rows([xyz],3):
        raise ValueError("Invalid texture projection position")
    d=sub(xyz,fit["origin"])
    uv=tuple(o+dot(g,d) for o,g in zip(fit["uv_origin"],fit["gradients"]))
    if not _finite_rows([uv],2):
        raise ValueError("Nonfinite projected primary UV")
    return uv


def preview_uv(fit,source_xyz,source_uv,position):
    """Preserve source pairs at surviving corners, interpolate only on proof."""
    for xyz,uv in zip(source_xyz,source_uv):
        if math.dist(xyz,position)<=1e-7:
            return tuple(uv),"original"
    if (fit["max_uv_error"]>UV_PREVIEW_TOL or fit["max_plane_error"]>POSITION_TOL
            or abs(dot(sub(position,fit["origin"]),fit["normal"]))>POSITION_TOL):
        raise ValueError("Unverified affine UV interpolation")
    return evaluate_uv(fit,position),"affine"


def decode_tangent_like(raw):
    if type(raw) is not bytes or len(raw)!=8:
        raise ValueError("Expected two original packed words")
    return tuple((raw[i]-127.5)/127.5 for i in (2,1,0)),raw[3],raw[4:]==b"\xff"*4


def inspect_polygon_uv(level,blocks,polygons,links):
    if len(polygons)!=len(links):
        raise ValueError("Polygon UV crosswalk length mismatch")
    counts=Counter()
    max_uv_error=0.
    for poly,link in zip(polygons,links):
        vs=poly["vertices"]
        xyz=[v[:3] for v in vs]
        uv=[v[6:8] for v in vs]
        if (poly["polygon"]!=link["polygon"] or len(vs)!=link["packed_vertex_count"]
                or not 0<=link["packed_block"]<len(blocks)):
            raise ValueError("Polygon UV crosswalk identity mismatch")
        block=blocks[link["packed_block"]]
        start=link["packed_vertex_start"]
        if not 0<=start<=len(block["vertices"])-len(vs):
            raise ValueError("Polygon UV packed vertex range mismatch")
        counts["source_faces"]+=1
        try:
            fit=fit_affine_uv(xyz,uv)
        except ValueError:
            counts["source_faces_uv_fit_refused"]+=1
            fit=None
        if fit:
            err=fit["max_uv_error"]
            max_uv_error=max(max_uv_error,err)
            counts["source_faces_uv_fit"]+=1
            counts["source_faces_uv_within_1e6"]+=int(err<=1e-6)
            counts["source_faces_uv_within_1e5"]+=int(err<=1e-5)
            counts["source_faces_uv_within_1e4"]+=int(err<=1e-4)
            counts["source_faces_uv_within_1e3"]+=int(err<=1e-3)
            counts["source_faces_uv_within_001"]+=int(err<=.01)
            counts["source_faces_basis_planar_015"]+=int(fit["max_plane_error"]<=POSITION_TOL)
        packed_words=[]
        for i,v in enumerate(vs):
            at=block["offset"]+80+32*(start+i)
            if not 0<=at<=block["end"]-32 or at+32>len(level):
                raise ValueError("Packed UV vector offset outside source block")
            if struct.unpack_from("<3f",level,at)!=v[:3]:
                raise ValueError("Source expanded/packed position mismatch")
            raw=level[at+24:at+32]
            direction,alpha,white=decode_tangent_like(raw)
            normal=unit(v[3:6])
            if normal is None:
                raise ValueError("Degenerate source polygon normal")
            counts["packed_vertices"]+=1
            counts["packed_final_word_all_ff"]+=int(white)
            counts["packed_vector_fourth_byte_ff"]+=int(alpha==255)
            counts["packed_vector_unit_within_02"]+=int(abs(math.sqrt(dot(direction,direction))-1)<.02)
            counts["packed_vector_normal_orthogonal_02"]+=int(abs(dot(direction,normal))<.02)
            if fit and fit["tangent_direction"] is not None:
                d=dot(direction,fit["tangent_direction"])
                counts["packed_texture_tangent_direction_available"]+=1
                counts["packed_texture_tangent_dot_above_098"]+=int(d>.98)
                counts["packed_texture_tangent_dot_below_minus_098"]+=int(d<-.98)
            packed_words.append(raw[:4])
        counts["faces_constant_packed_vector"]+=int(len(set(packed_words))==1)
    return {"counts":dict(counts),"max_source_uv_fit_error":max_uv_error,
            "packed_trailing_words_are_secondary_float_uv":False,
            "exact_native_tangent_encoder_verified":False}


def audit_map(path):
    path=Path(path)
    if (path.suffix.casefold()!=".gmp" or not path.is_file() or path.is_symlink()
            or path.stat().st_size>MAX_GMP):
        raise ValueError("Expected bounded original user-owned GMP")
    raw=path.read_bytes()
    pin=hashlib.sha256(raw).hexdigest()
    pkg,exp,level,model,blocks,polys,links,collision,inventory,end=_read_context(path,raw)
    result=inspect_polygon_uv(level,blocks,polys,links)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError("Original GMP changed during UV audit")
    return {"source_map":path.name,"source_sha256":pin,**result}


def audit_maps(paths):
    if not 1<=len(paths)<=world.MAX_MAPS or len({Path(p).resolve() for p in paths})!=len(paths):
        raise ValueError("Expected 1..64 distinct original maps")
    rows=[audit_map(p) for p in paths]
    counts=Counter()
    for row in rows:
        counts.update(row["counts"])
    return {"schema":SCHEMA,"map_count":len(rows),"summary":dict(counts),
            "max_source_uv_fit_error":max(r["max_source_uv_fit_error"] for r in rows),
            "packed_trailing_words_are_secondary_float_uv":False,
            "exact_native_tangent_encoder_verified":False,"source_files_modified":False,
            "native_geometry_writer_enabled":False,"retail_runtime_verified":False,"maps":rows}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",nargs="+",type=Path)
    p.add_argument("--report",type=Path)
    a=p.parse_args(argv)
    try:
        result=audit_maps(a.maps)
        if a.report:
            world.write_report(result,a.report,a.maps)
        print(json.dumps({k:v for k,v in result.items() if k!="maps"},indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,KeyError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
