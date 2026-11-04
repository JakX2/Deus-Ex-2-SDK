#!/usr/bin/env python3
"""Read-only DX2 Level/MOPP audit of reproducible off-surface finite segments.

Two intentionally different sampling strata:
* bbox_random: both endpoints independently chosen from expanded source bounds,
  without selecting or aiming at a source triangle.
* triangle_aimed: an independently randomized direction through a randomly
  chosen source-triangle interior, with both endpoints off the surface.

Finite segments are NOT Havok rays or sweeps. A separate Level-geometry oracle
finds ALL transverse and coplanar hits before comparing to FULL-SEGMENT MOPP
candidate lists. Experimental diagonal equations are NEVER the default.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

import export_level_mopp_triangle_debug_mesh as exporter
import inspect_mopp_axis_point_candidates as mopp
import inspect_mopp_point_triangle_oracle as geometry
import inspect_mopp_segment_geometry_oracle as transverse
import inspect_mopp_segment_interval_candidates as interval

SCHEMA = "DX2SDK-offsurface-segment-vs-source-MOPP-interval-v1"
DEFAULT_RANDOM_SEGMENTS = 128
DEFAULT_AIMED_SEGMENTS = 128
MAX_PER_STRATUM = 10_000
MAX_MAPS = 64


def _validated_options(random_segments: int, aimed_segments: int, seed: int) -> None:
    if (type(random_segments) is not int or type(aimed_segments) is not int
            or type(seed) is not int or not 0 <= seed <= (1 << 64)-1
            or not 0 <= random_segments <= MAX_PER_STRATUM
            or not 0 <= aimed_segments <= MAX_PER_STRATUM
            or not random_segments + aimed_segments):
        raise ValueError("Expected positive, bounded deterministic off-surface probes")


def _bbox(oracle: geometry.LevelPointTriangleOracle):
    lo, hi, _, _, _ = oracle.nodes[oracle.root]
    sizes = [hi[k] - lo[k] for k in range(3)]
    diagonal = math.hypot(*sizes)
    if not math.isfinite(diagonal) or diagonal <= 1e-8:
        raise ValueError("Original Level source extent too small for off-surface sampling")
    return lo, hi, diagonal


def _direction(rng):
    for _ in range(64):
        vector = tuple(rng.uniform(-1., 1.) for _ in range(3))
        norm = math.hypot(*vector)
        if norm > .01:
            return tuple(v / norm for v in vector)
    raise ValueError("Deterministic off-surface random direction failed")


def _endpoints_offsurface(oracle, a, b):
    return (not oracle.containing_triangle_ids(a) and
            not oracle.containing_triangle_ids(b))


def _random_bbox_segment(oracle, rng, bounds):
    lo, hi, size = bounds
    # Truly unconditioned with respect to triangle selection or normal.
    padding = .1 * size
    for _ in range(64):
        a = tuple(rng.uniform(lo[k]-padding, hi[k]+padding) for k in range(3))
        b = tuple(rng.uniform(lo[k]-padding, hi[k]+padding) for k in range(3))
        if math.dist(a, b) > 1e-6 and _endpoints_offsurface(oracle, a, b):
            return a, b
    raise ValueError("Could not generate an independent off-surface bbox segment")


def _triangle_aimed_segment(oracle, rng, bounds, leaf_ids):
    # A separate *collision-positive* stratum to avoid hiding failures when
    # nearly all independent world-AABB random segments miss sparse geometry.
    # Direction and endpoints are randomized, NOT source normal probes.
    _, _, diagonal = bounds
    half = min(10., max(.1, diagonal * .01))
    for _ in range(128):
        tid = leaf_ids[rng.randrange(len(leaf_ids))]
        # Interior barycentric point. Jitter the location, retaining a true
        # interior point but avoiding constant centroid/edge probes.
        u = rng.uniform(.15, .65)
        v = rng.uniform(.15, .85-u)
        p = oracle.sample_triangle(tid, (u, v, 1-u-v))
        direction = _direction(rng)
        tri = oracle.tris[tid]
        incidence = abs(sum(direction[k]*tri.normal[k] for k in range(3)) /
                        tri.normal_len)
        if incidence < .30:
            continue
        a = tuple(p[k] - half*direction[k] for k in range(3))
        b = tuple(p[k] + half*direction[k] for k in range(3))
        if _endpoints_offsurface(oracle, a, b):
            return a, b, tid
    raise ValueError("Could not generate transverse off-surface triangle-aimed segment")


def compare_independent_segment(oracle, walker, a, b, *, modes=None, tolerance_units=1.0):
    """Compare ALL transverse and coplanar original IDs to the interval query."""
    if not isinstance(oracle, geometry.LevelPointTriangleOracle):
        raise ValueError("Independent source geometry oracle required")
    if modes is None:
        modes = mopp.DIAGONAL_MODES
    if (not isinstance(modes, (tuple, list)) or not modes or
            any(mode not in mopp.DIAGONAL_MODES for mode in modes)):
        raise ValueError("Unrecognized diagonal research comparison mode")
    cross = transverse.segment_crossings(oracle, a, b)
    cop = interval.coplanar_segment_overlaps(oracle, a, b)
    truth = {hit.original_triangle_id for hit in cross["hits"]}
    truth.update(hit.original_triangle_id for hit in cop)
    # Geometric cross-check: if an endpoint of a line hits a shared triangle,
    # the MOPP candidate set must include it, not just the seed face.
    for hit in cross["hits"]:
        hits_at_point = oracle.containing_triangle_ids(hit.point)
        if hit.original_triangle_id not in hits_at_point:
            raise ValueError("Independent segment/point geometric truth disagrees")
        truth.update(hits_at_point)
    for hit in cop:
        middle = tuple((hit.entry_xyz[k]+hit.exit_xyz[k])/2 for k in range(3))
        truth.update(oracle.containing_triangle_ids(middle))
    outputs = {}
    for mode in modes:
        candidates = interval.segment_candidate_triangle_ids(
            walker, a, b, diagonal_mode=mode, tolerance_units=tolerance_units)
        found = set(candidates["candidate_original_triangle_ids"])
        outputs[mode] = {
            "candidate_count":len(found),
            "missing_source_triangle_ids": sorted(truth - found),
            "false_positive_candidate_count": len(found - truth),
            "candidate_query_was_havok_runtime":False,
        }
    return {
        "geometry_hit_source_triangle_ids":sorted(truth),
        "geometry_hit_count":len(truth),
        "transverse_crossing_events":len(cross["hits"]),
        "coplanar_overlap_events":len(cop),
        "parallel_or_coplanar_bbox_candidates_not_certified":len(cross[
            "parallel_or_coplanar_triangle_ids"]),
        "mode_results":outputs,
        "geometry_origin_independent_of_MOPP":True,
        "runtime_Havok_ray_or_sweep_tested":False,
    }


def audit_source_level(level: bytes, blocks: list[dict], *,
                       random_segments=DEFAULT_RANDOM_SEGMENTS,
                       aimed_segments=DEFAULT_AIMED_SEGMENTS,
                       seed=20261104, tolerance_units=1.0):
    _validated_options(random_segments, aimed_segments, seed)
    atlas=exporter.inspect_mesh(level,blocks)
    oracle=geometry.original_atlas_oracle(atlas)
    checked=exporter.provenance.mopp.inspect_mopp_link(level,blocks)
    code_start=checked["mopp_code_start_in_level"]
    walker=mopp.ConservativeMoppPointCandidates(
        level[code_start:checked["mopp_code_end_in_level"]],
        atlas["source_triangle_count"],struct.unpack_from("<4f",level,code_start-20))
    if set(oracle.tris)!=walker.complete_leaf_set:
        raise ValueError("Source geometry leaf IDs disagree with independently validated MOPP")
    bounds=_bbox(oracle)
    # Seed per source Level bytes, not a process-global mutable RNG.
    source_seed=seed ^ int.from_bytes(hashlib.sha256(level).digest()[:8],"little")
    rng=random.Random(source_seed)
    leaf_ids=sorted(oracle.tris)
    totals=Counter()
    examples=[]
    for category,n in (("bbox_random",random_segments),("triangle_aimed",aimed_segments)):
        for index in range(n):
            if category=="bbox_random":
                a,b=_random_bbox_segment(oracle,rng,bounds)
                target=None
            else:
                a,b,target=_triangle_aimed_segment(oracle,rng,bounds,leaf_ids)
            result=compare_independent_segment(
                oracle,walker,a,b,tolerance_units=tolerance_units)
            truth=result["geometry_hit_source_triangle_ids"]
            totals[f"{category}_segments"]+=1
            totals[f"{category}_with_geometric_contact"]+=bool(truth)
            totals[f"{category}_no_contact"]+=not bool(truth)
            totals[f"{category}_transverse_crossings"]+=result["transverse_crossing_events"]
            totals[f"{category}_coplanar_overlaps"]+=result["coplanar_overlap_events"]
            totals[f"{category}_geometrically_hit_triangle_ids"]+=len(truth)
            totals[f"{category}_parallel_candidate_events"]+=result[
                "parallel_or_coplanar_bbox_candidates_not_certified"]
            if target is not None and target not in truth:
                raise ValueError("Randomized geometry-targeted segment missed its own source triangle")
            for mode, outcome in result["mode_results"].items():
                k=f"{category}_{mode}"
                totals[f"{k}_comparisons"]+=1
                totals[f"{k}_candidate_triangle_ids"]+=outcome["candidate_count"]
                totals[f"{k}_queries_missing_any_hit"]+=bool(outcome["missing_source_triangle_ids"])
                totals[f"{k}_missing_original_triangle_ids"]+=len(outcome["missing_source_triangle_ids"])
                totals[f"{k}_false_positive_candidate_ids"]+=outcome["false_positive_candidate_count"]
                if outcome["missing_source_triangle_ids"] and len(examples)<12:
                    # NO proprietary source positions or Level geometry are exported.
                    examples.append({"category":category,"sample_index":index,
                                     "mode":mode,
                                     "missing_source_triangle_ids":outcome["missing_source_triangle_ids"][:32]})
    return {
        "schema":SCHEMA,
        "source_level_sha256":hashlib.sha256(level).hexdigest(),
        "source_triangle_count":atlas["source_triangle_count"],
        "mopp_source_triangle_count":len(leaf_ids),
        "seed":seed,
        "source_hash_mixed_into_seed":True,
        "strata":["bbox_random", "triangle_aimed"],
        "bbox_endpoints_are_independent_of_triangle_selection":True,
        "aimed_directions_are_randomized_not_only_face_normals":True,
        "all_endpoints_verified_off_source_surfaces":True,
        "summary":dict(totals),
        "first_missing_original_triangle_ids_no_coordinates":examples,
        "runtime_havok_ray_tested":False,
        "swept_volume_tested":False,
        "coplanar_nearparallel_contact_fully_verified":False,
        "game_source_bytes_modified":False,
    }


def audit_map(path: Path, **options):
    path=Path(path).resolve()
    if (not path.is_file() or path.suffix.lower()!=".gmp" or
            path.stat().st_size>exporter.provenance.mopp.flatcheck.MAX_MAP_BYTES):
        raise ValueError("Expected user-owned original DX2 GMP")
    atlas, meta=exporter.audit_map(path)
    root=Path(__file__).resolve().parents[2]/"map_exporter"
    if str(root) not in sys.path:sys.path.insert(0,str(root))
    from dx2inspect import Package
    from dx2scene import find_bsp
    package=Package(path)
    if hashlib.sha256(package.data).hexdigest()!=meta["sha256"]:
        raise ValueError("Original GMP changed after validation")
    levels=[e for e in package.exports if package.class_name(e)=="Level" and e["size"]>0]
    if len(levels)!=1:raise ValueError("Expected exactly one authenticated source Level")
    result=audit_source_level(package.payload(levels[0]),find_bsp(package),**options)
    if atlas["source_triangle_count"]!=result["source_triangle_count"]:
        raise ValueError("Original Level changed between repeated validations")
    return {"file":path.name,"original_gmp_sha256":meta["sha256"],**result}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",nargs="+",type=Path)
    p.add_argument("--bbox-random",type=int,default=DEFAULT_RANDOM_SEGMENTS)
    p.add_argument("--triangle-aimed",type=int,default=DEFAULT_AIMED_SEGMENTS)
    p.add_argument("--seed",type=int,default=20261104)
    p.add_argument("--tolerance-units",type=float,default=1.0)
    p.add_argument("--report",type=Path)
    args=p.parse_args(argv)
    try:
        _validated_options(args.bbox_random,args.triangle_aimed,args.seed)
        if not 1<=len(args.maps)<=MAX_MAPS:raise ValueError("Expected 1..64 user-owned GMPs")
        paths=[path.resolve() for path in args.maps]
        if len(set(paths))!=len(paths):raise ValueError("Duplicate original source GMP path")
        rows=[audit_map(path,random_segments=args.bbox_random,
                aimed_segments=args.triangle_aimed,seed=args.seed,
                tolerance_units=args.tolerance_units) for path in paths]
        totals=Counter()
        for row in rows:totals.update(row["summary"])
        misses=sum(n for key,n in totals.items() if key.endswith("queries_missing_any_hit"))
        report={"schema":SCHEMA,"maps_checked":len(rows),"summary":dict(totals),
                "per_map":rows,"query_misses":misses,
                "source_bytes_modified":False,"runtime_havok_verified":False}
        if args.report:
            out=args.report.resolve()
            if (out.suffix.lower()!=".json" or any(
                    out==src or out.is_relative_to(src.parent) for src in paths)):
                raise ValueError("New research JSON must be outside original source Maps")
            out.parent.mkdir(parents=True,exist_ok=True)
            with out.open("x",encoding="utf-8") as f:
                json.dump(report,f,indent=2,allow_nan=False);f.write("\n")
            print(json.dumps({"status":"ok","report":str(out),
                              "missing_comparisons":misses,"summary":dict(totals)}))
        else:print(json.dumps(report,indent=2,allow_nan=False))
        return int(misses>0)
    except (OSError,ValueError,TypeError,IndexError,KeyError,OverflowError,struct.error) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}),file=sys.stderr)
        return 1


if __name__=="__main__":raise SystemExit(main())
