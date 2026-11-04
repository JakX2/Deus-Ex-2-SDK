#!/usr/bin/env python3
"""Read-only DX2 MOPP point candidates vs complete independent geometric hits.

Each original f32 Level point is independently intersected against every
source MOPP-linked triangle through a geometry-only AABB BVH, then compared
against both axis/diagonal MOPP point-candidate research interpreters.

NOT Havok collision, a raycast, a contact solver, or a new Level/MOPP writer.
Original game bytes remain unchanged and private.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import export_level_mopp_triangle_debug_mesh as exporter
import inspect_mopp_axis_point_candidates as mopp_spatial
import inspect_mopp_point_triangle_oracle as geometry

SCHEMA = "DX2SDK-source-MOPP-complete-geometric-hit-check-v1"
BARY = {
    "centroid": (1/3,1/3,1/3),
    "edge_ab": (0.5,0.5,0),
    "vertex_a": (1,0,0),
    "vertex_b": (0,1,0),
    "vertex_c": (0,0,1),
}


def audit_source_level(level: bytes, blocks: list[dict], *,
                       max_source_triangles: int = 0,
                       vertex_stride: int = 10,
                       tolerance_units: float = 1.0) -> dict:
    if (type(max_source_triangles) is not int
            or not 0 <= max_source_triangles <= 300_000
            or type(vertex_stride) is not int
            or not 1 <= vertex_stride <= 100_000):
        raise ValueError("Invalid original triangle or vertex probe bounds")
    atlas = exporter.inspect_mesh(level, blocks)
    oracle = geometry.original_atlas_oracle(atlas)
    validated = exporter.provenance.mopp.inspect_mopp_link(level, blocks)
    code_start = validated["mopp_code_start_in_level"]
    code_end = validated["mopp_code_end_in_level"]
    spatial = mopp_spatial.ConservativeMoppPointCandidates(
        level[code_start:code_end],
        atlas["source_triangle_count"],
        struct.unpack_from("<4f",level,code_start-20))
    if (len(oracle.tris) != atlas["mopp_leaf_triangle_count"]
            or set(oracle.tris) != spatial.complete_leaf_set):
        raise ValueError("Independent original triangle ID domains differ")

    evaluated = Counter()
    misses = Counter()
    missing_ids = Counter()
    multiplicities = Counter()
    candidates = Counter()
    evidence = []
    for count, tid in enumerate(sorted(oracle.tris)):
        if max_source_triangles and count >= max_source_triangles:
            break
        probes = ["centroid", "edge_ab"]
        if tid % vertex_stride == 0:
            probes.extend(("vertex_a", "vertex_b", "vertex_c"))
        for name in probes:
            xyz = oracle.sample_triangle(tid,BARY[name])
            truth = oracle.containing_triangle_ids(xyz)
            if tid not in truth:
                raise ValueError("Independent geometry oracle lost originating triangle")
            evaluated[name] += 1
            multiplicities[f"{name}_{len(truth)}"] += 1
            for mode in mopp_spatial.DIAGONAL_MODES:
                result = geometry.compare_point_to_mopp(
                    oracle, spatial, xyz,
                    diagonal_mode=mode, tolerance_units=tolerance_units)
                key = f"{name}_{mode}"
                candidates[key] += result["candidate_count"]
                if not result["all_geometric_hits_retained"]:
                    misses[key] += 1
                    missing_ids[key] += len(result[
                        "geometrically_intersecting_triangles_missing_from_mopp"])
                    if len(evidence) < 12:
                        # Intentionally DO NOT serialize private map XYZ.
                        evidence.append({
                            "probe_source_triangle_id":tid,
                            "probe_type":name, "mode":mode,
                            "all_geometric_source_triangle_ids":truth[:48],
                            "missing_geometrically_valid_source_ids":result[
                                "geometrically_intersecting_triangles_missing_from_mopp"][:48],
                        })
    means = {}
    for probe, n in evaluated.items():
        for mode in mopp_spatial.DIAGONAL_MODES:
            key = f"{probe}_{mode}"
            means[key] = candidates[key]/n
    return {
        "schema":SCHEMA,
        "original_source_triangles":atlas["source_triangle_count"],
        "nondegenerate_source_triangles":len(oracle.tris),
        "geometry_oracle_bvh_nodes":len(oracle.nodes),
        "probes_by_type":dict(evaluated),
        "geometric_hit_multiplicity_counts":dict(multiplicities),
        "probe_queries_missing_geometric_triangle_ids":dict(misses),
        "total_geometric_triangle_ids_missing":dict(missing_ids),
        "mean_mopp_candidates_by_probe_mode":means,
        "first_missed_source_triangle_examples":evidence,
        "all_original_leaf_ids_checked":not max_source_triangles or
            max_source_triangles >= len(oracle.tris),
        "geometric_plane_tolerance_Level_units":1e-5,
        "geometric_barycentric_tolerance":1e-8,
        "mopp_quantization_tolerance_units":tolerance_units,
        "diagonal_modes_tested":list(mopp_spatial.DIAGONAL_MODES),
        "runtime_havok_executed":False,
        "swept_shapes_or_rays_tested":False,
        "native_collision_writer_available":False,
        "original_level_bytes_modified":False,
    }


def audit_map(source: Path, **opts) -> dict:
    # Complete existing strict source Package/Level/MOPP validation chain.
    atlas, meta = exporter.audit_map(source)
    root = Path(__file__).resolve().parents[2]
    exporter_dir = root / "map_exporter"
    if str(exporter_dir) not in sys.path:
        sys.path.insert(0,str(exporter_dir))
    from dx2inspect import Package
    from dx2scene import find_bsp
    package = Package(source)
    if hashlib.sha256(package.data).hexdigest() != meta["sha256"]:
        raise ValueError("Source map changed between validation and audit")
    levels = [x for x in package.exports
              if package.class_name(x)=="Level" and x["size"]>0]
    if len(levels)!=1:
        raise ValueError("Expected exactly one authenticated original Level")
    report = audit_source_level(
        package.payload(levels[0]),find_bsp(package),**opts)
    if report["original_source_triangles"] != atlas["source_triangle_count"]:
        raise ValueError("Original triangle counts changed after source validation")
    return {**meta,**report}


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps",nargs="+",type=Path)
    parser.add_argument("--max-source-triangles",type=int,default=0)
    parser.add_argument("--vertex-stride",type=int,default=10)
    parser.add_argument("--tolerance-units",type=float,default=1.)
    parser.add_argument("--report",type=Path,
                        help="Fresh research JSON outside original Maps directories")
    args=parser.parse_args(argv)
    try:
        if not 1 <= len(args.maps) <= 64:
            raise ValueError("Supply 1..64 user-owned original DX2 maps")
        maps=[p.resolve() for p in args.maps]
        if len(set(maps))!=len(maps):
            raise ValueError("Duplicate original source GMP path")
        rows=[audit_map(
            p,max_source_triangles=args.max_source_triangles,
            vertex_stride=args.vertex_stride,
            tolerance_units=args.tolerance_units) for p in maps]
        all_misses=sum(sum(r["probe_queries_missing_geometric_triangle_ids"].values())
                       for r in rows)
        probes=sum(sum(r["probes_by_type"].values()) for r in rows)
        summary={
            "maps":len(rows),
            "geometric_point_probes":probes,
            "mopp_candidate_set_comparisons":2*probes,
            "candidate_queries_missing_any_exact_geometric_hit":all_misses,
            "mopp_query_runtime_verified":False,
            "source_assets_modified":False,
        }
        report={"schema":SCHEMA,"summary":summary,"maps":rows,
                "read_only":True,"native_collision_writer_implemented":False}
        if args.report:
            out=args.report.resolve()
            if out.suffix.lower()!=".json" or any(
                out==src or out.is_relative_to(src.parent) for src in maps):
                raise ValueError("Research JSON must not overwrite or be inside source Maps")
            out.parent.mkdir(parents=True,exist_ok=True)
            with out.open("x",encoding="utf-8") as f:
                json.dump(report,f,indent=2,allow_nan=False)
                f.write("\n")
            print(json.dumps({"status":"ok","report":str(out),"summary":summary}))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return int(all_misses>0)
    except (OSError,ValueError,KeyError,IndexError,TypeError,
            OverflowError,struct.error) as error:
        print(json.dumps({"status":"refused","reason":str(error)}),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
