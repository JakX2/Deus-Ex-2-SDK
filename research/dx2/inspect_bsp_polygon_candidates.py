#!/usr/bin/env python3
"""Infer preview-only BSP polygon outlines from original Level triangles.

No native Model polygon array or engine ownership is assumed. Source-framed
planes, vertex slot counts and a candidate sphere constrain reconstructed
boundaries. Reports contain aggregate counts by default; preview vertices
are emitted only on explicit request to a private local report.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct

import inspect_bsp_render_spatial_candidates as spatial
import inspect_world_bsp_zone_relations as zones
import inspect_world_bsp_node_boundaries as boundaries
from dx2scene import find_bsp

SCHEMA = "DX2SDK-inferred-BSP-polygon-boundaries-v1"
CENTER_TOL = 0.15
RADIUS_TOL = 0.15
RADIUS_FACTOR = 1.001
AREA_TOL = 1e-5
MAX_GROUP_TRIANGLES = 128


def area(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def boundary_loop(triangles):
    """Require one connected oriented triangulated disk, using exact XYZ."""
    if not 1 <= len(triangles) <= MAX_GROUP_TRIANGLES:
        return "group_size", None
    edges = defaultdict(list)
    vertices = set()
    for i, tri in enumerate(triangles):
        if len(tri) != 3 or len(set(tri)) != 3:
            return "degenerate", None
        vertices.update(tri)
        for a, b in zip(tri, tri[1:]+tri[:1]):
            edges[tuple(sorted((a,b)))].append((a,b,i))
    if any(len(rows)>2 for rows in edges.values()):
        return "nonmanifold", None
    adjacent = defaultdict(set)
    next_vertex, incoming = {}, set()
    for rows in edges.values():
        a,b,i = rows[0]
        if len(rows)==2:
            c,d,j = rows[1]
            if (a,b)!=(d,c):
                return "inconsistent_winding", None
            adjacent[i].add(j)
            adjacent[j].add(i)
        else:
            if a in next_vertex or b in incoming:
                return "boundary_degree", None
            next_vertex[a] = b
            incoming.add(b)
    visited = {0}
    stack = [0]
    while stack:
        i = stack.pop()
        for j in adjacent[i]-visited:
            visited.add(j)
            stack.append(j)
    if len(visited)!=len(triangles):
        return "disconnected_triangles", None
    if len(vertices)-len(edges)+len(triangles)!=1:
        return "euler", None
    if not next_vertex or set(next_vertex)!=incoming:
        return "open_boundary", None
    start = min(next_vertex)
    loop = [start]
    seen = {start}
    while True:
        nxt = next_vertex[loop[-1]]
        if nxt==start:
            break
        if nxt in seen:
            return "repeated_boundary_vertex", None
        seen.add(nxt)
        loop.append(nxt)
    if len(loop)!=len(next_vertex):
        return "multiple_boundary_cycles", None
    if len(loop)<3:
        return "short_boundary", None
    return "disk", loop


def classify_polygon(plane, sphere, count, triangles):
    """Return progressive geometry checks, never a native ownership claim."""
    status, loop = boundary_loop(triangles)
    if loop is None:
        return {"status":status}, None
    evidence = {"status":"disk",
                "vertex_count_match":len(loop)==count,
                "boundary_only_n_minus_2":False,
                "center_match":False,"unscaled_radius_match":False,
                "inflated_radius_match":False,"strict_convex":False,
                "weak_convex":False,"area_match":False,"preview_candidate":False}
    if len(loop)!=count:
        return evidence,None
    vertices={v for tri in triangles for v in tri}
    if vertices!=set(loop) or len(triangles)!=count-2:
        return evidence,None
    evidence["boundary_only_n_minus_2"]=True
    center,radius=sphere[:3],sphere[3]
    lo=[min(v[i] for v in loop) for i in range(3)]
    hi=[max(v[i] for v in loop) for i in range(3)]
    midpoint=[(a+b)/2 for a,b in zip(lo,hi)]
    farthest=max(math.dist(v,center) for v in loop)
    evidence["center_match"]=math.dist(center,midpoint)<=CENTER_TOL
    evidence["unscaled_radius_match"]=abs(farthest-radius)<=RADIUS_TOL
    evidence["inflated_radius_match"]=abs(farthest*RADIUS_FACTOR-radius)<=RADIUS_TOL
    # Project along the largest normal component to avoid unstable axes.
    # All edges must support the same convex polygon. Strict convexity is
    # deliberately required for the subset offered as editable previews.
    axis=max(range(3),key=lambda i:abs(plane[i]))
    project=lambda v:tuple(v[i] for i in range(3) if i!=axis)
    q=[project(v) for v in loop]
    signed=sum(area(q[0],q[i],q[i+1]) for i in range(1,len(q)-1))
    if abs(signed)<=AREA_TOL:
        return evidence,None
    sign=1 if signed>0 else -1
    turns=[sign*area(a,b,v)
           for i,(a,b) in enumerate(zip(q,q[1:]+q[:1]))
           for j,v in enumerate(q) if j not in (i,(i+1)%len(q))]
    evidence["weak_convex"]=all(t>=-AREA_TOL for t in turns)
    evidence["strict_convex"]=all(t>AREA_TOL for t in turns)
    tri_areas=[sign*area(*[project(v) for v in tri]) for tri in triangles]
    evidence["area_match"]=(all(a>0 for a in tri_areas) and
        math.isclose(sum(tri_areas),abs(signed),rel_tol=1e-7,abs_tol=AREA_TOL))
    evidence["preview_candidate"]=all(evidence[k] for k in
        ("center_match","inflated_radius_match","strict_convex","area_match"))
    return evidence,loop if evidence["preview_candidate"] else None


def analyze_polygons(nodes, triangles, *, include_polygons=False):
    """Use only uniquely matched triangles; exclude every ambiguous node.

    nodes contain a validated plane, spatial sphere and source slot count.
    triangles contain the previous Level render locator and XYZ triplet.
    """
    if not nodes:
        raise ValueError("No source BSP nodes")
    if any(type(n["count"])!=int or not 3<=n["count"]<=32 for n in nodes):
        raise ValueError("Invalid source vertex slot count")
    triangles=list(triangles)
    by_locator={}
    for locator,tri in triangles:
        key=tuple(locator)
        if len(key)!=3 or key in by_locator:
            raise ValueError("Duplicate or malformed render triangle locator")
        by_locator[key]=tuple(tuple(v) for v in tri)
    matches=spatial.analyze_spatial_candidates(
        [(n["plane"],n["sphere"]) for n in nodes],triangles,include_matches=True)
    groups=defaultdict(list)
    ambiguous=set()
    for match in matches["candidate_triangle_nodes"]:
        candidates=match["candidate_nodes"]
        if len(candidates)==1:
            groups[candidates[0]].append(tuple(match["triangle"]))
        elif candidates:
            ambiguous.update(candidates)
    counts=Counter(matches["counts"])
    counts["nodes"]=len(nodes)
    counts["nodes_with_unique_triangles"]=len(groups)
    counts["nodes_excluded_for_ambiguous_triangles"]=len(set(groups)&ambiguous)
    preview=[]
    for i,locators in sorted(groups.items()):
        if i in ambiguous:
            continue
        node=nodes[i]
        evidence,loop=classify_polygon(node["plane"],node["sphere"],node["count"],
                                       [by_locator[k] for k in locators])
        counts["boundary_"+evidence["status"]]+=1
        for key,value in evidence.items():
            if key!="status" and value:
                counts[key]+=1
        if loop is not None:
            # Multiple render sections may indicate different materials.
            section_ids=sorted(set(k[:2] for k in locators))
            if len(section_ids)==1:
                counts["single_section_preview_candidates"]+=1
            if include_polygons:
                preview.append({"source_node":i,
                                "raw_candidate_vertex_start":node.get("vertex_start"),
                                "raw_candidate_surface_value":node.get("surface"),
                                "source_vertex_slots":node["count"],
                                "inferred_boundary_xyz":loop,
                                "original_render_triangle_locators":locators,
                                "render_section_locators":section_ids,
                                "engine_ownership_verified":False,
                                "native_write_allowed":False})
    return {"counts":dict(counts),
            **({"preview_polygons":preview} if include_polygons else {})}


def audit_map(path, *, include_polygons=False):
    path=Path(path)
    if path.suffix.casefold()!=".gmp" or not path.is_file() or path.is_symlink() or path.stat().st_size>boundaries.world.MAX_MAP_BYTES:
        raise ValueError("Expected bounded original user-owned GMP")
    pkg=boundaries.world.Package(path)
    if pkg.version!=95 or pkg.licensee not in boundaries.world.OBSERVED_LICENSEES:
        raise ValueError("Expected UE95 DX2 licensee 65/67/68/69")
    pin=hashlib.sha256(pkg.data).hexdigest()
    root=boundaries.world._parse_world_model(pkg)
    exp=pkg.exports[root["world_model_export_ref"]-1]
    raw=pkg.payload(exp)
    frame=boundaries.parse_world_model(raw,include_nodes=True)
    zones.inspect_zone_relations(raw,frame)
    nodes=[]
    for rec in frame["node_records"]:
        at,size=rec["start"],rec["length"]
        c=boundaries.world.Cursor(raw,at+48,at+size-53)
        fields=[c.ci() for _ in range(8)]
        if c.at!=at+size-53:
            raise ValueError("Original compact fields shifted")
        nodes.append({"plane":struct.unpack_from("<4f",raw,at),
                      "sphere":struct.unpack_from("<4f",raw,at+size-53),
                      "count":raw[at+size-17],"vertex_start":fields[1],"surface":fields[2]})
    blocks=find_bsp(pkg)
    if not blocks:
        raise ValueError("No validated original Level render blocks")
    result=analyze_polygons(nodes,spatial._triangles_from_render_blocks(blocks),
                            include_polygons=include_polygons)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError("Original GMP changed during audit")
    return {"source_map":path.name,"source_sha256":pin,"licensee":pkg.licensee,
            "world_model_export":exp["index"],
            "world_model_sha256":hashlib.sha256(raw).hexdigest(),
            "render_blocks":len(blocks),**result}


def audit_maps(paths, *, include_polygons=False):
    if not 1<=len(paths)<=boundaries.world.MAX_MAPS:
        raise ValueError("Expected 1..64 original GMP paths")
    if len({Path(p).resolve() for p in paths})!=len(paths):
        raise ValueError("Duplicate GMP path")
    rows=[audit_map(p,include_polygons=include_polygons) for p in paths]
    total=Counter()
    for row in rows:
        total.update(row["counts"])
    return {"schema":SCHEMA,"read_only":True,"maps":rows,"summary":dict(total),
            "map_count":len(rows),"radius_factor_hypothesis":RADIUS_FACTOR,
            "center_tolerance":CENTER_TOL,"radius_tolerance":RADIUS_TOL,
            "native_surface_array_decoded":False,"engine_ownership_verified":False,
            "native_BSP_writer_enabled":False,"collision_writer_enabled":False,
            "retail_runtime_verified":False,"source_modified":False,
            "private_preview_geometry_included":include_polygons}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",nargs="+",type=Path)
    p.add_argument("--report",type=Path)
    p.add_argument("--include-preview-polygons",action="store_true")
    a=p.parse_args(argv)
    try:
        if a.include_preview_polygons and a.report is None:
            raise ValueError("Private preview geometry requires an explicit local report path")
        report=audit_maps(a.maps,include_polygons=a.include_preview_polygons)
        if a.report is not None:
            boundaries.world.write_report(report,a.report,a.maps)
            print(json.dumps({"status":"ok","summary":report["summary"]},sort_keys=True))
        else:
            # Aggregate counts only, not source names or hashes.
            print(json.dumps({k:v for k,v in report.items() if k!="maps"},indent=2,sort_keys=True))
        return 0
    except (OSError,ValueError,IndexError,KeyError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
