"""Read-only MOPP coverage preflight for coupled original triangle motion.

Use the exact original render/flat triangle topology, float32 coordinate
conversion and unchanged original MOPP code. Samples can falsify reuse;
passing them is not a collision compiler or proof of full coverage.
"""
from collections import Counter
import math
import struct

import inspect_level_mopp_triangle_tree as mopp
from inspect_mopp_axis_point_candidates import ConservativeMoppPointCandidates
from inspect_world_position_dependencies import inspect_flat_exact, scaled_position, f32

MAX_TRIANGLE_PROBES=300000


def triangle_samples(v):
    a,b,c=v
    return [a,b,c,*(tuple((x+y)/2 for x,y in zip(p,q))
                     for p,q in ((a,b),(b,c),(c,a))),
            tuple(sum(p[k] for p in v)/3 for k in range(3))]


def area_vector(v):
    a,b,c=v
    x=tuple(y-z for y,z in zip(b,a))
    y=tuple(y-z for y,z in zip(c,a))
    return (x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0])


def compare_triangle(walker,tid,old,new):
    counts=Counter()
    n0,n1=area_vector(old),area_vector(new)
    if not sum(x*x for x in n0) or not sum(x*x for x in n1):
        counts["collision_zero_area_candidate_triangles"]+=1
    elif sum(x*y for x,y in zip(n0,n1))<=0:
        counts["collision_reversed_candidate_triangles"]+=1
    if tid not in walker.complete_leaf_set:
        counts["collision_affected_nonleaf_triangles"]+=1
        return counts
    counts["collision_sampled_triangles"]+=1
    misses=0
    for p,q in zip(triangle_samples(old),triangle_samples(new)):
        a=set(walker.point(p)["candidate_triangle_ids"])
        b=set(walker.point(q)["candidate_triangle_ids"])
        counts["collision_point_comparisons"]+=1
        counts["collision_original_sample_misses"]+=int(tid not in a)
        counts["collision_candidate_sample_misses"]+=int(tid not in b)
        reg=int(tid in a and tid not in b)
        counts["collision_new_sample_misses"]+=reg
        misses+=reg
        counts["collision_candidate_sets_changed"]+=int(a!=b)
    counts["collision_triangles_with_new_sample_misses"]+=int(misses>0)
    return counts


def inspect_candidate_collision(level,blocks,polygons,links,source_rows,preview,*,refit_axis=False,refit_diagonal=False):
    """Compare accepted private face subset; do not cook or write collision."""
    flat,_=inspect_flat_exact(level,blocks)
    proof=mopp.inspect_mopp_link(level,blocks)
    n=flat["render_and_flat_triangle_count"]
    nv=flat["render_and_flat_vertex_count"]
    va=flat["level_flat_vertex_array_offset"]
    ia=flat["level_flat_index_array_offset"]
    ca,ce=proof["mopp_code_start_in_level"],proof["mopp_code_end_in_level"]
    origin=struct.unpack_from("<4f",level,ca-20)
    walker=ConservativeMoppPointCandidates(level[ca:ce],n,origin)
    by_loc={tuple(row["render_locator"]):row for row in source_rows}
    if len(by_loc)!=n:
        raise ValueError("Incomplete original collision provenance")
    before=[struct.unpack_from("<3f",level,va+i*16) for i in range(nv)]
    after=list(before)
    ids=struct.unpack_from("<"+str(3*n)+"I",level,ia)
    bases=[]
    cursor=0
    for block in blocks:
        bases.append(cursor)
        cursor+=len(block["vertices"])
    if cursor!=nv:
        raise ValueError("Packed and flattened source vertex inventory mismatch")
    seen_vertices=set()
    seen_triangles=set()
    counts=Counter()
    for face in preview["faces"]:
        i=face["source_polygon"]
        if not 0<=i<len(polygons) or links[i]["polygon"]!=i:
            raise ValueError("Candidate collision source polygon identity mismatch")
        link=links[i]
        source=polygons[i]["vertices"]
        if (len(source)!=len(face["vertices"])
                or len(source)!=link["packed_vertex_count"]):
            raise ValueError("Candidate collision topology changed")
        start=bases[link["packed_block"]]+link["packed_vertex_start"]
        for j,v in enumerate(face["vertices"]):
            k=start+j
            if (v["source_corner"]!=j or k in seen_vertices or not 0<=k<nv
                    or before[k]!=scaled_position(source[j][:3])):
                raise ValueError("Candidate collision source corner mismatch")
            seen_vertices.add(k)
            after[k]=scaled_position(tuple(f32(x) for x in v["xyz"]))
        for loc in link["triangle_locators"]:
            row=by_loc[tuple(loc)]
            tid=row["flattened_triangle_id"]
            if (not 0<=tid<n or tid in seen_triangles
                    or any(not start<=j<start+len(source) for j in ids[3*tid:3*tid+3])
                    or row["original_mopp_terminal_leaf_present"]!=(tid in walker.complete_leaf_set)):
                raise ValueError("Candidate collision original triangle mismatch")
            seen_triangles.add(tid)
            if 7*len(seen_triangles)>MAX_TRIANGLE_PROBES:
                raise ValueError("Candidate collision query budget exceeded")
    for tid in sorted(seen_triangles):
        indices=ids[3*tid:3*tid+3]
        counts.update(compare_triangle(walker,tid,[before[j] for j in indices],
                                        [after[j] for j in indices]))
    lo=[min(v[k] for v in after) for k in range(3)]
    hi=[max(v[k] for v in after) for k in range(3)]
    extent=max(b-a for a,b in zip(lo,hi))
    expected_scale=mopp.MOPP_SCALE_NUMERATOR/(extent+mopp.MOPP_SCALE_EXPANSION)
    origin_error=max(abs(lo[k]-mopp.MOPP_OFFSET_EXPANSION-origin[k]) for k in range(3))
    scale_error=abs(origin[3]-expected_scale)/expected_scale
    counts["collision_preview_flat_vertices"]=len(seen_vertices)
    counts["collision_preview_flat_triangles"]=len(seen_triangles)
    counts["collision_origin_scale_source_formula_passed"]=int(
        origin_error<=mopp.MAX_OFFSET_ERROR and scale_error<=mopp.MAX_SCALE_RELATIVE_ERROR)
    passed=bool(seen_triangles) and counts["collision_origin_scale_source_formula_passed"] and not any(counts[k] for k in (
        "collision_zero_area_candidate_triangles","collision_reversed_candidate_triangles",
        "collision_affected_nonleaf_triangles","collision_original_sample_misses",
        "collision_candidate_sample_misses"))
    result={"counts":dict(counts),"sampled_unchanged_mopp_preflight_passed":bool(passed),
            "candidate_origin_error":origin_error,"candidate_scale_relative_error":scale_error,
            "original_bytecode_recompiled":False,"collision_coverage_proven":False,
            "retail_runtime_verified":False}

    if refit_axis or refit_diagonal:
        from inspect_mopp_axis_refit import refit_axis_bounds,diagonal_diagnostics
        original=[tuple(before[j] for j in ids[3*i:3*i+3]) for i in range(n)]
        candidate=[tuple(after[j] for j in ids[3*i:3*i+3]) for i in range(n)]
        code,refit=refit_axis_bounds(level[ca:ce],original,candidate,origin)
        refit["diagonal_diagnostics"]=diagonal_diagnostics(level[ca:ce],original,candidate,origin)
        refit["original_origin_scale_formula_passed"]=bool(counts["collision_origin_scale_source_formula_passed"])
        samples=misses=derived_misses=0
        if code is not None:
            updated=ConservativeMoppPointCandidates(code,n,origin)
            for tid in sorted(seen_triangles & updated.complete_leaf_set):
                for point in triangle_samples(candidate[tid]):
                    samples+=1
                    misses+=int(tid not in updated.point(point)["candidate_triangle_ids"])
                    derived_misses+=int(tid not in updated.point(point,diagonal_mode="derived_diagonals")["candidate_triangle_ids"])
            if misses:
                raise ValueError("Refitted axis path proof disagrees with independent point interpreter")
        refit.update(sample_count=samples,axis_sample_misses=misses,derived_diagonal_sample_misses=derived_misses,
                     candidate_code_written=False,
                     sampled_refit_preflight_passed=bool(code is not None and samples and not misses
                        and counts["collision_origin_scale_source_formula_passed"] and not any(counts[k] for k in (
                        "collision_zero_area_candidate_triangles","collision_reversed_candidate_triangles",
                        "collision_affected_nonleaf_triangles","collision_original_sample_misses"))))
        result["axis_refit"]=refit
        if refit_diagonal:
            from inspect_mopp_diagonal_refit import refit_diagonal_bounds
            diagonal={"refit_passed":False,"axis_refit_required":True,
                      "diagonal_refit_bytes_changed":0,"sample_count":0,"sample_misses":0,
                      "projection_hypotheses_runtime_verified":False}
            if code is not None:
                patched,diagonal=refit_diagonal_bounds(code,original,candidate,origin)
                diagonal.update(sample_count=0,sample_misses=0)
                if patched is not None:
                    updated=ConservativeMoppPointCandidates(patched,n,origin)
                    for tid in sorted(seen_triangles & updated.complete_leaf_set):
                        for point in triangle_samples(candidate[tid]):
                            diagonal["sample_count"]+=1
                            diagonal["sample_misses"]+=int(tid not in updated.point(point,diagonal_mode="derived_diagonals")["candidate_triangle_ids"])
                    if diagonal["sample_misses"]:
                        raise ValueError("Diagonal refit disagrees with independent projection walker")
            result["experimental_diagonal_refit"]=diagonal
    return result
