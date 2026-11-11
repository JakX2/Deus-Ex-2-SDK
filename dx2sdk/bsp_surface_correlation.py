"""DX2 native BSP compact field-2 vs Level render/MOPP source provenance.

Only exact original serialized identities and *candidate* geometric matches.
Field 2 is NOT promoted to a decoded native iSurf or geometry ownership link.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import struct

from dx2inspect import Cursor
from dx2scene import find_bsp
from inspect_world_bsp_node_boundaries import parse_world_model
from inspect_bsp_render_spatial_candidates import (
    analyze_spatial_candidates, _triangles_from_render_blocks,
)
from .bsp_trace import _load_model
from .bsp_mopp_plane_impact import _source_triangle_rows

SCHEMA = "DX2SDK-BSP-compact-field2-versus-Level-provenance-correlation-v1"
MAX_EXAMPLES = 12
MAX_TRIANGLES = 1000000
MAX_NODES = 20000


def correlate_surface_candidates(nodes: list[dict], triangles: list,
                                 provenance_rows: list[dict]) -> dict:
    """Pure evidence counter; source parsers separately validate serialized data.

    Only triangles associated to exactly ONE BSP plane+sphere candidate
    contribute field2↔Level provenance equality statistics. Ambiguous and
    unmatched triangles stay explicitly unclassified.
    """
    if (not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES
            or not isinstance(triangles, list)
            or not isinstance(provenance_rows, list)
            or not 1 <= len(triangles) <= MAX_TRIANGLES
            or len(triangles) != len(provenance_rows)):
        raise ValueError("BSP nodes and Level triangle inventories are missing or out of range")
    for i, node in enumerate(nodes):
        if (not isinstance(node, dict) or type(node.get("field2")) is not int
                or node["field2"] < -1
                or type(node.get("field2_offset_in_model")) is not int
                or node["field2_offset_in_model"] < 0):
            raise ValueError(f"BSP node {i} has no verified compact-field-2 source position")
    locators = set()
    for i, ((locator, _), row) in enumerate(zip(triangles, provenance_rows)):
        if (not isinstance(locator, (tuple, list)) or len(locator) != 3
                or any(type(x) is not int or x < 0 for x in locator)
                or not isinstance(row, dict)
                or row.get("render_locator") != list(locator)
                or row.get("flattened_triangle_id") != i
                or type(row.get("source_provenance_block_field_a")) is not int
                or type(row.get("source_provenance_section_field_b")) is not int
                or row["source_provenance_section_field_b"] != locator[1]
                or type(row.get("original_mopp_terminal_leaf_present")) is not bool):
            raise ValueError(f"Level render/provenance triangle order disagrees at {i}")
        key = tuple(locator)
        if key in locators:
            raise ValueError("Duplicate source Level render locator")
        locators.add(key)
    candidates = analyze_spatial_candidates(
        [(node["plane"], node["sphere"]) for node in nodes],
        triangles, include_matches=True)
    observed = candidates["candidate_triangle_nodes"]
    by_loc = {}
    for item in observed:
        key = tuple(item["triangle"])
        if key not in locators or key in by_loc:
            raise ValueError("Original Model geometry candidate returned an invalid locator")
        ids = item["candidate_nodes"]
        if (not isinstance(ids, list) or len(ids) != len(set(ids))
                or any(type(x) is not int or not 0 <= x < len(nodes) for x in ids)):
            raise ValueError("Malformed candidate BSP node indexes")
        by_loc[key] = ids
    # The geometric candidate decoder does not output exactly zero-area
    # triangles: source MOPP has separately verified that exception.
    if len(observed) + candidates["counts"].get("degenerate_triangles", 0) != len(triangles):
        raise ValueError("Model candidate inventory does not account for all original triangles")
    equal = {"field2_equals_level_provenance_A": 0,
             "field2_equals_render_block_ordinal": 0,
             "field2_equals_render_section_ordinal": 0,
             "field2_equals_flat_triangle_ordinal": 0}
    groups = defaultdict(lambda: {"provenance_A": set(), "render_blocks": set(),
                                  "render_sections": set(), "flat_triangles": 0})
    examples, ambiguous, unmatched, unique, unique_leaf = [], 0, 0, 0, 0
    for (locator, _), row in zip(triangles, provenance_rows):
        ids = by_loc.get(tuple(locator), [])
        if len(ids) != 1:
            ambiguous += int(len(ids) > 1)
            unmatched += int(not ids)
            continue
        node_index = ids[0]
        source = nodes[node_index]
        field2 = source["field2"]
        a = row["source_provenance_block_field_a"]
        global_id = row["flattened_triangle_id"]
        unique += 1
        unique_leaf += int(row["original_mopp_terminal_leaf_present"])
        equal["field2_equals_level_provenance_A"] += int(field2 == a)
        equal["field2_equals_render_block_ordinal"] += int(field2 == locator[0])
        equal["field2_equals_render_section_ordinal"] += int(field2 == locator[1])
        equal["field2_equals_flat_triangle_ordinal"] += int(field2 == global_id)
        g = groups[field2]
        g["provenance_A"].add(a)
        g["render_blocks"].add(locator[0])
        g["render_sections"].add((locator[0], locator[1]))
        g["flat_triangles"] += 1
        if len(examples) < MAX_EXAMPLES:
            examples.append({
                "original_node_ordinal": node_index,
                "node_compact_field2_raw": field2,
                "node_compact_field2_offset_in_model": source["field2_offset_in_model"],
                "original_flat_triangle_id": global_id,
                "original_render_locator": list(locator),
                "original_level_provenance_A": a,
                "original_level_provenance_B": row["source_provenance_section_field_b"],
                "original_mopp_terminal_present": row["original_mopp_terminal_leaf_present"],
                "field2_equals_provenance_A": field2 == a,
            })
    if unique + ambiguous + unmatched != len(triangles):
        raise ValueError("BSP candidate classifications do not partition source triangles")
    return {
        "schema": SCHEMA,
        "status": "read-only-cross-domain-field2-numeric-hypotheses",
        "original_bsp_node_count": len(nodes),
        "original_flat_triangle_count": len(triangles),
        "unique_geometric_node_candidates": unique,
        "ambiguous_geometric_node_candidates": ambiguous,
        "unmatched_or_degenerate_render_triangles": unmatched,
        "original_mopp_leaves_among_unique_candidates": unique_leaf,
        "numeric_equality_only": equal,
        "candidate_field2_groups_with_matched_triangles": len(groups),
        "candidate_field2_groups_single_provenance_A": sum(
            len(g["provenance_A"]) == 1 for g in groups.values()),
        "candidate_field2_groups_multiple_provenance_A": sum(
            len(g["provenance_A"]) > 1 for g in groups.values()),
        "candidate_field2_groups_multiple_render_blocks": sum(
            len(g["render_blocks"]) > 1 for g in groups.values()),
        "candidate_field2_groups_multiple_render_sections": sum(
            len(g["render_sections"]) > 1 for g in groups.values()),
        "example_unique_candidate_pairs": examples,
        "field2_is_engine_authenticated_surface_index": False,
        "geometric_candidate_is_native_node_triangle_ownership": False,
        "native_BSP_or_collision_writer_enabled": False,
        "retail_runtime_verified": False,
    }


def inspect_original_bsp_surface_correlation(world) -> dict:
    """Use independently validated original Model and Level serialization."""
    world._check_original_unchanged()
    model = _load_model(world)
    pkg = world._package
    if hashlib.sha256(pkg.data).hexdigest() != world.source_sha256:
        raise ValueError("Original source GMP SHA-256 differs from mapped package")
    exp = pkg.exports[model["world_model_export"] - 1]
    offset, size = exp["offset"], exp["size"]
    if (type(offset) is not int or type(size) is not int
            or offset < 0 or size < 100 or offset + size > len(pkg.data)):
        raise ValueError("Original Model source export has invalid byte bounds")
    payload = pkg.payload(exp)
    if (payload != pkg.data[offset:offset+size]
            or hashlib.sha256(payload).hexdigest() != model["world_model_sha256"]):
        raise ValueError("Original native Model export byte identity disagrees")
    frame = parse_world_model(payload, include_nodes=True)
    if frame["candidate_node_count"] != model["node_count"]:
        raise ValueError("Original Model node inventory disagrees with independent audit")
    nodes = []
    for ordinal, record in enumerate(frame["node_records"]):
        start, size = record["start"], record["length"]
        cursor = Cursor(payload, start+48, start+size-53)
        values, positions = [], []
        for _ in range(8):
            positions.append(cursor.at)
            values.append(cursor.ci())
        if cursor.at != start+size-53:
            raise ValueError("Original BSP node compact field segment shifted")
        plane = struct.unpack_from("<4f", payload, start)
        sphere = struct.unpack_from("<4f", payload, start+size-53)
        if plane != tuple(model["nodes"][ordinal]["plane"]):
            raise ValueError("Original Model plane evidence changed between validators")
        nodes.append({
            "field2": values[2], "field2_offset_in_model": positions[2],
            "plane": plane, "sphere": sphere,
        })
    levels = [(i, exp) for i, exp in enumerate(pkg.exports, start=1)
              if pkg.class_name(exp) == "Level" and exp["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected one original nonempty Level export")
    level_export, level_record = levels[0]
    level = pkg.payload(level_record)
    blocks = find_bsp(pkg)
    if not blocks:
        raise ValueError("No original validated Level render blocks")
    triangles = list(_triangles_from_render_blocks(blocks))
    rows, provenance = _source_triangle_rows(level, blocks)
    report = correlate_surface_candidates(nodes, triangles, rows)
    if report["original_mopp_leaves_among_unique_candidates"] > provenance[
            "mopp_leaves_with_render_section_attribution"]:
        raise ValueError("Original MOPP terminal count exceeds Level source")
    world._check_original_unchanged()
    return {
        **report,
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "source_model_export": model["world_model_export"],
        "source_model_sha256": model["world_model_sha256"],
        "source_model_absolute_offset": offset,
        "source_level_export": level_export,
        "source_level_sha256": hashlib.sha256(level).hexdigest(),
        "validated_render_blocks": len(blocks),
        "model_compact_field2_byte_positions_source_checked": True,
        "original_gmp_modified": False,
        "limitations": [
            "Field 2 is a raw compact integer: a numeric coincidence with Level fields is not an engine pointer.",
            "Only unique geometric plane+sphere node candidates enter equality counts; ambiguous nodes remain separate.",
            "BSP Model and Level triangle indexes may be unrelated numeric domains; mismatches do not imply corruption.",
            "No authenticated world BSP surface array or Model vertex XYZ pool has been found.",
            "No BSP/CSG rebuild, collision cooking, source GMP edits or retail DX2 runtime validation.",
        ],
    }
