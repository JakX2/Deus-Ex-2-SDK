"""Geometric Model ancestor constraints and independent coplanar node evidence.

Field 3/4 negative/positive side semantics remain hypotheses. Field 5 is
checked by the existing direct-link audit, not inherited as a halfspace.
"""
from collections import Counter,defaultdict

TOL=.15
MAX_CHECKS=4000000


def _distance(plane,v,field):
    return (1 if field==4 else -1)*(sum(x*y for x,y in zip(plane[:3],v))-plane[3])


def unique_owners(links):
    reverse=defaultdict(list)
    for i,row in enumerate(links):
        for j in row:reverse[j].append(i)
    return {j:ids[0] for j,ids in reverse.items() if len(ids)==1 and links[ids[0]]==[j]}


def ancestor_regressions(edges,old,new,original,candidate,links):
    if len(old)!=len(new) or len(original)!=len(candidate):
        raise ValueError('Model ancestor inventory changed')
    parents={}; n=len(old); counts=Counter(); mapped=unique_owners(links)
    for e in edges:
        p,c,f=e['parent'],e['child'],e['compact_field']
        if not 0<=p<n or not 0<c<n or c in parents or p==c or f not in (3,4,5):
            raise ValueError('Invalid original Model ancestor graph')
        parents[c]=(p,f)
    if set(parents)!=set(range(1,n)):raise ValueError('Incomplete Model parent graph')
    checks=0
    for j in range(n):
        child=j; seen=set(); poly=mapped.get(j)
        before=[v[:3] for v in original[poly]['vertices']] if poly is not None else []
        after=[v[:3] for v in candidate[poly]['vertices']] if poly is not None else []
        while child in parents:
            if child in seen:raise ValueError('Cyclic Model ancestry')
            seen.add(child); p,f=parents[child]; child=p; checks+=1
            if checks>MAX_CHECKS:raise ValueError('Model ancestor check budget exceeded')
            if f==5 or (old[p][0]==new[p][0] and old[j]==new[j] and before==after):continue
            a,b=old[p][0],new[p][0]
            counts['model_affected_ancestor_center_checks']+=1
            if _distance(a,old[j][1][:3],f)>=-TOL and _distance(b,new[j][1][:3],f)<-TOL:
                counts['model_new_ancestor_center_violations']+=1
            if before:
                counts['model_affected_ancestor_polygon_checks']+=1
                if min(_distance(a,v,f) for v in before)>=-TOL and min(_distance(b,v,f) for v in after)<-TOL:
                    counts['model_new_ancestor_polygon_violations']+=1
            else:
                counts['model_affected_unmapped_ancestor_center_checks']+=1
    return dict(counts)


def classify_plane_aliases(aliases,updated,links,original,candidate,old,new):
    """Only retain an alias with a unique stationary face and identical record."""
    mapped=unique_owners(links); resolved=set(); unresolved=set()
    for j in aliases:
        i=mapped.get(j)
        if j not in updated and i is not None and original[i]==candidate[i] and old[j]==new[j]:
            resolved.add(j)
        else:unresolved.add(j)
    return resolved,unresolved
