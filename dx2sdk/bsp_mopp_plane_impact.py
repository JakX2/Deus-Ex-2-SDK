"""DX2Ed v0.72: source BSP plane candidate ↔ Level/MOPP triangle ID crosswalk.

A geometric BSP node ↔ render triangle *candidate* is not an engine-authenticated
ownership reference. The MOPP triangle ID ↔ Level flattened triangle ordinal ↔
Flesh render section provenance, by contrast, is source-observed and independently
validated. This module joins them without modifying BSP, Level, or MOPP bytes.
"""
from __future__ import annotations

import hashlib
import struct

from .bsp_render_plane_impact import (
    _one_node_candidates, compare_plane_render_triangles,
    compare_original_plane_render_impact,
)
from .bsp_plane_impact import _plane
from inspect_bsp_render_spatial_candidates import _triangles_from_render_blocks
from inspect_level_mopp_triangle_provenance import inspect_triangle_provenance
import inspect_level_mopp_triangle_tree as mopp
from inspect_world_bsp_node_boundaries import parse_world_model
from dx2scene import find_bsp

SCHEMA = "DX2SDK-original-BSP-render-MOPP-triangle-provenance-v1"
MAX_EXAMPLES = 16


def _source_triangle_rows(level: bytes, blocks: list[dict]) -> tuple[list[dict], dict]:
    """Recover exact flat ID, source provenance pair and MOPP terminal membership.

    The existing independent PR27/28/29 parsers must accept the *whole*
    Level, not just the few candidate triangles being inspected.
    """
    provenance = inspect_triangle_provenance(level, blocks)
    link = mopp.inspect_mopp_link(level, blocks)
    count = provenance["triangle_provenance_record_count"]
    if (count != link["flat_triangles_prevalidated"]
            or provenance["mopp_leaves_with_render_section_attribution"]
            != link["unique_valid_mopp_triangle_leaves"]):
        raise ValueError("Original Level triangle provenance/MOPP counts disagree")
    code = level[link["mopp_code_start_in_level"]:link["mopp_code_end_in_level"]]
    leaves = set(mopp.trace_mopp_code(code, count)["reachable_terminal_triangle_ids"])
    if len(leaves) != link["unique_valid_mopp_triangle_leaves"]:
        raise ValueError("Original MOPP leaf set disagrees with validated Level")
    rows = []
    table = provenance["triangle_provenance_start_in_level"]
    for block_index, block in enumerate(blocks):
        for section_index, section in enumerate(block["sections"]):
            for triangle_index in range(len(section["indices"]) // 3):
                ordinal = len(rows)
                if ordinal >= count:
                    raise ValueError("Source render sections exceed validated flat triangles")
                offset = table + 8 * ordinal
                a, b = struct.unpack_from("<II", level, offset)
                if b != section_index:
                    raise ValueError("Source Level provenance section mismatch")
                rows.append({
                    "render_locator": [block_index, section_index, triangle_index],
                    "flattened_triangle_id": ordinal,
                    "source_provenance_block_field_a": a,
                    "source_provenance_section_field_b": b,
                    "provenance_pair_offset_in_level": offset,
                    "original_mopp_terminal_leaf_present": ordinal in leaves,
                })
    if (len(rows) != count
            or sum(r["original_mopp_terminal_leaf_present"] for r in rows) != len(leaves)
            or count - len(leaves) != provenance["non_mopp_leaf_triangle_count"]):
        raise ValueError("Original render/flat/MOPP triangle indexing is inconsistent")
    return rows, provenance


def compare_render_collision_candidates(
    nodes: list, triangles: list, level: bytes, blocks: list[dict],
    *, node: int, replacement, max_examples: int = MAX_EXAMPLES,
) -> dict:
    """Pure source-format crosswalk; synthetic fixtures need no original GMP.

    triangles must be in exact render block/section/triangle order, as emitted
    by _triangles_from_render_blocks for a real source package.
    """
    if type(max_examples) is not int or not 1 <= max_examples <= 32:
        raise ValueError("Sample cap must be 1..32")
    rows, provenance = _source_triangle_rows(level, blocks)
    if not isinstance(triangles, list) or len(triangles) != len(rows):
        raise ValueError("Original render triangle inventory differs from Level flat count")
    for (locator, _xyz), row in zip(triangles, rows):
        if (not isinstance(locator, (list, tuple))
                or tuple(locator) != tuple(row["render_locator"])):
            raise ValueError("Render locator order disagrees with original Level flattened IDs")
    base = compare_plane_render_triangles(
        nodes, triangles, node=node, replacement=replacement)
    original_plane, sphere = nodes[node]
    before = _one_node_candidates(_plane(original_plane), sphere, triangles)
    after = _one_node_candidates(_plane(replacement), sphere, triangles)
    lost, gained = before - after, after - before
    if (len(before) != base["original_candidate_render_triangles"]
            or len(after) != base["hypothetical_candidate_render_triangles"]
            or len(lost) != base["lost_candidate_render_triangles"]
            or len(gained) != base["gained_candidate_render_triangles"]):
        raise ValueError("BSP render candidate counts disagree with independent analysis")
    by_locator = {tuple(row["render_locator"]): row for row in rows}
    if len(by_locator) != len(rows) or not lost.union(gained) <= by_locator.keys():
        raise ValueError("Candidate render locator has no exact Level provenance")
    def samples(candidates: set) -> list[dict]:
        return [dict(by_locator[loc]) for loc in sorted(candidates)[:max_examples]]
    lost_leaf = sum(by_locator[loc]["original_mopp_terminal_leaf_present"] for loc in lost)
    gained_leaf = sum(by_locator[loc]["original_mopp_terminal_leaf_present"] for loc in gained)
    return {
        **base,
        "schema": SCHEMA,
        "status": "read-only-BSP-candidate-to-original-MOPP-leaf-crosswalk",
        "source_render_triangle_count": len(rows),
        "source_provenance_record_count": provenance["triangle_provenance_record_count"],
        "source_provenance_start_in_level": provenance["triangle_provenance_start_in_level"],
        "source_mopp_terminal_leaf_count": provenance["mopp_leaves_with_render_section_attribution"],
        "source_non_mopp_degenerate_triangle_count": provenance["non_mopp_leaf_triangle_count"],
        "lost_candidate_original_mopp_leaf_count": lost_leaf,
        "gained_candidate_original_mopp_leaf_count": gained_leaf,
        "lost_candidate_nonleaf_count": len(lost) - lost_leaf,
        "gained_candidate_nonleaf_count": len(gained) - gained_leaf,
        "lost_candidate_mopp_id_examples": samples(lost),
        "gained_candidate_mopp_id_examples": samples(gained),
        "mopp_leaf_id_is_original_flat_triangle_ordinal": True,
        "candidate_matching_is_engine_ownership": False,
        "original_mopp_bytecode_modified": False,
        "original_render_vertices_modified": False,
        "native_collision_writer_enabled": False,
        "native_bsp_writer_enabled": False,
        "retail_runtime_verified": False,
    }


def compare_original_plane_mopp_impact(world, *, node: int, replacement) -> dict:
    """Reconstruct a source-pinned crosswalk from an unchanged original GMP."""
    world._check_original_unchanged()
    render = compare_original_plane_render_impact(
        world, node=node, replacement=replacement)
    if (render.get("source_sha256") != world.source_sha256
            or render.get("node") != node
            or render.get("native_bsp_writer_enabled") is not False
            or render.get("collision_rebuilt") is not False
            or render.get("retail_runtime_verified") is not False):
        raise ValueError("Original BSP render impact source or safety flags disagree")
    pkg = world._package
    model_export = render["world_model_export"]
    model_payload = pkg.payload(pkg.exports[model_export - 1])
    if hashlib.sha256(model_payload).hexdigest() != render["world_model_sha256"]:
        raise ValueError("Source Model payload changed after render impact audit")
    frame = parse_world_model(model_payload, include_nodes=True)
    if type(node) is not int or not 0 <= node < frame["candidate_node_count"]:
        raise ValueError("Original Model node index out of range")
    record = frame["node_records"][node]
    start, size = record["start"], record["length"]
    plane = struct.unpack_from("<4f", model_payload, start)
    sphere = struct.unpack_from("<4f", model_payload, start + size - 53)
    if list(plane) != render["original_plane_float32"]:
        raise ValueError("Independent original Model plane values disagree")
    levels = [(i, exp) for i, exp in enumerate(pkg.exports, start=1)
              if pkg.class_name(exp) == "Level" and exp["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected exactly one original nonempty Level export")
    level_export, level_record = levels[0]
    level_payload = pkg.payload(level_record)
    blocks = find_bsp(pkg)
    if len(blocks) != render["validated_render_blocks"]:
        raise ValueError("Original render block count changed during source audit")
    triangles = list(_triangles_from_render_blocks(blocks))
    if len(triangles) != render["source_render_triangles"]:
        raise ValueError("Original render triangle inventory changed during source audit")
    result = compare_render_collision_candidates(
        [(plane, sphere)], triangles, level_payload, blocks,
        node=0, replacement=replacement)
    for field in (
        "original_candidate_render_triangles", "hypothetical_candidate_render_triangles",
        "lost_candidate_render_triangles", "gained_candidate_render_triangles",
    ):
        if result[field] != render[field]:
            raise ValueError("Original render and MOPP candidate impact counts disagree")
    if result["original_plane_float32"] != render["original_plane_float32"]:
        raise ValueError("Original Model plane evidence disagrees with MOPP crosswalk")
    world._check_original_unchanged()
    return {
        **result,
        "node": node,
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "world_model_export": model_export,
        "world_model_sha256": render["world_model_sha256"],
        "source_level_export": level_export,
        "source_level_sha256": hashlib.sha256(level_payload).hexdigest(),
        "source_render_blocks": len(blocks),
        "limitations": [
            "Source MOPP terminal IDs correspond to validated Level flattened triangle ordinals.",
            "Plane-to-render candidate association remains geometric, not an engine node ownership field.",
            "A changed candidate does not mean actual Havok collision or runtime contact changed.",
            "MOPP bytecode, BSP planes, source render vertices and original GMP remain unchanged.",
            "No BSP/CSG rebuild, Havok/MOPP compiler, Region solver or retail runtime test.",
        ],
    }
