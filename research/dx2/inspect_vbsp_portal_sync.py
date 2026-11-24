"""Fixed-width experimental VBSP splitter/portal sync, without GMP output."""
from collections import Counter, defaultdict
import math
import struct
from inspect_vbsp_coupled_corners import solve_displacement, CONTACT_TOL, MAX_DELTA
from inspect_vbsp_plane_dependencies import leaf_paths
from inspect_vbsp_local_clip import plane_basis, project, convex, signed_area, dot
from inspect_level_spatial_vbsp import parse_spatial_tail, locate_point
from inspect_world_position_dependencies import BytePatch, f32

TOL=.15
ROUND_TOL=.002


def path_regressions(before,after,old,new,path):
    def minimum(vs,p,s):
        return min((1 if s==0 else -1)*(dot(v,p[:3])+p[3]) for v in vs)
    return sum(minimum(before,old[i],s)>=-TOL and minimum(after,new[i],s)<-TOL for i,s in path)


def portal_plan(tail,original,candidate,owners,pi,delta):
    planes=tail['planes']; paths=leaf_paths(tail['nodes'])
    if (type(pi) is not int or not 0<=pi<len(planes) or not math.isfinite(delta)
            or not 0<abs(delta)<=MAX_DELTA or len(original)!=len(candidate) or len(original)!=len(owners)):
        raise ValueError('Invalid portal sync plane or inventory')
    changed=list(planes); p=planes[pi]; changed[pi]=(*p[:3],f32(p[3]+delta))
    actual=changed[pi][3]-p[3]
    if abs(actual-delta)>ROUND_TOL:raise ValueError('Splitter rounding exceeds gate')
    n=tail['counts']['vbsp_portal_vertices']; coords=tail['coordinates'][-n:] if n else []
    points=defaultdict(list); records=[]; counts=Counter(); motion={}; conflicts=set()
    for i,(a,b) in enumerate(zip(original,candidate)):
        if a['polygon']!=i or b['polygon']!=i or len(a['vertices'])!=len(b['vertices']):
            raise ValueError('Original render topology changed')
        before=[v[:3] for v in a['vertices']]; after=[v[:3] for v in b['vertices']]
        path=paths[owners[i]]
        counts['render_new_path_violations']+=path_regressions(before,after,planes,changed,path)
        def probe(vs):
            return tuple(sum(v[k] for v in vs)/len(vs)+.1*a['vertices'][0][3+k] for k in range(3))
        if locate_point(tail['nodes'],planes,probe(before))==owners[i] and locate_point(tail['nodes'],changed,probe(after))!=owners[i]:
            counts['render_new_owner_probe_misses']+=1
        for v,w in zip(before,after):
            if v in motion and motion[v]!=w:conflicts.add(v)
            motion[v]=w
    for idx,(a,b,c,d,ref,_) in enumerate(tail['portals']):
        j=ref if ref>=0 else ~ref; path=tuple(sorted(set(paths[a]+paths[b])))
        xyz=[v for _,v in coords[c:d]]
        if len(xyz)!=d-c or len(xyz)<3:raise ValueError('Invalid original portal span')
        records.append((j,path,xyz))
        for v in xyz:points[v].append(idx)
    moved={}; bad=set()
    for v,refs in points.items():
        ids=set()
        for i in refs:
            j,path,_=records[i]; ids.add(j)
            ids.update(k for k,_ in path if abs(dot(v,planes[k][:3])+planes[k][3])<=CONTACT_TOL)
        if pi not in ids:
            if v in motion and motion[v]!=v:counts['portal_render_contact_unresolved']+=1
            continue
        counts['active_portal_corner_groups']+=1
        try:
            eq=[(planes[k][:3],-actual if k==pi else 0.) for k in [pi]+sorted(ids-{pi})]
            if v in conflicts:raise ValueError('Conflicting original render corner motion')
            if v in motion:
                w=motion[v]; counts['portal_render_corner_contacts_tested']+=1
            else:
                shift,_=solve_displacement(eq,max(1.,8*abs(delta)))
                w=tuple(f32(x+y) for x,y in zip(v,shift))
            if any(abs(dot(n,tuple(y-x for x,y in zip(v,w)))-rhs)>ROUND_TOL for n,rhs in eq):
                raise ValueError('Portal corner residual exceeds gate')
            moved[v]=w
        except ValueError:
            counts['portal_corner_constraints_refused']+=1;bad.add(v)
    for i,(j,path,xyz) in enumerate(records):
        new=[moved.get(v,v) for v in xyz]; active=any(v in moved or v in bad for v in xyz)
        if active:counts['affected_portals']+=1
        if any(v in bad for v in xyz):counts['portals_with_refused_corners']+=1;continue
        if active:
            basis=plane_basis(planes[j]); before=[project(v,basis) for v in xyz]; after=[project(v,basis) for v in new]
            if not convex(before) or not convex(after) or signed_area(before)*signed_area(after)<=0:
                counts['portal_loop_geometry_refused']+=1
        counts['portal_new_path_violations']+=path_regressions(xyz,new,planes,changed,path)
        plane=changed[j]
        if max(abs(dot(v,plane[:3])+plane[3]) for v in new)>TOL:counts['portal_support_violations']+=1
        center=tuple(sum(v[k] for v in new)/len(new) for k in range(3))
        pair=tuple(locate_point(tail['nodes'],changed,tuple(x+s*.1*y for x,y in zip(center,plane[:3]))) for s in (1,-1))
        if pair!=tail['portal_leaf_links'][i]:counts['portal_side_probe_regressions']+=1
    passed=not any(counts[k] for k in ('render_new_path_violations','render_new_owner_probe_misses','portal_render_contact_unresolved','portal_corner_constraints_refused','portal_loop_geometry_refused','portal_new_path_violations','portal_support_violations','portal_side_probe_regressions'))
    counts['portal_vertices_moved']=sum(v in moved and moved[v]!=v for _,v in coords)
    return changed,moved,dict(counts),passed


def sync_portals(level,tail,original,candidate,owners,pi,delta):
    planes,moved,counts,passed=portal_plan(tail,original,candidate,owners,pi,delta)
    if not passed:return None,counts
    patch=BytePatch(level);at,old=tail['plane_offsets'][pi]
    if struct.unpack_from('<4f',level,at-12)!=old:raise ValueError('Original splitter span mismatch')
    patch.add(at,struct.pack('<f',planes[pi][3]))
    n=tail['counts']['vbsp_portal_vertices']
    for offset,v in tail['coordinates'][-n:] if n else []:
        if struct.unpack_from('<3f',level,offset)!=v:raise ValueError('Original portal vertex span mismatch')
        if v in moved and moved[v]!=v:patch.add(offset,struct.pack('<3f',*moved[v]))
    out=patch.finish()
    start=tail['vbsp_start']-12-92*tail['counts']['grid_cells']-24*tail['counts']['grid_directional_points']
    parsed=parse_spatial_tail(out,start,tail['end'])
    if parsed['planes']!=planes or any(parsed[k]!=tail[k] for k in ('nodes','portals','portal_leaf_links','leaves')):
        raise ValueError('Portal sync changed original spatial identity')
    counts['splitter_portal_patch_bytes']=sum(a!=b for a,b in zip(level,out))
    counts['splitter_portal_sync_passed']=1
    return out,counts
