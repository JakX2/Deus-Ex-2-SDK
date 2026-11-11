"""In-memory BSP plane edit impact on source-authored Light candidate paths.

No native BSP writer, Region solver, collision cook or runtime verification.
"""
from __future__ import annotations
import math
import struct
from .bsp_trace import _load_model, _point, _trace, _epsilon

SCHEMA = "DX2SDK-original-BSP-plane-counterfactual-impact-v1"

def _plane(values):
    if not isinstance(values, (tuple, list)) or len(values) != 4 or any(type(x) not in (int, float) for x in values):
        raise ValueError("Four numeric plane coefficients required")
    if any(not math.isfinite(x) or abs(x) > 1_000_000 for x in values):
        raise ValueError("Plane coefficients must be finite")
    plane = struct.unpack("<4f", struct.pack("<4f", *values))
    if abs(sum(x*x for x in plane[:3]) - 1) >= 2e-4:
        raise ValueError("Source plane normal must be unit length")
    return plane

def _signature(trace):
    return sorted((t["parent_node"], t["missing_branch"],
                   tuple((step["node"], step["field"]) for step in t["plane_path"]))
                  for t in trace["candidate_missing_branch_terminals"])

def compare_plane_model(model, lights, *, node, replacement, epsilon=.01, limit=100):
    """Pure, bounded synthetic-testable sensitivity oracle."""
    if type(node) is not int or not 0 <= node < len(model["nodes"]):
        raise ValueError("Invalid original BSP node ordinal")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Sample limit outside 1..1000")
    if not isinstance(lights, list) or len(lights) > 1000:
        raise ValueError("Invalid bounded original Light inventory")
    eps = _epsilon(epsilon)
    old = _plane(model["nodes"][node]["plane"])
    new = _plane(replacement)
    if old == new:
        raise ValueError("No float32 plane change")
    original_bytes = struct.pack("<4f", *old)
    modified_bytes = struct.pack("<4f", *new)
    alt = {**model, "nodes": [dict(item) for item in model["nodes"]]}
    alt["nodes"][node]["plane"] = new
    rows = []
    seen = set()
    for light in lights[:limit]:
        export = light.get("export")
        if type(export) is not int or export < 1 or export in seen:
            raise ValueError("Duplicate/invalid original Light export")
        seen.add(export)
        point = _point(light["location_unreal"])
        before = _signature(_trace(model, point, eps))
        after = _signature(_trace(alt, point, eps))
        rows.append({
            "source_light_export": export,
            "original_region_leaf": light["region_leaf"],
            "original_region_zone": light["region_zone_number_low"],
            "candidate_path_changed": before != after,
            "before_candidate_paths": before,
            "after_candidate_paths": after,
            "region_recomputed": False,
        })
    return {
        "schema": SCHEMA,
        "status": "read-only-hypothetical-plane-impact",
        "node": node,
        "original_plane_float32": list(old),
        "hypothetical_plane_float32": list(new),
        "changed_plane_byte_offsets": [i for i in range(16) if original_bytes[i] != modified_bytes[i]],
        "epsilon": eps,
        "sampled_original_lights": len(rows),
        "changed_candidate_light_paths": sum(x["candidate_path_changed"] for x in rows),
        "original_light_paths": rows,
        "original_gmp_modified": False,
        "native_bsp_writer_enabled": False,
        "native_region_solver_verified": False,
        "collision_rebuild_verified": False,
        "gameplay_runtime_verified": False,
    }

def compare_original_plane_impact(world, *, node, replacement, epsilon=.01, limit=100):
    """Use unchanged original GMP and source-verified Model + Light inventory."""
    world._check_original_unchanged()
    model = _load_model(world)
    audit = world.audit_original_lights()
    if (audit.get("source_sha256") != world.source_sha256
            or audit.get("native_light_spawn_enabled") is not False
            or len(audit["lights"]) != audit["source_light_count"]):
        raise ValueError("Source Light evidence did not validate")
    result = compare_plane_model(model, audit["lights"], node=node,
                                 replacement=replacement, epsilon=epsilon, limit=limit)
    world._check_original_unchanged()
    return {
        **result, "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "world_model_export": model["world_model_export"],
        "world_model_sha256": model["world_model_sha256"],
        "limitations": [
            "Only an in-memory copy of one source-observed plane is changed.",
            "Candidate BSP plane-side links are hypotheses, not verified engine leaf IDs.",
            "Original Light Region fields remain observations and are not recalculated.",
            "No BSP/Havok/MOPP/zone or runtime output is produced.",
        ],
    }
