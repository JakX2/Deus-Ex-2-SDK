#!/usr/bin/env python3
"""Read-only original DX2 Level finite-segment geometry/MOPP point audit.

A segment crosses ORIGINAL Level source triangles according to a geometry-only
BVH. MOPP is queried with POINTS at the measured transverse intersections.
This is NOT a Havok raycast, ray broadphase, contact or collision writer.
Parallel/coplanar segments remain outside the transverse-only contract.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import export_level_mopp_triangle_debug_mesh as exporter
import inspect_mopp_axis_point_candidates as spatial
import inspect_mopp_point_triangle_oracle as geom
import inspect_mopp_segment_geometry_oracle as segments

SCHEMA = "DX2SDK-Level-MOPP-transverse-segment-crossings-audit-v1"


def audit_source_level(level: bytes, blocks: list[dict], *,
                       sample_stride: int = 1,
                       segment_half_length: float = .1,
                       max_samples: int = 0,
                       tolerance_units: float = 1.0) -> dict:
    if (type(sample_stride) is not int or not 1 <= sample_stride <= 100000
            or type(max_samples) is not int or not 0 <= max_samples <= 300000
            or type(segment_half_length) not in (float,int)
            or not math.isfinite(segment_half_length)
            or not 1e-7 <= segment_half_length <= 100):
        raise ValueError("Invalid transverse segment sampling parameters")
    atlas = exporter.inspect_mesh(level,blocks)
    oracle = geom.original_atlas_oracle(atlas)
    verified = exporter.provenance.mopp.inspect_mopp_link(level,blocks)
    code_start = verified["mopp_code_start_in_level"]
    walker = spatial.ConservativeMoppPointCandidates(
        level[code_start:verified["mopp_code_end_in_level"]],
        atlas["source_triangle_count"],
        struct.unpack_from("<4f",level,code_start-20))
    if set(oracle.tris) != walker.complete_leaf_set:
        raise ValueError("Independent geometry and original MOPP leaf IDs differ")

    counts = Counter()
    missing_examples = []
    sampled = 0
    for index,tid in enumerate(sorted(oracle.tris)):
        if index % sample_stride:
            continue
        if max_samples and sampled >= max_samples:
            break
        t = oracle.tris[tid]
        normal = tuple(component/t.normal_len for component in t.normal)
        center = oracle.sample_triangle(tid,(.2,.3,.5))
        a = tuple(center[i]-segment_half_length*normal[i] for i in range(3))
        b = tuple(center[i]+segment_half_length*normal[i] for i in range(3))
        crossing = segments.segment_crossings(oracle,a,b)
        if tid not in {hit.original_triangle_id for hit in crossing["hits"]}:
            raise ValueError("Independent transverse oracle missed seed triangle")
        sampled += 1
        counts["transverse_segment_queries"] += 1
        counts["geometric_triangle_crossings"] += len(crossing["hits"])
        counts["segments_with_multiple_geometric_crossings"] += int(
            len(crossing["hits"])>1)
        counts["parallel_or_coplanar_bvhs_encountered"] += len(
            crossing["parallel_or_coplanar_triangle_ids"])

        for endpoint in (a,b):
            counts["segment_endpoints_tested"] += 1
            counts["endpoints_with_geometric_hits"] += bool(
                oracle.containing_triangle_ids(endpoint))

        for mode in spatial.DIAGONAL_MODES:
            counts[f"{mode}_segments_tested"] += 1
            for hit in crossing["hits"]:
                xyz = hit.point
                geom_ids = oracle.containing_triangle_ids(xyz)
                if hit.original_triangle_id not in geom_ids:
                    raise ValueError("Geometric point oracle inconsistent with crossing")
                result = walker.point(
                    xyz,diagonal_mode=mode,tolerance_units=tolerance_units)
                missed = set(geom_ids)-set(result["candidate_triangle_ids"])
                counts[f"{mode}_crossing_point_comparisons"] += 1
                counts[f"{mode}_total_candidate_ids"] += len(
                    result["candidate_triangle_ids"])
                if missed:
                    counts[f"{mode}_crossings_with_missing_geometry"] += 1
                    counts[f"{mode}_total_missing_original_ids"] += len(missed)
                    if len(missing_examples)<12:
                        # No original source vertex positions in the report.
                        missing_examples.append({
                            "seed_original_triangle_id":tid,
                            "crossing_original_triangle_id":hit.original_triangle_id,
                            "mode":mode,"missing_original_ids":sorted(missed)[:48]})
    return {
        "schema":SCHEMA,
        "original_source_triangles":atlas["source_triangle_count"],
        "mopp_leaf_source_triangles":len(oracle.tris),
        "segment_half_length_level_units":segment_half_length,
        "sample_stride":sample_stride,
        "sampled_original_triangles":sampled,
        "totals":dict(counts),
        "first_missing_source_ID_examples":missing_examples,
        "all_nondegenerate_source_triangle_ids_sampled":(
            sample_stride==1 and sampled==len(oracle.tris)),
        "point_query_only_at_independent_segment_crossings":True,
        "coplanar_segment_overlap_fully_supported":False,
        "mopp_segment_or_ray_traversal_implemented":False,
        "runtime_havok_contacts_verified":False,
        "original_level_bytes_modified":False,
    }


def audit_map(path: Path, **options) -> dict:
    # Original Package/Flesh/Level/MOPP path is reused, not guessed.
    atlas,metadata = exporter.audit_map(path)
    src = Path(__file__).resolve().parents[2] / "map_exporter"
    if str(src) not in sys.path:
        sys.path.insert(0,str(src))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg = Package(path)
    if hashlib.sha256(pkg.data).hexdigest()!=metadata["sha256"]:
        raise ValueError("Source GMP changed between validation and segment audit")
    levels = [row for row in pkg.exports
              if pkg.class_name(row)=="Level" and row["size"]>0]
    if len(levels)!=1:
        raise ValueError("Expected exactly one authenticated source Level")
    result = audit_source_level(pkg.payload(levels[0]),find_bsp(pkg),**options)
    if atlas["source_triangle_count"]!=result["original_source_triangles"]:
        raise ValueError("Original geometry counts changed between validations")
    return {**metadata,**result}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps",nargs="+",type=Path)
    parser.add_argument("--sample-stride",type=int,default=1)
    parser.add_argument("--max-samples",type=int,default=0)
    parser.add_argument("--half-length",type=float,default=.1)
    parser.add_argument("--tolerance-units",type=float,default=1.0)
    parser.add_argument("--report",type=Path,
                        help="Fresh JSON outside original game Maps directories")
    args = parser.parse_args(argv)
    try:
        if not 1<=len(args.maps)<=64:
            raise ValueError("Expected 1..64 original user-owned DX2 maps")
        paths = [p.resolve() for p in args.maps]
        if len(set(paths))!=len(paths):
            raise ValueError("Duplicate source GMP")
        rows = [audit_map(
            path,sample_stride=args.sample_stride,
            max_samples=args.max_samples,
            segment_half_length=args.half_length,
            tolerance_units=args.tolerance_units) for path in paths]
        totals = Counter()
        for row in rows:
            totals["maps"] += 1
            totals.update(row["totals"])
        report = {
            "schema":SCHEMA,"summary":dict(totals),"maps":rows,
            "original_retail_game_files_written":False,
            "havok_raycast_verified":False,
        }
        if args.report:
            dest = args.report.resolve()
            if (dest.suffix.casefold()!=".json"
                    or any(dest==p or dest.is_relative_to(p.parent)
                           for p in paths)):
                raise ValueError("Report must be new JSON outside original Maps")
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open("x",encoding="utf-8") as file:
                json.dump(report,file,indent=2,allow_nan=False)
                file.write("\n")
            print(json.dumps({"status":"ok","report":str(dest),
                              "summary":dict(totals)}))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return int(any(k.endswith("_crossings_with_missing_geometry") and v
                       for k,v in totals.items()))
    except (OSError,ValueError,TypeError,KeyError,IndexError,OverflowError,
            struct.error) as error:
        print(json.dumps({"status":"refused","reason":str(error)},file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
