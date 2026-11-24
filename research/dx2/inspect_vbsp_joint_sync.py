#!/usr/bin/env python3
"""In-memory coupled render/flat/MOPP and candidate Model synchronization.

No native file writer. Model correspondence remains geometric; the separate
navigation and grid dependencies remain unmodified.
"""
from collections import Counter
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from dx2scene import find_bsp
from experimental_polygon_uv import _read_context, MAX_GMP
from inspect_level_expanded_polygons import match_model_candidates
from inspect_vbsp_coupled_corners import load_context, select_plane, coupled_preview
from inspect_vbsp_render_sync import sync_render
from inspect_world_position_dependencies import (BytePatch, inspect_flat_exact,
    inspect_model_positions, inspect_packed_positions, scaled_position, f32)
from inspect_world_bsp_tree_links import inspect_link_graph
from inspect_mopp_axis_refit import refit_axis_bounds
from inspect_mopp_diagonal_refit import refit_diagonal_bounds
from inspect_mopp_rescale_rebase import rebase_rescale, intervals, signature, _rebase_choices
from inspect_mopp_axis_refit import assess
from inspect_mopp_axis_point_candidates import ConservativeMoppPointCandidates
from inspect_vbsp_candidate_collision import triangle_samples
import inspect_level_mopp_triangle_tree as mopp
import inspect_level_world_model as world
from inspect_vbsp_leaf_bounds import verify_leaf_boxes,sync_leaf_boxes
from inspect_vbsp_portal_sync import sync_portals
from inspect_vbsp_navigation_impact import audit_navigation_impact

SCHEMA='DX2SDK-joint-render-collision-model-research-v1'
TOL=.15
ROUND_TOL=.002


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def model_sphere(xyz):
    center=tuple(f32((min(v[k] for v in xyz)+max(v[k] for v in xyz))/2) for k in range(3))
    return (*center,f32(max(math.dist(v,center) for v in xyz)*1.001))


def model_plane_update(plane, before, after):
    shifts=[dot(plane[:3],tuple(y-x for x,y in zip(a,b))) for a,b in zip(before,after)]
    if not shifts or max(shifts)-min(shifts)>ROUND_TOL:
        raise ValueError('Model candidate plane does not translate rigidly')
    w=f32(plane[3]+sum(shifts)/len(shifts))
    if max(abs(dot(plane[:3],v)-w) for v in after)>TOL:
        raise ValueError('Updated Model plane no longer supports candidate face')
    return (*plane[:3],w)


def relation(a,b,field):
    plane,sphere,_=a
    other,center,_=b
    if field==5:
        eps=max(.001,2e-5*max(abs(v) for v in plane+other))
        return max(abs(x-y) for x,y in zip(plane,other))<=eps or max(abs(x+y) for x,y in zip(plane,other))<=eps
    d=dot(plane[:3],center[:3])-plane[3]
    eps=max(.001,2e-5*max(abs(v) for v in plane+center[:3]))
    return d < -eps if field==3 else d > eps


def model_sync(model,polygons,new_polys,faces):
    frame,nodes=inspect_model_positions(model)
    graph=inspect_link_graph(model,frame,include_edges=True)
    _,links=match_model_candidates(polygons,nodes)
    owners=Counter(j for row in links for j in row)
    counts=Counter(); patch=BytePatch(model); updated=set(); moved_planes=set()
    for face in faces:
        i=face['source_polygon']; old=polygons[i]; new=new_polys[i]
        before=[v[:3] for v in old['vertices']]; after=[v[:3] for v in new['vertices']]
        if before==after:continue
        counts['model_moved_faces']+=1
        c=links[i]
        if len(c)!=1 or owners[c[0]]!=1:
            counts['model_unresolved_moved_faces']+=1; continue
        j=c[0]; plane,sphere,n=nodes[j]
        if n!=len(before) or len(before)!=len(after):raise ValueError('Model candidate vertex count changed')
        if math.dist(model_sphere(before)[:3],sphere[:3])>TOL or abs(model_sphere(before)[3]-sphere[3])>TOL:
            raise ValueError('Source Model sphere hypothesis fails')
        p=model_plane_update(plane,before,after)
        s=model_sphere(after)
        rec=frame['node_records'][j]; at,size=rec['start'],rec['length']
        if p!=plane:
            patch.add(at+12,struct.pack('<f',p[3])); moved_planes.add(j)
        if s!=sphere:patch.add(at+size-53,struct.pack('<4f',*s))
        updated.add(j); counts['model_candidate_nodes_updated']+=1
    out=patch.finish(); f2,n2=inspect_model_positions(out)
    g2=inspect_link_graph(out,f2,include_edges=True)
    if graph['graph_edges']!=g2['graph_edges']:raise ValueError('Model graph topology changed')
    _,links2=match_model_candidates(new_polys,n2)
    counts['model_candidate_links_changed']=sum(a!=b for a,b in zip(links,links2))
    for e in graph['graph_edges']:
        i,j,k=e['parent'],e['child'],e['compact_field']
        if relation(nodes[i],nodes[j],k) and not relation(n2[i],n2[j],k):
            counts['model_new_link_geometry_violations']+=1
    # Distinct nodes sharing an original splitter plane may need a coupled
    # update even when a polygon association is absent. Do not guess it.
    aliases=set()
    for i in moved_planes:
        a=nodes[i][0]
        for j,(b,_,_) in enumerate(nodes):
            if j in updated:continue
            if min(max(abs(x-y) for x,y in zip(a,b)),max(abs(x+y) for x,y in zip(a,b)))<=ROUND_TOL:
                aliases.add(j)
    counts['model_unupdated_original_plane_aliases']=len(aliases)
    counts['model_changed_bytes']=sum(a!=b for a,b in zip(model,out))
    passed=not any(counts[k] for k in ('model_unresolved_moved_faces','model_candidate_links_changed',
        'model_new_link_geometry_violations','model_unupdated_original_plane_aliases'))
    return out,dict(counts),passed


def candidate_root(vertices,original):
    lo=[min(v[k] for v in vertices) for k in range(3)]
    hi=[max(v[k] for v in vertices) for k in range(3)]
    scale=mopp.MOPP_SCALE_NUMERATOR/(max(b-a for a,b in zip(lo,hi))+mopp.MOPP_SCALE_EXPANSION)
    if (max(abs(v-mopp.MOPP_OFFSET_EXPANSION-o) for v,o in zip(lo,original[:3]))<=mopp.MAX_OFFSET_ERROR
            and abs(original[3]-scale)/scale<=mopp.MAX_SCALE_RELATIVE_ERROR):
        return original
    return tuple(f32(v-mopp.MOPP_OFFSET_EXPANSION) for v in lo)+(f32(scale),)


def refit_root(code,original,candidate,old_root,new_root):
    states,req,roles=intervals(code,original,old_root)
    if assess(code,req,roles)['violated_axis_operands']:
        raise ValueError('Original root path proof failed')
    sig=signature(states)
    states,req,roles=intervals(code,candidate,new_root)
    choices=[None]
    if assess(code,req,roles)['infeasible_axis_operands']:
        choices=_rebase_choices(states,req,roles,code)
    for choice in choices:
        seed=bytearray(code)
        if choice is not None:seed[choice[2]]=choice[3]
        seed=bytes(seed)
        st,req,roles=intervals(seed,candidate,new_root)
        if signature(st)!=sig:raise ValueError('Root refit changed control flow')
        if assess(seed,req,roles)['infeasible_axis_operands']:continue
        out=bytearray(seed)
        for (at,width),(lo,hi) in req.items():
            old=int.from_bytes(seed[at:at+width],'big')
            out[at:at+width]=min(max(old,lo),hi).to_bytes(width,'big')
        out=bytes(out); st2,r2,roles2=intervals(out,candidate,new_root)
        if signature(st2)!=sig or assess(out,r2,roles2)['violated_axis_operands']:
            raise ValueError('Root refit verification failed')
        restored=bytearray(out)
        for at,width in req:restored[at:at+width]=code[at:at+width]
        if choice is not None:restored[choice[2]]=code[choice[2]]
        if bytes(restored)!=code:raise ValueError('Root refit changed unrelated bytes')
        return out,choice is not None
    raise ValueError('Root refit cannot represent candidate bounds')


def sync_collision(level,rendered,blocks,new_blocks):
    flat,_=inspect_flat_exact(level,blocks); proof=mopp.inspect_mopp_link(level,blocks)
    va=flat['level_flat_vertex_array_offset']; ia=flat['level_flat_index_array_offset']
    nv=flat['render_and_flat_vertex_count']; nt=flat['render_and_flat_triangle_count']
    ca,ce=proof['mopp_code_start_in_level'],proof['mopp_code_end_in_level']
    ids=struct.unpack_from('<'+str(3*nt)+'I',level,ia)
    old=[struct.unpack_from('<3f',level,va+16*i) for i in range(nv)]
    new=[scaled_position(v[0]) for b in new_blocks for v in b['vertices']]
    if len(new)!=nv:raise ValueError('Candidate collision vertex count changed')
    t0=[tuple(old[j] for j in ids[i:i+3]) for i in range(0,len(ids),3)]
    t1=[tuple(new[j] for j in ids[i:i+3]) for i in range(0,len(ids),3)]
    origin=struct.unpack_from('<4f',level,ca-20); code=level[ca:ce]
    root=candidate_root(new,origin)
    rebased=False
    if root!=origin:
        out,rebased=refit_root(code,t0,t1,origin,root)
    else:
        out,axis=refit_axis_bounds(code,t0,t1,origin)
        if out is not None:out,diag=refit_diagonal_bounds(out,t0,t1,origin)
        if out is None:out,rb=rebase_rescale(code,t0,t1,origin); rebased=out is not None
    if out is None:raise ValueError('Candidate MOPP fixed-width refit refused')
    patch=BytePatch(rendered); changed=0
    for i,(a,b) in enumerate(zip(old,new)):
        if a!=b:patch.add(va+16*i,struct.pack('<3f',*b));changed+=1
    if root!=origin:patch.add(ca-20,struct.pack('<4f',*root))
    if out!=code:patch.add(ca,out)
    result=patch.finish(); inspect_flat_exact(result,new_blocks)
    after=mopp.inspect_mopp_link(result,new_blocks)
    if after['omitted_zero_area_triangle_ids']!=proof['omitted_zero_area_triangle_ids'] or after['mopp_code_start_in_level']!=ca or after['mopp_code_end_in_level']!=ce:
        raise ValueError('Candidate collision source topology changed')
    walker=ConservativeMoppPointCandidates(out,nt,root)
    samples=0; changed_tri=0
    for i,(a,b) in enumerate(zip(t0,t1)):
        if a==b:continue
        changed_tri+=1
        if i not in walker.complete_leaf_set:raise ValueError('Moved nonleaf collision triangle')
        for p in triangle_samples(b):
            samples+=1
            for mode in ('conservative','derived_diagonals'):
                if i not in walker.point(p,diagonal_mode=mode)['candidate_triangle_ids']:
                    raise ValueError('Refit misses affected original triangle')
    return result,{'collision_vertices_updated':changed,'collision_triangles_changed':changed_tri,
        'collision_code_bytes_changed':sum(a!=b for a,b in zip(code,out)),
        'collision_rebased':int(rebased),'collision_root_updated':int(root!=origin),'collision_samples_passed':samples}


def audit_map(path,delta):
    path=Path(path)
    if path.suffix.casefold()!='.gmp' or not path.is_file() or path.is_symlink() or path.stat().st_size>MAX_GMP:
        raise ValueError('Expected bounded original GMP')
    raw=path.read_bytes(); pin=hashlib.sha256(raw).hexdigest()
    pkg,exp,level,model,blocks,polys,links,collision,inventory,end=_read_context(path,raw)
    tail,p2,owners,b2,l2,c2=load_context(path,raw)
    if (p2,b2,l2,c2)!=(polys,blocks,links,collision):raise ValueError('Source contexts disagree')
    pi=select_plane(tail,polys,owners)
    preview=coupled_preview(tail,polys,owners,pi,delta,blocks=blocks,links=links,include_geometry=True)
    counts=Counter(verify_leaf_boxes(tail,polys)); status='geometry_refused'; reason=None
    if preview['coupled_corner_preview_passed']:
        counts['geometry_gate_passed']=1
        try:
            faces=preview['private_preview_geometry']['faces']
            rendered,rc,shadows=sync_render(level,blocks,polys,links,faces)
            at=exp['offset']; rp=world.Package(path,data=raw[:at]+rendered+raw[at+len(level):]); nb=find_bsp(rp)
            changed,cc=sync_collision(level,rendered,blocks,nb)
            ref=world._parse_world_model(pkg)['world_model_export_ref']; me=pkg.exports[ref-1]
            patch=BytePatch(raw); patch.add(at,changed); candidate=patch.finish()
            q,e,lv,mo,bl,po,li,co,inv,en=_read_context(path,candidate)
            if (q.names,q.imports,q.exports,e,mo,li,co,en)!=(pkg.names,pkg.imports,pkg.exports,exp,model,links,collision,end):
                raise ValueError('Joint render/collision package reparse changed original identity')
            if inspect_packed_positions(lv,bl)[1]!=shadows:raise ValueError('Joint shadow association changed')
            counts.update(rc); counts.update(cc); counts['joint_render_collision_passed']=1
            status='joint_render_collision_passed'
            changed,lc=sync_leaf_boxes(changed,tail,polys,po)
            lp=BytePatch(raw); lp.add(at,changed); leaf_candidate=lp.finish()
            t3,p3,o3,b3,l3,c3=load_context(path,leaf_candidate)
            if (p3,o3,b3,l3,c3)!=(po,owners,bl,li,co) or any(t3[k]!=tail[k] for k in ('nodes','planes','portals','portal_leaf_links')):
                raise ValueError('Leaf-bound synchronization changed original ownership or spatial topology')
            verify_leaf_boxes(t3,p3)
            counts.update(lc); counts['joint_leaf_bounds_passed']=1
            # Portal motion is a separate gate; retain the earlier result on refusal.
            spatial,sc=sync_portals(changed,t3,polys,po,owners,pi,delta)
            counts.update(sc)
            if spatial is not None:
                sp=BytePatch(raw); sp.add(at,spatial)
                t4,p4,o4,b4,l4,c4=load_context(path,sp.finish())
                if (p4,o4,b4,l4,c4)!=(po,owners,bl,li,co) or any(t4[k]!=t3[k] for k in ('nodes','portals','portal_leaf_links','leaves')):
                    raise ValueError('Splitter/portal package reparse changed original ownership')
                changed=spatial
                counts['joint_splitter_portal_passed']=1
                refinfo=world._parse_world_model(pkg)
                cur=world.Cursor(level,refinfo['level_model_ref_offset_in_level'])
                if cur.ci()!=refinfo['world_model_export_ref']:
                    raise ValueError('Original Model reference changed')
                nav=audit_navigation_impact(level,cur.at,tail,t4,polys,po,pi)
                counts.update(nav['counts'])
                counts['graph_grid_dependency_warning']=int(nav['graph_grid_dependency_warning'])
                counts['graph_grid_probe_passed_without_warning']=int(not nav['graph_grid_dependency_warning'])
            try:
                m2,mc,mp=model_sync(model,polys,po,faces); counts.update(mc)
                counts['model_candidate_gate_passed']=int(mp)
                if mp:
                    both=BytePatch(raw); both.add(at,changed); both.add(me['offset'],m2)
                    final=both.finish(); q2,e2,lv2,mo2,bl2,po2,li2,co2,inv2,en2=_read_context(path,final)
                    if (q2.names,q2.imports,q2.exports,e2,lv2,mo2,li2,co2,en2)!=(pkg.names,pkg.imports,pkg.exports,exp,changed,m2,links,collision,end):
                        raise ValueError('Combined candidate reparse failed')
                    counts['joint_model_render_collision_passed']=1
                    counts['joint_model_splitter_portal_passed']=int(spatial is not None)
                    status='joint_model_render_collision_passed'
            except (ValueError,struct.error,IndexError,KeyError,OverflowError) as exc:
                counts['model_candidate_exception']=1;reason=str(exc)
        except (ValueError,struct.error,IndexError,KeyError,OverflowError) as exc:
            counts['joint_render_collision_refused']=1; status='joint_render_collision_refused';reason=str(exc)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:raise ValueError('Original GMP changed')
    return {'source_map':path.name,'source_sha256':pin,'plane_index':pi,'delta_d':delta,'status':status,'reason':reason,'counts':dict(counts),
            'vbsp_splitter_portal_updated':bool(counts['joint_splitter_portal_passed']),'navigation_and_grids_unmodified':True,'native_geometry_writer_enabled':False,'retail_runtime_verified':False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('maps',type=Path,nargs='+');p.add_argument('--delta-d',type=float,default=1.);p.add_argument('--report',type=Path);a=p.parse_args(argv)
    try:
        if not 1<=len(a.maps)<=world.MAX_MAPS or len({x.resolve() for x in a.maps})!=len(a.maps):raise ValueError('Expected distinct bounded maps')
        rows=[audit_map(path,a.delta_d) for path in a.maps]; counts=Counter()
        for row in rows:counts.update(row['counts'])
        result={'schema':SCHEMA,'map_count':len(rows),'summary':dict(counts),'maps':rows,'candidate_gmp_written':False,'retail_runtime_verified':False}
        if a.report:world.write_report(result,a.report,a.maps)
        print(json.dumps({k:v for k,v in result.items() if k!='maps'},indent=2,allow_nan=False));return 0
    except (OSError,ValueError,KeyError,IndexError,struct.error,OverflowError) as exc:
        print(json.dumps({'status':'refused','reason':str(exc)}));return 2

if __name__=='__main__':raise SystemExit(main())
