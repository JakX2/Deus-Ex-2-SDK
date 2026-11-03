#!/usr/bin/env python3
"""Read-only, hypothesis-driven DX2 world BSP compact-field role audit.

No compact field 1/2/6/7 name is asserted as a decoded native member.
Correlations are reported as successes and exceptions, not validated semantics.
Uses the prior source-observed node, rooted-tree and zone validators.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import inspect_world_bsp_zone_relations as zones

SCHEMA = "DX2SDK-world-BSP-compact-role-hypotheses-v1"
INTERESTING_COLUMNS = (0, 1, 2, 6, 7)
EXAMPLE_LIMIT = 16


def analyze_rows(rows: list[dict], *, include_nodes: bool = False) -> dict:
    """Pure analyzer for strictly framed eight-compact BSP node rows."""
    if not rows:
        raise ValueError("No BSP nodes supplied")
    n = len(rows)
    counter = Counter()
    field_values = {field: [] for field in INTERESTING_COLUMNS}
    spans = []
    anomalies = {"noncontiguous_candidate_vertex_starts": [],
                 "coplanar_differing_candidate_surfaces": [],
                 "negative_candidate_vertex_start": []}
    prev_start = prev_count = None
    for i, row in enumerate(rows):
        fields = row.get("fields")
        vcount = row.get("vertex_count")
        if (not isinstance(fields, (tuple, list)) or len(fields) != 8 or
                any(type(v) is not int for v in fields) or
                type(vcount) is not int or not 3 <= vcount <= 32):
            raise ValueError(f"Invalid compact fields or candidate vertex count on node {i}")
        for field in INTERESTING_COLUMNS:
            field_values[field].append(fields[field])
        counter["candidate_vertex_slots"] += vcount
        start = fields[1]
        if start < 0:
            counter["negative_candidate_vertex_starts"] += 1
            if len(anomalies["negative_candidate_vertex_start"]) < EXAMPLE_LIMIT:
                anomalies["negative_candidate_vertex_start"].append({"node": i, "value": start})
        else:
            spans.append((start, start + vcount))
        if prev_start is not None:
            counter["adjacent_record_pairs"] += 1
            if start == prev_start + prev_count:
                counter["adjacent_candidate_vertex_spans_contiguous"] += 1
            elif len(anomalies["noncontiguous_candidate_vertex_starts"]) < EXAMPLE_LIMIT:
                anomalies["noncontiguous_candidate_vertex_starts"].append({
                    "left_node": i-1, "right_node": i,
                    "left_end_candidate": prev_start+prev_count,
                    "right_start_candidate": start})
        prev_start, prev_count = start, vcount
        coplanar = fields[5]
        if coplanar >= 0:
            if coplanar >= n or coplanar == i:
                raise ValueError(f"Invalid field 5 rooted-tree target on node {i}")
            other = rows[coplanar]["fields"]
            counter["coplanar_candidate_pairs"] += 1
            if fields[2] == other[2]:
                counter["coplanar_pairs_same_candidate_surface"] += 1
            elif len(anomalies["coplanar_differing_candidate_surfaces"]) < EXAMPLE_LIMIT:
                anomalies["coplanar_differing_candidate_surfaces"].append({
                    "node": i, "coplanar_node": coplanar,
                    "surface_a_candidate": fields[2], "surface_b_candidate": other[2]})
    spans.sort()
    # A compact index can be unique and sparse (offset-like), unique and
    # dense (per-record ordinal), or dense with repetition (shared-table ID).
    # These categories are independent of any presumed engine member name.
    index_shapes = {}
    for field in (1, 2, 6, 7):
        values = field_values[field]
        nonnegative = [v for v in values if v >= 0]
        unique = set(nonnegative)
        maximum = max(unique) if unique else None
        dense = (bool(unique) and min(unique) == 0
                 and len(unique) == maximum + 1)
        index_shapes[str(field)] = {
            "nonnegative_occurrences": len(nonnegative),
            "nonnegative_distinct": len(unique),
            "duplicate_nonnegative_occurrences": len(nonnegative) - len(unique),
            "negative_one_occurrences": values.count(-1),
            "max_nonnegative": maximum,
            "zero_based_dense": dense,
            "zero_based_unique_dense": dense and len(nonnegative) == len(unique),
            "unique_nonnegative": len(nonnegative) == len(unique),
            "missing_zero_based_values": (
                maximum + 1 - len(unique) if maximum is not None else None),
        }
    sorted_gaps = [spans[i+1][0] - spans[i][1]
                   for i in range(len(spans)-1)]
    if any(gap < 0 for gap in sorted_gaps):
        counter["overlapping_sorted_neighbors"] = sum(
            gap < 0 for gap in sorted_gaps)
    counter["sorted_contiguous_neighbors"] = sum(
        gap == 0 for gap in sorted_gaps)
    counter["sorted_gapped_neighbors"] = sum(
        gap > 0 for gap in sorted_gaps)
    counter["sorted_gap_slots"] = sum(
        gap for gap in sorted_gaps if gap > 0)
    covered = 0
    overlapping_slots = 0
    first = last = None
    for a, b in spans:
        if first is None:
            first, last = a, b
            continue
        if a >= last:
            covered += last-first
            first, last = a, b
        else:
            overlapping_slots += min(last, b)-a
            last = max(last, b)
    if first is not None:
        covered += last-first
    end_max = max((b for _, b in spans), default=None)
    counter["candidate_vertex_span_union_slots"] = covered
    counter["candidate_vertex_span_overlap_slots"] = overlapping_slots
    counter["candidate_vertex_span_max_end"] = end_max or 0
    result = {
        "nodes": n,
        "candidate_slot_count": counter["candidate_vertex_slots"],
        "index_shapes": index_shapes,
        "fields": {
            str(field): {
                "min": min(values), "max": max(values),
                "negative_one_count": sum(v == -1 for v in values),
                "zero_count": sum(v == 0 for v in values),
                "negative_other_count": sum(v < -1 for v in values),
                "unique_values": len(set(values)),
                "at_least_node_count": sum(v >= n for v in values),
            } for field, values in field_values.items()
        },
        "candidate_vertex_spans": {
            "nonnegative_starts": len(spans),
            "negative_starts": counter["negative_candidate_vertex_starts"],
            "adjacent_pairs": counter["adjacent_record_pairs"],
            "adjacent_exact_contiguous": counter["adjacent_candidate_vertex_spans_contiguous"],
            "union_slots": covered,
            "overlap_slot_count": overlapping_slots,
            "all_nonnegative_spans_disjoint": overlapping_slots == 0,
            "sorted_contiguous_neighbors": counter["sorted_contiguous_neighbors"],
            "sorted_gapped_neighbors": counter["sorted_gapped_neighbors"],
            "sorted_gap_slots": counter["sorted_gap_slots"],
            "max_end": end_max,
            "dense_zero_based_no_overlaps": (
                len(spans) == n and covered == counter["candidate_vertex_slots"]
                and min(a for a, _ in spans) == 0 and end_max == covered),
        },
        "coplanar_candidate_surface": {
            "field5_links": counter["coplanar_candidate_pairs"],
            "same_field2": counter["coplanar_pairs_same_candidate_surface"],
            "different_field2": (counter["coplanar_candidate_pairs"] -
                                 counter["coplanar_pairs_same_candidate_surface"]),
        },
        "exception_examples": anomalies,
        **({"node_compact_rows": [
            {"node": i, "compact_fields": list(row["fields"]),
             "candidate_vertex_count": row["vertex_count"]}
            for i, row in enumerate(rows)]} if include_nodes else {}),
    }
    if (result["candidate_vertex_spans"]["adjacent_exact_contiguous"] > n-1 or
            result["coplanar_candidate_surface"]["same_field2"] >
            result["coplanar_candidate_surface"]["field5_links"]):
        raise ValueError("Internal role-audit counters inconsistent")
    return result


def inspect_model(payload: bytes, frame: dict, *, include_nodes: bool = False) -> dict:
    """Require existing strict zone+tree validation before evaluating hypotheses."""
    verified = zones.inspect_zone_relations(payload, frame)
    if not verified["rooted_node_graph_validated"]:
        raise ValueError("Rooted BSP graph not validated")
    rows = []
    for i, record in enumerate(frame["node_records"]):
        start, size = record["start"], record["length"]
        reader = zones.topology.boundaries.world.Cursor(payload,
                                                       start + 48, start + size - 53)
        compact = [reader.ci() for _ in range(8)]
        if reader.at != start + size - 53:
            raise ValueError(f"Compact integer segment does not terminate on node {i}")
        vcount = payload[start + size - 17]
        rows.append({"fields": compact, "vertex_count": vcount})
    return {
        "status": "analyzed_compact_role_hypotheses_only",
        "rooted_node_graph_and_zone_masks_prevalidated": True,
        "hypotheses_are_not_field_names": True,
        **analyze_rows(rows, include_nodes=include_nodes),
    }


def audit_map(path: Path, *, include_nodes: bool = False) -> dict:
    path = Path(path)
    world = zones.topology.boundaries.world
    if (path.suffix.casefold() != ".gmp" or not path.is_file() or
            path.stat().st_size > world.MAX_MAP_BYTES):
        raise ValueError("Expected existing user-owned retail DX2 GMP within size limit")
    pkg = world.Package(path)
    if pkg.version != 95 or pkg.licensee not in world.OBSERVED_LICENSEES:
        raise ValueError("Expected UE95 DX2 licensee 65/67/68/69")
    model_ref = world._parse_world_model(pkg)["world_model_export_ref"]
    model = pkg.exports[model_ref - 1]
    payload = pkg.payload(model)
    frame = zones.topology.boundaries.parse_world_model(payload, include_nodes=True)
    result = inspect_model(payload, frame, include_nodes=include_nodes)
    return {
        "file": path.name,
        "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
        "world_model_sha256": hashlib.sha256(payload).hexdigest(),
        "licensee": pkg.licensee,
        "world_model_export_ref": model_ref,
        **result,
    }


def audit_maps(paths, *, include_nodes: bool = False) -> dict:
    world = zones.topology.boundaries.world
    if not 1 <= len(paths) <= world.MAX_MAPS:
        raise ValueError("Provide between 1 and 64 user-owned GMPs")
    inputs = [Path(p).resolve() for p in paths]
    if len(set(inputs)) != len(inputs):
        raise ValueError("Duplicate GMP input paths")
    maps = [audit_map(p, include_nodes=include_nodes) for p in inputs]
    totals = Counter()
    for row in maps:
        totals["maps"] += 1
        totals["nodes"] += row["nodes"]
        totals["candidate_vertex_slots"] += row["candidate_slot_count"]
        totals["candidate_vertex_span_contiguous_adjacent_pairs"] += (
            row["candidate_vertex_spans"]["adjacent_exact_contiguous"])
        totals["candidate_vertex_span_adjacent_pairs"] += (
            row["candidate_vertex_spans"]["adjacent_pairs"])
        totals["candidate_vertex_span_overlap_slots"] += (
            row["candidate_vertex_spans"]["overlap_slot_count"])
        totals["maps_with_disjoint_candidate_vertex_spans"] += int(
            row["candidate_vertex_spans"]["all_nonnegative_spans_disjoint"]
            and row["candidate_vertex_spans"]["negative_starts"] == 0)
        totals["sorted_vertex_span_contiguous_neighbors"] += (
            row["candidate_vertex_spans"]["sorted_contiguous_neighbors"])
        totals["sorted_vertex_span_gapped_neighbors"] += (
            row["candidate_vertex_spans"]["sorted_gapped_neighbors"])
        totals["sorted_vertex_span_gap_slots"] += (
            row["candidate_vertex_spans"]["sorted_gap_slots"])
        for field in (1, 2, 6, 7):
            shape = row["index_shapes"][str(field)]
            totals[f"field{field}_nonnegative_occurrences"] += (
                shape["nonnegative_occurrences"])
            totals[f"field{field}_unique_nonnegative_maps"] += int(
                shape["unique_nonnegative"])
            totals[f"field{field}_dense_nonnegative_maps"] += int(
                shape["zero_based_dense"])
            totals[f"field{field}_unique_dense_nonnegative_maps"] += int(
                shape["zero_based_unique_dense"])
        totals["maps_dense_zero_based_candidate_vertex_pool"] += int(
            row["candidate_vertex_spans"]["dense_zero_based_no_overlaps"])
        totals["field5_coplanar_links"] += row["coplanar_candidate_surface"]["field5_links"]
        totals["field5_same_field2"] += row["coplanar_candidate_surface"]["same_field2"]
    return {
        "schema": SCHEMA, "read_only": True, "native_gmp_written": False,
        "actual_vertex_xyz_decoded": False, "surface_references_proven": False,
        "collision_or_render_bound_references_proven": False,
        "runtime_verified": False, "summary": dict(totals), "maps": maps,
        "hypotheses": {
            "field0": "candidate node flags (0/5 in earlier corpus)",
            "field1": "candidate first node vertex-pool index",
            "field2": "candidate node surface index",
            "field6": "candidate collision-bound index",
            "field7": "candidate render-bound index",
        },
        "limitations": [
            "Historical Unreal FBspNode member names are hypotheses, not direct DX2 symbols.",
            "Vertex spans are candidate index ranges only; no XYZ vertex pool has been located.",
            "Observed index uniqueness, zero-based density and gap patterns are not native field-name proofs.",
            "An original-map corpus may contain valid gaps in first-vertex ranges; never reject a map for gaps alone.",
            "Same field2 on field5 coplanar links is correlational, not proof of surface ownership.",
            "Fields6/7 are profiled numerically without treating them as BSP child links.",
            "No writer, rebuilt CSG, PVS, rendering or collision is claimed.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--include-nodes", action="store_true",
                        help="Include all raw compact fields; can make a large report")
    args = parser.parse_args(argv)
    try:
        report = audit_maps(args.maps, include_nodes=args.include_nodes)
        if args.report:
            zones.topology.boundaries.world.write_report(report,args.report,args.maps)
            print(json.dumps({"status":"ok","report":str(args.report),
                              "summary":report["summary"]},indent=2))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,KeyError,OverflowError,struct.error) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}),file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
