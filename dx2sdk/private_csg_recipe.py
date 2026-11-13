"""P103: isolated, replayable source-private CSG recipes.

A recipe preserves only two authored clipped Box specifications, two proper
rigid placements and the requested operation. It does NOT store an accepted
mesh as authoritative: loading recomputes CSG and compares exact canonical
result/provenance fingerprints before exposing a preview to Godot.

No native map, BSP/CSG, GameSys, Havok/MOPP or original game files are read,
written or modified. Saving is NEW-file-only and never targets Content/DX2/Maps.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import stat
import sys
from typing import Any

from .private_brush_obj import _load_private_json
from .private_brush_pair_sat import _rigid
from .private_brush_intersection import intersect_private_boxes
from .private_brush_subtraction import subtract_private_boxes

SCHEMA = "DX2Ed-private-CSG-recipe-v1"
MAX_RECIPE_BYTES = 256 * 1024
_NAME = re.compile(r"DraftProp_[1-9][0-9]{0,7}\Z")
_FIELDS = frozenset({
    "schema", "operation", "source_private_a", "source_private_b",
    "brush_a", "brush_b", "transform_a", "transform_b",
    "source_payload_sha256", "computed_result_sha256",
    "piece_count", "remaining_volume_m3", "read_only_source",
    "native_world_bsp_writer_enabled", "native_havok_mopp_collision_enabled",
    "retail_game_runtime_verified",
})


def _canonical(raw: Any) -> bytes:
    return json.dumps(raw, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def _sha(raw: Any) -> str:
    return sha256(_canonical(raw)).hexdigest()


def _private_name(name: Any) -> str:
    if type(name) is not str or _NAME.fullmatch(name) is None:
        raise ValueError("Only a private DraftProp_N identity is accepted")
    return name


def _validate_inputs(
    a: Any, b: Any, transform_a: Any, transform_b: Any,
    operation: str, name_a: str, name_b: str,
) -> tuple[dict, dict, dict, dict, dict]:
    name_a = _private_name(name_a)
    name_b = _private_name(name_b)
    if name_a == name_b:
        raise ValueError("CSG operands must be two different private drafts")
    if operation not in ("intersection", "subtraction"):
        raise ValueError("Unsupported source-private CSG recipe operation")
    if type(a) is not dict or type(b) is not dict:
        raise ValueError("CSG recipe requires two private Box dictionaries")
    # The existing preflight called by these functions rejects unknown native
    # actors, unsupported geometry and degenerate/oversized convex results.
    aa, bb = _rigid(transform_a), _rigid(transform_b)
    build = intersect_private_boxes if operation == "intersection" else subtract_private_boxes
    result = build(a, b, transform_a=aa, transform_b=bb)
    if (result.get("original_gmp_or_ibd_modified") is not False
        or result.get("retail_game_runtime_verified") is not False):
        raise ValueError("CSG result is outside source-private boundaries")
    return a, b, aa, bb, result


def make_private_csg_recipe(
    a: Any, b: Any, transform_a: Any, transform_b: Any,
    operation: str, name_a: str, name_b: str,
) -> tuple[dict, dict]:
    a, b, aa, bb, result = _validate_inputs(
        a, b, transform_a, transform_b, operation, name_a, name_b)
    count = (1 if result["has_volume"] else 0) if operation == "intersection" else result["piece_count"]
    volume = (result["volume_m3"] if operation == "intersection"
              else result["remaining_volume_m3"])
    payload = {
        "operation": operation, "source_private_a": name_a,
        "source_private_b": name_b, "brush_a": a, "brush_b": b,
        "transform_a": aa, "transform_b": bb,
    }
    recipe = {
        "schema": SCHEMA, **payload,
        "source_payload_sha256": _sha(payload),
        "computed_result_sha256": _sha(result),
        "piece_count": count, "remaining_volume_m3": volume,
        "read_only_source": True,
        "native_world_bsp_writer_enabled": False,
        "native_havok_mopp_collision_enabled": False,
        "retail_game_runtime_verified": False,
    }
    if len(_canonical(recipe)) > MAX_RECIPE_BYTES:
        raise ValueError("Private CSG recipe exceeds bounded file capacity")
    return recipe, result


def _safe_path(path: str | Path, *, must_exist: bool) -> Path:
    given = Path(path).expanduser()
    if not given.name.lower().endswith(".dx2csg.json"):
        raise ValueError("Only .dx2csg.json private recipes are accepted")
    if given.is_symlink():
        raise ValueError("Private recipe symlinks are not accepted")
    resolved = given.resolve(strict=False)
    lower = tuple(part.casefold() for part in resolved.parts)
    if any(lower[i:i+3] == ("content", "dx2", "maps")
           for i in range(max(0, len(lower)-2))):
        raise ValueError("Private CSG recipes cannot touch retail game maps")
    if must_exist:
        try:
            info = resolved.lstat()
        except OSError as exc:
            raise ValueError("Private CSG recipe is missing") from exc
        if (not stat.S_ISREG(info.st_mode)
            or not 0 < info.st_size <= MAX_RECIPE_BYTES):
            raise ValueError("Private CSG recipe must be bounded regular JSON")
    elif resolved.exists() or given.exists():
        raise ValueError("Private CSG recipe destination already exists")
    return resolved


def write_private_csg_recipe(
    a: Any, b: Any, transform_a: Any, transform_b: Any,
    operation: str, name_a: str, name_b: str, output: str | Path,
) -> dict:
    """Explicit NEW private recipe, no overwrite and no original game writes."""
    recipe, result = make_private_csg_recipe(
        a, b, transform_a, transform_b, operation, name_a, name_b)
    dest = _safe_path(output, must_exist=False)
    blob = _canonical(recipe) + b"\n"
    if len(blob) > MAX_RECIPE_BYTES:
        raise ValueError("Private CSG recipe exceeds maximum file size")
    # No intermediate file is written next to original game source files.
    # 'xb' atomically refuses existing destinations and races.
    with dest.open("xb") as output_file:
        output_file.write(blob)
    return {
        "schema": SCHEMA, "operation": operation,
        "source_private_a": name_a, "source_private_b": name_b,
        "piece_count": recipe["piece_count"],
        "remaining_volume_m3": recipe["remaining_volume_m3"],
        "computed_result_sha256": recipe["computed_result_sha256"],
        "read_only_source": True, "original_game_files_modified": False,
        "retail_game_runtime_verified": False,
    }


def _no_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key in private CSG recipe")
        result[key] = value
    return result


def read_private_csg_recipe(path: str | Path) -> tuple[dict, dict]:
    """Recompute everything. Refuse edited, stale or unsupported recipes."""
    src = _safe_path(path, must_exist=True)
    with src.open("rb") as handle:
        data = handle.read(MAX_RECIPE_BYTES + 1)
    if not 0 < len(data) <= MAX_RECIPE_BYTES:
        raise ValueError("Private CSG recipe became oversized")
    try:
        document = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_no_duplicate_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("Nonfinite recipe numbers refused")),
        )
    except UnicodeError as exc:
        raise ValueError("Recipe is not valid UTF-8") from exc
    if type(document) is not dict or set(document) != _FIELDS:
        raise ValueError("Private CSG recipe has unknown or missing fields")
    if (document["schema"] != SCHEMA or
        document["read_only_source"] is not True or
        document["native_world_bsp_writer_enabled"] is not False or
        document["native_havok_mopp_collision_enabled"] is not False or
        document["retail_game_runtime_verified"] is not False):
        raise ValueError("Unsupported source-private recipe capability")
    payload = {k: document[k] for k in (
        "operation", "source_private_a", "source_private_b", "brush_a",
        "brush_b", "transform_a", "transform_b")}
    if document["source_payload_sha256"] != _sha(payload):
        raise ValueError("Private CSG source payload fingerprint mismatch")
    fresh, result = make_private_csg_recipe(
        document["brush_a"], document["brush_b"],
        document["transform_a"], document["transform_b"],
        document["operation"], document["source_private_a"],
        document["source_private_b"])
    if _canonical(fresh) != _canonical(document):
        raise ValueError("Private CSG recipe result or provenance mismatch")
    return fresh, result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Save/replay an isolated source-private CSG recipe only")
    commands = parser.add_subparsers(dest="command", required=True)
    save = commands.add_parser("save")
    save.add_argument("operation", choices=("intersection", "subtraction"))
    save.add_argument("name_a")
    save.add_argument("name_b")
    save.add_argument("brush_a", type=Path)
    save.add_argument("brush_b", type=Path)
    save.add_argument("transform_a", type=Path)
    save.add_argument("transform_b", type=Path)
    save.add_argument("output", type=Path)
    load = commands.add_parser("load")
    load.add_argument("recipe_path", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "save":
            details = write_private_csg_recipe(
                _load_private_json(args.brush_a),
                _load_private_json(args.brush_b),
                _load_private_json(args.transform_a),
                _load_private_json(args.transform_b),
                args.operation, args.name_a, args.name_b, args.output)
            print(json.dumps(details, sort_keys=True, allow_nan=False))
        else:
            recipe, result = read_private_csg_recipe(args.recipe_path)
            print(json.dumps({
                "schema": SCHEMA,
                "operation": recipe["operation"],
                "source_private_a": recipe["source_private_a"],
                "source_private_b": recipe["source_private_b"],
                "computed_result_sha256": recipe["computed_result_sha256"],
                "read_only_source": True,
                "result": result,
            }, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print("Private CSG recipe REFUSED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
