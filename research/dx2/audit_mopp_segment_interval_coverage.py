#!/usr/bin/env python3
"""Read-only original DX2 GMP coplanar/segment-interval MOPP candidate audit.

For every sampled source MOPP triangle, test an extended in-plane AB edge
segment and a short transverse segment through an interior point. Compare the
COMPLETE independently reconstructed geometric hit set to full-segment MOPP
candidate IDs in conservative and opt-in experimental diagonal modes.
This is not Havok runtime validation or a native collision writer.
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
import inspect_mopp_segment_interval_candidates as segment
import inspect_mopp_segment_geometry_oracle as transverse

SCHEMA = "DX2SDK-original-Level-segment-interval-geometric-coverage-audit-v1"


def audit_level(level: bytes, blocks: list[dict], *, stride: int = 1,
                max_samples: int = 0, tolerance_units: float = 1.) -> dict:
    if (type(stride) is not int or not 1 <= stride <= 100_000
            or type(max_samples) is not int or not 0 <= max_samples <= 300_000):
        raise ValueError("Invalid segment sampling bounds")
    atlas=exporter.inspect_mesh(level,blocks)
    oracle=geom.original_atlas_oracle(atlas)
    checked=exporter.provenance.mopp.inspect_mopp_link(level,blocks)
    offset=checked["mopp_code_start_in_level"]
    walker=spatial.ConservativeMoppPointCandidates(
        level[offset:checked["mopp_code_end_in_level"]],
        atlas["source_triangle_count"],struct.unpack_from("<4f",level,offset-20))
    if set(oracle.tris)!=walker.complete_leaf_set:
        raise ValueError("Original MOPP leaf IDs differ from Level geometry")
    counts=Counter()
    first_missing=[]
    sampled=0
    for order,tid in enumerate(sorted(oracle.tris)):
        if order % stride:
            continue
        if max_samples and sampled>=max_samples:
            break
        sampled+=1
        tri=oracle.tris[tid]
        # Extend 20% past both ends of original AB edge. Tests shared edges,
        # redundant triangles and coplanar overlaps with off-face endpoints.
        edge=tuple(tri.b[i]-tri.a[i] for i in range(3))
        a=tuple(tri.a[i]-.2*edge[i] for i in range(3))
        b=tuple(tri.b[i]+.2*edge[i] for i in range(3))
        overlaps=segment.coplanar_segment_overlaps(oracle,a,b)
        truth={hit.original_triangle_id for hit in overlaps}
        if tid not in truth:
            raise ValueError("Independent coplanar geometry lost source edge")
        counts["coplanar_segments"]+=1
        counts["coplanar_triangle_overlap_events"]+=len(overlaps)
        for mode in spatial.DIAGONAL_MODES:
            result=segment.segment_candidate_triangle_ids(
                walker,a,b,diagonal_mode=mode,tolerance_units=tolerance_units)
            missing=truth-set(result["candidate_original_triangle_ids"])
            counts[f"{mode}_coplanar_candidate_count"]+=result["candidate_count"]
            counts[f"{mode}_coplanar_missing_queries"]+=bool(missing)
            counts[f"{mode}_coplanar_missing_triangle_ids"]+=len(missing)
            if missing and len(first_missing)<12:
                first_missing.append({"seed_triangle_id":tid,
                    "mode":mode,"segment_kind":"coplanar",
                    "missing_original_triangle_ids":sorted(missing)[:48]})
        # Short source-normal transverse segment through a triangle interior.
        center=oracle.sample_triangle(tid,(.2,.3,.5))
        normal=tuple(v/tri.normal_len for v in tri.normal)
        c=tuple(center[i]-.1*normal[i] for i in range(3))
        d=tuple(center[i]+.1*normal[i] for i in range(3))
        crossing=transverse.segment_crossings(oracle,c,d)
        source_ids={hit.original_triangle_id for hit in crossing["hits"]}
        if tid not in source_ids:
            raise ValueError("Independent transverse geometry lost source triangle")
        counts["transverse_segments"]+=1
        counts["transverse_triangle_crossing_events"]+=len(crossing["hits"])
        for mode in spatial.DIAGONAL_MODES:
            result=segment.segment_candidate_triangle_ids(
                walker,c,d,diagonal_mode=mode,tolerance_units=tolerance_units)
            missing=source_ids-set(result["candidate_original_triangle_ids"])
            counts[f"{mode}_transverse_candidate_count"]+=result["candidate_count"]
            counts[f"{mode}_transverse_missing_queries"]+=bool(missing)
            counts[f"{mode}_transverse_missing_triangle_ids"]+=len(missing)
            if missing and len(first_missing)<12:
                first_missing.append({"seed_triangle_id":tid,
                    "mode":mode,"segment_kind":"transverse",
                    "missing_original_triangle_ids":sorted(missing)[:48]})
    return {"schema":SCHEMA,
        "source_level_original_triangle_count":atlas["source_triangle_count"],
        "original_mopp_leaf_triangle_count":len(oracle.tris),
        "sampled_leaf_triangle_count":sampled,
        "complete_leaf_coverage":(stride==1 and sampled==len(oracle.tris)),
        "sampling_stride":stride,"totals":dict(counts),
        "first_missed_original_triangle_IDs_no_coordinates":first_missing,
        "coplanar_segment_was_source_AB_edge_extended_by_fraction":.2,
        "transverse_half_length_source_Level_units":.1,
        "mopp_quantization_margin_units":tolerance_units,
        "coplanar_geometry_plane_tolerance_source_Level_units":1e-5,
        "actual_Havok_segment_query_performed":False,
        "native_game_file_written":False}


def audit_map(source: Path, **options) -> dict:
    source=Path(source).resolve()
    if (not source.is_file() or source.suffix.lower()!=".gmp"
            or source.stat().st_size > exporter.provenance.mopp.flatcheck.MAX_MAP_BYTES):
        raise ValueError("Expected owner-provided original DX2 GMP")
    atlas,meta=exporter.audit_map(source)
    exporter_path=Path(__file__).resolve().parents[2]/"map_exporter"
    if str(exporter_path) not in sys.path:
        sys.path.insert(0,str(exporter_path))
    from dx2inspect import Package
    from dx2scene import find_bsp
    package=Package(source)
    if hashlib.sha256(package.data).hexdigest()!=meta["sha256"]:
        raise ValueError("Original GMP changed during validation")
    levels=[entry for entry in package.exports
            if package.class_name(entry)=="Level" and entry["size"]>0]
    if len(levels)!=1:
        raise ValueError("Expected one original authenticated Level export")
    result=audit_level(package.payload(levels[0]),find_bsp(package),**options)
    if result["source_level_original_triangle_count"]!=atlas["source_triangle_count"]:
        raise ValueError("Original triangle counts changed during validation")
    return {**meta,**result}


def main(argv=None) -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("maps",type=Path,nargs="+")
    ap.add_argument("--stride",type=int,default=1)
    ap.add_argument("--max-samples",type=int,default=0)
    ap.add_argument("--tolerance-units",type=float,default=1.)
    ap.add_argument("--report",type=Path)
    args=ap.parse_args(argv)
    try:
        if not 1<=len(args.maps)<=64:
            raise ValueError("Expected 1..64 original GMPs")
        paths=[p.resolve() for p in args.maps]
        if len(set(paths))!=len(paths):
            raise ValueError("Duplicate original GMP paths")
        rows=[audit_map(p,stride=args.stride,max_samples=args.max_samples,
                        tolerance_units=args.tolerance_units) for p in paths]
        summary=Counter()
        for row in rows:
            summary.update(row["totals"])
        missing=sum(v for k,v in summary.items() if k.endswith("_missing_queries"))
        report={"schema":SCHEMA,"read_only":True,"maps":rows,
                "summary":dict(summary),"maps_checked":len(rows),
                "mopp_interval_havok_runtime_verified":False,
                "game_sources_modified":False}
        if args.report:
            dest=args.report.resolve()
            if dest.suffix.lower()!=".json" or any(
                dest==p or dest.is_relative_to(p.parent) for p in paths):
                raise ValueError("Report must be fresh JSON outside all Maps directories")
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open("x",encoding="utf-8") as f:
                json.dump(report,f,indent=2,allow_nan=False)
                f.write("\n")
            print(json.dumps({"status":"ok","report":str(dest),
                              "missing_queries":missing}))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return int(bool(missing))
    except (OSError,ValueError,TypeError,IndexError,KeyError,
            OverflowError,struct.error) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
