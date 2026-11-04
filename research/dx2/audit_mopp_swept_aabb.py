#!/usr/bin/env python3
"""Owner-GMP read-only Level swept-AABB SAT versus source MOPP interval audit.

Verifies original UE95 Level/Flesh/MOPP provenance, then compares independent
moving-box triangle intersections with shape-expanded MOPP point candidates.
Reports IDs/statistics only. Never writes proprietary game data.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import struct
import sys

import export_level_mopp_triangle_debug_mesh as exporter
import audit_mopp_offsurface_segments as offsurface
import inspect_mopp_axis_point_candidates as mopp
import inspect_mopp_point_triangle_oracle as geometry
import inspect_mopp_swept_aabb as sweep

SCHEMA="DX2SDK-owner-Level-swept-AABB-geometry-versus-MOPP-v1"


def audit_source_level(level,blocks,*,bbox_random=128,triangle_aimed=128,
                       half_extents=(.2,.2,.3),seed=20261104,tolerance_units=1.):
    offsurface._validated_options(bbox_random,triangle_aimed,seed)
    half=sweep._half_extents(half_extents)
    atlas=exporter.inspect_mesh(level,blocks)
    oracle=geometry.original_atlas_oracle(atlas)
    verified=exporter.provenance.mopp.inspect_mopp_link(level,blocks)
    start=verified["mopp_code_start_in_level"]
    walker=mopp.ConservativeMoppPointCandidates(
        level[start:verified["mopp_code_end_in_level"]],
        atlas["source_triangle_count"],struct.unpack_from("<4f",level,start-20))
    if set(oracle.tris)!=walker.complete_leaf_set:
        raise ValueError("Source Level triangle IDs diverge from authenticated MOPP leaves")
    bounds=offsurface._bbox(oracle)
    rng=random.Random(seed ^ int.from_bytes(hashlib.sha256(level).digest()[:8],"little"))
    ids=sorted(oracle.tris)
    totals=Counter()
    miss_examples=[]
    for kind,count in (("bbox_random",bbox_random),("triangle_aimed",triangle_aimed)):
        for i in range(count):
            if kind=="bbox_random":
                a,b=offsurface._random_bbox_segment(oracle,rng,bounds)
                target=None
            else:
                a,b,target=offsurface._triangle_aimed_segment(oracle,rng,bounds,ids)
            truth=sweep.swept_aabb_triangle_hits(oracle,a,b,half)
            actual=set(truth["original_triangle_hit_ids"])
            if target is not None and target not in actual:
                raise ValueError("Source geometry target missing from independently swept AABB")
            totals[f"{kind}_sweeps"]+=1
            totals[f"{kind}_with_geometric_contact"]+=bool(actual)
            totals[f"{kind}_swept_triangle_ids"]+=len(actual)
            for mode in mopp.DIAGONAL_MODES:
                candidates=sweep.swept_aabb_mopp_candidates(
                    walker,a,b,half,diagonal_mode=mode,
                    tolerance_units=tolerance_units)
                present=set(candidates["candidate_original_triangle_ids"])
                missing=actual-present
                totals[f"{kind}_{mode}_comparisons"]+=1
                totals[f"{kind}_{mode}_candidate_ids"]+=len(present)
                totals[f"{kind}_{mode}_missing_queries"]+=bool(missing)
                totals[f"{kind}_{mode}_missing_triangle_ids"]+=len(missing)
                if missing and len(miss_examples)<10:
                    miss_examples.append({
                        "stratum":kind,"sample_index":i,"mode":mode,
                        "missing_original_triangle_ids":sorted(missing)[:32]})
    return {
        "schema":SCHEMA,
        "source_level_sha256":hashlib.sha256(level).hexdigest(),
        "original_source_triangle_count":atlas["source_triangle_count"],
        "mopp_leaf_source_triangle_count":len(oracle.tris),
        "half_extents_original_level_xyz":list(half),
        "seed":seed,
        "seed_mixed_with_original_level_sha256":True,
        "strata":["bbox_random","triangle_aimed"],
        "independent_geometry_is_continuous_13axis_SAT":True,
        "source_coordinate_tolerance_level_units":1e-7,
        "quantized_mopp_tolerance_units":tolerance_units,
        "totals":dict(totals),
        "first_missing_ID_counterexamples_without_coordinates":miss_examples,
        "runtime_Havok_swept_shape_verified":False,
        "rotation_and_capsules_supported":False,
        "source_bytes_modified":False,
    }


def audit_map(path,**options):
    path=Path(path).resolve()
    if (not path.is_file() or path.suffix.lower()!=".gmp" or
            path.stat().st_size>exporter.provenance.mopp.flatcheck.MAX_MAP_BYTES):
        raise ValueError("Expected original user-owned DX2 GMP")
    atlas,meta=exporter.audit_map(path)
    exporter_dir=Path(__file__).resolve().parents[2]/"map_exporter"
    if str(exporter_dir) not in sys.path:
        sys.path.insert(0,str(exporter_dir))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg=Package(path)
    sha=hashlib.sha256(pkg.data).hexdigest()
    if sha!=meta["sha256"]:
        raise ValueError("Original GMP SHA-256 changed between source validations")
    levels=[row for row in pkg.exports if pkg.class_name(row)=="Level" and row["size"]>0]
    if len(levels)!=1:
        raise ValueError("Expected exactly one authenticated original Level")
    result=audit_source_level(pkg.payload(levels[0]),find_bsp(pkg),**options)
    if result["original_source_triangle_count"]!=atlas["source_triangle_count"]:
        raise ValueError("Original flattened Level triangle count changed during verification")
    return {"file":path.name,"original_gmp_sha256":sha,**result}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps",nargs="+",type=Path)
    parser.add_argument("--bbox-random",type=int,default=128)
    parser.add_argument("--triangle-aimed",type=int,default=128)
    parser.add_argument("--half-extents",type=float,nargs=3,default=(.2,.2,.3))
    parser.add_argument("--seed",type=int,default=20261104)
    parser.add_argument("--tolerance-units",type=float,default=1.)
    parser.add_argument("--report",type=Path,
                        help="Create NEW JSON outside original game Maps")
    options=parser.parse_args(argv)
    try:
        offsurface._validated_options(
            options.bbox_random,options.triangle_aimed,options.seed)
        sweep._half_extents(options.half_extents)
        if not 1<=len(options.maps)<=64:
            raise ValueError("Expected 1..64 user-owned retail GMP maps")
        paths=[p.resolve() for p in options.maps]
        if len(set(paths))!=len(paths):
            raise ValueError("Duplicate original GMP input paths")
        rows=[audit_map(p,bbox_random=options.bbox_random,
                triangle_aimed=options.triangle_aimed,
                half_extents=options.half_extents,seed=options.seed,
                tolerance_units=options.tolerance_units) for p in paths]
        count=Counter()
        for row in rows:
            count.update(row["totals"])
        miss=sum(v for k,v in count.items() if k.endswith("_missing_queries"))
        report={"schema":SCHEMA,"maps_checked":len(rows),"summary":dict(count),
                "missing_candidate_comparisons":miss,"maps":rows,
                "owner_original_game_assets_modified":False,
                "runtime_havok_sweep_verified":False}
        if options.report:
            dest=options.report.resolve()
            if (dest.suffix.lower()!=".json" or any(
                    dest==p or dest.is_relative_to(p.parent) for p in paths)):
                raise ValueError("Report must be fresh JSON outside retail source Maps")
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open("x",encoding="utf-8") as handle:
                json.dump(report,handle,indent=2,allow_nan=False)
                handle.write("\n")
            print(json.dumps({"status":"ok","report":str(dest),
                              "summary":dict(count)}))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return int(bool(miss))
    except (OSError,ValueError,IndexError,TypeError,KeyError,
            OverflowError,struct.error) as error:
        print(json.dumps({"status":"refused","reason":str(error)}),
              file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
