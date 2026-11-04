#!/usr/bin/env python3
"""Read-only original GMP source-capsule-versus-MOPP enclosure audit.

Both sampling strata are deterministic and source-authenticated. Computes
triangle contacts with the independent swept-axis-patch geometry oracle, then
compares to shape-enclosing AABB MOPP candidates. Reports no source XYZ or code.
Not a Havok contact, capsule runtime emulator, collision compiler or GMP writer.
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
import audit_mopp_offsurface_segments as sampler
import inspect_mopp_axis_point_candidates as mopp
import inspect_mopp_point_triangle_oracle as geometry
import inspect_mopp_swept_capsule as capsule
import inspect_mopp_swept_aabb as box

SCHEMA="DX2SDK-owner-source-Level-swept-capsule-geometry-audit-v1"


def audit_source_level(level,blocks,*,bbox_random=32,triangle_aimed=32,
                       radius=.2,axis_half_length=.5,axis=(0.,0.,1.),
                       seed=20261104,tolerance_units=1.):
    sampler._validated_options(bbox_random,triangle_aimed,seed)
    rad,unit,half=capsule._shape(radius,axis,axis_half_length)
    atlas=exporter.inspect_mesh(level,blocks)
    source=geometry.original_atlas_oracle(atlas)
    valid=exporter.provenance.mopp.inspect_mopp_link(level,blocks)
    off=valid["mopp_code_start_in_level"]
    walker=mopp.ConservativeMoppPointCandidates(
        level[off:valid["mopp_code_end_in_level"]],
        atlas["source_triangle_count"],
        struct.unpack_from("<4f",level,off-20))
    if set(source.tris)!=walker.complete_leaf_set:
        raise ValueError("Original MOPP leaf IDs disagree with independent Level geometry")
    bounds=sampler._bbox(source)
    rng=random.Random(seed ^ int.from_bytes(hashlib.sha256(level).digest()[:8],"little"))
    ids=sorted(source.tris)
    totals=Counter()
    examples=[]
    # Extra independent geometric consistency check: every capsule hit must
    # also intersect its enclosing swept axis-aligned box.
    enclosing_half=tuple(rad+half*abs(unit[k]) for k in range(3))
    for kind,n in (("bbox_random",bbox_random),("triangle_aimed",triangle_aimed)):
        for i in range(n):
            if kind=="bbox_random":
                a,b=sampler._random_bbox_segment(source,rng,bounds)
                target=None
            else:
                a,b,target=sampler._triangle_aimed_segment(source,rng,bounds,ids)
            truth=capsule.swept_capsule_triangle_hits(
                source,a,b,rad,unit,half)
            hit_ids=set(truth["original_triangle_hit_ids"])
            if target is not None and target not in hit_ids:
                raise ValueError("Independent capsule geometry missed aimed original triangle")
            box_ids=set(box.swept_aabb_triangle_hits(
                source,a,b,enclosing_half)["original_triangle_hit_ids"])
            if not hit_ids<=box_ids:
                raise ValueError("Independent capsule triangle hit escaped enclosing AABB SAT")
            totals[f"{kind}_sweeps"]+=1
            totals[f"{kind}_with_geometric_hits"]+=bool(hit_ids)
            totals[f"{kind}_geometric_triangle_ids"]+=len(hit_ids)
            for mode in mopp.DIAGONAL_MODES:
                answer=capsule.swept_capsule_mopp_candidates(
                    walker,a,b,rad,unit,half,diagonal_mode=mode,
                    tolerance_units=tolerance_units)
                candidate_ids=set(answer["candidate_original_triangle_ids"])
                missing=hit_ids-candidate_ids
                totals[f"{kind}_{mode}_comparisons"]+=1
                totals[f"{kind}_{mode}_candidate_triangle_ids"]+=len(candidate_ids)
                totals[f"{kind}_{mode}_missing_queries"]+=bool(missing)
                totals[f"{kind}_{mode}_missing_triangle_ids"]+=len(missing)
                if missing and len(examples)<12:
                    examples.append({
                        "kind":kind,"sample_index":i,"mode":mode,
                        "missing_original_triangle_ids":sorted(missing)[:32]})
    return {
        "schema":SCHEMA,
        "source_level_sha256":hashlib.sha256(level).hexdigest(),
        "original_flat_source_triangles":atlas["source_triangle_count"],
        "mopp_leaf_source_triangles":len(source.tris),
        "capsule_radius_original_level_units":rad,
        "capsule_axis_unit_xyz":list(unit),
        "capsule_axis_half_length_original_level_units":half,
        "enclosing_AABB_half_extents_original_level_xyz":list(enclosing_half),
        "random_seed":seed,
        "seed_mixed_with_original_Level_sha":True,
        "strata":["bbox_random","triangle_aimed"],
        "source_geometry_and_MOPP_are_independent_checks":True,
        "capsule_geometry_subset_of_independent_swept_AABB":True,
        "source_MOPP_point_branch_models_only":True,
        "totals":dict(totals),
        "first_missing_original_ids_without_source_coordinates":examples,
        "native_Havok_runtime_capsule_tested":False,
        "retail_assets_modified":False,
    }


def audit_map(path: Path,**options):
    path=Path(path).resolve()
    if (not path.is_file() or path.suffix.lower()!=".gmp" or
            path.stat().st_size>exporter.provenance.mopp.flatcheck.MAX_MAP_BYTES):
        raise ValueError("Expected owner-provided original DX2 GMP")
    atlas,meta=exporter.audit_map(path)
    module=Path(__file__).resolve().parents[2]/"map_exporter"
    if str(module) not in sys.path:sys.path.insert(0,str(module))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg=Package(path)
    sha=hashlib.sha256(pkg.data).hexdigest()
    if sha!=meta["sha256"]:
        raise ValueError("Original GMP changed between source validations")
    levels=[e for e in pkg.exports
            if pkg.class_name(e)=="Level" and e["size"]>0]
    if len(levels)!=1:
        raise ValueError("Expected exactly one source Level export")
    result=audit_source_level(pkg.payload(levels[0]),find_bsp(pkg),**options)
    if result["original_flat_source_triangles"]!=atlas["source_triangle_count"]:
        raise ValueError("Source triangle count changed between validations")
    return {"original_gmp":path.name,"original_gmp_sha256":sha,**result}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("maps",nargs="+",type=Path)
    p.add_argument("--bbox-random",type=int,default=32)
    p.add_argument("--triangle-aimed",type=int,default=32)
    p.add_argument("--radius",type=float,default=.2)
    p.add_argument("--axis-half-length",type=float,default=.5)
    p.add_argument("--axis",type=float,nargs=3,default=(0.,0.,1.))
    p.add_argument("--seed",type=int,default=20261104)
    p.add_argument("--tolerance-units",type=float,default=1.)
    p.add_argument("--report",type=Path,help="Create new JSON outside retail Maps directories")
    args=p.parse_args(argv)
    try:
        sampler._validated_options(args.bbox_random,args.triangle_aimed,args.seed)
        capsule._shape(args.radius,args.axis,args.axis_half_length)
        if not 1<=len(args.maps)<=64:
            raise ValueError("Expected 1..64 user-owned original GMP maps")
        paths=[s.resolve() for s in args.maps]
        if len(set(paths))!=len(paths):
            raise ValueError("Duplicate original source GMP path")
        rows=[audit_map(path,bbox_random=args.bbox_random,
            triangle_aimed=args.triangle_aimed,
            radius=args.radius,axis=args.axis,axis_half_length=args.axis_half_length,
            seed=args.seed,tolerance_units=args.tolerance_units) for path in paths]
        totals=Counter()
        for row in rows:totals.update(row["totals"])
        misses=sum(n for key,n in totals.items() if key.endswith("_missing_queries"))
        report={"schema":SCHEMA,"maps_checked":len(rows),"summary":dict(totals),
                "missing_candidate_queries":misses,"per_map":rows,
                "original_game_assets_modified":False,
                "Havok_runtime_contact_verified":False}
        if args.report:
            out=args.report.resolve()
            if out.suffix.lower()!=".json" or any(
                    out==source or out.is_relative_to(source.parent) for source in paths):
                raise ValueError("Report must be new JSON outside original source Maps")
            out.parent.mkdir(parents=True,exist_ok=True)
            with out.open("x",encoding="utf-8") as f:
                json.dump(report,f,indent=2,allow_nan=False)
                f.write("\n")
            print(json.dumps({"status":"ok","report":str(out),
                              "missing_candidate_queries":misses}))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return int(misses>0)
    except (OSError,ValueError,IndexError,TypeError,KeyError,
            OverflowError,struct.error) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
