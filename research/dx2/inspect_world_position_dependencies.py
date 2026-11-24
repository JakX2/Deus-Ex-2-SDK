#!/usr/bin/env python3
"""Audit original position dependencies and dry-run rigid world translation.

This is a research-only in-memory package experiment. It does not move
actors, decode the opaque Level prefix, regenerate CSG/MOPP, or write a GMP.
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

from experimental_polygon_uv import _read_context, MAX_GMP
from inspect_level_expanded_polygons import (
    STRIDE, match_model_candidates, validate_counted_render_array,
)
import inspect_level_flattened_mesh_crossref as flat
import inspect_level_mopp_triangle_tree as mopp
import inspect_world_bsp_node_boundaries as boundaries
import inspect_world_bsp_zone_relations as zones
import inspect_level_world_model as world
from inspect_mopp_axis_point_candidates import ConservativeMoppPointCandidates

SCHEMA = "DX2SDK-position-dependency-rigid-translation-research-v1"
SHADOW_TOL = .301
RADIUS_TOL = .002
MAX_DELTA = 16.
MAX_ROUNDING = .002
MAX_SHADOW_CHOICES = 4096
NEIGHBORS = tuple(product((-1,0,1), repeat=3))


def f32(x):
    return struct.unpack("<f",struct.pack("<f",x))[0]


SOURCE_SCALE = f32(flat.SCALE)


def scaled_position(xyz):
    return tuple(f32(v*SOURCE_SCALE) for v in xyz)


def bounds_of(vertices):
    if not vertices:
        raise ValueError("Empty packed geometry")
    lo=tuple(min(v[i] for v in vertices) for i in range(3))
    hi=tuple(max(v[i] for v in vertices) for i in range(3))
    center=tuple(f32((a+b)/2) for a,b in zip(lo,hi))
    radius=math.dist(lo,tuple((a+b)/2 for a,b in zip(lo,hi)))
    return lo+hi,center,radius


def inspect_packed_positions(level, blocks):
    """Validate bounds, shadow cap index layout and source geometric candidates.

    Distinct index triangles can have identical XYZ. The unique geometric
    triangle claim is deliberately separate from index-ownership uniqueness.
    """
    counts=Counter()
    links=[]
    max_shadow_distance=0.
    for bi,b in enumerate(blocks):
        s=b["offset"]
        nv,ni,nt,ns,nsi,nst,nsv=struct.unpack_from("<7I",level,s+40)
        if nv!=len(b["vertices"]) or ns!=len(b["sections"]):
            raise ValueError("Packed header vertex/section count mismatch")
        xyz=[v[0] for v in b["vertices"]]
        box,center,radius=bounds_of(xyz)
        stored=struct.unpack_from("<10f",level,s)
        if (stored[:6]!=box or stored[7:]!=center
                or not math.isfinite(stored[6]) or abs(stored[6]-radius)>RADIUS_TOL):
            raise ValueError("Packed render bounds, center or radius mismatch")
        counts["packed_blocks"]+=1
        counts["packed_exact_boxes"]+=1
        counts["packed_exact_centers"]+=1
        counts["packed_radius_within_tolerance"]+=1
        counts["packed_vertices"]+=nv
        shadow_at=s+80+nv*32
        idx_at=shadow_at+nsv*16
        if (nsv%6 or nsi!=4*nsv or nst!=nsi//3
                or idx_at+nsi*2+ni*2>b["end"]):
            raise ValueError("Unrecognized shadow stream framing")
        if not nsv:
            continue
        counts["shadow_blocks"]+=1
        counts["shadow_vertices"]+=nsv
        counts["shadow_indices"]+=nsi
        buckets=defaultdict(list)
        for v in set(xyz):
            buckets[tuple(math.floor(x) for x in v)].append(v)
        triangle_geometry=defaultdict(list)
        for si,sec in enumerate(b["sections"]):
            ids=sec["indices"]
            for ti in range(len(ids)//3):
                key=tuple(sorted(xyz[j] for j in ids[3*ti:3*ti+3]))
                triangle_geometry[key].append((bi,si,ti))
        indices=struct.unpack_from("<"+str(nsi)+"H",level,idx_at)
        options=[]
        for i in range(nsv):
            v=struct.unpack_from("<3fI",level,shadow_at+16*i)
            if not all(math.isfinite(x) for x in v[:3]) or v[3]>>24:
                raise ValueError("Invalid source shadow position or fourth word")
            key=tuple(math.floor(x) for x in v[:3])
            near=sorted((math.dist(v[:3],q),q) for d in NEIGHBORS
                        for q in buckets.get(tuple(a+b for a,b in zip(key,d)),())
                        if math.dist(v[:3],q)<=SHADOW_TOL)
            if not near:
                raise ValueError("Shadow vertex has no nearby render position")
            max_shadow_distance=max(max_shadow_distance,near[0][0])
            counts["shadow_vertices_multiple_xyz_candidates"]+=int(len(near)>1)
            options.append([q for _,q in near])
        for j in range(0,nsv,3):
            k=4*j
            pattern=indices[k:k+12]
            if (pattern[:9:3]!=(j,j+1,j+2)
                    or pattern[2:9:3]!=(j+1,j+2,j)
                    or pattern[9:]!=(j,j+1,j+2)
                    or any(i>=nsv for i in pattern)):
                raise ValueError("Unrecognized shadow cap/side index pattern")
            group=options[j:j+3]
            if math.prod(map(len,group))>MAX_SHADOW_CHOICES:
                raise ValueError("Shadow corner association search cap exceeded")
            keys={tuple(sorted(t)) for t in product(*group)
                  if tuple(sorted(t)) in triangle_geometry}
            if len(keys)!=1:
                raise ValueError("Shadow cap has absent or ambiguous render XYZ triangle")
            locs=tuple(sorted(triangle_geometry[next(iter(keys))]))
            nearest=tuple(sorted(v[0] for v in group))
            counts["shadow_caps"]+=1
            counts["shadow_unique_render_xyz_caps"]+=1
            counts["shadow_unique_render_index_caps"]+=int(len(locs)==1)
            counts["shadow_nearest_only_mismatch_caps"]+=int(nearest not in keys)
            links.append((bi,j//3,locs))
    return dict(counts),links,max_shadow_distance


def inspect_flat_exact(level,blocks):
    proof=flat.inspect_level_flattened_mesh(level,blocks)
    xyz,_=flat._flatten_render_blocks(blocks)
    at=proof["level_flat_vertex_array_offset"]
    double_matches=0
    for i,v in enumerate(xyz):
        old=level[at+16*i:at+16*i+12]
        if old!=struct.pack("<3f",*scaled_position(v)):
            raise ValueError("Flattened XYZ differs from exact float32 scale rule")
        double_matches+=sum(old[4*j:4*j+4]==struct.pack("<f",x*flat.SCALE)
                            for j,x in enumerate(v))
    return proof,{"flat_exact_scaled_vertices":len(xyz),
                  "flat_exact_scaled_components":3*len(xyz),
                  "flat_double_scale_component_matches":double_matches}


def inspect_model_positions(model):
    frame=boundaries.parse_world_model(model,include_nodes=True)
    zones.inspect_zone_relations(model,frame)
    nodes=[]
    for rec in frame["node_records"]:
        at,size=rec["start"],rec["length"]
        plane=struct.unpack_from("<4f",model,at)
        sphere=struct.unpack_from("<4f",model,at+size-53)
        if (not all(math.isfinite(v) for v in sphere) or sphere[3]<0
                or model[at+size-37:at+size-21]!=bytes(16)):
            raise ValueError("Unsupported Model sphere/reserved profile")
        nodes.append((plane,sphere,model[at+size-17]))
    return frame,nodes


class BytePatch:
    """Disjoint fixed-width spans, with full exact original reversal."""
    def __init__(self,source):
        self.source=source
        self.spans=[]

    def add(self,at,data):
        if type(at) is not int or not isinstance(data,bytes) or not data or not 0<=at<=len(self.source)-len(data):
            raise ValueError("Patch span outside original byte envelope")
        self.spans.append((at,self.source[at:at+len(data)],data))

    def finish(self):
        out=bytearray(self.source)
        end=0
        for at,old,new in sorted(self.spans):
            if at<end or out[at:at+len(old)]!=old:
                raise ValueError("Overlapping or stale source patch span")
            out[at:at+len(old)]=new
            end=at+len(old)
        back=bytearray(out)
        for at,old,new in self.spans:
            if back[at:at+len(new)]!=new:
                raise ValueError("Patch candidate readback mismatch")
            back[at:at+len(new)]=old
        if bytes(back)!=self.source or len(out)!=len(self.source):
            raise ValueError("Patch reversal/length mismatch")
        return bytes(out)


def validate_delta(delta):
    if (not isinstance(delta,(tuple,list)) or len(delta)!=3
            or any(type(x) not in (int,float) or not math.isfinite(x)
                   or abs(x)>MAX_DELTA for x in delta) or not any(delta)):
        raise ValueError("Expected nonzero finite translation within +/-16 source units")
    return tuple(float(x) for x in delta)


def moved(v,delta):
    q=tuple(f32(x+d) for x,d in zip(v,delta))
    if (not all(math.isfinite(x) for x in q)
            or any(abs((y-x)-d)>MAX_ROUNDING for x,y,d in zip(v,q,delta))):
        raise ValueError("Unrepresentable source position translation")
    return q


def translate_model(model,frame,nodes,delta):
    patch=BytePatch(model)
    for rec,(plane,sphere,n) in zip(frame["node_records"],nodes):
        at,size=rec["start"],rec["length"]
        w=f32(plane[3]+sum(a*b for a,b in zip(plane[:3],delta)))
        if abs((w-plane[3])-sum(a*b for a,b in zip(plane[:3],delta)))>MAX_ROUNDING:
            raise ValueError("Model plane translation exceeds float32 tolerance")
        patch.add(at+12,struct.pack("<f",w))
        patch.add(at+size-53,struct.pack("<3f",*moved(sphere[:3],delta)))
    return patch.finish()


def translate_level(level,blocks,polygons,flat_proof,mopp_proof,delta):
    patch=BytePatch(level)
    flat_at=flat_proof["level_flat_vertex_array_offset"]
    ordinal=0
    new_flat=[]
    for b in blocks:
        s=b["offset"]
        nv,_,_,_,_,_,nsv=struct.unpack_from("<7I",level,s+40)
        xyz=[moved(v[0],delta) for v in b["vertices"]]
        box,center,radius=bounds_of(xyz)
        old_radius=struct.unpack_from("<f",level,s+24)[0]
        if abs(old_radius-radius)>RADIUS_TOL:
            raise ValueError("Rigid translation changes packed radius outside tolerance")
        patch.add(s,struct.pack("<6f",*box))
        patch.add(s+28,struct.pack("<3f",*center))
        for i,v in enumerate(xyz):
            patch.add(s+80+32*i,struct.pack("<3f",*v))
            q=scaled_position(v)
            new_flat.append(q)
            patch.add(flat_at+16*ordinal,struct.pack("<3f",*q))
            ordinal+=1
        shadow_at=s+80+nv*32
        for i in range(nsv):
            v=struct.unpack_from("<3f",level,shadow_at+16*i)
            patch.add(shadow_at+16*i,struct.pack("<3f",*moved(v,delta)))
    for row in polygons:
        for i,v in enumerate(row["vertices"]):
            patch.add(row["start"]+2+i*STRIDE,struct.pack("<3f",*moved(v[:3],delta)))
    origin_at=mopp_proof["mopp_code_start_in_level"]-20
    old_origin=struct.unpack_from("<4f",level,origin_at)
    new_origin=tuple(f32(min(v[k] for v in new_flat)-mopp.MOPP_OFFSET_EXPANSION)
                     for k in range(3))
    patch.add(origin_at,struct.pack("<3f",*new_origin))
    if ordinal!=flat_proof["render_and_flat_vertex_count"]:
        raise ValueError("Flattened vertex translation inventory mismatch")
    max_drift=0.
    for i,q in enumerate(new_flat):
        v=struct.unpack_from("<3f",level,flat_at+16*i)
        drift=max(abs(((q[k]-new_origin[k])-(v[k]-old_origin[k]))
                      *old_origin[3]/65536.) for k in range(3))
        max_drift=max(max_drift,drift)
    if max_drift>.01:
        raise ValueError("Rigid translation changes root quantized coordinates beyond research limit")
    return patch.finish(),max_drift


def _centroid_comparison(level,changed,flat_proof,mopp_proof,limit):
    if type(limit) is not int or not 0<=limit<=300000:
        raise ValueError("Invalid centroid sample count")
    if limit==0:
        return {}
    n=flat_proof["render_and_flat_triangle_count"]
    va=flat_proof["level_flat_vertex_array_offset"]
    ia=flat_proof["level_flat_index_array_offset"]
    ca,ce=mopp_proof["mopp_code_start_in_level"],mopp_proof["mopp_code_end_in_level"]
    ids=struct.unpack_from("<"+str(3*n)+"I",level,ia)
    walkers=[ConservativeMoppPointCandidates(x[ca:ce],n,
             struct.unpack_from("<4f",x,ca-20)) for x in (level,changed)]
    leaves=sorted(walkers[0].complete_leaf_set)
    samples=leaves if len(leaves)<=limit else [
        leaves[i*(len(leaves)-1)//max(1,limit-1)] for i in range(limit)]
    counts=Counter()
    for tid in samples:
        candidates=[]
        for x,w in zip((level,changed),walkers):
            verts=[struct.unpack_from("<3f",x,va+16*j) for j in ids[3*tid:3*tid+3]]
            center=tuple(sum(v[k] for v in verts)/3 for k in range(3))
            candidates.append(set(w.point(center)["candidate_triangle_ids"]))
        counts["centroid_samples"]+=1
        counts["centroid_original_misses"]+=int(tid not in candidates[0])
        counts["centroid_translated_misses"]+=int(tid not in candidates[1])
        counts["centroid_candidate_sets_changed"]+=int(candidates[0]!=candidates[1])
        counts["centroid_new_misses"]+=int(tid in candidates[0] and tid not in candidates[1])
    if counts["centroid_new_misses"]:
        raise ValueError("Translated source centroid lost its original candidate")
    return dict(counts)


def audit_map(path,*,delta=None,centroids=64):
    path=Path(path)
    if (path.suffix.casefold()!=".gmp" or not path.is_file() or path.is_symlink()
            or path.stat().st_size>MAX_GMP):
        raise ValueError("Expected bounded original user-owned GMP")
    raw=path.read_bytes()
    pin=hashlib.sha256(raw).hexdigest()
    context=_read_context(path,raw)
    pkg,exp,level,model,blocks,polys,links,collision,inventory,end=context
    packed,shadow_links,max_shadow=inspect_packed_positions(level,blocks)
    flat_proof,exact=inspect_flat_exact(level,blocks)
    mopp_proof=mopp.inspect_mopp_link(level,blocks)
    frame,nodes=inspect_model_positions(model)
    model_counts,model_links=match_model_candidates(polys,nodes)
    block_frame=validate_counted_render_array(level,blocks,collision)
    prefix=block_frame["render_block_count_offset"]
    ref=world._parse_world_model(pkg)
    counts=Counter(packed)
    counts.update(exact)
    counts.update(model_counts)
    counts["model_zero_reserved_records"]=len(nodes)
    counts["unmodified_level_prefix_bytes"]=prefix
    counts["original_mopp_leaves"]=mopp_proof["unique_valid_mopp_triangle_leaves"]
    result={"source_map":path.name,"source_sha256":pin,"counts":dict(counts),
            "max_shadow_nearest_distance":max_shadow}
    if delta is not None:
        delta=validate_delta(delta)
        level2,drift=translate_level(level,blocks,polys,flat_proof,mopp_proof,delta)
        model2=translate_model(model,frame,nodes,delta)
        me=pkg.exports[ref["world_model_export_ref"]-1]
        patch=BytePatch(raw)
        for e,before,after in ((exp,level,level2),(me,model,model2)):
            if len(before)!=e["size"] or raw[e["offset"]:e["offset"]+e["size"]]!=before:
                raise ValueError("Original export offset or size mismatch")
            patch.add(e["offset"],after)
        candidate=patch.finish()
        if candidate==raw:
            raise ValueError("Translation produced no change")
        after=_read_context(path,candidate)
        p2,e2,l2,m2,b2,poly2,links2,col2,inv2,end2=after
        if (p2.names!=pkg.names or p2.imports!=pkg.imports or p2.exports!=pkg.exports
                or e2!=exp or l2!=level2 or m2!=model2 or links!=links2
                or collision!=col2 or inventory!=inv2 or end!=end2
                or level[:prefix]!=l2[:prefix]):
            raise ValueError("Translated package reparse or source structure mismatch")
        packed2,shadow_links2,_=inspect_packed_positions(l2,b2)
        flat2,exact2=inspect_flat_exact(l2,b2)
        mopp2=mopp.inspect_mopp_link(l2,b2)
        frame2,nodes2=inspect_model_positions(m2)
        model_counts2,model_links2=match_model_candidates(poly2,nodes2)
        ca,ce=mopp_proof["mopp_code_start_in_level"],mopp_proof["mopp_code_end_in_level"]
        if (shadow_links!=shadow_links2 or model_links!=model_links2
                or flat_proof["level_flat_index_array_offset"]!=flat2["level_flat_index_array_offset"]
                or level[flat_proof["level_flat_index_array_offset"]:flat_proof["level_flat_index_array_end"]]
                   !=l2[flat2["level_flat_index_array_offset"]:flat2["level_flat_index_array_end"]]
                or (ca,ce)!=(mopp2["mopp_code_start_in_level"],mopp2["mopp_code_end_in_level"])
                or level[ca:ce]!=l2[ca:ce]
                or level[ca-8:ca]!=l2[ca-8:ca]
                or mopp_proof["omitted_zero_area_triangle_ids"]!=mopp2["omitted_zero_area_triangle_ids"]):
            raise ValueError("Translated shadow/Model association, topology or MOPP code changed")
        counts.update(_centroid_comparison(level,l2,flat_proof,mopp_proof,centroids))
        counts["translated_maps"]=1
        counts["translated_changed_bytes"]=sum(a!=b for a,b in zip(raw,candidate))
        result.update({"counts":dict(counts),"root_quantized_max_drift":drift,
                       "full_package_exact_reverse":True,"package_reparse_passed":True,
                       "shadow_candidate_links_unchanged":True,
                       "model_candidate_links_unchanged":True,
                       "mopp_bytecode_and_leaf_ids_unchanged":True})
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError("Original GMP changed during audit")
    return result


def audit_maps(paths,*,delta=None,centroids=64):
    if not 1<=len(paths)<=world.MAX_MAPS or len({Path(p).resolve() for p in paths})!=len(paths):
        raise ValueError("Expected 1..64 distinct original maps")
    rows=[audit_map(p,delta=delta,centroids=centroids) for p in paths]
    counts=Counter()
    for row in rows:
        counts.update(row["counts"])
    return {"schema":SCHEMA,"map_count":len(rows),"summary":dict(counts),
            "max_shadow_nearest_distance":max(r["max_shadow_nearest_distance"] for r in rows),
            "max_root_quantized_drift":max((r.get("root_quantized_max_drift",0.) for r in rows)),
            "translation":delta,"source_files_modified":False,"gmp_output_enabled":False,
            "level_prefix_position_semantics_decoded":False,"actors_translated":False,
            "native_csg_rebuilt":False,"mopp_compiler_implemented":False,
            "retail_runtime_verified":False,"maps":rows}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",type=Path,nargs="+")
    p.add_argument("--delta",type=float,nargs=3,metavar=("DX","DY","DZ"))
    p.add_argument("--centroids",type=int,default=64,help="Per-map deterministic centroid sample cap; 0 disables")
    p.add_argument("--report",type=Path)
    a=p.parse_args(argv)
    try:
        result=audit_maps(a.maps,delta=a.delta,centroids=a.centroids)
        if a.report:
            world.write_report(result,a.report,a.maps)
        print(json.dumps({k:v for k,v in result.items() if k!="maps"},indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,KeyError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
