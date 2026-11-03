#!/usr/bin/env python3
"""Validate DX2Ed brush drafts and emit an engine-agnostic Unreal-units plan.

READ-ONLY input. NO Unreal CSG, DX2 BSP, GMP, collision or game verification.
Only box-like brushes are admitted; preview stairs need real CSG union.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

SCALE_METRES_PER_UE_UNIT = 0.01905  # DX2Ed viewer convention, not game-verified
SCHEMA_IN = "DX2Ed-prop-draft-v1"
SCHEMA_OUT = "DX2SDK-brush-authoring-plan-v1"
COORDS_IN = "Godot world metres (X=UE X, Y=UE Z, Z=UE Y)"
MAX_DRAFT_BYTES = 2_000_000
MAX_BRUSHES = 128
MAX_SIZE_METRES = 256.0
MIN_SIZE_METRES = 0.05
MAX_ABS_COORD_METRES = 100_000.0
MIN_BASIS_LENGTH = 0.01
MAX_BASIS_LENGTH = 100.0
# Sets of the corners on each of the six faces. Orient outward after mapping.
QUADS = ((0,3,7,4),(1,5,6,2),(0,4,5,1),(3,2,6,7),(0,1,2,3),(4,7,6,5))


def _number(raw, label: str, *, limit=MAX_ABS_COORD_METRES) -> float:
    if type(raw) not in (float, int):
        raise ValueError(f"{label} must be numeric, not boolean or text")
    value = float(raw)
    if not math.isfinite(value) or abs(value) > limit:
        raise ValueError(f"{label} is outside finite supported range")
    return value


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _sub(a, b):
    return [x-y for x, y in zip(a, b)]


def _cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def _length(v):
    return math.sqrt(_dot(v, v))


def _mean(points):
    return [sum(p[i] for p in points)/len(points) for i in range(3)]


def _as_unreal(v):
    return [v[0]/SCALE_METRES_PER_UE_UNIT, v[2]/SCALE_METRES_PER_UE_UNIT,
            v[1]/SCALE_METRES_PER_UE_UNIT]


def _transform(raw):
    if type(raw) is not list or len(raw) != 12:
        raise ValueError("Brush transform must contain 12 Godot basis/origin numbers")
    a = [_number(x, f"transform[{i}]") for i, x in enumerate(raw)]
    bx, by, bz = (a[0:3], a[3:6], a[6:9])
    basis = (bx, by, bz)
    lengths = [_length(v) for v in basis]
    if any(n < MIN_BASIS_LENGTH or n > MAX_BASIS_LENGTH for n in lengths):
        raise ValueError("Brush basis has a degenerate or unsupported scale")
    for i in range(3):
        for j in range(i+1, 3):
            if abs(_dot(basis[i], basis[j])) > 1e-4*lengths[i]*lengths[j]:
                raise ValueError("Sheared brush transforms are not supported")
    if _dot(bx, _cross(by, bz)) <= 0:
        raise ValueError("Mirrored or left-handed Godot brush transform is not supported")
    return basis, a[9:12]


def _spec(raw, source):
    if type(raw) is not dict:
        raise ValueError("Brush metadata must be an object")
    kind = raw.get("kind")
    if kind == "Stairs":
        raise ValueError("Stairs use overlapping preview boxes; CSG union is not implemented")
    if kind not in ("Box","Wall","Floor") or source != "Brush::"+str(kind):
        raise ValueError("Unsupported/mismatched brush kind or source")
    size = raw.get("size")
    if type(size) is not list or len(size) != 3:
        raise ValueError("Brush size must have exactly three dimensions")
    size = [_number(v, f"brush size[{i}]", limit=MAX_SIZE_METRES)
            for i, v in enumerate(size)]
    if any(s < MIN_SIZE_METRES for s in size):
        raise ValueError("Brush dimension smaller than supported minimum")
    steps = raw.get("steps", 1)
    if type(steps) not in (int, float) or steps != 1:
        raise ValueError("Box/Wall/Floor must have exactly one step")
    return kind, size


def _one_brush(entry):
    if type(entry) is not dict:
        raise ValueError("Invalid brush entry")
    name = entry.get("name")
    if type(name) is not str or not name.startswith("DraftProp_") or not name[10:].isdigit():
        raise ValueError("Invalid draft brush name")
    if entry.get("class_template", {}) not in ({}, None):
        raise ValueError("A preview brush cannot carry an actor class template")
    kind, size = _spec(entry.get("brush"), entry.get("from_actor"))
    basis, origin = _transform(entry.get("transform"))
    half = [s/2 for s in size]
    local = [[sx*half[0], sy*half[1], sz*half[2]]
             for sx,sy,sz in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                              (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
    world = [[origin[i]+sum(basis[k][i]*v[k] for k in range(3))
              for i in range(3)] for v in local]
    verts = [_as_unreal(v) for v in world]
    center = _mean(verts)
    faces = []
    for face_id, raw_indices in enumerate(QUADS):
        indices = list(raw_indices)
        pts = [verts[i] for i in indices]
        normal = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))
        magnitude = _length(normal)
        if magnitude <= 1e-8:
            raise ValueError("Degenerate brush face")
        if _dot(normal, _sub(_mean(pts), center)) < 0:
            indices.reverse()
            normal = [-x for x in normal]
        faces.append({"id": face_id, "vertices": indices,
                      "normal": [x/magnitude for x in normal], "material": None})
    return {
        "draft_name": name, "kind": kind,
        "csg_intent": "additive_solid_not_compiled",
        "size_godot_metres": size, "origin_ue_units": _as_unreal(origin),
        "world_vertices_ue_units": verts, "faces_quads_outward_ue": faces,
        "bounds_ue_units": {
            "min": [min(v[i] for v in verts) for i in range(3)],
            "max": [max(v[i] for v in verts) for i in range(3)],
        },
    }


def build_plan(document, raw_digest: str) -> dict:
    if type(document) is not dict or document.get("schema") != SCHEMA_IN:
        raise ValueError("Expected a DX2Ed-prop-draft-v1 JSON document")
    if document.get("coordinate_space") != COORDS_IN or document.get("read_only_source") is not True:
        raise ValueError("Unsupported draft coordinate space or source safety marker")
    if type(document.get("map_cache")) is not str or not document["map_cache"]:
        raise ValueError("Missing source map-cache identity")
    copies = document.get("copies")
    if type(copies) is not list or len(copies) > MAX_BRUSHES:
        raise ValueError("Invalid or excessive draft copy count")
    for field in ("moved", "property_edits"):
        if document.get(field, []) != []:
            raise ValueError(f"Non-brush draft edits ({field}) must be handled separately")
    if not copies:
        raise ValueError("No draft brushes found")
    brushes = []
    names = set()
    for entry in copies:
        brush = _one_brush(entry)
        if brush["draft_name"] in names:
            raise ValueError("Duplicate draft brush name")
        names.add(brush["draft_name"])
        brushes.append(brush)
    return {
        "schema": SCHEMA_OUT, "source_draft_sha256": raw_digest,
        "map_cache_identity_sha256": hashlib.sha256(document["map_cache"].encode("utf8")).hexdigest(),
        "coordinate_space": "UE units XYZ; Godot X=UE X, Godot Z=UE Y, Godot Y=UE Z",
        "viewer_scale_metres_per_ue_unit": SCALE_METRES_PER_UE_UNIT,
        "brushes": brushes, "native_gmp_written": False,
        "native_bsp_compiled": False, "collision_generated": False,
        "game_runtime_verified": False,
        "limitations": [
            "Geometry-authoring intent only, NOT an Unreal Brush or native Flesh BSP export.",
            "No surface materials, UV, lightmaps, portals, CSG cut rules, physics or AI.",
            "Current viewer coordinate scale is not independently game verified.",
            "Stairs, mirrored and sheared brushes are intentionally refused.",
            "Source maps and retail assets are never modified.",
        ],
    }


def convert_file(source: Path, output: Path) -> dict:
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError("Cannot overwrite the source draft")
    if source.parent == output.parent:
        raise ValueError("Write the geometry plan outside the original draft directory")
    if source.stat().st_size > MAX_DRAFT_BYTES:
        raise ValueError("Draft exceeds 2 MB safety limit")
    raw = source.read_bytes()
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid draft JSON") from exc
    plan = build_plan(document, hashlib.sha256(raw).hexdigest())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf8") as dest:
        json.dump(plan, dest, indent=2, ensure_ascii=True, allow_nan=False)
        dest.write("\n")
    return plan


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        plan = convert_file(args.draft, args.output)
        print(json.dumps({"status": "authoring-plan-only", "output": str(args.output),
                          "brushes": len(plan["brushes"]), "native_gmp_written": False}))
        return 0
    except (ValueError, OSError, OverflowError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
