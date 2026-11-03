#!/usr/bin/env python3
"""Read-only DX2 UE95 Level -> actor -> GameSys(45) -> Model ownership audit.

This does NOT decode model polygons, native collision, CSG or compiled BSP.
Only source map packages that the user owns may be supplied. Never rewrites GMP.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

SDK_ROOT = Path(__file__).resolve().parents[2]
EXPORTER = SDK_ROOT / "map_exporter"
if str(EXPORTER) not in sys.path:
    sys.path.insert(0, str(EXPORTER))
from dx2inspect import Package, Cursor
from dx2scene import decode_full_actor

SCHEMA = "DX2SDK-native-brush-model-ownership-v1"
DX2_LICENSEES = (68, 69)
LEVEL_ACTORS_OFFSET = 13  # UE95/Flesh Level source-observed layout
GAMESYS_MODEL_REF_ID = 45
MAX_MAP_BYTES = 250 * 1024 * 1024
MAX_LEVEL_ACTORS = 100000
MAX_PROBLEMS = 100


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _level_actor_refs(pkg: Package) -> tuple[list[int], dict]:
    levels = [e for e in pkg.exports if pkg.class_name(e) == "Level" and e["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected exactly one nonempty Level export")
    raw = pkg.payload(levels[0])
    if len(raw) < LEVEL_ACTORS_OFFSET + 8:
        raise ValueError("Level payload is too short for an actor list")
    cursor = Cursor(raw, LEVEL_ACTORS_OFFSET)
    count = cursor.u32()
    check = cursor.u32()
    if count != check or count > MAX_LEVEL_ACTORS or count > len(raw):
        raise ValueError("Invalid/different repeated Level actor count")
    first = cursor.at
    refs = []
    for _ in range(count):
        ref = cursor.ci()
        if ref <= 0 or ref > len(pkg.exports):
            raise ValueError(f"Level actor list contains invalid export ref {ref}")
        refs.append(ref)
    return refs, {
        "level_export": levels[0]["name"],
        "actor_count": count,
        "actor_refs_start_level_offset": first,
        "actor_refs_end_level_offset": cursor.at,
        "actor_export_refs_unique": len(set(refs)) == len(refs),
        "actor_classes": dict(sorted(Counter(pkg.class_name(pkg.exports[ref - 1])
                                            for ref in refs).items())),
    }


def _candidate_bounds(pkg: Package, exp: dict) -> dict:
    """Source-observed 9-zero-byte prefix followed by six bbox-like float32.

    This checks structural consistency only, not the true serialized meaning
    or whether these are local/world, collision or render bounds.
    """
    raw = pkg.payload(exp)
    result = {"payload_bytes": len(raw), "header_zero9": raw[:9] == b"\0" * 9}
    if len(raw) < 33 or not result["header_zero9"]:
        result["candidate_bounds_status"] = "unavailable_unrecognized_prefix"
        return result
    numbers = struct.unpack_from("<6f", raw, 9)
    lo, hi = numbers[:3], numbers[3:]
    if not (all(math.isfinite(v) and abs(v) < 1e8 for v in numbers)
            and all(a <= b for a, b in zip(lo, hi))):
        result["candidate_bounds_status"] = "unavailable_invalid_bounds"
        return result
    result["candidate_bounds_status"] = "six_ordered_f32_at_offset_9"
    result["candidate_bounds_ue_units"] = {"min": list(lo), "max": list(hi)}
    return result


def audit_map(path: Path) -> dict:
    path = Path(path)
    if path.suffix.casefold() != ".gmp" or not path.is_file():
        raise ValueError("Expected existing original DX2 .gmp")
    if path.stat().st_size > MAX_MAP_BYTES:
        raise ValueError("Map file exceeds safe research size")
    pkg = Package(path)
    if pkg.version != 95 or pkg.licensee not in DX2_LICENSEES:
        raise ValueError(f"Expected DX2 Unreal v95 / licensee 68 or 69, got {pkg.version}/{pkg.licensee}")
    actor_refs, actor_list = _level_actor_refs(pkg)
    models = {e["index"]: e for e in pkg.exports if pkg.class_name(e) == "Model"}
    brushes = {e["index"]: e for e in pkg.exports if pkg.class_name(e) == "Brush"}
    # Package export indices in DX2 inspector are one-based.
    model_headers = {idx: _candidate_bounds(pkg, exp) for idx, exp in models.items()}
    owners = []
    owners_by_model = defaultdict(list)
    problems = []
    parse_failures = 0
    owner_class_counts = Counter()
    csg_oper_counts = Counter()
    referenced_brushes = set()
    null_model_properties = Counter()

    for ref in actor_refs:
        exp = pkg.exports[ref - 1]
        cls = pkg.class_name(exp)
        try:
            tagged, gamesys = decode_full_actor(pkg, exp, {})
        except (ValueError, IndexError, KeyError, struct.error) as err:
            parse_failures += 1
            if len(problems) < MAX_PROBLEMS:
                problems.append({"actor_export": ref, "class": cls,
                                 "issue": "actor_decode_failed", "reason": type(err).__name__})
            continue

        if cls == "Brush":
            oper = tagged.get("CsgOper")
            csg_oper_counts[str(oper) if type(oper) is int else "absent_or_unreadable"] += 1

        candidates = [block for block in gamesys if block.get("id") == GAMESYS_MODEL_REF_ID]
        if cls == "Brush" and len(candidates) != 1 and len(problems) < MAX_PROBLEMS:
            problems.append({"actor_export": ref, "class": cls,
                             "issue": "brush_missing_or_duplicate_model_property",
                             "property_count": len(candidates)})
        for block in candidates:
            if block.get("encoding") != "object":
                if len(problems) < MAX_PROBLEMS:
                    problems.append({"actor_export": ref, "class": cls,
                                     "issue": "model_property_wrong_encoding"})
                continue
            value = block.get("value")
            if value is None:
                null_model_properties[cls] += 1
                continue
            model_ref = value.get("ref") if isinstance(value, dict) else None
            if type(model_ref) is not int or model_ref <= 0 or model_ref not in models:
                if len(problems) < MAX_PROBLEMS:
                    problems.append({"actor_export": ref, "class": cls,
                                     "issue": "property_45_not_valid_model_export"})
                continue
            owners.append({"actor_export": ref, "actor_name": exp["name"],
                           "actor_class": cls, "gamesys_property_id": GAMESYS_MODEL_REF_ID,
                           "model_export": model_ref, "model_name": models[model_ref]["name"],
                           "model_header": model_headers[model_ref]})
            owners_by_model[model_ref].append(ref)
            owner_class_counts[cls] += 1
            if cls == "Brush":
                referenced_brushes.add(ref)

    model_refs = set(models)
    missing_brush_list = sorted(set(brushes) - set(actor_refs))
    linked = set(owners_by_model)
    unlinked = sorted(model_refs - linked)
    collisions = [{"model_export": idx, "actor_exports": actor_indices}
                  for idx, actor_indices in sorted(owners_by_model.items())
                  if len(actor_indices) > 1]
    return {
        "schema": SCHEMA, "read_only": True, "native_writer_executed": False,
        "game_runtime_verified_by_this_tool": False,
        "source": {
            "file": path.name, "sha256": _sha(pkg.data), "bytes": len(pkg.data),
            "unreal_package_version": pkg.version, "licensee_version": pkg.licensee,
            "exports": len(pkg.exports),
        },
        "level_actor_list": actor_list,
        "summary": {
            "brush_exports": len(brushes), "model_exports": len(models),
            "brushes_present_in_level_actor_list": len(set(brushes) & set(actor_refs)),
            "brushes_with_valid_model_reference": len(referenced_brushes),
            "nonbrush_model_owners": sum(n for cls, n in owner_class_counts.items() if cls != "Brush"),
            "unique_models_referenced": len(linked),
            "unreferenced_models": len(unlinked),
            "multiply_referenced_models": len(collisions),
            "actor_decode_failures": parse_failures,
            "property_45_null_by_class": dict(sorted(null_model_properties.items())),
            "owner_class_counts": dict(sorted(owner_class_counts.items())),
            "brush_csg_oper_raw_tag_values": dict(sorted(csg_oper_counts.items())),
            "models_matching_candidate_zero9_and_six_f32": sum(
                h["candidate_bounds_status"] == "six_ordered_f32_at_offset_9"
                for h in model_headers.values()),
        },
        "unreferenced_model_exports": [
            {"export": idx, "name": models[idx]["name"], "header": model_headers[idx]}
            for idx in unlinked
        ],
        "invalid_or_unlisted_brush_exports": missing_brush_list,
        "model_reference_collisions": collisions,
        "issues": problems,
        "issues_truncated": len(problems) == MAX_PROBLEMS,
        "owners": owners,
        "limits": [
            "Model ownership is inferred only from validated GameSys object property 45 in Level-listed actors.",
            "Unreferenced Model exports are candidates for global/world geometry, not proven world-model structures.",
            "Nine zero bytes then six ordered f32 at Model offset 9 is a bounds hypothesis, not a decoded native schema.",
            "CsgOper values are preserved as raw tags; Add/Subtract semantics are not claimed.",
            "Property 45 links are not collision, PVS, Havok, baked lightmap or render-block ownership links.",
            "No DX2 native map changes, BSP compilation, collision generation or runtime validation are performed.",
        ],
    }


def _write_report(report: dict, output: Path, input_path: Path) -> None:
    output = Path(output).resolve()
    input_path = Path(input_path).resolve()
    if output.suffix.casefold() != ".json" or output == input_path:
        raise ValueError("Report must be a new JSON file, not the map")
    if output.is_relative_to(input_path.parent):
        raise ValueError("Write reports outside the game map directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit_map(args.map)
        if args.report:
            _write_report(result, args.report, args.map)
            print(json.dumps({"status": "ok", "report": str(args.report),
                              "summary": result["summary"]}, indent=2))
        else:
            print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, IndexError, KeyError, struct.error) as err:
        print(json.dumps({"status": "error", "reason": str(err)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
