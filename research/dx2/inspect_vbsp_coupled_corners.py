#!/usr/bin/env python3
"""Read-only topology-preserving coupled corner motion for original DX2 faces.

Exact XYZ coincidence is a geometric hypothesis, not a native weld ID.
Solve all incident source support constraints simultaneously and refuse
inconsistent systems, invalid face geometry or changed leaf halfspaces.
This is not CSG, portal rebuilding, collision cooking or a GMP writer.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct

from experimental_polygon_uv import _read_context, MAX_GMP
from inspect_level_expanded_polygons import validate_counted_render_array
from inspect_level_prefix_graph import parse_prefix_graph
from inspect_level_spatial_vbsp import parse_spatial_tail, validate_leaf_render_ownership
from inspect_vbsp_plane_dependencies import leaf_paths
from inspect_vbsp_local_clip import (
    dot, cross, unit, convex, signed_area, project, _surface_basis,
    _supporting_candidates, _path_violation, SOURCE_TOL,
)
from inspect_level_polygon_uv_basis import fit_affine_uv, UV_PREVIEW_TOL
from inspect_vbsp_preview_seams import (
    source_seam_inventory, inspect_preview_seams, attach_original_triangle_provenance,
)
import inspect_level_world_model as world

SCHEMA = "DX2SDK-coupled-source-corner-motion-v1"
RANK_TOL = 1e-6
EQUATION_TOL = 1e-5
CONTACT_TOL = .002
MAX_DELTA = 16.
MAX_TESTS = 4000000


def solve_displacement(equations, limit):
    """Minimum norm displacement subject to n dot d = offset.

    Incremental orthogonalization keeps at most three independent rows.
    Reject inconsistent redundant rows and ill-conditioned large movement.
    """
    basis=[]
    d=(0.,0.,0.)
    for normal,rhs in equations:
        if (len(normal)!=3 or not all(math.isfinite(x) for x in (*normal,rhs))
                or abs(dot(normal,normal)-1)>.002):
            raise ValueError("Invalid displacement equation")
        v=tuple(normal)
        for q in basis:
            v=tuple(x-dot(v,q)*y for x,y in zip(v,q))
        length=math.sqrt(dot(v,v))
        residual=rhs-dot(normal,d)
        if length<=RANK_TOL:
            if abs(residual)>EQUATION_TOL:
                raise ValueError("Inconsistent incident plane constraints")
            continue
        q=tuple(x/length for x in v)
        d=tuple(x+residual/length*y for x,y in zip(d,q))
        basis.append(q)
    if (not all(math.isfinite(x) for x in d) or math.sqrt(dot(d,d))>limit
            or any(abs(dot(n,d)-rhs)>EQUATION_TOL for n,rhs in equations)):
        raise ValueError("Unstable or excessive coupled corner displacement")
    return d,len(basis)


def support_inventory(tail, polygons, owners, paths):
    counts=Counter()
    supports=[]
    tests=0
    for i,p in enumerate(polygons):
        if p["polygon"]!=i or owners[i] not in paths:
            raise ValueError("Invalid source polygon/owner identity")
        vs=p["vertices"]
        if len(vs)<3:
            raise ValueError("Invalid source face")
        xyz=[v[:3] for v in vs]
        tests+=len(xyz)*len(paths[owners[i]])
        if tests>MAX_TESTS:
            raise ValueError("Source support constraint budget exceeded")
        candidates=_supporting_candidates(xyz,vs[0][3:6],tail["planes"],paths[owners[i]])
        supports.append(candidates[0] if len(candidates)==1 else None)
        counts["support_"+("unique" if len(candidates)==1 else "none" if not candidates else "multiple")]+=1
    return supports,counts


def _contact(plane,v):
    return abs(dot(plane[:3],v)+plane[3])<=CONTACT_TOL


def _corner_constraints(v,refs,owners,supports,paths,planes,pi,delta):
    ids=set()
    for i,_ in refs:
        support=supports[i]
        if support is None:
            raise ValueError("Incident face lacks unique original support")
        ids.add(support)
        # Preserve actual incident path contacts, not every ancestor plane.
        ids.update(k for k,_ in paths[owners[i]] if _contact(planes[k],v))
    if pi not in ids:
        raise ValueError("Moving plane has no source corner contact")
    ordered=[pi]+sorted(ids-{pi})
    return [(planes[k][:3],-delta if k==pi else 0.) for k in ordered]


def _check_face(poly, positions, planes, path, support, pi, delta):
    vs=poly["vertices"]
    source=[v[:3] for v in vs]
    normal=unit(vs[0][3:6])
    basis=_surface_basis(source,normal)
    before=[project(v,basis) for v in source]
    after=[project(v,basis) for v in positions]
    if not convex(before) or not convex(after) or signed_area(before)*signed_area(after)<=0:
        raise ValueError("Original or moved face is nonconvex/degenerate/reversed")
    if _path_violation(positions,planes,path):
        raise ValueError("Moved face violates its original leaf path")
    p=planes[support]
    if any(abs(dot(p[:3],v)+p[3])>SOURCE_TOL for v in positions):
        raise ValueError("Moved face leaves its support plane")
    # Maintain original material projection; translate its origin with the
    # supporting plane only. Adjacent stationary faces stretch their UV.
    fit=fit_affine_uv(source,[v[6:8] for v in vs])
    if fit["max_uv_error"]>UV_PREVIEW_TOL or fit["max_plane_error"]>SOURCE_TOL:
        raise ValueError("Source face UV basis not verified")
    shift=tuple(-delta*x/dot(p[:3],p[:3]) for x in p[:3]) if support==pi else (0.,0.,0.)
    out=[]
    for j,(old,new) in enumerate(zip(source,positions)):
        change=tuple(b-a-s for a,b,s in zip(old,new,shift))
        uv=tuple(t+dot(g,change) for t,g in zip(vs[j][6:8],fit["gradients"]))
        if not all(math.isfinite(x) for x in uv):
            raise ValueError("Nonfinite coupled preview UV")
        out.append({"source_corner":j,"xyz":new,"primary_uv":uv})
    return out


def _check_original_triangles(poly,face,link,blocks):
    """Check the original indexed topology, not a substitute triangulation."""
    b=blocks[link["packed_block"]]
    start=link["packed_vertex_start"]
    source=[v[:3] for v in poly["vertices"]]
    target=[v["xyz"] for v in face]
    if link["packed_vertex_count"]!=len(source):
        raise ValueError("Original packed vertex inventory mismatch")
    for i,v in enumerate(source):
        if b["vertices"][start+i][0]!=v:
            raise ValueError("Original packed XYZ mismatch")
    n=unit(poly["vertices"][0][3:6])
    for bi,si,ti in link["triangle_locators"]:
        if bi!=link["packed_block"]:
            raise ValueError("Original triangle block mismatch")
        ids=[i-start for i in b["sections"][si]["indices"][3*ti:3*ti+3]]
        if len(ids)!=3 or any(not 0<=i<len(source) for i in ids):
            raise ValueError("Original triangle outside face vertex range")
        def area(v):
            a,c,e=[v[i] for i in ids]
            return dot(cross(tuple(y-x for x,y in zip(a,c)),tuple(y-x for x,y in zip(a,e))),n)
        old,new=area(source),area(target)
        if abs(old)<=1e-7 or abs(new)<=1e-7 or old*new<=0:
            raise ValueError("Original triangle degeneracy or winding changed")
    return len(link["triangle_locators"])


def coupled_preview(tail,polygons,owners,pi,delta,*,blocks=None,links=None,include_geometry=False):
    planes=tail["planes"]
    if (type(pi) is not int or not 0<=pi<len(planes) or type(delta) not in (int,float)
            or not math.isfinite(delta) or not 0<abs(delta)<=MAX_DELTA):
        raise ValueError("Expected valid plane and nonzero finite offset within +/-16")
    paths=leaf_paths(tail["nodes"])
    if len(paths)!=len(tail["leaves"]):
        raise ValueError("Incomplete leaf path inventory")
    inventory,points=source_seam_inventory(polygons,owners)
    supports,counts=support_inventory(tail,polygons,owners,paths)
    counts.update(inventory)
    changed=list(planes)
    changed[pi]=(*planes[pi][:3],planes[pi][3]+delta)
    # All corners of the selected supporting faces, plus original contacts
    # on affected leaf paths, become shared variables.
    active={}
    affected=set()
    for v,refs in points.items():
        if any(supports[i]==pi or (_contact(planes[pi],v) and
               any(k==pi for k,_ in paths[owners[i]])) for i,_ in refs):
            active[v]=refs
            affected.update(i for i,_ in refs)
    counts["active_corner_groups"]=len(active)
    counts["active_corner_occurrences"]=sum(map(len,active.values()))
    counts["coupled_affected_faces"]=len(affected)
    counts["coupled_supporting_faces"]=sum(s==pi for s in supports)
    moved={}
    refused={}
    for v,refs in active.items():
        try:
            eq=_corner_constraints(v,refs,owners,supports,paths,planes,pi,delta)
            d,rank=solve_displacement(eq,max(1.,8*abs(delta)))
            moved[v]=tuple(x+y for x,y in zip(v,d))
            counts["solved_rank_"+str(rank)]+=1
        except ValueError as exc:
            refused[v]=str(exc)
            counts["corner_constraints_refused"]+=1
    states={}
    faces=[]
    for i in sorted(affected):
        poly=polygons[i]
        source=[v[:3] for v in poly["vertices"]]
        try:
            if any(v in refused for v in source) or supports[i] is None:
                raise ValueError("Unresolved incident corner or face support")
            target=[moved.get(v,v) for v in source]
            vertices=_check_face(poly,target,changed,paths[owners[i]],supports[i],pi,delta)
            if blocks is not None:
                counts["original_triangles_winding_verified"]+=_check_original_triangles(
                    poly,vertices,links[i],blocks)
        except ValueError as exc:
            states[i]="coupled_face_refused"
            counts["coupled_faces_refused"]+=1
            continue
        states[i]="preview_passed"
        counts["coupled_faces_passed"]+=1
        counts["coupled_faces_with_moved_corners"]+=int(target!=source)
        faces.append({"source_polygon":i,"owner_leaf":owners[i],
                      "source_support_plane":supports[i],"material":poly.get("material"),
                      "vertices":vertices,"native_write_allowed":False})
    # A changed splitter can invalidate even an unmoved face if its path
    # crosses the displaced plane. Check the complete affected leaf domain.
    for i,poly in enumerate(polygons):
        if not any(k==pi for k,_ in paths[owners[i]]) or i in affected:
            continue
        xyz=[v[:3] for v in poly["vertices"]]
        counts["stationary_faces_in_changed_paths"]+=1
        if not _path_violation(xyz,planes,paths[owners[i]]) and _path_violation(xyz,changed,paths[owners[i]]):
            counts["stationary_new_leaf_violations"]+=1
    seam_counts,issues=inspect_preview_seams(polygons,owners,points,faces,states)
    counts.update(seam_counts)
    ready=bool(active) and not refused and not any(state!="preview_passed" for state in states.values()) and not issues and not counts["stationary_new_leaf_violations"]
    result={"counts":dict(counts),"plane_index":pi,"delta_d":delta,
            "coupled_corner_preview_passed":ready,
            "watertightness_verified":False,"native_geometry_writer_enabled":False,
            "portal_geometry_rebuilt":False,"collision_rebuilt":False}
    if include_geometry:
        result["private_preview_geometry"]={"faces":faces,
            "face_states":[{"source_polygon":i,"owner_leaf":owners[i],"state":s}
                           for i,s in sorted(states.items())],
            "source_seam_issues":issues}
    return result


def load_context(path,raw):
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
    return tail,polys,owners,blocks,links,collision


def select_plane(tail,polygons,owners):
    """Deterministic small source experiment; never select by edit outcome."""
    paths=leaf_paths(tail["nodes"])
    supports,_=support_inventory(tail,polygons,owners,paths)
    faces=Counter(s for s in supports if s is not None)
    paths_count=Counter(k for owner in owners for k in {k for k,_ in paths[owner]})
    portals=Counter(k for a,b,_,_,ref,_ in tail["portals"]
                    for k in ({j for leaf in (a,b) for j,_ in paths[leaf]}|
                              {ref if ref>=0 else ~ref}))
    candidates=[k for k in faces if portals[k] and paths_count[k]<200]
    if not candidates:
        candidates=list(faces)
    if not candidates:
        raise ValueError("No original support planes")
    return min(candidates,key=lambda k:(paths_count[k]+portals[k],-faces[k],k))


def audit_map(path,*,plane_index=None,delta_d=1.,include_geometry=False):
    path=Path(path)
    if (path.suffix.casefold()!=".gmp" or not path.is_file() or path.is_symlink()
            or path.stat().st_size>MAX_GMP):
        raise ValueError("Expected bounded original user-owned GMP")
    raw=path.read_bytes()
    pin=hashlib.sha256(raw).hexdigest()
    tail,polys,owners,blocks,links,collision=load_context(path,raw)
    pi=select_plane(tail,polys,owners) if plane_index is None else plane_index
    report=coupled_preview(tail,polys,owners,pi,delta_d,blocks=blocks,links=links,include_geometry=True)
    report["counts"].update(attach_original_triangle_provenance(report["private_preview_geometry"],links,collision))
    if not include_geometry:
        del report["private_preview_geometry"]
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError("Original GMP changed during coupled audit")
    return {"source_map":path.name,"source_sha256":pin,**report}


def audit_maps(paths,*,plane_index=None,delta_d=1.,include_geometry=False):
    if not 1<=len(paths)<=world.MAX_MAPS or len({Path(p).resolve() for p in paths})!=len(paths):
        raise ValueError("Expected 1..64 distinct original maps")
    if (plane_index is not None or include_geometry) and len(paths)!=1:
        raise ValueError("Explicit plane or private geometry requires one map")
    rows=[audit_map(p,plane_index=plane_index,delta_d=delta_d,include_geometry=include_geometry) for p in paths]
    counts=Counter()
    for row in rows:
        counts.update(row["counts"])
        counts["map_previews_passed"]+=int(row["coupled_corner_preview_passed"])
    return {"schema":SCHEMA,"map_count":len(rows),"summary":dict(counts),
            "source_files_modified":False,"native_geometry_writer_enabled":False,
            "retail_runtime_verified":False,"maps":rows}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",nargs="+",type=Path)
    p.add_argument("--plane",type=int)
    p.add_argument("--delta-d",type=float,default=1.)
    p.add_argument("--report",type=Path)
    p.add_argument("--include-preview-geometry",action="store_true")
    a=p.parse_args(argv)
    try:
        if a.include_preview_geometry and not a.report:
            raise ValueError("Private geometry requires fresh local JSON report")
        result=audit_maps(a.maps,plane_index=a.plane,delta_d=a.delta_d,
                          include_geometry=a.include_preview_geometry)
        if a.report:
            world.write_report(result,a.report,a.maps)
        print(json.dumps({k:v for k,v in result.items() if k!="maps"},indent=2,allow_nan=False))
        return 0
    except (ValueError,OSError,IndexError,KeyError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
