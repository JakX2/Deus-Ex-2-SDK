"""Deterministic Wavefront OBJ for validated *private* DX2Ed convex Box brushes.

No read/write path to native Deus Ex: Invisible War BSP, GMP, IBD, collision,
MOPP, original assets or package exporters. The OBJ is local preview geometry
and deliberately has no original-game material or BSP surface identifiers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

from .private_brush_preflight import (
    SCHEMA as PREFLIGHT_SCHEMA,
    inspect_private_box_convex,
    inspect_private_draft_copy,
    load_private_json_text,
)

SCHEMA = "DX2SDK-private-Box-Wavefront-OBJ-v1"
MAX_INPUT_BYTES = 128 * 1024
MAX_OBJ_BYTES = 128 * 1024
PRECISION = 9


def _coord(number: float) -> str:
    if not math.isfinite(number):
        raise ValueError("Nonfinite private geometry cannot be exported")
    rounded = f"{number:.{PRECISION}f}"
    if rounded == "-0.000000000":
        return "0"
    return rounded.rstrip("0").rstrip(".") if "." in rounded else rounded


def _cross(a, b):
    return (a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])


def _subtract(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _render_validated_report(report: dict) -> tuple[bytes, dict]:
    if (report["schema"] != PREFLIGHT_SCHEMA
            or report["native_world_model_writer_enabled"] is not False
            or report["original_gmp_or_ibd_modified"] is not False
            or report["runtime_verified"] is not False):
        raise ValueError("Not a validated source-private convex report")
    faces = report["local_faces_not_native_bsp"]
    n_vertices = report["vertex_count"]
    if (type(n_vertices) is not int or not 4 <= n_vertices <= 64
            or type(faces) is not list or len(faces) != report["face_count"]
            or not 4 <= len(faces) <= 14):
        raise ValueError("Private mesh exceeds bounded OBJ capacity")
    vertex_positions = [None] * n_vertices
    triangles = 0
    for face in faces:
        ids = face["vertex_ids"]
        positions = face["vertices"]
        if (type(ids) is not list or type(positions) is not list
                or len(ids) != len(positions)
                or not 3 <= len(ids) <= 16
                or len(set(ids)) != len(ids)):
            raise ValueError("Malformed private polygon face")
        for i, point in zip(ids, positions):
            if type(i) is not int or not 0 <= i < n_vertices:
                raise ValueError("Private face references out-of-range vertex")
            if (type(point) is not list or len(point) != 3
                    or any(type(v) not in (float, int) or not math.isfinite(v)
                           for v in point)):
                raise ValueError("Malformed nonfinite private face vertex")
            old = vertex_positions[i]
            if old is not None and math.dist(point, old) > 0.00001:
                raise ValueError("Private faces disagree on shared vertex")
            vertex_positions[i] = tuple(point)
        triangles += len(ids) - 2
    if (any(point is None for point in vertex_positions)
            or triangles != report["triangle_count"]
            or triangles > 44):
        raise ValueError("Private triangle / vertex census disagrees")
    content = [
        "# DX2Ed source-private preview OBJ; not native Invisible War geometry",
        f"# format: {SCHEMA}",
        "# coordinates: Godot local metres, Y-up",
        "# no original DX2 BSP surface IDs, materials, or collision",
        "# original GMP/IBD files are never read or written",
        "# private_geometry_sha256: "
        + report["private_geometry_sha256_quantized_1e-6m"],
        "o DX2Ed_Private_Box",
        "s off",
    ]
    for point in vertex_positions:
        content.append("v " + " ".join(_coord(value) for value in point))
    for face in faces:
        content.append("vn " + " ".join(
            _coord(value) for value in face["normal"]))
    cap_count = 0
    for face_number, face in enumerate(faces, 1):
        kind = face["kind"]
        slot = face["slot"]
        if (kind not in ("private_cut_cap", "private_box_side")
                or type(slot) is not int or slot < 0 or slot > 8):
            raise ValueError("Nonprivate or untrusted polygon group name")
        if kind == "private_cut_cap":
            cap_count += 1
        content.append(f"g {kind}_{slot:02d}")
        ids = face["vertex_ids"]
        normal = face["normal"]
        for i in range(1, len(ids) - 1):
            a, b, c = [vertex_positions[ids[j]] for j in (0, i, i + 1)]
            oriented = _dot(_cross(_subtract(b, a), _subtract(c, a)), normal)
            if oriented <= 1e-10:
                raise ValueError("Private OBJ triangle would face inward")
            content.append("f " + " ".join(
                f"{ids[j]+1}//{face_number}" for j in (0, i, i+1)))
    if cap_count != report["active_cut_cap_count"]:
        raise ValueError("Private face cap count disagrees with source preflight")
    payload = ("\n".join(content) + "\n").encode("ascii")
    if not 0 < len(payload) <= MAX_OBJ_BYTES:
        raise ValueError("Private OBJ output exceeds bounded export size")
    return payload, {
        "schema": SCHEMA,
        "status": "source-private-OBJ-generated-in-memory",
        "private_geometry_sha256": report[
            "private_geometry_sha256_quantized_1e-6m"],
        "source_private_spec_sha256": report["private_brush_spec_sha256"],
        "vertex_count": n_vertices,
        "face_count": len(faces),
        "triangle_count": triangles,
        "cut_cap_count": cap_count,
        "obj_sha256": hashlib.sha256(payload).hexdigest(),
        "obj_bytes": len(payload),
        "coordinate_system": "Godot-local-metres-Y-up",
        "bsp_surface_indices_included": False,
        "original_materials_included": False,
        "native_world_model_writer_enabled": False,
        "native_collision_generated": False,
        "retail_game_runtime_verified": False,
        "original_game_files_modified": False,
    }


def render_private_box_obj(raw: Any, *, copy_name: str | None = None) -> tuple[bytes, dict]:
    """Generate only an in-memory private preview OBJ and non-native summary."""
    report = (inspect_private_box_convex(raw) if copy_name is None
              else inspect_private_draft_copy(raw, copy_name))
    return _render_validated_report(report)


def export_private_box_obj(
        raw: Any, destination: Path, *, copy_name: str | None = None,
        input_path: Path | None = None) -> dict:
    """Create only a NEW .obj file with exclusive create, never overwrite.

    Caller explicitly chooses the output. Refuses symlinks, existing output
    and non-OBJ paths; original maps are not inputs to this interface.
    """
    if not isinstance(destination, Path) or destination.suffix.lower() != ".obj":
        raise ValueError("Export destination must be a new .obj file")
    if destination.is_symlink() or destination.exists():
        raise ValueError("Output exists or is symlinked; refusing overwrite")
    if (input_path is not None
            and destination.resolve() == input_path.resolve()):
        raise ValueError("Private source file cannot be overwritten")
    content, summary = render_private_box_obj(raw, copy_name=copy_name)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(destination, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as writer:
            writer.write(content)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return {**summary, "status": "new-source-private-OBJ-written",
            "output": str(destination)}


def _load_private_json(path: Path) -> Any:
    if (path.suffix.lower() != ".json" or path.is_symlink()
            or not path.is_file() or not 0 < path.stat().st_size <= MAX_INPUT_BYTES):
        raise ValueError("Only regular private JSON input <=128 KiB is accepted")
    return load_private_json_text(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export validated private DX2Ed convex Box to NEW OBJ, no native BSP")
    parser.add_argument("private_json", type=Path,
                        help="Private Box spec or DX2Ed-prop-draft-v1 sidecar")
    parser.add_argument("output_obj", type=Path,
                        help="NEW Wavefront .obj file; overwrites are refused")
    parser.add_argument("--copy", dest="copy_name",
                        help="Exact DraftProp_N name for a private draft sidecar")
    args = parser.parse_args(argv)
    try:
        raw = _load_private_json(args.private_json)
        if (args.copy_name is None and type(raw) is dict
                and raw.get("schema") == "DX2Ed-prop-draft-v1"):
            raise ValueError("A saved private draft requires --copy DraftProp_N")
        report = export_private_box_obj(
            raw, args.output_obj, copy_name=args.copy_name,
            input_path=args.private_json)
        print(json.dumps(report, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(f"Private OBJ export REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
