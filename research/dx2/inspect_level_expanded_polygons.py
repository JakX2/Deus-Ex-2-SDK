#!/usr/bin/env python3
"""Read-only original Level expanded polygon stream and packed render crosswalk.

The stream is source-observed, not an authenticated UModel vertex pool.
No original GMP writes, BSP cooking, or engine ownership assertion.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import struct

import inspect_level_world_model as world
import inspect_world_bsp_node_boundaries as boundaries
import inspect_world_bsp_zone_relations as zones
from inspect_bsp_polygon_candidates import boundary_loop
from dx2scene import find_bsp

SCHEMA = "DX2SDK-original-Level-expanded-polygon-stream-v1"
STRIDE = 92
MAX_VERTICES = 300000
MAX_POLYGON_VERTICES = 64
NORMAL_TOL = 2/127
UV_REPEAT_TOL = 1e-6
SPHERE_TOL = .15
CENTER_BUCKET = .25
NEIGHBORS = tuple(product((-1,0,1), repeat=3))


def parse_expanded_polygons(level, start, end, expected_vertices):
    """Read until independently validated render vertex count is exhausted.

    end is the start of the subsequent independently framed provenance
    header, not a pattern-searched zero. Require the intervening tail to
    contain only zeros. All 23 f32 words are retained in original order.
    """
    if (not isinstance(level, bytes) or type(start) is not int
            or type(end) is not int or not 0 <= start < end <= len(level)
            or type(expected_vertices) is not int
            or not 3 <= expected_vertices <= MAX_VERTICES):
        raise ValueError("Invalid expanded polygon stream envelope")
    rows, rebuilt = [], bytearray()
    at, total = start, 0
    while total < expected_vertices:
        if at+2 > end:
            raise ValueError("Truncated expanded polygon count")
        n = struct.unpack_from("<H",level,at)[0]
        stop = at+2+n*STRIDE
        if (not 3 <= n <= MAX_POLYGON_VERTICES
                or total+n > expected_vertices or stop+4 > end):
            raise ValueError("Invalid expanded polygon vertex count or span")
        vertices = [struct.unpack_from("<23f",level,at+2+i*STRIDE)
                    for i in range(n)]
        for v in vertices:
            if (not all(math.isfinite(x) for x in v)
                    or any(abs(x)>1e6 for x in v[:3])
                    or abs(sum(x*x for x in v[3:6])-1)>0.02):
                raise ValueError("Invalid expanded polygon XYZ or normal")
        size = struct.unpack_from("<I",level,stop)[0]
        next_at = stop+4+size
        if not 2 <= size <= 256 or next_at > end:
            raise ValueError("Invalid expanded polygon material length")
        name = level[stop+4:next_at]
        if name[-1] != 0 or any(not 32 <= c <= 126 for c in name[:-1]):
            raise ValueError("Invalid expanded polygon material encoding")
        rows.append({"polygon":len(rows),"start":at,"end":next_at,
                     "material":name[:-1].decode("ascii"),
                     "vertices":vertices})
        rebuilt.extend(struct.pack("<H",n))
        for v in vertices:
            rebuilt.extend(struct.pack("<23f",*v))
        rebuilt.extend(struct.pack("<I",size))
        rebuilt.extend(name)
        total += n
        at = next_at
    if any(level[at:end]):
        raise ValueError("Nonzero unclassified bytes after expanded polygon stream")
    if bytes(rebuilt) != level[start:at]:
        raise ValueError("Expanded polygon decode/encode no-op differs from source")
    return rows, {"expanded_polygon_stream_bytes":at-start,
                  "expanded_polygon_zero_tail_bytes":end-at,
                  "expanded_polygon_stream_end":at,
                  "expanded_polygon_noop_byte_identical":True}


def match_expanded_render(polygons, blocks):
    """Prove a one-to-one ordered XYZ/material join to indexed render disks.

    Index connectivity is used rather than XYZ welding. Each polygon must
    use contiguous packed vertices, exactly n-2 triangles, and an ascending
    oriented index boundary. Non-fan triangulations are retained verbatim.
    """
    by_key = defaultdict(list)
    for row in polygons:
        key=(row["material"],tuple(v[:3] for v in row["vertices"]))
        by_key[key].append(row)
    counts=Counter()
    matched={}
    for bi,block in enumerate(blocks):
        vertices=block["vertices"]
        claimed=set()
        for si,section in enumerate(block["sections"]):
            ids=section["indices"]
            if not ids or len(ids)%3:
                raise ValueError("Invalid packed section index count")
            adj=defaultdict(set)
            triangle_ids=defaultdict(set)
            for ti in range(len(ids)//3):
                tri=ids[ti*3:ti*3+3]
                if len(set(tri))!=3 or any(type(i) is not int or
                        not 0<=i<len(vertices) for i in tri):
                    raise ValueError("Invalid packed polygon triangle indices")
                for i in tri:
                    adj[i].update(tri)
                    triangle_ids[i].add(ti)
            if claimed.intersection(adj):
                raise ValueError("Packed vertex shared across render sections")
            claimed.update(adj)
            seen=set()
            for seed in sorted(adj):
                if seed in seen:
                    continue
                stack=[seed]
                comp={seed}
                seen.add(seed)
                while stack:
                    a=stack.pop()
                    for v in adj[a]-seen:
                        seen.add(v)
                        comp.add(v)
                        stack.append(v)
                ci=sorted(comp)
                if (len(ci)<3 or len(ci)>MAX_POLYGON_VERTICES
                        or ci[-1]-ci[0]+1!=len(ci)):
                    raise ValueError("Noncontiguous packed polygon vertex component")
                tids=sorted(set().union(*(triangle_ids[v] for v in ci)))
                tris=[tuple(ids[3*i:3*i+3]) for i in tids]
                status,loop=boundary_loop(tris)
                if len(tris)!=len(ci)-2 or status!="disk" or loop!=ci:
                    raise ValueError("Packed triangle disk does not match ordered polygon boundary")
                key=(section["material"].rstrip("\0"),tuple(vertices[i][0] for i in ci))
                candidates=by_key.get(key,[])
                if len(candidates)!=1 or candidates[0]["polygon"] in matched:
                    raise ValueError("Expanded/packed polygon association not one-to-one")
                row=candidates[0]
                values=row["vertices"]
                if not all(max(abs(x-y) for x,y in zip(vertices[i][1],v[3:6]))<=NORMAL_TOL
                           for i,v in zip(ci,values)):
                    raise ValueError("Expanded/packed normal mismatch")
                deltas=[tuple(vertices[i][2][j]-v[6+j] for j in range(2))
                        for i,v in zip(ci,values)]
                if not all(abs(d[j]-round(deltas[0][j]))<=UV_REPEAT_TOL
                           for d in deltas for j in range(2)):
                    raise ValueError("Expanded/packed UV difference is not a constant integer repeat")
                counts["expanded_polygons"]+=1
                counts["expanded_vertices"]+=len(ci)
                counts["packed_triangles"]+=len(tids)
                counts["exact_uv_polygons"]+=int(all(d==(0.,0.) for d in deltas))
                counts["integer_repeat_uv_polygons"]+=1
                fan={tuple(sorted((ci[0],ci[j],ci[j+1])))
                     for j in range(1,len(ci)-1)}
                counts["first_vertex_fan_polygons"]+=int(
                    {tuple(sorted(t)) for t in tris}==fan)
                matched[row["polygon"]]={"polygon":row["polygon"],
                    "packed_block":bi,"packed_section":si,
                    "packed_vertex_start":ci[0],
                    "packed_vertex_count":len(ci),
                    "triangle_locators":[(bi,si,i) for i in tids],
                    "packed_uv_integer_delta":[round(x) for x in deltas[0]]}
        if claimed != set(range(len(vertices))):
            raise ValueError("Expanded polygon crosswalk omits packed vertices")
    if len(matched)!=len(polygons):
        raise ValueError("Expanded polygon crosswalk omits source records")
    return dict(counts),[matched[i] for i in sorted(matched)]


def match_model_candidates(polygons,nodes):
    """Geometric association only: count, AABB center, sphere and plane."""
    buckets=defaultdict(list)
    for i,(plane,sphere,n) in enumerate(nodes):
        if (len(plane)!=4 or len(sphere)!=4 or
                not all(math.isfinite(x) for x in (*plane,*sphere))
                or abs(sum(x*x for x in plane[:3])-1)>0.002
                or sphere[3]<0 or type(n) is not int or not 3<=n<=32):
            raise ValueError("Invalid source Model spatial node")
        buckets[(n,*(math.floor(x/CENTER_BUCKET) for x in sphere[:3]))].append(
            (i,plane,sphere))
    by_node=defaultdict(list)
    matches=[]
    counts=Counter()
    for row in polygons:
        xyz=[v[:3] for v in row["vertices"]]
        center=tuple((min(v[k] for v in xyz)+max(v[k] for v in xyz))/2
                     for k in range(3))
        key=tuple(math.floor(x/CENTER_BUCKET) for x in center)
        cand=[]
        for d in NEIGHBORS:
            for i,plane,sphere in buckets.get(
                    (len(xyz),*(a+b for a,b in zip(key,d))),()):
                if math.dist(center,sphere[:3])>SPHERE_TOL:
                    continue
                if abs(max(math.dist(v,sphere[:3]) for v in xyz)*1.001
                       -sphere[3])>SPHERE_TOL:
                    continue
                if max(abs(sum(v[k]*plane[k] for k in range(3))-plane[3])
                       for v in xyz)>SPHERE_TOL:
                    continue
                cand.append(i)
        cand.sort()
        counts["model_candidate_"+("none" if not cand else
               "unique" if len(cand)==1 else "multiple")]+=1
        for i in cand:
            by_node[i].append(row["polygon"])
        matches.append(cand)
    counts["model_nodes"]=len(nodes)
    counts["model_bidirectionally_unique_candidates"]=sum(
        len(c)==1 and len(by_node[c[0]])==1 for c in matches)
    return dict(counts),matches


def audit_map(path, *, include_details=False):
    from dx2sdk.bsp_mopp_plane_impact import _source_triangle_rows
    path=Path(path)
    if (path.suffix.casefold()!=".gmp" or not path.is_file() or path.is_symlink()
            or path.stat().st_size>world.MAX_MAP_BYTES):
        raise ValueError("Expected bounded original DX2 GMP")
    pkg=world.Package(path)
    if pkg.version!=95 or pkg.licensee not in world.OBSERVED_LICENSEES:
        raise ValueError("Expected source-observed DX2 UE95 licensee")
    pin=hashlib.sha256(pkg.data).hexdigest()
    ref=world._parse_world_model(pkg)["world_model_export_ref"]
    model=pkg.payload(pkg.exports[ref-1])
    frame=boundaries.parse_world_model(model,include_nodes=True)
    zones.inspect_zone_relations(model,frame)
    nodes=[]
    for rec in frame["node_records"]:
        at,size=rec["start"],rec["length"]
        nodes.append((struct.unpack_from("<4f",model,at),
                      struct.unpack_from("<4f",model,at+size-53),
                      model[at+size-17]))
    levels=[e for e in pkg.exports if pkg.class_name(e)=="Level" and e["size"]>0]
    if len(levels)!=1:
        raise ValueError("Expected exactly one nonempty Level export")
    level=pkg.payload(levels[0])
    blocks=find_bsp(pkg)
    if not blocks:
        raise ValueError("Missing validated packed render blocks")
    for b in blocks:
        if b["offset"]<4 or b["end"]>len(level) or b["id"]!=b["end"]-b["offset"]:
            raise ValueError("Packed block source envelope mismatch")
    if any(a["end"]>b["offset"]-4 for a,b in zip(blocks,blocks[1:])):
        raise ValueError("Overlapping packed block source envelopes")
    source_rows,provenance=_source_triangle_rows(level,blocks)
    start=blocks[-1]["end"]
    end=provenance["triangle_provenance_start_in_level"]-24
    polygons,framing=parse_expanded_polygons(
        level,start,end,sum(len(b["vertices"]) for b in blocks))
    counts,links=match_expanded_render(polygons,blocks)
    candidate_counts,candidates=match_model_candidates(polygons,nodes)
    counts.update(candidate_counts)
    counts.update({k:v for k,v in framing.items()
                   if k.endswith("_bytes")})
    by_locator={tuple(r["render_locator"]):r for r in source_rows}
    seen=set()
    leaves=0
    for link in links:
        locs=link["triangle_locators"]
        if seen.intersection(locs) or not set(locs)<=by_locator.keys():
            raise ValueError("Expanded polygon collision locator conflict")
        seen.update(locs)
        records=[by_locator[k] for k in locs]
        leaf_count=sum(r["original_mopp_terminal_leaf_present"] for r in records)
        leaves+=leaf_count
        counts["all_leaf_polygons"]=counts.get("all_leaf_polygons",0)+int(
            leaf_count==len(records))
        if include_details:
            link["original_flat_triangle_ids"]=[r["flattened_triangle_id"] for r in records]
            link["original_mopp_leaf_ids"]=[r["flattened_triangle_id"] for r in records
                                           if r["original_mopp_terminal_leaf_present"]]
    if seen!=set(by_locator) or len(seen)!=counts["packed_triangles"]:
        raise ValueError("Expanded polygon collision crosswalk incomplete")
    counts["original_mopp_leaves"]=leaves
    counts["original_nonleaf_triangles"]=len(seen)-leaves
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError("Original GMP changed during audit")
    result={"counts":counts,"source_map":path.name,"source_sha256":pin,
            "source_level_sha256":hashlib.sha256(level).hexdigest(),
            "source_model_sha256":hashlib.sha256(model).hexdigest(),
            "expanded_polygon_stream_start":start,**framing}
    if include_details:
        result["private_polygons"]=[{**row,**link,"model_candidates":cand,
              "native_model_ownership_verified":False,"native_write_allowed":False}
              for row,link,cand in zip(polygons,links,candidates)]
    return result


def audit_maps(paths, *, include_details=False):
    if (not 1<=len(paths)<=world.MAX_MAPS
            or len({Path(p).resolve() for p in paths})!=len(paths)):
        raise ValueError("Expected 1..64 distinct original maps")
    rows=[audit_map(p,include_details=include_details) for p in paths]
    counts=Counter()
    for row in rows:
        counts.update(row["counts"])
    return {"schema":SCHEMA,"read_only":True,"map_count":len(rows),
            "summary":dict(counts),"maps":rows,
            "native_model_vertex_pool_decoded":False,
            "native_model_surface_ownership_verified":False,
            "native_bsp_writer_enabled":False,"native_collision_writer_enabled":False,
            "retail_runtime_verified":False,"private_details_included":include_details}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",nargs="+",type=Path)
    p.add_argument("--report",type=Path)
    p.add_argument("--include-private-polygons",action="store_true")
    a=p.parse_args(argv)
    try:
        if a.include_private_polygons and not a.report:
            raise ValueError("Private polygon details require an explicit local report path")
        result=audit_maps(a.maps,include_details=a.include_private_polygons)
        if a.report:
            world.write_report(result,a.report,a.maps)
        print(json.dumps({k:v for k,v in result.items() if k!="maps"},
                         indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,KeyError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
