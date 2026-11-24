#!/usr/bin/env python3
"""Private in-memory render/expanded/shadow synchronization experiment.

Only complete coupled-corner previews are eligible. Original indices and
material sections stay fixed. Model, spatial prefix and collision remain
unchanged, so the candidate is NOT a playable GMP and is never written.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from itertools import permutations
import json
import math
from pathlib import Path
import struct

from dx2scene import find_bsp
from experimental_polygon_uv import _read_context, MAX_GMP, UV_PAIR_OFFSETS
from inspect_level_expanded_polygons import (
    STRIDE, UV_REPEAT_TOL, parse_expanded_polygons, match_expanded_render,
    match_model_candidates,
)
from inspect_level_polygon_uv_basis import fit_affine_uv, decode_tangent_like, UV_PREVIEW_TOL
from inspect_vbsp_coupled_corners import load_context, select_plane, coupled_preview
from inspect_world_position_dependencies import (
    BytePatch, bounds_of, f32, inspect_packed_positions, inspect_model_positions,
    SHADOW_TOL,
)
import inspect_level_world_model as world

SCHEMA = 'DX2SDK-coupled-fixed-width-render-shadow-sync-v1'
TANGENT_DOT = .9999
POSITION_ROUND_TOL = .002


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def round_tuple(v):
    out = tuple(f32(x) for x in v)
    if not all(math.isfinite(x) and abs(x)<1e6 for x in out):
        raise ValueError('Unrepresentable render coordinate or UV')
    return out


def shadow_corner_order(shadow, render):
    """Require a unique source XYZ assignment for the validated cap triangle."""
    if len(shadow) != 3 or len(render) != 3:
        raise ValueError('Expected three shadow and render corners')
    candidates = {p for p in permutations(render) if all(
        math.dist(a,b)<=SHADOW_TOL for a,b in zip(shadow,p))}
    if len(candidates)!=1:
        raise ValueError('Ambiguous shadow corner assignment')
    return next(iter(candidates))


def _check_tangent(before, after, packed_words):
    a=fit_affine_uv([v[:3] for v in before],[v[6:8] for v in before])
    b=fit_affine_uv([v[0] for v in after],[v[1] for v in after])
    if (a['max_uv_error']>UV_PREVIEW_TOL or b['max_uv_error']>UV_PREVIEW_TOL
            or a['max_plane_error']>.15 or b['max_plane_error']>.15
            or abs(dot(a['normal'],b['normal']))<TANGENT_DOT
            or a['tangent_direction'] is None or b['tangent_direction'] is None
            or dot(a['tangent_direction'],b['tangent_direction'])<TANGENT_DOT):
        raise ValueError('Candidate changes or lacks verified original texture basis')
    for raw in packed_words:
        direction,alpha,white=decode_tangent_like(raw)
        if (alpha!=255 or not white or abs(math.sqrt(dot(direction,direction))-1)>.02
                or abs(dot(direction,a['normal']))>.02 or min(dot(direction,t) for t in (
                a['tangent_direction'],b['tangent_direction']))<=.98):
            raise ValueError('Original tangent-like word not supported by both UV bases')


def sync_render(level, blocks, polygons, links, faces):
    """Return a reversible Level-only render candidate and aggregate proof."""
    patch=BytePatch(level)
    counts=Counter()
    positions={}
    target={}
    seen=set()
    changed_blocks=set()
    for face in faces:
        i=face['source_polygon']
        if type(i) is not int or not 0<=i<len(polygons) or i in seen:
            raise ValueError('Invalid candidate polygon identity')
        seen.add(i)
        row,link=polygons[i],links[i]
        vs=row['vertices']
        candidate=face['vertices']
        bi,start=link['packed_block'],link['packed_vertex_start']
        block=blocks[bi]
        if (row['polygon']!=i or link['polygon']!=i or len(vs)!=len(candidate)
                or len(vs)!=link['packed_vertex_count'] or not 0<=start<=len(block['vertices'])-len(vs)):
            raise ValueError('Candidate changes original render topology')
        after=[]
        words=[]
        for j,(v,new) in enumerate(zip(vs,candidate)):
            if new['source_corner']!=j:
                raise ValueError('Candidate changes original source corner identity')
            xyz,uv=round_tuple(new['xyz']),round_tuple(new['primary_uv'])
            if math.dist(xyz,new['xyz'])>POSITION_ROUND_TOL:
                raise ValueError('Candidate render position rounding exceeded tolerance')
            a=row['start']+2+j*STRIDE
            b=block['offset']+80+(start+j)*32
            if (struct.unpack_from('<23f',level,a)!=v or block['vertices'][start+j][0]!=v[:3]
                    or struct.unpack_from('<3f',level,b)!=v[:3] or b+32>block['end']):
                raise ValueError('Candidate render source byte mismatch')
            old_uv=level[a+24:a+32]
            if level[a+32:a+68]!=bytes(36) or any(level[a+k:a+k+8]!=old_uv for k in UV_PAIR_OFFSETS):
                raise ValueError('Unsupported expanded UV duplicate profile')
            repeat=link['packed_uv_integer_delta']
            packed_uv=round_tuple(tuple(x+d for x,d in zip(uv,repeat)))
            if any(abs(x-y-d)>UV_REPEAT_TOL for x,y,d in zip(packed_uv,uv,repeat)):
                raise ValueError('Candidate packed UV repeat offset is unrepresentable')
            # Exact unchanged source UV pairs stay byte-identical, including
            # their original rounding differences at integer texture repeats.
            if uv==v[6:8]:
                packed_uv=block['vertices'][start+j][2]
            after.append((xyz,uv))
            words.append(level[b+24:b+32])
            for at,value in ((a,struct.pack('<3f',*xyz)),(b,struct.pack('<3f',*xyz)),
                             (b+16,struct.pack('<2f',*packed_uv)),
                             *((a+k,struct.pack('<2f',*uv)) for k in UV_PAIR_OFFSETS)):
                if level[at:at+len(value)]!=value:
                    patch.add(at,value)
            target[bi,start+j]=xyz
            if v[:3] in positions and positions[v[:3]]!=xyz:
                raise ValueError('Candidate source-coincident corners separate')
            positions[v[:3]]=xyz
            counts['render_candidate_vertices']+=1
            counts['render_changed_xyz_vertices']+=int(xyz!=v[:3])
            counts['render_changed_uv_vertices']+=int(uv!=v[6:8])
        _check_tangent(vs,after,words)
        changed_blocks.add(bi)
        counts['render_candidate_faces']+=1
    _,shadow_links,_=inspect_packed_positions(level,blocks)
    # Check every cap in touched blocks, not just caps of selected faces.
    for bi,cap,locs in shadow_links:
        if bi not in changed_blocks:
            continue
        if len(locs)!=1:
            raise ValueError('Ambiguous original shadow triangle locator')
        _,si,ti=locs[0]
        block=blocks[bi]
        ids=block['sections'][si]['indices'][3*ti:3*ti+3]
        render=[block['vertices'][j][0] for j in ids]
        at=block['offset']+80+len(block['vertices'])*32+cap*3*16
        shadow=[struct.unpack_from('<3f',level,at+j*16) for j in range(3)]
        order=shadow_corner_order(shadow,render)
        counts['shadow_caps_checked_in_candidate_blocks']+=1
        for j,(s,p) in enumerate(zip(shadow,order)):
            idx=ids[render.index(p)]
            q=target.get((bi,idx),p)
            if q==p:
                continue
            moved=round_tuple(tuple(x+y-z for x,y,z in zip(s,q,p)))
            if math.dist(tuple(x-y for x,y in zip(moved,q)),tuple(x-y for x,y in zip(s,p)))>POSITION_ROUND_TOL:
                raise ValueError('Shadow source offset rounding exceeded tolerance')
            patch.add(at+j*16,struct.pack('<3f',*moved))
            counts['shadow_vertices_moved']+=1
    for bi in changed_blocks:
        block=blocks[bi]
        xyz=[target.get((bi,j),v[0]) for j,v in enumerate(block['vertices'])]
        box,center,radius=bounds_of(xyz)
        at=block['offset']
        data=struct.pack('<10f',*box,f32(radius),*center)
        if level[at:at+40]!=data:
            patch.add(at,data)
            counts['render_block_bounds_updated']+=1
    modified=patch.finish()
    counts['render_patch_spans']=len(patch.spans)
    counts['render_patch_changed_bytes']=sum(a!=b for a,b in zip(level,modified))
    return modified,dict(counts),shadow_links


def audit_map(path,delta):
    path=Path(path)
    if (path.suffix.casefold()!='.gmp' or not path.is_file() or path.is_symlink()
            or path.stat().st_size>MAX_GMP):
        raise ValueError('Expected bounded original user-owned GMP')
    raw=path.read_bytes()
    pin=hashlib.sha256(raw).hexdigest()
    pkg,exp,level,model,blocks,polys,links,collision,inventory,end=_read_context(path,raw)
    tail,polys2,owners,blocks2,links2,collision2=load_context(path,raw)
    if polys!=polys2 or blocks!=blocks2 or links!=links2 or collision!=collision2:
        raise ValueError('Independent original coupled context mismatch')
    pi=select_plane(tail,polys,owners)
    preview=coupled_preview(tail,polys,owners,pi,delta,blocks=blocks,links=links,include_geometry=True)
    faces=preview['private_preview_geometry']['faces']
    counts=Counter()
    counts['geometry_gate_passed']=int(preview['coupled_corner_preview_passed'])
    # A separate source Model candidate association audit, never a Model write.
    _,nodes=inspect_model_positions(model)
    _,matches=match_model_candidates(polys,nodes)
    node_refs=Counter(j for c in matches for j in c)
    for face in faces:
        c=matches[face['source_polygon']]
        counts['preview_model_faces']+=1
        counts['preview_model_unique_both_directions']+=int(len(c)==1 and node_refs[c[0]]==1)
    status='geometry_gate_refused'
    reason=None
    if preview['coupled_corner_preview_passed']:
        try:
            modified,rc,old_shadow=sync_render(level,blocks,polys,links,faces)
            at=exp['offset']
            candidate=raw[:at]+modified+raw[at+len(level):]
            p2=world.Package(path,data=candidate)
            if (p2.names!=pkg.names or p2.imports!=pkg.imports or p2.exports!=pkg.exports
                    or p2.payload(exp)!=modified or len(candidate)!=len(raw)):
                raise ValueError('Render-only candidate package framing changed')
            b2=find_bsp(p2)
            if len(b2)!=len(blocks) or any((a['offset'],a['end'],a['id'],a['sections'])!=(b['offset'],b['end'],b['id'],b['sections']) for a,b in zip(blocks,b2)):
                raise ValueError('Candidate render block topology changed')
            expanded,_=parse_expanded_polygons(modified,polys[0]['start'],end,sum(len(b['vertices']) for b in b2))
            _,new_links=match_expanded_render(expanded,b2)
            if new_links!=links:
                raise ValueError('Candidate expanded/packed crosswalk changed')
            _,new_shadow,_=inspect_packed_positions(modified,b2)
            if new_shadow!=old_shadow or modified[end:]!=level[end:] or modified[:blocks[0]['offset']]!=level[:blocks[0]['offset']]:
                raise ValueError('Candidate shadow ownership or untouched Level spans changed')
            counts.update(rc)
            counts['render_sync_passed']=1
            status='render_only_roundtrip_passed'
        except (ValueError,struct.error,IndexError,KeyError,OverflowError) as exc:
            status='render_sync_refused'
            reason=str(exc)
            counts['render_sync_refused']=1
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError('Original GMP changed during render audit')
    return {'source_map':path.name,'source_sha256':pin,'plane_index':pi,'delta_d':delta,
            'status':status,'reason':reason,'counts':dict(counts),
            'native_geometry_writer_enabled':False,'retail_runtime_verified':False,
            'model_collision_and_spatial_prefix_unmodified':True}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('maps',nargs='+',type=Path)
    p.add_argument('--delta-d',type=float,default=1.)
    p.add_argument('--report',type=Path)
    a=p.parse_args(argv)
    try:
        if not 1<=len(a.maps)<=world.MAX_MAPS or len({v.resolve() for v in a.maps})!=len(a.maps):
            raise ValueError('Expected distinct original maps')
        rows=[audit_map(path,a.delta_d) for path in a.maps]
        counts=Counter()
        for r in rows:counts.update(r['counts'])
        result={'schema':SCHEMA,'map_count':len(rows),'summary':dict(counts),'maps':rows,
                'source_files_modified':False,'candidate_gmp_written':False,'retail_runtime_verified':False}
        if a.report:world.write_report(result,a.report,a.maps)
        print(json.dumps({k:v for k,v in result.items() if k!='maps'},indent=2,allow_nan=False))
        return 0
    except (ValueError,OSError,IndexError,KeyError,struct.error,OverflowError) as exc:
        print(json.dumps({'status':'refused','reason':str(exc)}))
        return 2

if __name__=='__main__':raise SystemExit(main())
