"""Source-pinned World Model plane vs original render-triangle edit sensitivity.

Geometric coplanarity and node-sphere containment are only candidate
associations. This module never writes BSP, render geometry, or collision.
"""
from __future__ import annotations

import hashlib
import struct

from .bsp_trace import _load_model
from .bsp_plane_impact import _plane
from inspect_world_bsp_node_boundaries import parse_world_model
from inspect_bsp_render_spatial_candidates import (
    analyze_spatial_candidates, _triangles_from_render_blocks,
)
from dx2scene import find_bsp

SCHEMA = "DX2SDK-original-BSP-render-plane-impact-v1"
MAX_EXAMPLES = 16


def _one_node_candidates(plane, sphere, triangles):
    result = analyze_spatial_candidates([(plane, sphere)], triangles,
                                        include_matches=True)
    return {
        tuple(row["triangle"]) for row in result["candidate_triangle_nodes"]
        if row["candidate_nodes"] == [0]
    }


def compare_plane_render_triangles(nodes, triangles, *, node, replacement):
    """Pure synthetic-testable comparison with bounded output examples."""
    if type(node) is not int or not 0 <= node < len(nodes):
        raise ValueError("Invalid source BSP node ordinal")
    old_plane, sphere = nodes[node]
    old = _plane(old_plane)
    new = _plane(replacement)
    if old == new:
        raise ValueError("No float32 plane change")
    if not isinstance(triangles, list) or len(triangles) > 1000000:
        raise ValueError("Render triangle inventory must be bounded")
    before = _one_node_candidates(old, sphere, triangles)
    after = _one_node_candidates(new, sphere, triangles)
    removed, added = sorted(before-after), sorted(after-before)
    return {
        "schema": SCHEMA,
        "status": "read-only-geometric-candidate-plane-impact",
        "node": node,
        "original_plane_float32": list(old),
        "hypothetical_plane_float32": list(new),
        "original_candidate_render_triangles": len(before),
        "hypothetical_candidate_render_triangles": len(after),
        "lost_candidate_render_triangles": len(removed),
        "gained_candidate_render_triangles": len(added),
        "lost_triangle_locator_examples": [list(x) for x in removed[:MAX_EXAMPLES]],
        "gained_triangle_locator_examples": [list(x) for x in added[:MAX_EXAMPLES]],
        "candidate_matching_is_engine_ownership": False,
        "render_triangle_vertices_changed": False,
        "native_bsp_writer_enabled": False,
        "collision_rebuilt": False,
        "retail_runtime_verified": False,
    }


def compare_original_plane_render_impact(world, *, node, replacement):
    """Compare original Model node against source Level render blocks."""
    world._check_original_unchanged()
    model = _load_model(world)
    pkg = world._package
    export = pkg.exports[model["world_model_export"]-1]
    payload = pkg.payload(export)
    if hashlib.sha256(payload).hexdigest() != model["world_model_sha256"]:
        raise ValueError("World Model source payload SHA mismatch")
    frame = parse_world_model(payload, include_nodes=True)
    if frame["candidate_node_count"] != model["node_count"]:
        raise ValueError("World Model node count mismatch")
    if type(node) is not int or not 0 <= node < model["node_count"]:
        raise ValueError("Invalid original Model node ordinal")
    record = frame["node_records"][node]
    offset, size = record["start"], record["length"]
    plane = struct.unpack_from("<4f", payload, offset)
    if plane != tuple(model["nodes"][node]["plane"]):
        raise ValueError("Independent Model plane evidence disagrees")
    sphere = struct.unpack_from("<4f", payload, offset+size-53)
    blocks = find_bsp(pkg)
    if not blocks:
        raise ValueError("No validated original Level render blocks")
    triangles = list(_triangles_from_render_blocks(blocks))
    report = compare_plane_render_triangles([(plane, sphere)], triangles,
                                            node=0, replacement=replacement)
    world._check_original_unchanged()
    return {
        **report,
        "node": node,
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "world_model_export": model["world_model_export"],
        "world_model_sha256": model["world_model_sha256"],
        "validated_render_blocks": len(blocks),
        "source_render_triangles": len(triangles),
        "limitations": [
            "Only candidate coplanarity plus node-sphere containment is compared.",
            "A changed plane may require changing render triangles and collision.",
            "No engine-authenticated node-to-triangle ownership or Havok rebuild.",
            "No GMP output or retail game runtime test.",
        ],
    }
