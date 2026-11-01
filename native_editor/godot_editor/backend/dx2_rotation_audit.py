#!/usr/bin/env python3
"""Read-only DX2Ed 0.5.6 orientation audit for cached actors.json.

Compare the legacy DX2Ed preview rotator with the UE2 FRotationMatrix
convention reconstructed from the supplied T3SDK t3common.py/t3_edits.gd.
This is a *reference transform comparison*, NOT a DX2 game-rendering oracle.
No GMP/IBD files are read, rewritten or distributed by this utility.

Usage:
  python dx2_rotation_audit.py path/to/actors.json --output rotation_audit.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

SCHEMA = "DX2Ed-rotation-reference-audit-v1"
UNIT = math.tau / 65536.0
EPSILON = 1e-4
SWAP = (0, 2, 1)  # Unreal (x,y,z) -> GLB/Godot (x,z,y)


def _rotator(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not math.isfinite(v) for v in value):
        return None
    return tuple(float(v) for v in value)


def ue2_reference_basis(rot):
    """3x3 Godot/GLB matrix, from UE2's row-vector FRotationMatrix.

    The rotation matrix rows in Unreal space are its transformed X/Y/Z axes.
    Convert to column vectors and conjugate by the Y/Z swap. This computes
    what the *T3SDK UE2 reference* predicts, not proven DX2 behavior.
    """
    pitch, yaw, roll = rot
    sp, cp = math.sin(pitch * UNIT), math.cos(pitch * UNIT)
    sy, cy = math.sin(yaw * UNIT), math.cos(yaw * UNIT)
    sr, cr = math.sin(roll * UNIT), math.cos(roll * UNIT)
    unreal_rows = (
        (cp * cy, cp * sy, sp),
        (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp),
        (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp),
    )
    # Unreal's row-vector rotation requires a transpose in GLB column space.
    return tuple(tuple(unreal_rows[SWAP[j]][SWAP[i]] for j in range(3))
                 for i in range(3))


def dx2_preview_basis(rot, invert_roll=False):
    """Mirror DX2Ed 0.5.5's Rz(yaw)*Ry(-pitch)*Rx(sign*roll).

    This independent calculation is used only for auditing, not scene exports.
    """
    pitch, yaw, roll = (v * UNIT for v in rot)
    if invert_roll:
        roll = -roll
    cp, sp = math.cos(-pitch), math.sin(-pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cr, sr = math.cos(roll), math.sin(roll)
    rx = ((1., 0., 0.), (0., cr, -sr), (0., sr, cr))
    ry = ((cp, 0., sp), (0., 1., 0.), (-sp, 0., cp))
    rz = ((cy, -sy, 0.), (sy, cy, 0.), (0., 0., 1.))

    def multiply(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3))
                           for j in range(3)) for i in range(3))

    original = multiply(rz, multiply(ry, rx))
    return tuple(tuple(original[SWAP[i]][SWAP[j]] for j in range(3))
                 for i in range(3))


def max_difference(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(3) for j in range(3))


def roll_class(rot):
    # 0 and 180 degrees are invariant under sign reversal. The rounding
    # threshold mirrors the shipping meaningful_roll_flip() heuristic.
    if abs(math.sin(rot[2] * UNIT)) > EPSILON:
        return "nontrivial_roll"
    return ("half_turn_roll" if math.cos(rot[2] * UNIT) < 0
            else "zero_or_full_turn_roll")


def analyze_actors(payload):
    """Create a deterministic, source-preserving audit of an actors.json dict."""
    if not isinstance(payload, dict) or not isinstance(payload.get("actors"), list):
        raise ValueError("Expected DX2Ed actors.json object with an actors array")
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    result = []
    counts = {"mesh_linked": 0, "nontrivial_roll": 0,
              "half_turn_roll": 0, "zero_or_full_turn_roll": 0,
              "invalid_rotator": 0}
    for actor in payload["actors"]:
        if not isinstance(actor, dict):
            continue
        mesh = actor.get("mesh")
        if isinstance(mesh, dict):
            mesh = mesh.get("name")
        if not isinstance(mesh, str) or not mesh.strip():
            continue
        counts["mesh_linked"] += 1
        rot = _rotator(actor.get("rotation"))
        identity = {"export": actor.get("export"), "actor": actor.get("name"),
                    "class": actor.get("class"), "mesh": mesh}
        if rot is None:
            counts["invalid_rotator"] += 1
            result.append({**identity, "status": "invalid_rotator",
                           "source_rotation_repr": repr(actor.get("rotation"))[:240]})
            continue
        status = roll_class(rot)
        counts[status] += 1
        reference = ue2_reference_basis(rot)
        original = dx2_preview_basis(rot)
        inverted = dx2_preview_basis(rot, invert_roll=True)
        result.append({**identity, "status": status, "rotation": list(rot),
                       "auto_roll_changes_basis": status == "nontrivial_roll",
                       "legacy_vs_ue2_max_abs": round(max_difference(original, reference), 9),
                       "inverted_vs_ue2_max_abs": round(max_difference(inverted, reference), 9)})
    return {
        "schema": SCHEMA, "map": meta.get("source_map", meta.get("map", "")),
        "map_sha256": meta.get("source_sha256", meta.get("map_sha256")),
        "read_only": True, "game_verified": False,
        "basis_reference": "UE2 FRotationMatrix (T3SDK source comparison)",
        "warnings": [
            "This mathematical parity does not verify the retail DX2 renderer, mesh pivot, or actor placement.",
            "A half-turn Roll is unchanged by sign inversion; it cannot be repaired by Auto Roll alone.",
            "No game archives, actor edits, or source map files are modified.",
        ],
        "counts": counts, "actors": result,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("actors_json", type=Path, help="Existing DX2Ed cached actors.json")
    ap.add_argument("--output", type=Path, help="Write a separate read-only JSON audit")
    args = ap.parse_args(argv)
    if args.output and args.actors_json.resolve() == args.output.resolve():
        ap.error("--output must not overwrite the original actors.json")
    try:
        payload = json.loads(args.actors_json.read_text(encoding="utf-8"))
        report = analyze_actors(payload)
        formatted = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(formatted, encoding="utf-8")
            print(json.dumps({"status": "ok", "output": str(args.output), "counts": report["counts"]}))
        else:
            print(formatted, end="")
    except (ValueError, OSError, TypeError) as err:
        print(json.dumps({"status": "error", "message": str(err)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
