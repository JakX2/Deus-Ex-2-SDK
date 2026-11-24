"""Read-only graph/grid dependency probes for one changed VBSP splitter.

Graph meaning, grid origin semantics and native navigation cooking are not
verified. Exact geometric contacts are candidates, not native weld IDs.
"""
from collections import Counter
import struct
from inspect_level_prefix_graph import parse_prefix_graph
from inspect_level_spatial_vbsp import locate_point


def _centroid(points):
    return tuple(sum(v[k] for v in points)/len(points) for k in range(3))


def collect_samples(level,graph,tail):
    """Original graph framing is validated by parse_prefix_graph first."""
    at=graph['graph_start']+graph['zero_header_bytes']
    n,=struct.unpack_from('<I',level,at); at+=4
    if n!=graph['counts']['prefix_graph_triangle_count']:
        raise ValueError('Graph triangle inventory mismatch')
    samples={k:[] for k in ('graph_triangle_corner','graph_triangle_centroid',
        'graph_edge_endpoint','graph_edge_midpoint','grid_origin','grid_directional')}
    for _ in range(n):
        r=struct.unpack_from('<I13fB',level,at); at+=57
        xyz=[r[j:j+3] for j in (1,4,7)]
        samples['graph_triangle_corner'].extend(xyz)
        samples['graph_triangle_centroid'].append(_centroid(xyz))
    en,=struct.unpack_from('<I',level,at); at+=4
    if en!=graph['counts']['prefix_graph_edge_count']:
        raise ValueError('Graph edge inventory mismatch')
    for _ in range(en):
        r=struct.unpack_from('<B6f8s',level,at); at+=33
        xyz=[r[1:4],r[4:7]]
        samples['graph_edge_endpoint'].extend(xyz)
        samples['graph_edge_midpoint'].append(_centroid(xyz))
    if at>graph['graph_end']:raise ValueError('Graph samples escape source span')
    gn=tail['counts']['grid_cells']; dn=tail['counts']['grid_directional_points']
    samples['grid_origin']=[v for _,v in tail['coordinates'][:gn]]
    samples['grid_directional']=[v for _,v in tail['coordinates'][gn:gn+dn]]
    if len(samples['grid_origin'])!=gn or len(samples['grid_directional'])!=dn:
        raise ValueError('Incomplete grid position inventory')
    return samples


def exact_motion(original,candidate,tail,new_tail):
    """Derive exact source-corner displacement candidates, refusing conflicts."""
    if len(original)!=len(candidate):raise ValueError('Graph contact polygon count changed')
    motion={}
    def add(v,w):
        if v in motion and motion[v]!=w:raise ValueError('Conflicting coincident contact motion')
        motion[v]=w
    for i,(a,b) in enumerate(zip(original,candidate)):
        if a['polygon']!=i or b['polygon']!=i or len(a['vertices'])!=len(b['vertices']):
            raise ValueError('Graph contact polygon identity changed')
        for v,w in zip(a['vertices'],b['vertices']):add(v[:3],w[:3])
    n=tail['counts']['vbsp_portal_vertices']
    if new_tail['counts']['vbsp_portal_vertices']!=n:
        raise ValueError('Graph contact portal inventory changed')
    if n:
        for (a,v),(b,w) in zip(tail['coordinates'][-n:],new_tail['coordinates'][-n:]):
            if a!=b:raise ValueError('Graph contact portal offset changed')
            add(v,w)
    return {v:w for v,w in motion.items() if v!=w}


def inspect_samples(samples,nodes,old,new,pi,motion):
    if not 0<=pi<len(old) or len(old)!=len(new) or old[pi][:3]!=new[pi][:3] or any(a!=b for i,(a,b) in enumerate(zip(old,new)) if i!=pi):
        raise ValueError('Expected one translated original splitter')
    p,q=old[pi],new[pi]; counts=Counter()
    def classify(v):
        a=sum(x*y for x,y in zip(v,p[:3]))
        return (a+p[3]<0)!=(a+q[3]<0)
    def compare(v,key):
        # The unchanged point can only change leaves if its decision at the
        # one edited plane changes; evaluate each upward probe independently.
        if not classify(v):return
        counts[key+'_splitter_side_changed']+=1
        a=locate_point(nodes,old,v); b=locate_point(nodes,new,v)
        counts[key+'_leaf_changed']+=int(a!=b)
        counts[key+'_new_solid']+=int(a!=-1 and b==-1)
        counts[key+'_new_open']+=int(a==-1 and b!=-1)
    for tag,vs in samples.items():
        for v in vs:
            counts[tag+'_points']+=1
            compare(v,tag)
            compare((v[0],v[1],v[2]+.1),tag+'_up')
            if v in motion:
                counts[tag+'_exact_moved_contact']+=1
                # Diagnostic only: see if copying the exact contact motion
                # retains classification. This is NOT a navigation edit.
                a=locate_point(nodes,old,v)
                b=locate_point(nodes,new,motion[v])
                counts[tag+'_hypothetical_contact_leaf_changed']+=int(a!=b)
                counts[tag+'_hypothetical_contact_new_solid']+=int(a!=-1 and b==-1)
    return dict(counts)


def audit_navigation_impact(level,start,tail,new_tail,original,candidate,pi):
    graph=parse_prefix_graph(level,start,tail['end'])
    samples=collect_samples(level,graph,tail)
    if tail['nodes']!=new_tail['nodes'] or tail['end']!=new_tail['end']:
        raise ValueError('Graph probe requires original VBSP topology')
    motion=exact_motion(original,candidate,tail,new_tail)
    counts=inspect_samples(samples,tail['nodes'],tail['planes'],new_tail['planes'],pi,motion)
    warning=any(v for k,v in counts.items() if k.endswith(('_leaf_changed','_exact_moved_contact')))
    return {'counts':counts,'graph_grid_dependency_warning':warning,
            'navigation_semantics_verified':False,'graph_grid_written':False,
            'runtime_verified':False}
