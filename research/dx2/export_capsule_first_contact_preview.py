#!/usr/bin/env python3
"""Write a PRIVATE, read-only DX2Ed capsule-contact research preview sidecar.

Requires an owner-provided original GMP, its expected SHA-256, and explicit
capsule motion in original Level XYZ. Uses strictly validated source geometry
and independent first-contact computations from PR #46. The resulting JSON is
for a VISUAL RESEARCH OVERLAY, not Havok gameplay or collision compilation.

Generated points are private, derived from retail geometry; NEVER commit a
real-map output sidecar. Writes only to a fresh file outside retail Maps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import export_level_mopp_triangle_debug_mesh as exporter
import inspect_mopp_point_triangle_oracle as geometry
import inspect_mopp_axis_point_candidates as mopp
import inspect_mopp_capsule_first_contact as toi
import inspect_mopp_swept_capsule as capsule

SCHEMA = "DX2Ed-capsule-first-contact-preview-v1"
COORD = "Godot preview (Level.x/10, Level.z/10, Level.y/10)"
MAX_INPUT_BYTES = 500_000_000


def preview_point(level_xyz):
    xyz = tuple(float(v) for v in level_xyz)
    if len(xyz) != 3 or not all(math.isfinite(v) and abs(v) <= 1e6 for v in xyz):
        raise ValueError("Invalid source Level XYZ")
    return [xyz[0] * .1, xyz[2] * .1, xyz[1] * .1]


def preview_unit(unit_level_xyz):
    xyz = tuple(float(v) for v in unit_level_xyz)
    return [xyz[0], xyz[2], xyz[1]]


def build_document(oracle, walker, *, map_name, source_hash, start,
                   end, radius, axis, axis_half_length):
    """Fixture-testable, source-ID-validated document without file writes."""
    if (not isinstance(oracle, geometry.LevelPointTriangleOracle) or
            not isinstance(walker, mopp.ConservativeMoppPointCandidates) or
            set(oracle.tris) != walker.complete_leaf_set):
        raise ValueError("Original source geometry and MOPP leaves disagree")
    if (not isinstance(map_name, str) or not map_name.lower().endswith(".gmp")
            or Path(map_name).name != map_name
            or not isinstance(source_hash, str) or len(source_hash) != 64
            or any(c not in "0123456789abcdef" for c in source_hash)):
        raise ValueError("Missing authenticated original GMP identity")
    a = geometry._point(start, label="Capsule motion start")
    b = geometry._point(end, label="Capsule motion end")
    r, unit, half = capsule._shape(radius, axis, axis_half_length)
    # An explicit nonzero path avoids misleading stationary-sweep graphics.
    if math.dist(a, b) <= 1e-10:
        raise ValueError("Preview requires a nonzero-length capsule motion")
    contacts = toi.first_capsule_triangle_contacts(
        oracle, a, b, r, unit, half)
    old = capsule.swept_capsule_triangle_hits(oracle, a, b, r, unit, half)
    newids = set(contacts["original_triangle_contact_ids"])
    if newids != set(old["original_triangle_hit_ids"]):
        raise ValueError("Independent full-sweep geometry disagrees with first-contact IDs")
    query = capsule.swept_capsule_mopp_candidates(
        walker, a, b, r, unit, half, diagonal_mode="conservative")
    if not newids <= set(query["candidate_original_triangle_ids"]):
        raise ValueError("MOPP research candidates omit a genuine contact: refuse preview")
    first = contacts["first_contact"]
    hit = None
    if first is not None:
        tid = first.original_triangle_id
        if tid not in oracle.tris:
            raise ValueError("Original Level triangle identity lost")
        normal = first.contact_normal_from_triangle_to_capsule
        if (first.contact_normal_resolved != (normal is not None) or
                not 0 <= first.t_first_inside <= 1 or
                (first.t_last_outside is not None and
                 not 0 <= first.t_last_outside <= first.t_first_inside)):
            raise ValueError("Inconsistent first-contact geometric evidence")
        hit = {
            "original_level_triangle_id": tid,
            "t_first_inside": first.t_first_inside,
            "t_last_outside": first.t_last_outside,
            "contact_triangle_point_godot_xyz": preview_point(first.triangle_point_xyz),
            "contact_capsule_axis_point_godot_xyz": preview_point(first.capsule_axis_point_xyz),
            "contact_normal_godot_xyz": preview_unit(normal) if normal is not None else None,
            "contact_normal_resolved": first.contact_normal_resolved,
            "initial_overlap": first.initial_overlap,
            "near_tangency": first.near_tangency,
            "numerical_contact_only": first.numerical_contact_only,
            "signed_gap_at_contact_level_units": first.signed_gap_at_contact,
            "original_mopp_candidate_included": True,
        }
    return {
        "schema": SCHEMA,
        "source_map": map_name,
        "source_sha256": source_hash,
        "read_only": True,
        "not_a_native_collision_writer": True,
        "havok_runtime_contact_verified": False,
        "physics_materials_verified": False,
        "coordinate_system": COORD,
        "capsule_start_godot_xyz": preview_point(a),
        "capsule_end_godot_xyz": preview_point(b),
        "capsule_axis_unit_godot_xyz": preview_unit(unit),
        "capsule_radius_godot_units": r / 10.,
        "capsule_axis_half_length_godot_units": half / 10.,
        "first_hit": hit,
        "geometric_source_triangle_hits": len(newids),
        "source_verified_mopp_leaf_ids": len(oracle.tris),
        "first_contact_method": "source-Level fixed-axis capsule, numerical first entry",
        "time_of_impact_exact_havok": False,
        "original_game_assets_modified": False,
    }


def build(map_path, destination, *, expected_sha256, start, end, radius,
          axis, axis_half_length):
    map_path = Path(map_path).resolve()
    destination = Path(destination).resolve()
    if (not map_path.is_file() or map_path.suffix.lower() != ".gmp"
            or map_path.stat().st_size > MAX_INPUT_BYTES
            or destination.suffix.lower() != ".json"
            or destination == map_path or
            destination.is_relative_to(map_path.parent)
            or destination.exists()):
        raise ValueError("Expected original GMP and fresh private JSON outside Maps")
    if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
            or any(c not in "0123456789abcdef" for c in expected_sha256)):
        raise ValueError("Expected original GMP SHA-256")
    digest = hashlib.sha256(map_path.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError("Original GMP SHA-256 differs from editor scene")
    atlas, metadata = exporter.audit_map(map_path)
    if metadata.get("sha256") != digest:
        raise ValueError("Original GMP changed during provenance validation")
    root = Path(__file__).resolve().parents[2] / "map_exporter"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from dx2inspect import Package
    from dx2scene import find_bsp
    package = Package(map_path)
    if hashlib.sha256(package.data).hexdigest() != digest:
        raise ValueError("Original source GMP changed during decoding")
    levels = [e for e in package.exports if
              package.class_name(e) == "Level" and e["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected exactly one authenticated original Level")
    level = package.payload(levels[0])
    blocks = find_bsp(package)
    candidate_atlas = exporter.inspect_mesh(level, blocks)
    if candidate_atlas["source_triangle_count"] != atlas["source_triangle_count"]:
        raise ValueError("Original triangle counts differ across source audits")
    oracle = geometry.original_atlas_oracle(candidate_atlas)
    verified = exporter.provenance.mopp.inspect_mopp_link(level, blocks)
    pc = verified["mopp_code_start_in_level"]
    walker = mopp.ConservativeMoppPointCandidates(
        level[pc:verified["mopp_code_end_in_level"]],
        candidate_atlas["source_triangle_count"],
        struct.unpack_from("<4f", level, pc-20))
    doc = build_document(oracle, walker, map_name=map_path.name,
                         source_hash=digest, start=start, end=end,
                         radius=radius, axis=axis, axis_half_length=axis_half_length)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return {"status": "ok", "private_preview": str(destination),
            "source_map": map_path.name, "first_hit_original_triangle_id":
            doc["first_hit"]["original_level_triangle_id"] if doc["first_hit"] else None,
            "research_only": True}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--expected-sha256", required=True)
    ap.add_argument("--start", type=float, nargs=3, required=True)
    ap.add_argument("--end", type=float, nargs=3, required=True)
    ap.add_argument("--radius", type=float, default=.2)
    ap.add_argument("--axis", type=float, nargs=3, default=(0.,0.,1.))
    ap.add_argument("--axis-half-length", type=float, default=.5)
    a = ap.parse_args(argv)
    try:
        result = build(a.map, a.output, expected_sha256=a.expected_sha256,
                       start=a.start, end=a.end, radius=a.radius,
                       axis=a.axis, axis_half_length=a.axis_half_length)
        print(json.dumps(result))
        return 0
    except (OSError, TypeError, KeyError, ValueError, IndexError,
            OverflowError, struct.error) as e:
        print(json.dumps({"status":"refused","reason":str(e)}),file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
