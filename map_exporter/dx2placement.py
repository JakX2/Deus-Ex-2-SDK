"""Read-only DX2 actor placement diagnostics, grounded in map and IBD bounds.

Coordinates here are original Unreal mesh-local units, NOT game-world values.
No orientation correction is assumed or automatically written.
"""
from __future__ import annotations
import math

SCALE = 0.01905
MAX_EXAMPLES = 80


def _bounds(raw):
    if not isinstance(raw, (list, tuple)) or len(raw) != 6:
        return None
    if any(type(x) not in (float, int) or not math.isfinite(x) for x in raw):
        return None
    low, high = tuple(float(x) for x in raw[:3]), tuple(float(x) for x in raw[3:])
    if any(a > b for a, b in zip(low, high)):
        return None
    return low, high


def _center(bounds):
    low, high = bounds
    return tuple((a + b) / 2.0 for a, b in zip(low, high))


def _extent(bounds):
    low, high = bounds
    return tuple(b - a for a, b in zip(low, high))


def _distance(values):
    return math.sqrt(sum(float(x) ** 2 for x in values))


def _delta(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _observed_bounds(mesh):
    pts = getattr(mesh, "positions", [])
    if not pts or len(pts) > 250000:
        return None
    if any(len(p) != 3 or any(not math.isfinite(v) for v in p) for p in pts):
        return None
    return (
        tuple(min(pt[axis] for pt in pts) for axis in range(3)),
        tuple(max(pt[axis] for pt in pts) for axis in range(3)),
    )


def analyze_mesh_placement(actor, mesh, source_bundle):
    """Compare three independent source representations of the same mesh.

    GMP: bounds of map's referenced StaticMesh resource.
    IBD: bound box in original mesh render payload.
    Polygons: measured vertex coordinates used by our exporter.
    """
    source_bounds = None
    meta = actor.get("mesh")
    if isinstance(meta, dict):
        vals = meta.get("bounds")
        if isinstance(vals, (list, tuple)) and len(vals) == 2 and all(
                isinstance(a, (list, tuple)) and len(a) == 3 for a in vals):
            source_bounds = _bounds([*vals[0], *vals[1]])
    declared = _bounds(getattr(mesh, "bounds", None))
    observed = _observed_bounds(mesh)
    if observed is None:
        return {"status": "invalid_mesh_vertices", "actor": actor.get("name"),
                "mesh": mesh.name, "source_bundle": source_bundle}
    size = _extent(observed)
    center = _center(observed)
    # The pivot is at (0,0,0) in original mesh-local space.
    pivot_distance = _distance(center) * SCALE
    candidate = {
        "actor": actor.get("name"), "export": actor.get("export"),
        "mesh": mesh.name, "source_bundle": source_bundle,
        "source_position_ue": [actor.get("x"), actor.get("y"), actor.get("z")],
        "source_rotation_pyr": actor.get("rotation"),
        "mesh_local_center_ue": list(center),
        "mesh_local_size_ue": list(size),
        "mesh_pivot_to_center_m": round(pivot_distance, 5),
        "gmp_mesh_bounds_ue": [list(source_bounds[0]), list(source_bounds[1])] if source_bounds else None,
        "ibd_declared_bounds_ue": [list(declared[0]), list(declared[1])] if declared else None,
        "observed_vertex_bounds_ue": [list(observed[0]), list(observed[1])],
        "warnings": [],
        "status": "observed",
    }
    for label, bounds in (("GMP", source_bounds), ("IBD", declared)):
        if bounds is None:
            candidate["warnings"].append(label.lower() + "_bounds_unavailable")
            continue
        difference = max(abs(a - b) for group_a, group_b in zip(bounds, observed)
                         for a, b in zip(group_a, group_b))
        tolerance = max(2.0, max(size) * 0.015)
        candidate[label.lower() + "_vertex_bounds_max_delta_ue"] = round(difference, 5)
        if difference > tolerance:
            candidate["warnings"].append(label.lower() + "_vertex_bounds_disagree")
    largest_extent = max(size)
    if largest_extent > 0.1 and _distance(center) > largest_extent * 1.5:
        candidate["warnings"].append("large_mesh_local_pivot_offset")
    rotation = actor.get("rotation") or [0, 0, 0]
    if len(rotation) == 3 and any(abs(float(v)) > 0.001 for v in rotation):
        candidate["raw_rotator_nonzero"] = True
    else:
        candidate["raw_rotator_nonzero"] = False
    # Do not classify an offset pivot as wrong; may be intentional.
    candidate["needs_review"] = bool(candidate["warnings"])
    return candidate


def add_world_transform_evidence(diagnostic, actor_matrix):
    """Project observed local mesh bounds into the *current export convention*.

    The output is useful for comparing real world coordinates, but does NOT
    prove the Unreal rotator convention matches Invisible War's runtime.
    Matrices are column-major glTF float arrays, with the UE Y/Z swap already
    applied to each vertex by the existing mesh exporter.
    """
    if diagnostic.get("status") != "observed":
        return diagnostic
    if not isinstance(actor_matrix, (list, tuple)) or len(actor_matrix) != 16:
        raise ValueError("Expected one 4x4 glTF column-major actor matrix")
    if any(type(n) not in (float, int) or not math.isfinite(n) for n in actor_matrix):
        raise ValueError("Actor matrix has nonfinite values")
    raw = diagnostic["observed_vertex_bounds_ue"]
    bounds = _bounds([*raw[0], *raw[1]])
    if bounds is None:
        raise ValueError("Observed source bounds are invalid")
    low, high = bounds
    def world(point):
        # UE (X,Y,Z) -> glTF (X,Z,Y) scaled to metres.
        x, y, z = point[0] * SCALE, point[2] * SCALE, point[1] * SCALE
        return [
            actor_matrix[0]*x + actor_matrix[4]*y + actor_matrix[8]*z + actor_matrix[12],
            actor_matrix[1]*x + actor_matrix[5]*y + actor_matrix[9]*z + actor_matrix[13],
            actor_matrix[2]*x + actor_matrix[6]*y + actor_matrix[10]*z + actor_matrix[14],
        ]
    corners = [world((x, y, z)) for x in (low[0], high[0])
               for y in (low[1], high[1]) for z in (low[2], high[2])]
    lower = [min(p[axis] for p in corners) for axis in range(3)]
    upper = [max(p[axis] for p in corners) for axis in range(3)]
    center = world(_center(bounds))
    extents = _extent(bounds)
    ordered = sorted(range(3), key=lambda axis: extents[axis], reverse=True)
    long_axis = ordered[0]
    end_lo = list(_center(bounds))
    end_hi = list(end_lo)
    end_lo[long_axis] = low[long_axis]
    end_hi[long_axis] = high[long_axis]
    symmetric_sides = (
        extents[long_axis] > 2.0 * max(extents[ordered[1]], 0.00001)
        and abs(extents[ordered[1]] - extents[ordered[2]])
            <= 0.01 * max(extents[ordered[1]], extents[ordered[2]], 1.0)
    )
    diagnostic.update({
        "preview_transform_basis_convention": "P * Rz(Yaw) * Ry(-Pitch) * Rx(Roll) * P",
        "preview_actor_origin_godot_m": list(actor_matrix[12:15]),
        "preview_mesh_center_godot_m": center,
        "preview_world_aabb_min_m": lower,
        "preview_world_aabb_max_m": upper,
        "mesh_major_local_axis_ue": "XYZ"[long_axis],
        "preview_major_axis_endpoints_godot_m": [world(end_lo), world(end_hi)],
        "major_axis_cross_section_nearly_square": symmetric_sides,
        "roll_direction_aabb_ambiguous": symmetric_sides and long_axis == 0,
        "preview_orientation_game_verified": False,
    })
    return diagnostic


def summarize_placement(entries):
    valid = [item for item in entries if item.get("status") == "observed"]
    counts = {}
    for item in valid:
        for flag in item["warnings"]:
            counts[flag] = counts.get(flag, 0) + 1
    # Don't rank by absolute object size; favor source mismatches first.
    by_mismatch = sorted((x for x in valid if x["needs_review"]),
                         key=lambda x: (
                             int("gmp_vertex_bounds_disagree" in x["warnings"]) +
                             int("ibd_vertex_bounds_disagree" in x["warnings"]),
                             x["mesh_pivot_to_center_m"]), reverse=True)
    return {
        "schema": "DX2Ed-placement-audit-v1",
        "read_only": True,
        "game_verified": False,
        "analyzed_actor_count": len(entries),
        "observed_actor_count": len(valid),
        "review_actor_count": len(by_mismatch),
        "warning_counts": dict(sorted(counts.items())),
        "review_examples": by_mismatch[:MAX_EXAMPLES],
        "warnings": [
            "The GMP/IBD/vertex bound comparison concerns local geometry, not confirmed game-world placement.",
            "A distant pivot is not necessarily an error. BSP AABB overlap is not collision proof.",
            "Original rotation conventions and game-scale fields remain provisional.",
            "Do not use this report to write automatic transform corrections.",
        ],
    }
