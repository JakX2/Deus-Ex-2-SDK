#!/usr/bin/env python3
"""Audit source VBSP polygon-plane dependencies and hypothetical plane offsets.

Read-only geometry preflight. A source plane shared by multiple nodes may
affect many leaves, portals, and polygons. No source bytes are changed.
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
from inspect_level_spatial_vbsp import parse_spatial_tail,validate_leaf_render_ownership
import inspect_level_world_model as world

SCHEMA="DX2SDK-VBSP-local-plane-dependency-preflight-v1"
PLANE_TOL=.15
NORMAL_TOL=.002
MAX_DEPTH=2048
MAX_PATH_CONSTRAINTS=2000000
MAX_POLYGON_PATH_TESTS=4000000


def leaf_paths(nodes):
    """Source tree is already validated; retain oriented splitting constraints."""
    paths={}
    visited=set()
    stack=[(0,())]
    total=0
    while stack:
        i,path=stack.pop()
        if i in visited or len(path)>MAX_DEPTH:
            raise ValueError("VBSP dependency path is cyclic or too deep")
        visited.add(i)
        flags,a,b,*_=nodes[i]
        for side,child in enumerate((a,b)):
            if child==-1:
                continue
            p=path+((flags>>2,side),)
            if flags&(1<<side):
                if child in paths:
                    raise ValueError("Duplicate VBSP leaf dependency path")
                total+=len(p)
                if total>MAX_PATH_CONSTRAINTS:
                    raise ValueError("VBSP leaf path constraint budget exceeded")
                paths[child]=p
            else:
                stack.append((child,p))
    if len(visited)!=len(nodes):
        raise ValueError("VBSP dependency paths omit source nodes")
    return paths


def _signed_dist(v,plane,side,delta=0.):
    return (1 if side==0 else -1)*(sum(x*y for x,y in zip(v,plane[:3]))+plane[3]+delta)


def inspect_dependencies(tail,polygons,owners,*,plane_index=None,delta_d=None):
    """Derive geometric supporting-plane candidates along actual leaf paths."""
    nodes,planes=tail["nodes"],tail["planes"]
    paths=leaf_paths(nodes)
    if len(paths)!=len(tail["leaves"]) or len(owners)!=len(polygons):
        raise ValueError("Incomplete VBSP polygon owner/path inventory")
    if (plane_index is None)!=(delta_d is None):
        raise ValueError("Plane index and hypothetical D delta are both required")
    if plane_index is not None and (type(plane_index) is not int
            or not 0<=plane_index<len(planes) or type(delta_d) not in (float,int)
            or not math.isfinite(delta_d) or not 0<abs(delta_d)<=128):
        raise ValueError("Expected valid plane index and nonzero finite D delta within +/-128")
    counts=Counter()
    by_plane=defaultdict(list)
    plane_leaves=defaultdict(set)
    plane_nodes=Counter(flags>>2 for flags,*_ in nodes)
    plane_portals=Counter(p[4] if p[4]>=0 else ~p[4] for p in tail["portals"])
    for leaf,path in paths.items():
        counts["leaf_path_constraints"]+=len(path)
        for pi,side in path:
            plane_leaves[pi].add(leaf)
    for i,poly in enumerate(polygons):
        if owners[i] not in paths or poly["polygon"]!=i:
            raise ValueError("Invalid original polygon owner or ordinal")
        vs=poly["vertices"]
        if len(vs)<3:
            raise ValueError("Invalid expanded polygon vertex count")
        xyz=[v[:3] for v in vs]
        normal=vs[0][3:6]
        matches=[]
        for pi,side in paths[owners[i]]:
            counts["polygon_path_tests"]+=1
            if counts["polygon_path_tests"]>MAX_POLYGON_PATH_TESTS:
                raise ValueError("VBSP polygon path test budget exceeded")
            pl=planes[pi]
            dist=[_signed_dist(v,pl,side) for v in xyz]
            counts["polygon_path_violation"]+=int(min(dist)<-PLANE_TOL)
            sign=1 if side==0 else -1
            if max(abs(d) for d in dist)<=PLANE_TOL and math.dist(
                    normal,tuple(sign*x for x in pl[:3]))<=NORMAL_TOL:
                matches.append((pi,side))
            if pi==plane_index:
                new=[_signed_dist(v,pl,side,delta_d) for v in xyz]
                counts["selected_plane_polygon_path_tests"]+=1
                counts["selected_plane_new_path_violations"]+=int(
                    min(dist)>=-PLANE_TOL and min(new)<-PLANE_TOL)
        counts["polygons"]+=1
        key="none" if not matches else "unique" if len(matches)==1 else "multiple"
        counts["polygon_path_plane_"+key]+=1
        if len(matches)==1:
            by_plane[matches[0][0]].append(i)
    for pi,polys in by_plane.items():
        counts["used_planes"]+=1
        counts["used_planes_multiple_polys"]+=int(len(polys)>1)
        counts["polys_on_shared_plane"]+=len(polys) if len(polys)>1 else 0
        counts["used_planes_multiple_nodes"]+=int(plane_nodes[pi]>1)
        counts["used_planes_portal_overlap"]+=int(plane_portals[pi]>0)
        counts["used_planes_multiple_leaves"]+=int(len(plane_leaves[pi])>1)
    impact=None
    if plane_index is not None:
        impacted=plane_leaves[plane_index]
        impact={"plane_index":plane_index,"hypothetical_delta_d":delta_d,
                "node_records_reusing_plane":plane_nodes[plane_index],
                "leaf_paths_reusing_plane":len(impacted),
                "polygons_in_impacted_leaf_paths":sum(i in impacted for i in owners),
                "unique_supporting_polygon_candidates":len(by_plane[plane_index]),
                "directly_referencing_portal_records":plane_portals[plane_index],
                "new_unchanged_polygon_path_violations":
                    counts["selected_plane_new_path_violations"],
                "plane_only_edit_is_native_geometry_compilation":False}
    return {"counts":dict(counts),"hypothetical_impact":impact}


def audit_map(path,*,plane_index=None,delta_d=None):
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
    result=inspect_dependencies(tail,polys,owners,plane_index=plane_index,delta_d=delta_d)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError("Original GMP changed during dependency audit")
    return {"source_map":path.name,"source_sha256":pin,**result}


def audit_maps(paths,*,plane_index=None,delta_d=None):
    if not 1<=len(paths)<=world.MAX_MAPS or len({Path(p).resolve() for p in paths})!=len(paths):
        raise ValueError("Expected 1..64 distinct original maps")
    if plane_index is not None and len(paths)!=1:
        raise ValueError("A hypothetical plane edit requires exactly one map")
    rows=[audit_map(p,plane_index=plane_index,delta_d=delta_d) for p in paths]
    counts=Counter()
    for row in rows:
        counts.update(row["counts"])
    return {"schema":SCHEMA,"map_count":len(rows),"summary":dict(counts),
            "hypothetical_impact":rows[0]["hypothetical_impact"] if len(rows)==1 else None,
            "source_files_modified":False,"native_geometry_writer_enabled":False,
            "retail_runtime_verified":False,"maps":rows}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",nargs="+",type=Path)
    p.add_argument("--plane",type=int)
    p.add_argument("--delta-d",type=float)
    p.add_argument("--report",type=Path)
    a=p.parse_args(argv)
    try:
        result=audit_maps(a.maps,plane_index=a.plane,delta_d=a.delta_d)
        if a.report:
            world.write_report(result,a.report,a.maps)
        print(json.dumps({k:v for k,v in result.items() if k!="maps"},indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,KeyError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
