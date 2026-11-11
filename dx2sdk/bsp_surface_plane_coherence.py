"""Source-backed plane coherence tests for DX2 World BSP compact field 2.

This diagnostic asks whether nodes sharing the same raw third compact integer
also share an infinite geometric plane. It does NOT decode a native surface
table, prove a field name, reconstruct CSG, or write any game package.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import math
import struct

from dx2inspect import Cursor
from inspect_world_bsp_node_boundaries import parse_world_model
from .bsp_trace import _load_model

SCHEMA = "DX2SDK-original-BSP-compact-field2-plane-coherence-v1"
MAX_NODES = 20_000
MAX_EXAMPLES = 12
NORMAL_TOLERANCE = 0.002
PLANE_W_TOLERANCE = 0.15


def _plane_relation(a, b) -> str:
    """Equivalent infinite planes may have opposite float32 orientation."""
    def distance(s: int) -> float:
        return math.sqrt(sum((a[i] - s*b[i])**2 for i in range(3)))
    if distance(1) <= NORMAL_TOLERANCE and abs(a[3] - b[3]) <= PLANE_W_TOLERANCE:
        return "same_orientation"
    if distance(-1) <= NORMAL_TOLERANCE and abs(a[3] + b[3]) <= PLANE_W_TOLERANCE:
        return "opposite_orientation"
    return "different_plane"


def analyze_surface_plane_coherence(nodes: list[dict]) -> dict:
    """Pure linear-time analysis of original source-framed Model node records.

    Anchor comparisons are to the lowest-ordinal node of each reused
    field-2 value. They are NOT all pairwise comparisons or proof that
    an engine surface table exists.
    """
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
        raise ValueError("Expected 1..20000 original BSP node records")
    groups = defaultdict(list)
    sentinel_count = 0
    for index, row in enumerate(nodes):
        if not isinstance(row, dict):
            raise ValueError("Original BSP node is not a record")
        raw, link, offset, plane = (row.get("field2"), row.get("coplanar"),
                                    row.get("field2_offset_in_model"),
                                    row.get("plane"))
        if (type(raw) is not int or raw < -1
                or type(link) is not int or link < -1 or link >= len(nodes)
                or link == index
                or type(offset) is not int or offset < 0
                or not isinstance(plane, (list, tuple)) or len(plane) != 4
                or any(type(v) not in (float, int) or not math.isfinite(v)
                       or abs(v) > 1_000_000 for v in plane)
                or abs(sum(v*v for v in plane[:3]) - 1.) > 0.002):
            raise ValueError(f"Malformed original BSP field2/plane/coplanar row {index}")
        if raw == -1:
            sentinel_count += 1
        else:
            groups[raw].append(index)
    reused = [group for group in groups.values() if len(group) > 1]
    reused_nodes = sum(len(group) for group in reused)
    aligned, flipped, differing = 0, 0, 0
    all_coherent, any_differing = 0, 0
    conflicts = []
    for surface, group in sorted(groups.items()):
        if len(group) == 1:
            continue
        first_index = group[0]
        first = nodes[first_index]["plane"]
        mismatch = False
        for index in group[1:]:
            relation = _plane_relation(first, nodes[index]["plane"])
            aligned += int(relation == "same_orientation")
            flipped += int(relation == "opposite_orientation")
            differing += int(relation == "different_plane")
            if relation == "different_plane":
                mismatch = True
                if len(conflicts) < MAX_EXAMPLES:
                    conflicts.append({
                        "raw_field2_value": surface,
                        "anchor_node": first_index,
                        "conflicting_node": index,
                        "anchor_field2_offset_in_model":
                            nodes[first_index]["field2_offset_in_model"],
                        "conflicting_field2_offset_in_model":
                            nodes[index]["field2_offset_in_model"],
                        "plane_relation": relation,
                    })
        all_coherent += int(not mismatch)
        any_differing += int(mismatch)
    links = {"total": 0, "same_field2": 0, "different_field2": 0,
             "same_infinite_plane": 0, "different_infinite_plane": 0,
             "same_field2_different_plane": 0,
             "different_field2_same_plane": 0}
    link_conflicts = []
    for index, row in enumerate(nodes):
        target = row["coplanar"]
        if target < 0:
            continue
        other = nodes[target]
        same_number = row["field2"] == other["field2"]
        same_plane = _plane_relation(row["plane"], other["plane"]) != "different_plane"
        links["total"] += 1
        links["same_field2" if same_number else "different_field2"] += 1
        links["same_infinite_plane" if same_plane else "different_infinite_plane"] += 1
        links["same_field2_different_plane"] += int(same_number and not same_plane)
        links["different_field2_same_plane"] += int(not same_number and same_plane)
        if not same_plane and len(link_conflicts) < MAX_EXAMPLES:
            link_conflicts.append({
                "source_node": index, "coplanar_target": target,
                "source_raw_field2": row["field2"],
                "target_raw_field2": other["field2"],
                "source_field2_offset_in_model": row["field2_offset_in_model"],
                "target_field2_offset_in_model": other["field2_offset_in_model"],
            })
    if (aligned + flipped + differing != reused_nodes - len(reused)
            or all_coherent + any_differing != len(reused)
            or links["same_field2"] + links["different_field2"] != links["total"]
            or links["same_infinite_plane"] + links["different_infinite_plane"]
            != links["total"]):
        raise ValueError("Original BSP field2 plane-coherence counters disagree")
    return {
        "schema": SCHEMA,
        "status": "read-only-original-BSP-field2-plane-coherence-hypothesis",
        "source_node_count": len(nodes),
        "source_field2_minus_one_sentinels": sentinel_count,
        "source_distinct_nonnegative_field2_values": len(groups),
        "source_singleton_field2_groups": len(groups) - len(reused),
        "source_reused_field2_groups": len(reused),
        "source_nodes_in_reused_field2_groups": reused_nodes,
        "reused_field2_groups_plane_coherent_with_first_node": all_coherent,
        "reused_field2_groups_containing_different_planes": any_differing,
        "within_reused_field2_anchor_comparisons": {
            "same_orientation": aligned,
            "opposite_orientation": flipped,
            "different_plane": differing,
        },
        "candidate_coplanar_field5_link_evidence": links,
        "example_reused_field2_plane_disagreements": conflicts,
        "example_field5_link_plane_disagreements": link_conflicts,
        "normal_vector_tolerance": NORMAL_TOLERANCE,
        "plane_w_tolerance_source_units": PLANE_W_TOLERANCE,
        "comparisons_are_first_node_anchored_not_all_pairs": True,
        "source_field2_is_authenticated_surface_index": False,
        "native_BSP_or_collision_writer_enabled": False,
        "retail_runtime_verified": False,
    }


def inspect_original_surface_plane_coherence(world) -> dict:
    """Read original GMP bytes with strict World Model and rooted-zone gates."""
    world._check_original_unchanged()
    model = _load_model(world)
    pkg = world._package
    if hashlib.sha256(pkg.data).hexdigest() != world.source_sha256:
        raise ValueError("Original GMP bytes differ from opened source SHA-256")
    export = model["world_model_export"]
    if (type(export) is not int or not 1 <= export <= len(pkg.exports)
            or pkg.class_name(pkg.exports[export-1]) != "Model"):
        raise ValueError("Original Level World Model reference changed")
    exp = pkg.exports[export-1]
    offset, size = exp["offset"], exp["size"]
    if (type(offset) is not int or type(size) is not int
            or offset < 0 or size < 100 or size > len(pkg.data)-offset):
        raise ValueError("Original Model export bytes exceed GMP")
    payload = pkg.payload(exp)
    if (payload != pkg.data[offset:offset+size]
            or hashlib.sha256(payload).hexdigest() != model["world_model_sha256"]):
        raise ValueError("Independent original Model payload differs from GMP")
    frame = parse_world_model(payload, include_nodes=True)
    if frame["candidate_node_count"] != model["node_count"]:
        raise ValueError("Original Model BSP record counts disagree")
    rows = []
    for index, record in enumerate(frame["node_records"]):
        start, size = record["start"], record["length"]
        cursor = Cursor(payload, start+48, start+size-53)
        values, positions = [], []
        for _ in range(8):
            positions.append(cursor.at)
            values.append(cursor.ci())
        if cursor.at != start+size-53:
            raise ValueError("Original Model compact field boundary shifted")
        plane = struct.unpack_from("<4f", payload, start)
        if tuple(model["nodes"][index]["plane"]) != plane:
            raise ValueError("Original source Model plane differs between validators")
        rows.append({"field2": values[2],
                     "coplanar": values[5],
                     "field2_offset_in_model": positions[2],
                     "plane": plane})
    result = analyze_surface_plane_coherence(rows)
    world._check_original_unchanged()
    return {
        **result,
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "original_world_model_export": export,
        "original_world_model_sha256": model["world_model_sha256"],
        "original_world_model_offset_in_gmp": offset,
        "original_world_model_bytes": size,
        "original_source_modified": False,
        "limitations": [
            "Raw World BSP compact field 2 is NOT proven to index a native surface table.",
            "First-node plane coherence or contradiction is a falsifiable numeric hypothesis, not engine semantics.",
            "Field-5 coplanar pointer links come from source-validated BSP tree observations.",
            "No decoded BSP surface array or Model vertex XYZ pool, collision compiler, GMP mutation or retail test.",
        ],
    }
