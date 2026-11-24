#!/usr/bin/env python3
"""Decode the post-graph spatial grids and VBSP v2, with offline point queries.

All inputs are private original GMPs. The opaque header words, saved pointer
values and non-coordinate fields are retained, not interpreted as host pointers.
No GMP output, runtime visibility solver, or native tree compiler.
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
from inspect_world_position_dependencies import BytePatch, moved, f32, validate_delta
import inspect_level_world_model as world

SCHEMA = "DX2SDK-Level-spatial-grid-VBSP-v2-research-v1"
MAX_RECORDS = 300000
GRID_SPACING = 192
VECTOR_SPACING = 24
LATTICE_TOL = .002
PORTAL_TOL = .15
PORTAL_PROBE = .1
GRID_VALUES = frozenset((0,32,60,85,107,126,143,157,170,181,191,199,
                         206,213,219,224,228,232,255))


def _finite(v):
    return all(math.isfinite(x) and abs(x)<1e6 for x in v)


def locate_point(nodes,planes,point):
    """Offline source-tree traversal. Positive/zero side selects child 0."""
    if len(point)!=3 or not _finite(point):
        raise ValueError("Invalid VBSP point")
    i=0
    for _ in range(len(nodes)):
        flags,a,b,*_=nodes[i]
        plane=planes[flags>>2]
        side=int(sum(x*y for x,y in zip(point,plane[:3]))+plane[3]<0)
        child=(a,b)[side]
        if child==-1 or flags&(1<<side):
            return child
        i=child
    raise ValueError("VBSP point traversal cycle")


def parse_spatial_tail(level,start,end):
    """Decode a complete source-bounded spatial tail and all VBSP arrays."""
    if type(level) is not bytes or not 0<=start<end<=len(level):
        raise ValueError("Invalid spatial tail envelope")
    at=start
    rebuilt=bytearray()
    counts=Counter()
    coordinates=[]
    plane_offsets=[]
    def take(fmt):
        nonlocal at
        size=struct.calcsize(fmt)
        if at+size>end:
            raise ValueError("Truncated spatial tail")
        v=struct.unpack_from(fmt,level,at)
        rebuilt.extend(struct.pack(fmt,*v))
        at+=size
        return v
    def bounded(n,minimum,stride):
        if not minimum<=n<=MAX_RECORDS or at+n*stride>end:
            raise ValueError("Invalid counted spatial array")
    version,n=take("<II")
    if version!=1:
        raise ValueError("Unknown grid version")
    bounded(n,1,92)
    base=None
    keys=set()
    for _ in range(n):
        x,y,ox,oy,oz,layers=take("<ii3fI")
        coordinates.append((at-16,(ox,oy,oz)))
        if not _finite((ox,oy,oz)) or layers!=1 or abs(x)>10000 or abs(y)>10000:
            raise ValueError("Unsupported source grid cell")
        origin=(ox-GRID_SPACING*x,oy-GRID_SPACING*y)
        if base is None:
            base=origin
        if any(abs(a-b)>LATTICE_TOL for a,b in zip(origin,base)):
            raise ValueError("Grid cell XY origin disagrees with 192-unit lattice")
        keys.add((x,y))
        size,=take("<I")
        if size!=64:
            raise ValueError("Expected one 8x8 byte grid")
        payload,=take("<64s")
        if not set(payload)<=GRID_VALUES:
            raise ValueError("Unknown source grid byte profile")
    counts.update(grid_cells=n,grid_unique_xy=len(keys),grid_bytes=64*n)
    k,=take("<I")
    bounded(k,0,24)
    for _ in range(k):
        x,y,z,nx,ny,nz=take("<6f")
        coordinates.append((at-24,(x,y,z)))
        if (not _finite((x,y,z,nx,ny,nz)) or nz!=0
                or abs(abs(nx)-math.sqrt(.5))>.001
                or abs(abs(ny)-math.sqrt(.5))>.001
                or any(abs(v-b-round((v-b)/VECTOR_SPACING)*VECTOR_SPACING)>LATTICE_TOL
                       for v,b in zip((x,y),base))):
            raise ValueError("Invalid lattice point or diagonal direction")
    counts["grid_directional_points"]=k
    vbsp_at=at
    tag,=take("<I")
    header=take("<22I")
    magic,version,nn,nl,z,np,nt,z2,nref,nport,nv=header[:11]
    if magic!=0x50534256 or version!=2 or z or z2:
        raise ValueError("Expected supported VBSP v2 header")
    for count in (nn,nl,np,nt,nref,nport,nv):
        if not 0<=count<=MAX_RECORDS:
            raise ValueError("VBSP count exceeds bounded profile")
    if not nn or not nl or not np:
        raise ValueError("Empty VBSP tree")
    p=header[11:19]
    # Serialized 32-bit values are saved addresses; only differences matter.
    expected=[p[0]]
    for count,stride in ((nn,36),(nl,52),(np,16),(nport,24),(nv,12)):
        expected.append(expected[-1]+count*stride)
    if (not p[0] or tuple(expected)!=p[:6] or p[6]!=0
            or p[7]!=p[5]+4*(nt+1)):
        raise ValueError("VBSP saved pointer differences disagree with array sizes")
    if at+36*nn+52*nl+16*np+24*nport+12*nv+4*nt!=end:
        raise ValueError("VBSP array sizes do not exhaust source span")
    nodes=[]
    node_refs=Counter()
    leaf_refs=Counter()
    for i in range(nn):
        row=take("<9i")
        nodes.append(row)
        flags,a,b,*reserved=row
        if not 0<=flags>>2<np or any(reserved):
            raise ValueError("Invalid VBSP packed plane or node reserved words")
        for bit,child in enumerate((a,b)):
            if child==-1:
                counts["vbsp_solid_sentinels"]+=1
            elif flags&(1<<bit):
                if not 0<=child<nl:
                    raise ValueError("VBSP leaf reference out of range")
                leaf_refs[child]+=1
            else:
                if not 0<=child<nn:
                    raise ValueError("VBSP child node out of range")
                node_refs[child]+=1
    if (node_refs!=Counter({i:1 for i in range(1,nn)})
            or leaf_refs!=Counter({i:1 for i in range(nl)})):
        raise ValueError("VBSP child/leaf ownership is not unique")
    visited=set()
    stack=[0]
    while stack:
        i=stack.pop()
        if i in visited:
            raise ValueError("Cyclic VBSP child graph")
        visited.add(i)
        f,a,b,*_=nodes[i]
        stack.extend(j for bit,j in enumerate((a,b))
                     if j!=-1 and not f&(1<<bit))
    if len(visited)!=nn:
        raise ValueError("Unreachable VBSP child nodes")
    leaves=[]
    for _ in range(nl):
        row=take("<5i6f2i")
        a,b,c,d,sentinel,*rest=row
        box=rest[:6]
        if (not 0<=a<=b<=nref or not 0<=c<=d<=nport or sentinel!=-1
                or not _finite(box) or any(x>y for x,y in zip(box[:3],box[3:]))):
            raise ValueError("Invalid VBSP leaf source ranges or bounds")
        coordinates.extend(((at-32,tuple(box[:3])),(at-20,tuple(box[3:]))))
        leaves.append(row)
    planes=[]
    for _ in range(np):
        row=take("<4f")
        if not _finite(row) or abs(sum(v*v for v in row[:3])-1)>.001:
            raise ValueError("Invalid VBSP plane")
        plane_offsets.append((at-4,row))
        planes.append(row)
    portals=[]
    vertex_cursor=0
    for _ in range(nport):
        row=take("<6i")
        a,b,c,d,ref,reserved=row
        index=ref if ref>=0 else ~ref
        if (not 0<=a<nl or not 0<=b<nl or a==b or c!=vertex_cursor
                or not c+3<=d<=nv or not 0<=index<np or reserved):
            raise ValueError("Invalid VBSP portal range, leaf or plane reference")
        vertex_cursor=d
        portals.append(row)
    if vertex_cursor!=nv:
        raise ValueError("VBSP portal vertex ranges do not cover array")
    # Both leaf range arrays have complete one-to-one ordinal coverage.
    # Expanded polygon inventory is independently checked in the crosswalk.
    owners=Counter()
    owner_count=0
    by_first_owner=defaultdict(list)
    for i,portal in enumerate(portals):
        by_first_owner[portal[0]].append(i)
    for i,row in enumerate(leaves):
        a,b,c,d=row[:4]
        if b-a>nref or owner_count+b-a>nref:
            raise ValueError("VBSP polygon ranges exceed total inventory")
        owners.update(range(a,b))
        owner_count+=b-a
        if list(range(c,d))!=by_first_owner[i]:
            raise ValueError("VBSP leaf portal range disagrees with first owner")
    if len(owners)!=nref or any(v!=1 for v in owners.values()):
        raise ValueError("VBSP polygon range partition has a gap or overlap")
    counts["vbsp_leaf_portal_ranges_verified"]=nl
    counts["vbsp_polygon_range_ordinals"]=nref
    vertices=[]
    for _ in range(nv):
        row=take("<3f")
        if not _finite(row):
            raise ValueError("Invalid VBSP portal vertex")
        coordinates.append((at-12,row))
        vertices.append(row)
    tail=take("<"+str(nt)+"I")
    if any(i>=nl for i in tail):
        raise ValueError("VBSP final candidate leaf list out of range")
    if at!=end or bytes(rebuilt)!=level[start:end]:
        raise ValueError("Spatial tail decode/encode no-op differs from source")
    point_links=[]
    for a,b,c,d,ref,_ in portals:
        plane=planes[ref if ref>=0 else ~ref]
        xyz=vertices[c:d]
        if max(abs(sum(x*y for x,y in zip(v,plane[:3]))+plane[3])
               for v in xyz)>PORTAL_TOL:
            raise ValueError("VBSP portal polygon not on referenced plane")
        center=tuple(sum(v[j] for v in xyz)/len(xyz) for j in range(3))
        points=[tuple(x+sign*PORTAL_PROBE*y for x,y in zip(center,plane[:3]))
                for sign in (1,-1)]
        pair=tuple(locate_point(nodes,planes,v) for v in points)
        if set(pair)!={a,b}:
            raise ValueError("VBSP portal side probe disagrees with recorded leaf pair")
        point_links.append(pair)
    counts.update(vbsp_nodes=nn,vbsp_leaves=nl,vbsp_planes=np,
                  vbsp_portals=nport,vbsp_portal_vertices=nv,vbsp_final_leaf_ids=nt,
                  vbsp_unique_node_refs=len(node_refs),vbsp_unique_leaf_refs=len(leaf_refs),
                  vbsp_portal_plane_matches=nport,vbsp_portal_side_probes=2*nport,
                  vbsp_portal_leaf_pairs_verified=nport,spatial_tail_bytes=end-start,
                  vbsp_bytes=end-vbsp_at)
    counts["vbsp_leaf_centers_classify_to_self"]=sum(
        locate_point(nodes,planes,tuple((a+b)/2 for a,b in zip(row[5:8],row[8:11])))==i
        for i,row in enumerate(leaves))
    return {"counts":dict(counts),"vbsp_start":vbsp_at,"end":end,
            "coordinates":coordinates,"plane_offsets":plane_offsets,
            "nodes":nodes,"planes":planes,"leaves":leaves,"portals":portals,
            "portal_leaf_links":point_links,
            "source_noop_byte_identical":True}


def validate_leaf_render_ownership(tail,polygons,links,source_rows,block_frame):
    """Cross-check native VBSP leaf polygon ranges with independent Level data.

    Polygon order is the actual expanded stream order; packed block ordinal
    comes from the independently verified Level provenance table. No inferred
    Model node association is used here.
    """
    leaves=tail["leaves"]
    if (len(polygons)!=len(links)
            or len(polygons)!=tail["counts"]["vbsp_polygon_range_ordinals"]
            or len(leaves)!=block_frame["native_render_block_entries"]):
        raise ValueError("VBSP leaf/polygon/render-block inventories disagree")
    by_locator={tuple(row["render_locator"]):row for row in source_rows}
    if len(by_locator)!=len(source_rows):
        raise ValueError("Duplicate source triangle provenance locator")
    counts=Counter()
    owners=[None]*len(polygons)
    seen=set()
    for i,row in enumerate(leaves):
        lo,hi=row[5:8],row[8:11]
        a,b=row[:2]
        counts["vbsp_nonempty_render_leaves"]+=int(b>a)
        counts["vbsp_empty_render_leaves"]+=int(b==a)
        for j in range(a,b):
            poly,link=polygons[j],links[j]
            if (poly["polygon"]!=j or link["polygon"]!=j or owners[j] is not None):
                raise ValueError("VBSP polygon source ordinal mismatch")
            owners[j]=i
            vs=poly["vertices"]
            if not vs or not all(all(l-PORTAL_TOL<=x<=h+PORTAL_TOL
                          for x,l,h in zip(v[:3],lo,hi)) for v in vs):
                raise ValueError("Expanded polygon lies outside assigned VBSP leaf bounds")
            counts["vbsp_polygon_vertices_in_owner_bounds"]+=len(vs)
            locs=[tuple(k) for k in link["triangle_locators"]]
            if (not locs or len(set(locs))!=len(locs) or seen.intersection(locs)
                    or not set(locs)<=by_locator.keys()):
                raise ValueError("VBSP polygon triangle provenance incomplete or reused")
            if any(by_locator[k]["source_provenance_block_field_a"]!=i for k in locs):
                raise ValueError("VBSP leaf differs from native render block provenance ID")
            seen.update(locs)
            counts["vbsp_owned_render_triangles"]+=len(locs)
            counts["vbsp_owned_expanded_polygons"]+=1
            center=tuple(sum(v[k] for v in vs)/len(vs) for k in range(3))
            probe=tuple(x+PORTAL_PROBE*y for x,y in zip(center,vs[0][3:6]))
            counts["vbsp_polygon_normal_probe_owner_matches"]+=int(
                locate_point(tail["nodes"],tail["planes"],probe)==i)
    if (None in owners or seen!=set(by_locator)
            or counts["vbsp_nonempty_render_leaves"]!=block_frame["native_render_nonempty_blocks"]
            or counts["vbsp_empty_render_leaves"]!=block_frame["native_render_empty_blocks"]):
        raise ValueError("VBSP leaf ownership does not cover complete native render inventory")
    return dict(counts),owners


def translate_spatial_prefix(level,graph,tail,delta):
    """In-memory position patch of decoded graph and spatial tail only."""
    delta=validate_delta(delta)
    patch=BytePatch(level)
    start=graph["graph_start"]
    at=start+graph["zero_header_bytes"]
    n=struct.unpack_from("<I",level,at)[0]
    at+=4
    for _ in range(n):
        for j in range(3):
            offset=at+4+12*j
            patch.add(offset,struct.pack("<3f",*moved(struct.unpack_from("<3f",level,offset),delta)))
        at+=57
    en=struct.unpack_from("<I",level,at)[0]
    at+=4
    for _ in range(en):
        for j in range(2):
            offset=at+1+12*j
            patch.add(offset,struct.pack("<3f",*moved(struct.unpack_from("<3f",level,offset),delta)))
        at+=33
    for offset,v in tail["coordinates"]:
        patch.add(offset,struct.pack("<3f",*moved(v,delta)))
    for offset,plane in tail["plane_offsets"]:
        correction=sum(x*y for x,y in zip(plane[:3],delta))
        value=f32(plane[3]-correction)
        if abs((plane[3]-value)-correction)>.002:
            raise ValueError("VBSP plane translation exceeds rounding gate")
        patch.add(offset,struct.pack("<f",value))
    changed=patch.finish()
    g2=parse_prefix_graph(changed,start,tail["end"])
    t2=parse_spatial_tail(changed,g2["graph_end"],tail["end"])
    if (g2["graph_end"]!=graph["graph_end"] or t2["nodes"]!=tail["nodes"]
            or t2["portal_leaf_links"]!=tail["portal_leaf_links"]
            or changed[:start]!=level[:start] or changed[tail["end"]:]!=level[tail["end"]:]):
        raise ValueError("Translated spatial graph or portal side association changed")
    # Floating-point distance diagnostics may shift at a tolerance boundary.
    for before,after,allowed in ((graph["counts"],g2["counts"],{
            "prefix_graph_triangle_normal_coplanar","prefix_graph_edge_both_owner_planes_near",
            "prefix_graph_edge_one_owner_plane_near"}),
            (tail["counts"],t2["counts"],{"vbsp_leaf_centers_classify_to_self"})):
        if {k:v for k,v in before.items() if k not in allowed}!={
                k:v for k,v in after.items() if k not in allowed}:
            raise ValueError("Translated spatial record inventory changed")
    return changed,{"translated_prefix_maps":1,
                    "translated_prefix_position_spans":len(patch.spans),
                    "translated_prefix_changed_bytes":sum(x!=y for x,y in zip(level,changed)),
                    "translated_portal_side_probes":t2["counts"]["vbsp_portal_side_probes"]}


def audit_map(path,*,delta=None):
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
    owner_counts,_=validate_leaf_render_ownership(tail,polys,links,collision,frame)
    counts=Counter(tail["counts"])
    counts.update(owner_counts)
    counts["post_model_prefix_bytes"]=stop-cursor.at
    counts["post_model_prefix_graph_bytes"]=graph["graph_end"]-cursor.at
    if delta is not None:
        _,translated=translate_spatial_prefix(level,graph,tail,delta)
        counts.update(translated)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError("Original GMP changed during spatial audit")
    return {"source_map":path.name,"source_sha256":pin,"counts":dict(counts),
            "source_noop_byte_identical":True,"source_post_model_prefix_framed":True}


def audit_maps(paths,*,delta=None):
    if not 1<=len(paths)<=world.MAX_MAPS or len({Path(p).resolve() for p in paths})!=len(paths):
        raise ValueError("Expected 1..64 distinct original maps")
    rows=[audit_map(p,delta=delta) for p in paths]
    counts=Counter()
    for row in rows:
        counts.update(row["counts"])
    return {"schema":SCHEMA,"map_count":len(rows),"summary":dict(counts),
            "translation":delta,"source_files_modified":False,
            "native_vbsp_compiler_enabled":False,"native_navigation_semantics_verified":False,
            "saved_pointer_semantics_decoded":False,"gmp_output_enabled":False,
            "retail_runtime_verified":False,"maps":rows}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",nargs="+",type=Path)
    p.add_argument("--delta",type=float,nargs=3,metavar=("DX","DY","DZ"))
    p.add_argument("--report",type=Path)
    a=p.parse_args(argv)
    try:
        result=audit_maps(a.maps,delta=a.delta)
        if a.report:
            world.write_report(result,a.report,a.maps)
        print(json.dumps({k:v for k,v in result.items() if k!="maps"},indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,KeyError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
