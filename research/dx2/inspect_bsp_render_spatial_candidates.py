#!/usr/bin/env python3
"""Read-only geometry cross-reference: DX2 Level render triangles vs world BSP nodes.

Node-plane agreement plus full triangle inclusion in a node's bounding sphere
gives an *inferred spatial candidate*, NOT an engine-authenticated index link.
A triangle can match multiple coplanar nodes; such cases remain ambiguous.

Reads user-owned UE95 DX2 licensee 65/67/68/69 GMPs. No package writes.
Standard-library-only; builds on strict existing DX2SDK source decoders.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import struct
import sys

import inspect_world_bsp_node_boundaries as boundaries
from dx2scene import find_bsp

SCHEMA = "DX2SDK-world-BSP-render-triangle-spatial-crossref-v1"
NORMAL_TOL = 0.002
PLANE_W_TOL = 0.15
SPHERE_MARGIN = 0.15
NORMAL_BUCKET = 0.01
W_BUCKET = 0.5
BUCKET_NEIGHBORS = tuple(product((-1, 0, 1), repeat=4))
MAX_SAMPLES = 12


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _length(v):
    return math.sqrt(_dot(v, v))


def _key(plane):
    return (math.floor(plane[0]/NORMAL_BUCKET),
            math.floor(plane[1]/NORMAL_BUCKET),
            math.floor(plane[2]/NORMAL_BUCKET),
            math.floor(plane[3]/W_BUCKET))


def _valid_vec(vec, count):
    return (isinstance(vec, (tuple, list)) and len(vec) == count
            and all(type(x) in (int, float) and math.isfinite(float(x))
                    and abs(float(x)) <= 1e8 for x in vec))


def analyze_spatial_candidates(nodes, triangles, *, include_matches=False):
    """Cross-check node (plane, sphere) pairs against labelled triangle XYZ.

    triangles: Iterable of (triangle_locator, (xyz0,xyz1,xyz2)).
    No node-to-render index field is assumed. Full-vertex sphere inclusion is
    stronger than just a coplanar point but not proof of serialized ownership.
    """
    if not nodes:
        raise ValueError("No world BSP nodes")
    buckets = defaultdict(list)
    for idx, fields in enumerate(nodes):
        plane, sphere = fields
        if not _valid_vec(plane, 4) or not _valid_vec(sphere, 4) or sphere[3] < 0:
            raise ValueError(f"Invalid plane or sphere for BSP node {idx}")
        if abs(_length(plane[:3])-1) > 1e-3:
            raise ValueError(f"Invalid node splitting-plane normal at {idx}")
        for sign in (1, -1):
            signed = tuple(sign*x for x in plane)
            buckets[_key(signed)].append((idx, signed, sphere))

    count = Counter()
    examples = {"plane_unmatched": [], "spatial_unmatched": [], "ambiguous": []}
    matches = []
    for locator, xyz in triangles:
        if not isinstance(xyz, (tuple, list)) or len(xyz) != 3 or any(
                not _valid_vec(vertex, 3) for vertex in xyz):
            raise ValueError("Invalid rendered triangle coordinates")
        a, b, c = xyz
        normal_unnormalized = _cross(_sub(b, a), _sub(c, a))
        magnitude = _length(normal_unnormalized)
        if magnitude <= 1e-5:
            count["degenerate_triangles"] += 1
            continue
        normal = tuple(value/magnitude for value in normal_unnormalized)
        plane_w = _dot(normal, a)
        lookup = normal + (plane_w,)
        key = _key(lookup)
        near_planes = {}
        for delta in BUCKET_NEIGHBORS:
            neighbor = tuple(key[i]+delta[i] for i in range(4))
            for node_idx, node_plane, sphere in buckets.get(neighbor, ()):
                if node_idx in near_planes:
                    continue
                if (_length(_sub(normal, node_plane[:3])) > NORMAL_TOL
                        or abs(plane_w-node_plane[3]) > PLANE_W_TOL):
                    continue
                near_planes[node_idx] = sphere
        count["nondegenerate_triangles"] += 1
        if not near_planes:
            if len(examples["plane_unmatched"]) < MAX_SAMPLES:
                examples["plane_unmatched"].append(locator)
            if include_matches:
                matches.append({"triangle": locator, "candidate_nodes": []})
            continue
        count["same_infinite_plane"] += 1
        centroid = tuple((a[i]+b[i]+c[i])/3 for i in range(3))
        centroid_ids = []
        full_ids = []
        for node_idx, sphere in near_planes.items():
            center, radius = sphere[:3], sphere[3] + SPHERE_MARGIN
            if _length(_sub(centroid, center)) <= radius:
                centroid_ids.append(node_idx)
            if all(_length(_sub(vertex, center)) <= radius for vertex in xyz):
                full_ids.append(node_idx)
        if centroid_ids:
            count["centroid_in_node_sphere"] += 1
        if full_ids:
            count["all_triangle_vertices_in_node_sphere"] += 1
            count["unique_candidate" if len(full_ids) == 1
                  else "ambiguous_candidates"] += 1
            if len(full_ids) > 1 and len(examples["ambiguous"]) < MAX_SAMPLES:
                examples["ambiguous"].append(
                    {"triangle": locator, "candidate_node_count": len(full_ids),
                     "candidate_nodes": sorted(full_ids)[:12]})
        elif len(examples["spatial_unmatched"]) < MAX_SAMPLES:
            examples["spatial_unmatched"].append(locator)
        if include_matches:
            matches.append({"triangle": locator, "candidate_nodes": sorted(full_ids)})
    return {
        "counts": dict(count),
        "examples": examples,
        **({"candidate_triangle_nodes": matches} if include_matches else {}),
    }


def _triangles_from_render_blocks(blocks):
    for bi, block in enumerate(blocks):
        start, end = block["offset"], block["end"]
        if not (0 <= start < end and block["id"] == end-start):
            raise ValueError("Render block missing exact 4-byte length prefix")
        vertices = block["vertices"]
        for si, section in enumerate(block["sections"]):
            indices = section["indices"]
            if len(indices) % 3 != 0:
                raise ValueError("Malformed render triangle index count")
            for ti in range(0, len(indices), 3):
                corners = []
                for idx in indices[ti:ti+3]:
                    if type(idx) is not int or idx < 0 or idx >= len(vertices):
                        raise ValueError("Render triangle index outside vertex buffer")
                    corners.append(vertices[idx][0])
                yield ([bi, si, ti//3], tuple(corners))


def audit_map(path: Path, *, include_matches=False):
    path = Path(path)
    if (path.suffix.casefold() != ".gmp" or not path.is_file()
            or path.stat().st_size > boundaries.world.MAX_MAP_BYTES):
        raise ValueError("Expected existing, reasonably sized user-owned DX2 GMP")
    pkg = boundaries.world.Package(path)
    if pkg.version != 95 or pkg.licensee not in boundaries.world.OBSERVED_LICENSEES:
        raise ValueError("Expected source-observed UE95 DX2 licensee 65/67/68/69")
    root = boundaries.world._parse_world_model(pkg)
    exp = pkg.exports[root["world_model_export_ref"]-1]
    payload = pkg.payload(exp)
    frame = boundaries.parse_world_model(payload, include_nodes=True)
    nodes = []
    for record in frame["node_records"]:
        start, size = record["start"], record["length"]
        nodes.append((
            struct.unpack_from("<4f", payload, start),
            struct.unpack_from("<4f", payload, start+size-53),
        ))
    blocks = find_bsp(pkg)
    if not blocks:
        raise ValueError("No structurally validated Flesh render blocks in Level")
    result = analyze_spatial_candidates(
        nodes, _triangles_from_render_blocks(blocks),
        include_matches=include_matches)
    return {
        "map": path.name, "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
        "licensee": pkg.licensee, "world_model_export": exp["index"],
        "world_model_sha256": hashlib.sha256(payload).hexdigest(),
        "node_count": len(nodes), "validated_render_blocks": len(blocks),
        "all_render_block_length_prefixes_verified": True,
        **result,
    }


def audit_maps(paths, *, include_matches=False):
    if not 1 <= len(paths) <= boundaries.world.MAX_MAPS:
        raise ValueError("Provide 1 to 64 user-owned GMP files")
    inputs = [Path(p).resolve() for p in paths]
    if len(set(inputs)) != len(inputs):
        raise ValueError("Duplicate source GMP input")
    maps = [audit_map(path, include_matches=include_matches) for path in inputs]
    totals = Counter()
    for row in maps:
        totals["maps"] += 1
        totals["nodes"] += row["node_count"]
        totals["render_blocks"] += row["validated_render_blocks"]
        totals.update(row["counts"])
    if (totals["unique_candidate"] + totals["ambiguous_candidates"]
            != totals["all_triangle_vertices_in_node_sphere"]):
        raise ValueError("Inconsistent candidate classification counts")
    return {
        "schema": SCHEMA, "read_only": True,
        "native_geometry_writer_implemented": False,
        "native_collision_decoded": False,
        "engine_node_triangle_index_decoded": False,
        "runtime_verified_by_this_audit": False,
        "tolerances": {"normal_vector_delta": NORMAL_TOL,
                       "plane_w_source_units": PLANE_W_TOL,
                       "node_sphere_margin_source_units": SPHERE_MARGIN},
        "summary": dict(totals), "maps": maps,
        "limits": [
            "Geometric candidates are inferred from shared planes and sphere containment.",
            "Matching geometry does not authenticate BSP surface/render-block ownership.",
            "Coplanar overlapping nodes can produce multiple candidates; never resolve by guess.",
            "Unmatched triangles and degenerate source triangles are retained in the report.",
            "Node plane is in source Model coordinates; no transforms or game physics are changed.",
            "Source maps are only read, never modified, installed or distributed.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--include-matches", action="store_true",
                        help="Include per-triangle candidate node lists (large JSON)")
    args = parser.parse_args(argv)
    try:
        report = audit_maps(args.maps, include_matches=args.include_matches)
        if args.report:
            boundaries.world.write_report(report, args.report, args.maps)
            print(json.dumps({"status": "ok", "report": str(args.report),
                              "summary": report["summary"]}, indent=2))
        else:
            print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, IndexError, OverflowError, struct.error) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
