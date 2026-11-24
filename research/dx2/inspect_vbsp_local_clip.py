#!/usr/bin/env python3
"""Read-only VBSP portal reconstruction and localized face clipping.

Reconstruct a convex portal from the intersection of its two leaf paths.
A source portal is eligible for a hypothetical offset only if the original
boundary and area are reproduced, every edge has a unique source constraint,
and the source polygon is convex. Never synthesize an unverified opening.
Face clipping is a preview, not a native CSG or visibility compiler.
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
from inspect_level_expanded_polygons import validate_counted_render_array
from inspect_level_prefix_graph import parse_prefix_graph
from inspect_level_spatial_vbsp import (
    parse_spatial_tail, validate_leaf_render_ownership, locate_point,
)
from inspect_vbsp_plane_dependencies import leaf_paths, NORMAL_TOL
from inspect_level_polygon_uv_basis import fit_affine_uv,preview_uv,UV_PREVIEW_TOL,POSITION_TOL
from inspect_vbsp_preview_seams import (source_seam_inventory,inspect_preview_seams,
    attach_original_triangle_provenance)
import inspect_level_world_model as world

SCHEMA = "DX2SDK-VBSP-portal-reconstruction-local-clip-v1"
SOURCE_TOL = .15
PARALLEL_TOL = .002
CLIP_EPS = 1e-7
AREA_REL_TOL = .001
AREA_ABS_TOL = .01
MAX_LOOP = 512
MAX_DELTA = 128.
MAX_CONSTRAINT_TESTS = 4000000


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def unit(v):
    length=math.sqrt(dot(v,v))
    if not math.isfinite(length) or length<1e-10:
        raise ValueError("Degenerate plane basis")
    return tuple(x/length for x in v)


def plane_basis(plane):
    n=plane[:3]
    if len(plane)!=4 or not all(math.isfinite(x) for x in plane) or abs(dot(n,n)-1)>.002:
        raise ValueError("Invalid unit source plane")
    origin=tuple(-plane[3]*x/dot(n,n) for x in n)
    axis=min(range(3),key=lambda i:abs(n[i]))
    u=unit(cross(n,tuple(float(i==axis) for i in range(3))))
    v=unit(cross(n,u))
    return origin,u,v


def project(v,basis):
    origin,u,w=basis
    d=tuple(x-y for x,y in zip(v,origin))
    return dot(d,u),dot(d,w)


def lift(p,basis):
    origin,u,v=basis
    return tuple(x+p[0]*a+p[1]*b for x,a,b in zip(origin,u,v))


def signed_area(loop):
    if len(loop)<3:
        return 0.
    # Relative coordinates reduce cancellation on large source maps.
    x0,y0=loop[0]
    return .5*sum((a[0]-x0)*(b[1]-y0)-(a[1]-y0)*(b[0]-x0)
                  for a,b in zip(loop,loop[1:]+loop[:1]))


def convex(loop):
    if not 3<=len(loop)<=MAX_LOOP or len(set(loop))!=len(loop):
        return False
    area=signed_area(loop)
    if abs(area)<=CLIP_EPS:
        return False
    sign=1 if area>0 else -1
    for a,b in zip(loop,loop[1:]+loop[:1]):
        length=math.dist(a,b)
        if length<=CLIP_EPS:
            return False
        if any(sign*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
               < -CLIP_EPS*length for p in loop):
            return False
    return True


def clean(loop):
    out=[]
    for v in loop:
        if not out or math.dist(out[-1],v)>CLIP_EPS:
            out.append(v)
    if len(out)>1 and math.dist(out[0],out[-1])<=CLIP_EPS:
        out.pop()
    if len(out)>MAX_LOOP:
        raise ValueError("Clipped polygon exceeds vertex budget")
    return out if len(out)>=3 and abs(signed_area(out))>CLIP_EPS else []


def clip_halfspace(loop,a,b,c):
    """Ordered convex loop intersected with a*x+b*y+c >= 0."""
    if not loop:
        return []
    out=[]
    for p,q in zip(loop[-1:]+loop[:-1],loop):
        dp=a*p[0]+b*p[1]+c
        dq=a*q[0]+b*q[1]+c
        ip,iq=dp>=-CLIP_EPS,dq>=-CLIP_EPS
        if ip!=iq:
            t=max(0.,min(1.,dp/(dp-dq)))
            out.append(tuple(x+t*(y-x) for x,y in zip(p,q)))
        if iq:
            out.append(q)
    return clean(out)


def clip_paths(loop,basis,planes,constraints,*,skip=None):
    origin,u,v=basis
    for i,side in sorted(set(constraints)):
        if i==skip:
            continue
        n=planes[i][:3]
        sign=1 if side==0 else -1
        a,b,c=sign*dot(n,u),sign*dot(n,v),sign*(dot(n,origin)+planes[i][3])
        if math.hypot(a,b)<1e-8:
            if c<-PARALLEL_TOL:
                return []
            continue
        loop=clip_halfspace(loop,a,b,c)
        if not loop:
            break
    return loop


def segment_distance(p,a,b):
    d=tuple(y-x for x,y in zip(a,b))
    den=dot(d,d)
    t=max(0.,min(1.,dot(tuple(x-y for x,y in zip(p,a)),d)/den)) if den else 0.
    return math.dist(p,tuple(x+t*y for x,y in zip(a,d)))


def boundary_error(a,b):
    if not a or not b:
        raise ValueError("Empty boundary comparison")
    return max(max(min(segment_distance(p,x,y) for x,y in zip(dst,dst[1:]+dst[:1]))
                   for p in src) for src,dst in ((a,b),(b,a)))


def compare_loops(source,candidate):
    if not candidate:
        return "empty",None
    err=boundary_error(source,candidate)
    area=abs(signed_area(source))
    area_error=abs(abs(signed_area(candidate))-area)
    if err<=SOURCE_TOL and area_error<=max(AREA_ABS_TOL,AREA_REL_TOL*area):
        return "match",err
    return "different",err


def portal_geometry(planes,paths,owners,pi,extent):
    basis=plane_basis(planes[pi])
    loop=[(-extent,-extent),(extent,-extent),(extent,extent),(-extent,extent)]
    constraints=tuple(sorted(set(k for i in owners for k in paths[i])))
    loop=clip_paths(loop,basis,planes,constraints,skip=pi)
    if loop and any(max(abs(x) for x in p)>=extent-1 for p in loop):
        return [],basis,"seed_boundary"
    return loop,basis,"bounded"


def plane_ref(value):
    return value if value>=0 else ~value


def edge_dependencies(xyz,planes,constraints,pi):
    """Find oriented owner-path planes supporting each original edge."""
    normal=planes[pi][:3]
    result=[]
    for a,b in zip(xyz,xyz[1:]+xyz[:1]):
        candidates=set()
        for j,side in constraints:
            p=planes[j]
            if j==pi or abs(dot(p[:3],normal))>.999999:
                continue
            if max(abs(dot(v,p[:3])+p[3]) for v in (a,b))>SOURCE_TOL:
                continue
            sign=1 if side==0 else -1
            if min(sign*(dot(v,p[:3])+p[3]) for v in xyz)<-SOURCE_TOL:
                continue
            candidates.add(j)
        result.append(tuple(sorted(candidates)))
    return result


def _portal_vertices(tail):
    n=tail["counts"]["vbsp_portal_vertices"]
    return [v for _,v in tail["coordinates"][-n:]] if n else []


def _path_violation(xyz,planes,constraints):
    return any(min((1 if side==0 else -1)*(dot(v,planes[i][:3])+planes[i][3])
                   for v in xyz)<-SOURCE_TOL for i,side in constraints)


def _supporting_candidates(xyz,normal,planes,path):
    return sorted(set(i for i,side in path
        if max(abs(dot(v,planes[i][:3])+planes[i][3]) for v in xyz)<=SOURCE_TOL
        and math.dist(normal,tuple((1 if side==0 else -1)*x for x in planes[i][:3]))
        <=NORMAL_TOL))


def _surface_basis(xyz,normal):
    n=unit(normal)
    return plane_basis((*n,-dot(n,xyz[0])))


def triangulate_convex(loop):
    """Preview-only triangulation preserving boundary corners and winding."""
    if not convex(loop):
        raise ValueError("Cannot triangulate invalid convex preview")
    remaining=list(range(len(loop)))
    area=signed_area(loop)
    sign=1 if area>0 else -1
    triangles=[]
    while len(remaining)>3:
        found=False
        for pos,i in enumerate(remaining):
            a,b,c=remaining[pos-1],i,remaining[(pos+1)%len(remaining)]
            ear=sign*signed_area([loop[a],loop[b],loop[c]])
            if ear<=CLIP_EPS:
                continue
            rest=remaining[:pos]+remaining[pos+1:]
            if sign*signed_area([loop[j] for j in rest])<=CLIP_EPS:
                continue
            triangles.append((a,b,c))
            remaining=rest
            found=True
            break
        if not found:
            raise ValueError("Convex preview triangulation stalled")
    triangles.append(tuple(remaining))
    if (len(triangles)!=len(loop)-2 or set(j for t in triangles for j in t)!=set(range(len(loop)))
            or any(sign*signed_area([loop[j] for j in t])<=CLIP_EPS for t in triangles)
            or not math.isclose(sum(signed_area([loop[j] for j in t]) for t in triangles),
                                area,rel_tol=1e-7,abs_tol=1e-6)):
        raise ValueError("Preview triangulation area or winding mismatch")
    return triangles


def face_preview(poly,owner,original_basis,new_basis,candidate):
    """Create private geometry only; no native tangent, index or material writer."""
    vs=poly["vertices"]
    xyz=[v[:3] for v in vs]
    uv=[v[6:8] for v in vs]
    fit=fit_affine_uv(xyz,uv)
    if (fit["max_uv_error"]>UV_PREVIEW_TOL or fit["max_plane_error"]>POSITION_TOL
            or any(math.dist(v[3:6],vs[0][3:6])>NORMAL_TOL for v in vs)):
        raise ValueError("Source material patch does not pass texture basis gate")
    result=[]
    source_projected=[project(v,original_basis) for v in xyz]
    shift=tuple(a-b for a,b in zip(new_basis[0],original_basis[0]))
    used=set()
    for p in candidate:
        matches=[j for j,v in enumerate(source_projected) if math.dist(v,p)<=CLIP_EPS]
        if len(matches)>1 or (matches and matches[0] in used):
            raise ValueError("Ambiguous surviving source corner in clipped preview")
        if matches:
            j=matches[0]
            used.add(j)
            position=tuple(x+d for x,d in zip(xyz[j],shift)) if any(shift) else xyz[j]
            tex,method=tuple(uv[j]),"original"
        else:
            j=None
            source_position=lift(p,original_basis)
            tex,method=preview_uv(fit,xyz,uv,source_position)
            if method!="affine":
                raise ValueError("Unresolved source corner association")
            position=lift(p,new_basis)
        result.append({"xyz":position,"primary_uv":tex,"uv_method":method,"source_corner":j})
    return {"source_polygon":poly["polygon"],"owner_leaf":owner,
            "material":poly.get("material"),"normal":vs[0][3:6],
            "source_vertex_count":len(vs),"vertices":result,
            "preview_triangles":triangulate_convex(candidate),
            "texture_mapping":"surface-locked-affine",
            "native_write_allowed":False}


def inspect_local_edit(tail,polygons,owners,*,plane_index=None,delta_d=None,include_preview=False):
    """Audit all original portals and faces; optionally preview one plane offset.

    Geometry is returned only for explicit private previews. Existing face patches may be
    translated or clipped, but never extended into newly exposed regions.
    Portal candidates are accepted only after reproducing the source portal
    and checking original two-sided traversal for the modified tree.
    """
    planes=tail["planes"]
    paths=leaf_paths(tail["nodes"])
    if len(paths)!=len(tail["leaves"]) or len(owners)!=len(polygons):
        raise ValueError("Invalid original polygon leaf inventory")
    if (plane_index is None)!=(delta_d is None):
        raise ValueError("Plane index and D offset must be specified together")
    if plane_index is not None and (type(plane_index) is not int or not 0<=plane_index<len(planes)
            or type(delta_d) not in (int,float) or not math.isfinite(delta_d)
            or not 0<abs(delta_d)<=MAX_DELTA):
        raise ValueError("Invalid hypothetical VBSP plane offset")
    if include_preview and plane_index is None:
        raise ValueError("Private geometry preview requires a hypothetical plane offset")
    preview={"faces":[],"portals":[]}
    states={}
    seam_inventory,source_points=source_seam_inventory(polygons,owners)
    changed=list(planes)
    if plane_index is not None:
        p=planes[plane_index]
        changed[plane_index]=(*p[:3],p[3]+delta_d)
    extent=4*max(abs(x) for row in tail["leaves"] for x in row[5:11])+1024
    vertices=_portal_vertices(tail)
    counts=Counter(seam_inventory)
    max_error=0.
    tested_constraints=0
    for portal_index,(a,b,c,d,ref,_) in enumerate(tail["portals"]):
        pi=plane_ref(ref)
        xyz=vertices[c:d]
        constraints=tuple(sorted(set(k for leaf in (a,b) for k in paths[leaf])))
        tested_constraints+=len(constraints)*len(xyz)
        if tested_constraints>MAX_CONSTRAINT_TESTS:
            raise ValueError("VBSP clipping constraint budget exceeded")
        basis=plane_basis(planes[pi])
        original=[project(v,basis) for v in xyz]
        edges=edge_dependencies(xyz,planes,constraints,pi)
        counts["portal_records"]+=1
        counts["portal_edges"]+=len(edges)
        for candidates in edges:
            counts["portal_edge_path_"+("none" if not candidates else
                   "unique" if len(candidates)==1 else "multiple")]+=1
        counts["portal_all_edges_supported"]+=int(all(edges))
        unique_edges=all(len(e)==1 for e in edges)
        counts["portal_all_edges_unique"]+=int(unique_edges)
        valid_convex=convex(original)
        counts["portal_original_convex"]+=int(valid_convex)
        violation=_path_violation(xyz,planes,constraints)
        counts["portal_original_path_violation"]+=int(violation)
        result,_,bound=portal_geometry(planes,paths,(a,b),pi,extent)
        status,err=compare_loops(original,result)
        if bound=="seed_boundary":
            status=bound
        counts["portal_rebuild_"+status]+=1
        if err is not None:
            max_error=max(max_error,err)
            counts["portal_rebuild_boundary_within_015"]+=int(err<=SOURCE_TOL)
            counts["portal_rebuild_same_vertex_count"]+=int(len(result)==len(original))
        eligible=status=="match" and unique_edges and valid_convex and not violation and convex(result)
        counts["portal_rebuild_eligible"]+=int(eligible)
        if plane_index is None or (pi!=plane_index and not any(i==plane_index for i,_ in constraints)):
            continue
        counts["affected_portals"]+=1
        counts["affected_portals_direct_plane"]+=int(pi==plane_index)
        if not eligible:
            counts["affected_portals_source_gate_refused"]+=1
            continue
        new,new_basis,new_bound=portal_geometry(changed,paths,(a,b),pi,extent)
        if not new or new_bound!="bounded" or not convex(new):
            counts["affected_portals_topology_or_bound_refused"]+=1
            continue
        new_xyz=[lift(v,new_basis) for v in new]
        centroid=tuple(sum(v[j] for v in new_xyz)/len(new_xyz) for j in range(3))
        normal=changed[pi][:3]
        probes=[tuple(x+sign*.1*y for x,y in zip(centroid,normal)) for sign in (1,-1)]
        if set(locate_point(tail["nodes"],changed,v) for v in probes)!={a,b}:
            counts["affected_portals_side_probe_refused"]+=1
            continue
        counts["affected_portals_preview_passed"]+=1
        counts["affected_portals_preview_vertex_count_changed"]+=int(len(new)!=len(result))
        if include_preview:
            if signed_area(new)*signed_area(original)<0:
                new=list(reversed(new))
            preview["portals"].append({"source_portal":portal_index,"owner_leaves":[a,b],
                "source_plane":pi,"vertices_xyz":[lift(v,new_basis) for v in new],
                "preview_triangles":triangulate_convex(new),"native_write_allowed":False})
    for i,poly in enumerate(polygons):
        if poly["polygon"]!=i or owners[i] not in paths:
            raise ValueError("Invalid expanded polygon ordinal or leaf")
        vs=poly["vertices"]
        xyz=[v[:3] for v in vs]
        if len(xyz)<3 or not all(len(v)==3 and all(math.isfinite(x) for x in v) for v in xyz):
            raise ValueError("Malformed expanded source polygon")
        path=paths[owners[i]]
        tested_constraints+=len(path)*len(xyz)
        if tested_constraints>MAX_CONSTRAINT_TESTS:
            raise ValueError("VBSP clipping constraint budget exceeded")
        normal=vs[0][3:6]
        basis=_surface_basis(xyz,normal)
        original=[project(v,basis) for v in xyz]
        planar=max(abs(dot(unit(normal),tuple(x-y for x,y in zip(v,xyz[0])))) for v in xyz)<=SOURCE_TOL
        valid=planar and convex(original)
        counts["face_records"]+=1
        counts["face_source_planar_convex"]+=int(valid)
        baseline=clip_paths(original,basis,planes,path) if valid else []
        status,_=compare_loops(original,baseline) if valid else ("nonconvex_or_nonplanar",None)
        counts["face_source_clip_"+status]+=1
        if plane_index is None or not any(j==plane_index for j,_ in path):
            continue
        counts["affected_faces"]+=1
        states[i]="source_gate_refused"
        if status!="match" or _path_violation(xyz,planes,path):
            counts["affected_faces_source_gate_refused"]+=1
            continue
        supporting=_supporting_candidates(xyz,normal,planes,path)
        if plane_index in supporting and len(supporting)!=1:
            counts["affected_faces_ambiguous_support_refused"]+=1
            states[i]="ambiguous_support_refused"
            continue
        if supporting==[plane_index]:
            n=planes[plane_index][:3]
            shift=tuple(-delta_d*x/dot(n,n) for x in n)
            origin,u,v=basis
            new_basis=(tuple(x+y for x,y in zip(origin,shift)),u,v)
            counts["affected_faces_support_translated"]+=1
        else:
            new_basis=basis
        # A material patch is only intersected, never extended; a real CSG
        # builder must generate newly exposed surface and texture data.
        candidate=clip_paths(original,new_basis,changed,path)
        if not candidate:
            counts["affected_faces_removed_preview"]+=1
            states[i]="removed"
            continue
        if not convex(candidate):
            counts["affected_faces_invalid_preview_refused"]+=1
            states[i]="invalid_preview_refused"
            continue
        counts["affected_faces_preview_passed"]+=1
        counts["affected_faces_preview_vertex_count_changed"]+=int(len(candidate)!=len(original))
        counts["affected_faces_preview_area_reduced"]+=int(
            abs(signed_area(candidate))<abs(signed_area(original))-AREA_ABS_TOL)
        if include_preview:
            try:
                entry=face_preview(poly,owners[i],basis,new_basis,candidate)
                if _path_violation([v["xyz"] for v in entry["vertices"]],changed,path):
                    raise ValueError("Preserved source corner violates edited leaf path")
            except ValueError:
                counts["affected_faces_textured_preview_refused"]+=1
                states[i]="textured_preview_refused"
            else:
                states[i]="preview_passed"
                preview["faces"].append(entry)
                counts["affected_faces_textured_preview_passed"]+=1
                counts["affected_faces_preview_affine_uv_vertices"]+=sum(
                    v["uv_method"]=="affine" for v in entry["vertices"])
    if include_preview:
        seam_counts,issues=inspect_preview_seams(polygons,owners,source_points,preview["faces"],states)
        counts.update(seam_counts)
        preview["face_states"]=[{"source_polygon":i,"owner_leaf":owners[i],"state":state}
                                for i,state in sorted(states.items())]
        preview["source_seam_issues"]=issues
        preview["seam_tolerance_source_units"]=.002
        preview["watertightness_verified"]=False
    return {"counts":dict(counts),"max_portal_boundary_error":max_error,
            "hypothetical_plane_index":plane_index,"hypothetical_delta_d":delta_d,
            "newly_exposed_surface_generated":False,"native_geometry_writer_enabled":False,
            **({"private_preview_geometry":preview} if include_preview else {})}


def audit_map(path,*,plane_index=None,delta_d=None,include_preview=False):
    path=Path(path)
    if (path.suffix.casefold()!=".gmp" or not path.is_file() or path.is_symlink()
            or path.stat().st_size>MAX_GMP):
        raise ValueError("Expected bounded original user-owned GMP")
    raw=path.read_bytes()
    pin=hashlib.sha256(raw).hexdigest()
    pkg,exp,level,model,blocks,polys,links,collision,inventory,end=_read_context(path,raw)
    ref=world._parse_world_model(pkg)
    cursor=world.Cursor(level,ref["level_model_ref_offset_in_level"])
    if cursor.ci()!=ref["world_model_export_ref"]:
        raise ValueError("Original Level Model reference changed")
    frame=validate_counted_render_array(level,blocks,collision)
    stop=frame["render_block_count_offset"]
    graph=parse_prefix_graph(level,cursor.at,stop)
    tail=parse_spatial_tail(level,graph["graph_end"],stop)
    _,owners=validate_leaf_render_ownership(tail,polys,links,collision,frame)
    report=inspect_local_edit(tail,polys,owners,plane_index=plane_index,delta_d=delta_d,
                              include_preview=include_preview)
    if include_preview:
        report["counts"].update(attach_original_triangle_provenance(
            report["private_preview_geometry"],links,collision))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError("Original GMP changed during clipping audit")
    return {"source_map":path.name,"source_sha256":pin,**report}


def audit_maps(paths,*,plane_index=None,delta_d=None,include_preview=False):
    if not 1<=len(paths)<=world.MAX_MAPS or len({Path(p).resolve() for p in paths})!=len(paths):
        raise ValueError("Expected 1..64 distinct original maps")
    if (plane_index is not None or delta_d is not None) and len(paths)!=1:
        raise ValueError("A hypothetical offset requires exactly one original map")
    if include_preview and (len(paths)!=1 or plane_index is None):
        raise ValueError("Private preview requires exactly one map and one plane offset")
    rows=[audit_map(p,plane_index=plane_index,delta_d=delta_d,include_preview=include_preview) for p in paths]
    counts=Counter()
    for row in rows:
        counts.update(row["counts"])
    return {"schema":SCHEMA,"map_count":len(rows),"summary":dict(counts),
            "max_portal_boundary_error":max(r["max_portal_boundary_error"] for r in rows),
            "hypothetical_plane_index":plane_index,"hypothetical_delta_d":delta_d,
            "source_files_modified":False,"gmp_output_enabled":False,
            "newly_exposed_surface_generated":False,"native_geometry_writer_enabled":False,
            "collision_rebuilt":False,"retail_runtime_verified":False,
            "private_preview_geometry_included":include_preview,"maps":rows}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",nargs="+",type=Path)
    p.add_argument("--plane",type=int)
    p.add_argument("--delta-d",type=float)
    p.add_argument("--report",type=Path)
    p.add_argument("--include-preview-geometry",action="store_true",help="Include private polygon/portal preview in fresh JSON report")
    a=p.parse_args(argv)
    try:
        if a.include_preview_geometry and not a.report:
            raise ValueError("Private preview geometry requires a fresh local report path")
        result=audit_maps(a.maps,plane_index=a.plane,delta_d=a.delta_d,
                          include_preview=a.include_preview_geometry)
        if a.report:
            world.write_report(result,a.report,a.maps)
        print(json.dumps({k:v for k,v in result.items() if k!="maps"},indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,IndexError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
