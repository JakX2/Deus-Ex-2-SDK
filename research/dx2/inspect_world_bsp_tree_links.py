#!/usr/bin/env python3
"""Read-only DX2 world BSP node reference graph / plane-side audit.

The source-observed variable-width Model records each contain exactly eight
Unreal compact integers between their 48-byte plane+mask prefix and sphere.
Fields 3/4/5 form a rooted tree across the examined DX2 retail corpus.
Semantics and engine member names are provisional. No native writer.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import inspect_world_bsp_node_boundaries as boundaries

SCHEMA = "DX2SDK-world-BSP-eight-compact-link-graph-v1"
LINK_FIELDS = (3, 4, 5)
FIELDS_PER_NODE = 8


def inspect_link_graph(payload: bytes, frame: dict, *, include_edges: bool = False) -> dict:
    """Verify exact compact framing, one-parent reachability and plane clues."""
    n = frame.get("candidate_node_count")
    records = frame.get("node_records")
    if type(n) is not int or not 1 <= n <= boundaries.MAX_NODES:
        raise ValueError("Invalid source candidate node count")
    if type(records) is not list or len(records) != n:
        raise ValueError("Full validated node-boundary records are required")
    links = []
    planes = []
    centers = []
    flag0 = Counter()
    for i, record in enumerate(records):
        start, size = record["start"], record["length"]
        if (type(start) is not int or type(size) is not int
                or size not in boundaries.OBSERVED_RECORD_LENGTHS):
            raise ValueError(f"Node {i} has unsupported record framing")
        begin = start + boundaries.PLANE_BYTES + boundaries.MASK_BYTES
        end = start + size - 53
        if begin >= end or end > len(payload):
            raise ValueError(f"Node {i} compact segment outside payload")
        cursor = boundaries.world.Cursor(payload, begin, end)
        try:
            values = [cursor.ci() for _ in range(FIELDS_PER_NODE)]
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Node {i} compact field segment truncated") from exc
        if cursor.at != end:
            raise ValueError(f"Node {i} has extra bytes in eight-compact segment")
        if values[0] not in (0, 5):
            raise ValueError(f"Node {i} compact field zero outside observed values")
        for column in LINK_FIELDS:
            target = values[column]
            if not (-1 <= target < n) or target == i:
                raise ValueError(f"Node {i} field {column} invalid linked index {target}")
        flag0[values[0]] += 1
        links.append(values)
        planes.append(tuple(struct.unpack_from("<4f", payload, start)))
        centers.append(tuple(struct.unpack_from("<3f", payload, start+size-53)))
    incoming = [0]*n
    edges = []
    by_field = Counter()
    for i, values in enumerate(links):
        for column in LINK_FIELDS:
            target = values[column]
            if target < 0:
                continue
            incoming[target] += 1
            edges.append((i, target, column))
            by_field[str(column)] += 1
    if len(edges) != n-1 or incoming[0] != 0 or any(v != 1 for v in incoming[1:]):
        raise ValueError("Node links do not form unique-parent root-zero graph")
    queue = deque([(0, 0)])
    seen = set()
    max_depth = depth_total = 0
    while queue:
        idx, depth = queue.popleft()
        if idx in seen:
            raise ValueError("Cycle or duplicate reachability in BSP reference graph")
        seen.add(idx)
        max_depth = max(max_depth, depth)
        depth_total += depth
        queue.extend((links[idx][k], depth+1)
                     for k in LINK_FIELDS if links[idx][k] >= 0)
    if len(seen) != n:
        raise ValueError(f"BSP link root cannot reach all nodes: {len(seen)}/{n}")

    side_evidence = Counter()
    chain_evidence = Counter()
    exceptional_links = []
    for parent, child, field in edges:
        a = planes[parent]
        if field == 5:
            b = planes[child]
            tolerance = max(.001, 2e-5*max(abs(v) for v in a+b))
            if max(abs(x-y) for x,y in zip(a,b)) <= tolerance:
                chain_evidence["same_plane"] += 1
            elif max(abs(x+y) for x,y in zip(a,b)) <= tolerance:
                chain_evidence["opposite_oriented_plane"] += 1
            else:
                chain_evidence["different_plane"] += 1
                if len(exceptional_links) < 12:
                    exceptional_links.append({"parent":parent,"child":child,
                                              "finding":"field5_different_plane"})
        else:
            signed = sum(a[k]*centers[child][k] for k in range(3))-a[3]
            eps = max(.001, 2e-5*max(abs(v) for v in a+centers[child]))
            correct = signed < -eps if field == 3 else signed > eps
            side_evidence[f"field{field}_expected_side" if correct
                          else f"field{field}_near_plane_or_unexpected_side"] += 1
            if not correct and len(exceptional_links) < 12:
                exceptional_links.append({"parent":parent,"child":child,
                                          "field":field,"signed_distance":signed})
    return {
        "status": "validated_rooted_eight-compact-link_graph",
        "candidate_node_count": n, "compact_integers_per_node": FIELDS_PER_NODE,
        "candidate_link_columns": list(LINK_FIELDS),
        "root_index": 0, "edges": len(edges),
        "max_depth": max_depth, "sum_depth": depth_total,
        "mean_depth": depth_total/n,
        "all_nodes_reachable": True, "one_parent_per_nonroot_node": True,
        "edges_by_column": dict(by_field), "first_compact_field_counts": dict(flag0),
        "plane_side_evidence": dict(side_evidence),
        "coplanar_chain_evidence": dict(chain_evidence),
        "exception_examples": exceptional_links,
        "other_compact_fields_unclassified": [0,1,2,6,7],
        **({"graph_edges":[{"parent":p,"child":c,"compact_field":field}
                          for p,c,field in edges]} if include_edges else {}),
    }


def audit_map(path: Path, *, include_edges=False) -> dict:
    path = Path(path)
    if (path.suffix.lower() != ".gmp" or not path.is_file()
            or path.stat().st_size > boundaries.world.MAX_MAP_BYTES):
        raise ValueError("Expected an existing user-owned DX2 .gmp within size limit")
    pkg = boundaries.world.Package(path)
    if pkg.version != 95 or pkg.licensee not in boundaries.world.OBSERVED_LICENSEES:
        raise ValueError("Expected UE95 DX2 licensee 65/67/68/69")
    model_id = boundaries.world._parse_world_model(pkg)["world_model_export_ref"]
    model = pkg.exports[model_id-1]
    payload = pkg.payload(model)
    frame = boundaries.parse_world_model(payload, include_nodes=True)
    return {"file":path.name, "licensee":pkg.licensee,
            "source_sha256":hashlib.sha256(pkg.data).hexdigest(),
            "world_model_sha256":hashlib.sha256(payload).hexdigest(),
            "world_model_export_ref":model_id,
            **inspect_link_graph(payload,frame,include_edges=include_edges)}


def audit_maps(paths, *, include_edges=False) -> dict:
    if not 1 <= len(paths) <= boundaries.world.MAX_MAPS:
        raise ValueError("Supply between 1 and 64 user-owned GMPs")
    sources = [Path(p).resolve() for p in paths]
    if len(set(sources)) != len(sources):
        raise ValueError("Duplicate source GMP paths")
    maps = [audit_map(p,include_edges=include_edges) for p in sources]
    aggregate = Counter()
    for row in maps:
        aggregate["maps"] += 1
        aggregate["nodes"] += row["candidate_node_count"]
        aggregate["edges"] += row["edges"]
        aggregate["sum_depth"] += row["sum_depth"]
        aggregate["max_depth"] = max(aggregate["max_depth"], row["max_depth"])
        aggregate.update({"column_"+col+"_edges": count
                          for col,count in row["edges_by_column"].items()})
        aggregate.update(row["plane_side_evidence"])
        aggregate.update(row["coplanar_chain_evidence"])
    return {
        "schema": SCHEMA, "read_only": True, "native_gmp_written": False,
        "native_bsp_compiled": False, "collision_generated": False,
        "runtime_verified": False, "summary": dict(aggregate),
        "maps": maps,
        "limitations": [
            "Fields 3/4 have strong negative/positive child-side correlations, not proven member names.",
            "Field 5 usually refers to a same- or opposite-oriented plane; 37 of 7733 corpus links differ.",
            "Tree connectivity is checked; collision, PVS, zone semantics, render links and native writer are not.",
            "Original source GMP maps remain unchanged.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps",nargs="+",type=Path)
    parser.add_argument("--report",type=Path)
    parser.add_argument("--include-edges",action="store_true")
    args = parser.parse_args(argv)
    try:
        report = audit_maps(args.maps,include_edges=args.include_edges)
        if args.report:
            boundaries.world.write_report(report,args.report,args.maps)
            print(json.dumps({"status":"ok","report":str(args.report),
                              "summary":report["summary"]},indent=2))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,KeyError,OverflowError,struct.error) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
