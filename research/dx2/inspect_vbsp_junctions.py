"""Geometric point-on-edge and near-corner seam diagnostics.

Source candidates may be unrelated coincident geometry; no weld or
T-junction semantics are asserted. Use bounded sorted-axis search without
a third-party geometry dependency. Check all original candidate relations
against moved source positions, never silently merge or split vertices.
"""
from bisect import bisect_left,bisect_right
from collections import Counter,defaultdict
from itertools import product
import math

TOL=.002
MAX_SEARCH=12000000


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def edge_measure(p,a,b):
    d=tuple(y-x for x,y in zip(a,b))
    l2=dot(d,d)
    if l2<=0:
        return math.dist(p,a),0.,0.
    t=dot(tuple(x-y for x,y in zip(p,a)),d)/l2
    q=tuple(x+t*y for x,y in zip(a,d))
    return math.dist(p,q),t,math.sqrt(l2)


def junction_inventory(polygons,points):
    """Return exact source-position references, not native topological IDs."""
    edges=defaultdict(set)
    for poly in polygons:
        xyz=[tuple(v[:3]) for v in poly["vertices"]]
        for a,b in zip(xyz,xyz[1:]+xyz[:1]):
            if a!=b:
                edges[tuple(sorted((a,b)))].add(poly["polygon"])
    ordered=list(sorted(points))
    axes=[sorted((v[i],v) for v in ordered) for i in range(3)]
    vals=[[x for x,_ in a] for a in axes]
    candidates=[]
    checks=0
    counts=Counter()
    for (a,b),owners in sorted(edges.items()):
        if math.dist(a,b)<=2*TOL:
            continue
        ranges=[(bisect_left(vals[i],min(a[i],b[i])-TOL),
                 bisect_right(vals[i],max(a[i],b[i])+TOL)) for i in range(3)]
        axis=min(range(3),key=lambda i:ranges[i][1]-ranges[i][0])
        lo,hi=ranges[axis]
        checks+=hi-lo
        if checks>MAX_SEARCH:
            raise ValueError("Point-on-edge search budget exceeded")
        for _,p in axes[axis][lo:hi]:
            if p==a or p==b or any(not min(x,y)-TOL<=v<=max(x,y)+TOL
                                   for x,y,v in zip(a,b,p)):
                continue
            if not any(i not in owners for i,_ in points[p]):
                continue
            dist,t,length=edge_measure(p,a,b)
            if dist<=TOL and TOL/length<t<1-TOL/length:
                candidates.append((a,b,p))
                counts["source_interior_point_edge_pairs"]+=1
                counts["source_exact_line_pairs"]+=int(dist<=1e-7)
                counts["source_approximate_line_pairs"]+=int(dist>.0001)
    buckets=defaultdict(list)
    near=[]
    for p in ordered:
        key=tuple(math.floor(v/TOL) for v in p)
        for off in product((-1,0,1),repeat=3):
            for q in buckets[tuple(x+y for x,y in zip(key,off))]:
                checks+=1
                if checks>MAX_SEARCH:
                    raise ValueError("Near-corner search budget exceeded")
                if math.dist(p,q)<=TOL:
                    near.append((q,p))
        buckets[key].append(p)
    counts["source_near_distinct_corner_pairs"]=len(near)
    counts["source_junction_search_checks"]=checks
    return dict(counts),candidates,near


def inspect_junction_motion(points,candidates,near,moved,refused,states):
    counts=Counter()
    issues=[]
    def unresolved(v):
        return v in refused or any(states.get(i,"preview_passed")!="preview_passed"
                                   for i,_ in points[v])
    def affected(v):
        return v in moved or v in refused or any(i in states for i,_ in points[v])
    for a,b,p in candidates:
        if not any(affected(v) for v in (a,b,p)):
            continue
        counts["affected_interior_point_edge_pairs"]+=1
        if any(unresolved(v) for v in (a,b,p)):
            status="unresolved"
        else:
            x,y,z=[moved.get(v,v) for v in (a,b,p)]
            dist,t,length=edge_measure(z,x,y)
            status="preserved" if length>2*TOL and dist<=TOL and TOL/length<t<1-TOL/length else "separated"
        counts["affected_interior_point_edge_"+status]+=1
        if status!="preserved":
            issues.append({"kind":"point_on_edge","status":status,
                           "edge_endpoint_corner_refs":[points[a],points[b]],
                           "interior_corner_refs":points[p]})
    for a,b in near:
        if not any(affected(v) for v in (a,b)):
            continue
        counts["affected_near_corner_pairs"]+=1
        if unresolved(a) or unresolved(b):
            status="unresolved"
        else:
            status="preserved" if math.dist(moved.get(a,a),moved.get(b,b))<=TOL else "separated"
        counts["affected_near_corner_"+status]+=1
        if status!="preserved":
            issues.append({"kind":"near_corner","status":status,"corner_refs":[points[a],points[b]]})
    return dict(counts),issues
