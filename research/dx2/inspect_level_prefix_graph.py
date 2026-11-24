#!/usr/bin/env python3
"""Read-only Level prefix triangle/edge graph, a navigation-like hypothesis.

The independently serialized edge-owner pairs and triangle edge lists are
exactly cross-checked. The engine graph type, extra float, flags and following
prefix arrays are not authenticated. No geometry or graph writer.
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
import inspect_level_world_model as world

SCHEMA = "DX2SDK-Level-prefix-triangle-edge-graph-v1"
MAX_TRIANGLES = 100000
MAX_EDGES = 300000
MAX_REFS_PER_TRIANGLE = 512
NORMAL_TOL = .01
GEOMETRY_TOL = .15


def parse_graph_at(level,start,end,zero_width):
    """Parse a bounded complete graph and verify redundant owner arrays."""
    if (type(level) is not bytes or type(start) is not int or type(end) is not int
            or not 0<=start<end<=len(level) or zero_width not in (30,31)
            or start+zero_width+4>end or level[start:start+zero_width]!=bytes(zero_width)):
        raise ValueError("Invalid Level prefix graph zero header or envelope")
    at=start+zero_width
    rebuilt=bytearray(zero_width)
    counts=Counter()

    def take(fmt):
        nonlocal at
        size=struct.calcsize(fmt)
        if at+size>end:
            raise ValueError("Truncated Level prefix graph")
        values=struct.unpack_from(fmt,level,at)
        rebuilt.extend(struct.pack(fmt,*values))
        at+=size
        return values

    n,=take("<I")
    if not 1<=n<=MAX_TRIANGLES or at+57*n+4>end:
        raise ValueError("Invalid Level prefix triangle count")
    triangles=[]
    normals=[]
    for _ in range(n):
        vc,*v,flag=take("<I13fB")
        if (vc!=3 or not all(math.isfinite(x) and abs(x)<1e6 for x in v)
                or v[11]<=0 or abs(sum(x*x for x in v[9:12])-1)>NORMAL_TOL):
            raise ValueError("Invalid Level prefix triangle or upward normal")
        xyz=[tuple(v[i:i+3]) for i in (0,3,6)]
        normal=tuple(v[9:12])
        triangles.append(xyz)
        normals.append(normal)
        counts["prefix_graph_triangle_count"]+=1
        counts["prefix_graph_triangle_vertices"]+=3
        counts["prefix_graph_triangle_normal_coplanar"]+=int(max(
            abs(sum((x-y)*z for x,y,z in zip(p,xyz[0],normal)))
            for p in xyz)<=GEOMETRY_TOL)
        counts["prefix_graph_triangle_zero_flag"]+=int(flag==0)
        counts["prefix_graph_extra_float_146_or_160"]+=int(v[12] in (146.,160.))
    en,=take("<I")
    if not 1<=en<=MAX_EDGES or at+33*en+4*n+8*en>end:
        raise ValueError("Invalid Level prefix edge count")
    endpoints=[]
    for _ in range(en):
        flag,*xyz,opaque=take("<B6f8s")
        if not all(math.isfinite(x) and abs(x)<1e6 for x in xyz):
            raise ValueError("Invalid Level prefix edge coordinates")
        a,b=tuple(xyz[:3]),tuple(xyz[3:])
        endpoints.append((a,b))
        counts["prefix_graph_edge_count"]+=1
        counts["prefix_graph_edge_endpoint_records"]+=2
        counts["prefix_graph_nondegenerate_edges"]+=int(a!=b)
        counts["prefix_graph_edge_zero_flag"]+=int(flag==0)
    owners=[[] for _ in range(en)]
    refs=0
    for i in range(n):
        k,=take("<I")
        if k>MAX_REFS_PER_TRIANGLE or refs+k>2*en:
            raise ValueError("Invalid Level prefix triangle edge-list count")
        ids=take("<"+str(k)+"I")
        if len(set(ids))!=k or any(j>=en for j in ids):
            raise ValueError("Duplicate or out-of-range Level prefix edge reference")
        for j in ids:
            if len(owners[j])>=2:
                raise ValueError("Level prefix edge has more than two owners")
            owners[j].append(i)
        refs+=k
    if refs!=2*en or any(len(x)!=2 or x[0]==x[1] for x in owners):
        raise ValueError("Incomplete two-owner Level prefix edge graph")
    for i,(a,b) in enumerate(endpoints):
        j,k=take("<II")
        if j==k or j>=n or k>=n or sorted((j,k))!=owners[i]:
            raise ValueError("Level prefix edge-owner pair disagrees with triangle edge lists")
        distances=[]
        for t in (j,k):
            base=triangles[t][0]
            normal=normals[t]
            distances.append(max(abs(sum((x-y)*z for x,y,z in zip(p,base,normal)))
                                 for p in (a,b)))
        counts["prefix_graph_edge_owner_pairs_verified"]+=1
        counts["prefix_graph_edge_both_owner_planes_near"]+=int(max(distances)<=GEOMETRY_TOL)
        counts["prefix_graph_edge_one_owner_plane_near"]+=int(min(distances)<=GEOMETRY_TOL)
    counts["prefix_graph_triangle_edge_references"]=refs
    counts["prefix_graph_decoded_bytes"]=at-start
    counts["prefix_graph_opaque_following_bytes"]=end-at
    if bytes(rebuilt)!=level[start:at]:
        raise ValueError("Level prefix graph no-op differs from original bytes")
    return {"graph_start":start,"graph_end":at,"render_array_count_offset":end,
            "zero_header_bytes":zero_width,"counts":dict(counts),
            "source_graph_noop_byte_identical":True,
            "source_edge_ownership_redundancy_verified":True,
            "native_navigation_semantics_verified":False,"native_graph_write_allowed":False}


def parse_prefix_graph(level,start,end):
    valid=[]
    for width in (30,31):
        try:
            valid.append(parse_graph_at(level,start,end,width))
        except (ValueError,struct.error,OverflowError):
            pass
    if len(valid)!=1:
        raise ValueError("Expected exactly one validated Level prefix graph layout")
    return valid[0]


def audit_map(path):
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
    block_frame=validate_counted_render_array(level,blocks,collision)
    result=parse_prefix_graph(level,cursor.at,block_frame["render_block_count_offset"])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError("Original GMP changed during graph audit")
    return {"source_map":path.name,"source_sha256":pin,**result}


def audit_maps(paths):
    if not 1<=len(paths)<=world.MAX_MAPS or len({Path(p).resolve() for p in paths})!=len(paths):
        raise ValueError("Expected 1..64 distinct original maps")
    rows=[audit_map(p) for p in paths]
    counts=Counter()
    for r in rows:
        counts.update(r["counts"])
    return {"schema":SCHEMA,"map_count":len(rows),"summary":dict(counts),
            "source_files_modified":False,"native_navigation_semantics_verified":False,
            "native_graph_writer_enabled":False,"retail_runtime_verified":False,"maps":rows}


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
