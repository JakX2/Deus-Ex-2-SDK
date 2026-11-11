"""Source-pinned BSP plane edit preflight: exact bytes plus actor impact.

This deliberately does NOT authorize a native BSP writer. A changed plane
can invalidate collision, zones, visibility and actor Region state.
"""
from __future__ import annotations

from .bsp_plane_bytes import inspect_original_plane_bytes
from .bsp_plane_impact import compare_original_plane_impact

SCHEMA = "DX2SDK-original-BSP-plane-edit-preflight-v1"


def _join(plane: dict, impact: dict) -> dict:
    """Fail closed if independent original-source observations disagree."""
    if (plane.get("source_package_sha256") != impact.get("source_sha256")
            or plane.get("source_model_sha256") != impact.get("world_model_sha256")
            or plane.get("original_world_model_export") != impact.get("world_model_export")
            or plane.get("original_node_ordinal") != impact.get("node")
            or plane.get("original_plane_float32") != impact.get("original_plane_float32")
            or plane.get("hypothetical_plane_float32") != impact.get("hypothetical_plane_float32")
            or plane.get("original_bytes_unchanged") is not True
            or plane.get("native_writer_enabled") is not False
            or impact.get("native_bsp_writer_enabled") is not False
            or impact.get("original_gmp_modified") is not False):
        raise ValueError("Independent source byte and actor impact evidence disagree")
    return {
        "schema": SCHEMA,
        "status": "read-only-original-BSP-plane-preflight",
        "source_sha256": plane["source_package_sha256"],
        "world_model_sha256": plane["source_model_sha256"],
        "world_model_export": plane["original_world_model_export"],
        "node": plane["original_node_ordinal"],
        "absolute_plane_byte_offset": plane["original_plane_absolute_offset"],
        "original_plane_sha256": plane["original_plane_sha256"],
        "hypothetical_plane_sha256": plane["hypothetical_plane_sha256"],
        "changed_byte_offsets_relative_to_plane": plane["changed_byte_offsets_relative_to_plane"],
        "original_plane_float32": plane["original_plane_float32"],
        "hypothetical_plane_float32": plane["hypothetical_plane_float32"],
        "sampled_original_lights": impact["sampled_original_lights"],
        "changed_candidate_light_paths": impact["changed_candidate_light_paths"],
        "original_light_paths": impact["original_light_paths"],
        "native_write_authorized": False,
        "collision_rebuild_verified": False,
        "region_recomputation_verified": False,
        "retail_runtime_verified": False,
        "original_gmp_modified": False,
        "limitations": [
            "This is a source-pinned counterfactual, not an engine-valid BSP edit.",
            "Candidate plane paths are not proven native Region leaf assignments.",
            "No BSP topology, visibility, collision or Havok/MOPP rebuild.",
            "No native package output, original retail mutation or runtime test.",
        ],
    }


def preflight_original_bsp_plane(world, *, node, replacement,
                                 epsilon=.01, limit=100):
    """Recheck original GMP before and after two independent read-only audits."""
    world._check_original_unchanged()
    plane = inspect_original_plane_bytes(world, node=node, replacement=replacement)
    impact = compare_original_plane_impact(world, node=node,
                                            replacement=replacement,
                                            epsilon=epsilon, limit=limit)
    report = _join(plane, impact)
    world._check_original_unchanged()
    return report
