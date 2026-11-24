"""Exact-position source seam inventory and private edit-preview diagnostics.

Coincident source positions are geometric candidates, not native weld IDs.
The diagnostic cannot certify watertightness, T-junctions, collision cooking
or engine safety. It can detect separated or unresolved original corners.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
import math

SEAM_TOL=.002
MAX_GROUP=512


def source_seam_inventory(polygons,owners):
    if len(polygons)!=len(owners):
        raise ValueError("Source seam owner inventory mismatch")
    points=defaultdict(list)
    edges=defaultdict(list)
    counts=Counter()
    for i,poly in enumerate(polygons):
        if poly["polygon"]!=i or type(owners[i]) is not int or owners[i]<0:
            raise ValueError("Source seam polygon ordinal or owner mismatch")
        xyz=[tuple(v[:3]) for v in poly["vertices"]]
        if len(xyz)<3 or any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in xyz):
            raise ValueError("Malformed source seam polygon")
        for j,v in enumerate(xyz):
            points[v].append((i,j))
            counts["source_seam_corner_records"]+=1
        for j,(a,b) in enumerate(zip(xyz,xyz[1:]+xyz[:1])):
            if a==b:
                counts["source_seam_zero_edges"]+=1
            else:
                edges[tuple(sorted((a,b)))].append((i,j))
                counts["source_seam_edge_records"]+=1
    for refs in points.values():
        if len(refs)>MAX_GROUP:
            raise ValueError("Source coincident corner group exceeds budget")
        shared=len({i for i,_ in refs})>1
        counts["source_seam_xyz_groups"]+=1
        counts["source_seam_shared_xyz_groups"]+=int(shared)
        counts["source_seam_shared_xyz_corners"]+=len(refs) if shared else 0
        counts["source_seam_cross_leaf_xyz_groups"]+=int(len({owners[i] for i,_ in refs})>1)
    for refs in edges.values():
        counts["source_seam_edge_groups"]+=1
        counts["source_seam_shared_edge_groups"]+=int(len(refs)>1)
        counts["source_seam_two_edge_groups"]+=int(len(refs)==2)
        counts["source_seam_more_than_two_edge_groups"]+=int(len(refs)>2)
        counts["source_seam_cross_leaf_edge_groups"]+=int(len({owners[i] for i,_ in refs})>1)
    return dict(counts),points


def inspect_preview_seams(polygons,owners,points,faces,states):
    """Compare source-coincident corners, including stationary neighboring faces.

    Removed source corners are diagnostic, not automatically cracks. Missing
    or refused face previews remain unresolved; never mark them safe.
    """
    if any(type(i) is not int or not 0<=i<len(polygons) for i in states):
        raise ValueError("Invalid preview face state ordinal")
    previews={}
    for face in faces:
        i=face["source_polygon"]
        if (i in previews or states.get(i)!="preview_passed"
                or face["owner_leaf"]!=owners[i]):
            raise ValueError("Private preview face/state identity mismatch")
        corners={}
        for vertex in face["vertices"]:
            j=vertex["source_corner"]
            if j is None:
                continue
            xyz=tuple(vertex["xyz"])
            if (type(j) is not int or not 0<=j<len(polygons[i]["vertices"])
                    or j in corners or len(xyz)!=3 or not all(math.isfinite(x) for x in xyz)):
                raise ValueError("Invalid private preview source corner association")
            corners[j]=xyz
        previews[i]=corners
    if set(previews)!={i for i,state in states.items() if state=="preview_passed"}:
        raise ValueError("Preview face/state coverage mismatch")
    counts=Counter()
    issues=[]
    for original,refs in points.items():
        if len({i for i,_ in refs})<2 or not any(i in states for i,_ in refs):
            continue
        counts["preview_affected_shared_xyz_groups"]+=1
        positions=[]
        removed=[]
        unresolved=[]
        for i,j in refs:
            state=states.get(i)
            if state is None:
                positions.append((i,j,original))
            elif state=="preview_passed":
                if j in previews[i]:
                    positions.append((i,j,previews[i][j]))
                else:
                    removed.append((i,j))
            elif state=="removed":
                removed.append((i,j))
            else:
                unresolved.append((i,j))
        separated=any(math.dist(a[2],b[2])>SEAM_TOL
                      for a,b in combinations(positions,2))
        mixed=bool(positions and removed)
        if separated:
            counts["preview_shared_xyz_groups_separated"]+=1
        if unresolved:
            counts["preview_shared_xyz_groups_unresolved"]+=1
        if mixed:
            counts["preview_shared_xyz_groups_removed_with_survivors"]+=1
        if removed and not positions and not unresolved:
            counts["preview_shared_xyz_groups_all_removed"]+=1
        if positions and not separated and not removed and not unresolved:
            counts["preview_shared_xyz_groups_agree"]+=1
        if separated or mixed or unresolved:
            issues.append({"source_corner_refs":[[i,j] for i,j in refs],
                "separated_surviving_positions":separated,
                "removed_source_corner_refs":removed,
                "unresolved_source_corner_refs":unresolved})
    return dict(counts),issues


def attach_original_triangle_provenance(preview,links,source_rows):
    """Add exact original render and MOPP IDs to affected private face records."""
    by_locator={}
    ids=set()
    for row in source_rows:
        loc=tuple(row["render_locator"])
        tid=row["flattened_triangle_id"]
        if (len(loc)!=3 or loc in by_locator or type(tid) is not int or tid in ids
                or type(row["original_mopp_terminal_leaf_present"]) is not bool):
            raise ValueError("Malformed source triangle provenance")
        by_locator[loc]=row
        ids.add(tid)
    if ids!=set(range(len(source_rows))):
        raise ValueError("Incomplete original flattened triangle ordinal inventory")
    counts=Counter()
    faces={f["source_polygon"]:f for f in preview["faces"]}
    seen=set()
    for state in preview["face_states"]:
        i=state["source_polygon"]
        if type(i) is not int or not 0<=i<len(links) or links[i]["polygon"]!=i:
            raise ValueError("Private preview polygon/source triangle link mismatch")
        locs=[tuple(k) for k in links[i]["triangle_locators"]]
        if (not locs or len(set(locs))!=len(locs) or seen.intersection(locs)
                or not set(locs)<=by_locator.keys()):
            raise ValueError("Private preview source triangle provenance missing or reused")
        seen.update(locs)
        records=[by_locator[k] for k in locs]
        tri_ids=[r["flattened_triangle_id"] for r in records]
        leaves=[r["flattened_triangle_id"] for r in records if r["original_mopp_terminal_leaf_present"]]
        state["original_flat_triangle_ids"]=tri_ids
        state["original_mopp_leaf_ids"]=leaves
        state["original_render_triangle_locators"]=locs
        counts["affected_original_render_triangles"]+=len(tri_ids)
        counts["affected_original_mopp_leaves"]+=len(leaves)
        if i in faces:
            f=faces[i]
            f["original_packed_block"]=links[i]["packed_block"]
            f["original_packed_vertex_start"]=links[i]["packed_vertex_start"]
            f["original_flat_triangle_ids"]=tri_ids
            f["original_mopp_leaf_ids"]=leaves
            counts["textured_preview_original_mopp_leaves"]+=len(leaves)
    return dict(counts)
