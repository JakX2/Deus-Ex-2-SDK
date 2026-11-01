#!/usr/bin/env python3
"""EXPERIMENTAL DX2 GMP save-as writer, limited to existing actor translation.

This is a binary *in-place field* patch on a NEW COPY: no package rebuild,
no actor creation, no rotation/scale/brush changes, no in-game validation.
Only the serialized FVector Location.X/Y/Z float32 bytes are changed.
Never point output into the original retail Maps directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3] / "map_exporter"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dx2inspect import Cursor, HAS_STACK, Package
from dx2level import SCALE, actor_matrix

SCHEMA = "DX2Ed-prop-draft-v1"
MAX_MOVES = 10000
BASIS_TOLERANCE = 0.001
SOURCE_TOLERANCE = 0.005


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tagged_entries(pkg: Package, cursor: Cursor):
    """Yield tagged-property payload offsets, preserving unknown field layouts.

    Matching the v95 decoder's compact names, flag/array indices, and size
    forms is essential. This parser only observes offsets; never reserializes.
    """
    for _ in range(100000):
        name_index = cursor.ci()
        if name_index < 0 or name_index >= len(pkg.names):
            raise ValueError("Tag references unknown property name")
        name = pkg.names[name_index]
        if name == "None":
            return
        info = cursor.u8()
        kind = info & 15
        sz_kind = (info >> 4) & 7
        flag = bool(info & 128)
        if kind == 10:
            struct_index = cursor.ci()
            if struct_index < 0 or struct_index >= len(pkg.names):
                raise ValueError("Tag references unknown struct name")
        if sz_kind < 5:
            size = (1, 2, 4, 12, 16)[sz_kind]
        elif sz_kind == 5:
            size = cursor.u8()
        elif sz_kind == 6:
            size = cursor.u16()
        else:
            size = cursor.u32()
        if flag and kind != 3:
            first = cursor.u8()
            if first & 128:
                if first & 64:
                    cursor.get(3)
                else:
                    cursor.get(1)
        offset = cursor.at
        cursor.get(size)
        yield name, kind, size, offset
    raise ValueError("Tagged property list is unterminated")


def location_float_offsets(pkg: Package, exp: dict) -> dict[str, int]:
    if exp["size"] <= 0 or pkg.version != 95:
        raise ValueError("Only nonempty DX2 v95 actor exports can be patched")
    cursor = Cursor(pkg.data, exp["offset"], exp["offset"] + exp["size"])
    if exp["flags"] & HAS_STACK:
        node = cursor.ci()
        cursor.ci()
        cursor.u64()
        cursor.u32()
        if node:
            cursor.ci()
    locations = []
    for name, kind, size, offset in _tagged_entries(pkg, cursor):
        if name != "Location":
            continue
        if kind != 10:
            raise ValueError("Location is not a tagged FVector struct")
        nested = Cursor(pkg.data, offset, offset + size)
        parts = {}
        for subname, subkind, subsize, suboffset in _tagged_entries(pkg, nested):
            if subname in ("X", "Y", "Z"):
                if subkind != 4 or subsize != 4 or subname in parts:
                    raise ValueError("Location has ambiguous/non-float components")
                parts[subname] = suboffset
        if set(parts) != {"X", "Y", "Z"}:
            raise ValueError("Location has incomplete FVector components")
        locations.append(parts)
    if len(locations) != 1:
        raise ValueError("Actor does not have exactly one writable Location property")
    return locations[0]


def _check_float(value: object, *, label: str, limit=1_000_000.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or abs(number) > limit:
        raise ValueError(f"{label} is outside the supported range")
    return number


def audit_native_locations(source: Path, actors_file: Path) -> dict:
    """Source-only read audit: report exactly which actor exports can be patched.

    No preview transforms are assumed. This does NOT establish in-game load
    behavior; it inventories the currently decoded native Location format.
    """
    source = source.expanduser().resolve(strict=True)
    actors_file = actors_file.expanduser().resolve(strict=True)
    if source.suffix.casefold() != ".gmp":
        raise ValueError("Audit needs an original .gmp source")
    if actors_file.stat().st_size > 64_000_000:
        raise ValueError("Actor metadata exceeds safety limit")
    pkg = Package(source)
    actors_doc = json.loads(actors_file.read_text(encoding="utf8"))
    meta = actors_doc.get("meta", {})
    if pkg.version != 95 or meta.get("source_sha256") != _sha(pkg.data):
        raise ValueError("Actor catalog SHA/version does not match original DX2 GMP")
    if str(meta.get("source_map", "")).casefold() != source.name.casefold():
        raise ValueError("Actor catalog filename differs from original GMP")
    raw = actors_doc.get("actors", [])
    if not isinstance(raw, list) or len(raw) > 500000:
        raise ValueError("Invalid source actor list")
    duplicates = set()
    seen = set()
    reasons: dict[str, int] = {}
    examples: list[dict] = []
    supported = 0
    mesh_candidates = 0
    for actor in raw:
        if not isinstance(actor, dict):
            continue
        name = actor.get("name")
        if not isinstance(name, str):
            continue
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    for actor in raw:
        if not isinstance(actor, dict) or not isinstance(actor.get("name"), str):
            continue
        name = actor["name"]
        if actor.get("class") != "StaticMeshActor" or not actor.get("mesh"):
            continue
        mesh_candidates += 1
        reason = None
        export_id = actor.get("export")
        if name in duplicates:
            reason = "duplicate_actor_name"
        elif type(export_id) is not int or not 1 <= export_id <= len(pkg.exports):
            reason = "invalid_export_index"
        else:
            exp = pkg.exports[export_id - 1]
            if pkg.class_name(exp) != "StaticMeshActor" or exp["name"] != name:
                reason = "export_class_or_name_mismatch"
            else:
                try:
                    offsets = location_float_offsets(pkg, exp)
                    loc = actor.get("location")
                    if not isinstance(loc, list) or len(loc) != 3:
                        reason = "no_decoded_actor_location"
                    else:
                        for axis, expected in zip(("X", "Y", "Z"), loc):
                            number = _check_float(expected, label="source Location")
                            native = struct.unpack_from("<f", pkg.data, offsets[axis])[0]
                            if not math.isclose(native, number, abs_tol=SOURCE_TOLERANCE, rel_tol=0):
                                reason = "decoded_location_mismatch"
                                break
                except (ValueError, IndexError, struct.error):
                    reason = "unsupported_or_ambiguous_location_tags"
        if reason is None:
            supported += 1
        else:
            reasons[reason] = reasons.get(reason, 0) + 1
            if len(examples) < 30:
                examples.append({"actor": name, "export": export_id, "reason": reason})
    return {
        "schema": "DX2Ed-native-location-audit-v1",
        "source": str(source),
        "source_sha256": _sha(pkg.data),
        "package_version": pkg.version,
        "total_actor_records": len(raw),
        "rendered_static_mesh_candidates": mesh_candidates,
        "native_location_candidates": supported,
        "unsupported_candidates": mesh_candidates - supported,
        "reasons": dict(sorted(reasons.items())),
        "unsupported_examples": examples,
        "read_only": True,
        "game_verified": False,
        "notes": [
            "Supported means the original serialized Location is identifiable and matches metadata.",
            "Exporting still requires a pure translation-only editor draft with unchanged basis.",
            "This audit does NOT prove GMP in-game loadability or collision behavior."
        ],
    }


def plan_translation_changes(pkg: Package, actors_doc: dict, draft: dict) -> list[dict]:
    meta = actors_doc.get("meta", {})
    if pkg.version != 95:
        raise ValueError("Only Ion Storm v95 GMP maps are supported")
    if _sha(pkg.data) != meta.get("source_sha256"):
        raise ValueError("Actors metadata SHA does not match the selected original GMP")
    if pkg.path.name.casefold() != str(meta.get("source_map", "")).casefold():
        raise ValueError("Actors metadata names a different GMP")
    if draft.get("schema") != SCHEMA or draft.get("read_only_source") is not True:
        raise ValueError("Unsupported or untrusted editor draft")
    if draft.get("copies") or draft.get("property_edits"):
        raise ValueError("New objects, brushes and property changes need a native writer; export refused")
    moves = draft.get("moved")
    if not isinstance(moves, list) or len(moves) > MAX_MOVES:
        raise ValueError("Invalid move list")
    names = {}
    for actor in actors_doc.get("actors", []):
        if not isinstance(actor, dict) or not isinstance(actor.get("name"), str):
            continue
        if actor["name"] in names:
            raise ValueError("Duplicate actor names in source metadata")
        names[actor["name"]] = actor
    edits = []
    visited = set()
    for item in moves:
        if not isinstance(item, dict) or not isinstance(item.get("actor"), str):
            raise ValueError("Invalid moved actor record")
        name = item["actor"]
        if name in visited or name not in names:
            raise ValueError(f"Duplicate or unrecognized actor in draft: {name}")
        visited.add(name)
        actor = names[name]
        if actor.get("class") != "StaticMeshActor" or not actor.get("mesh"):
            raise ValueError(f"Only existing rendered StaticMeshActors can be translated: {name}")
        export_id = actor.get("export")
        if type(export_id) is not int or not 1 <= export_id <= len(pkg.exports):
            raise ValueError(f"Invalid export index for {name}")
        exp = pkg.exports[export_id - 1]
        if pkg.class_name(exp) != actor["class"] or exp["name"] != name:
            raise ValueError(f"Original export identity does not match {name}")
        values = item.get("transform")
        if not isinstance(values, list) or len(values) != 12:
            raise ValueError(f"Invalid Godot transform on {name}")
        transform = [_check_float(v, label="transform") for v in values]
        # Writer accepts TRANSLATION ONLY. Rotated/scaled editor previews
        # cannot silently lose their basis changes.
        original = {
            "rotation": actor.get("rotation", [0, 0, 0]),
            "x": actor["location"][0],
            "y": actor["location"][1],
            "z": actor["location"][2],
        }
        expected_matrix = actor_matrix(original)
        expected_basis = [
            expected_matrix[0], expected_matrix[1], expected_matrix[2],
            expected_matrix[4], expected_matrix[5], expected_matrix[6],
            expected_matrix[8], expected_matrix[9], expected_matrix[10],
        ]
        if any(abs(x-y) > BASIS_TOLERANCE for x, y in zip(transform[:9], expected_basis)):
            raise ValueError(
                f"{name} has edited rotation/scale or an unverified preview correction; "
                "native translation-only export refused"
            )
        xyz = (
            _check_float(transform[9] / SCALE, label="native X"),
            _check_float(transform[11] / SCALE, label="native Y"),
            _check_float(transform[10] / SCALE, label="native Z"),
        )
        original_xyz = tuple(_check_float(v, label="original actor location") for v in actor["location"])
        offsets = location_float_offsets(pkg, exp)
        for component, before in zip(("X", "Y", "Z"), original_xyz):
            serialized = struct.unpack_from("<f", pkg.data, offsets[component])[0]
            if not math.isclose(serialized, before, abs_tol=SOURCE_TOLERANCE, rel_tol=0):
                raise ValueError(f"{name} Location.{component} differs from source metadata")
        edits.append({
            "actor": name, "export": export_id, "offsets": offsets,
            "before": list(original_xyz), "after": list(xyz),
        })
    if not edits:
        raise ValueError("No existing static mesh actor translations to export")
    if not any(any(abs(float(a) - float(b)) > 0.00001 for a, b in zip(entry["before"], entry["after"])) for entry in edits):
        raise ValueError("Draft contains no meaningful native Location changes")
    return edits


def apply_location_plan(original: bytes, edits: list[dict]) -> bytes:
    buffer = bytearray(original)
    touched = set()
    for edit in edits:
        for label, value in zip(("X", "Y", "Z"), edit["after"]):
            offset = edit["offsets"][label]
            if offset in touched or offset < 0 or offset + 4 > len(buffer):
                raise ValueError("Overlapping or out-of-bounds GMP location fields")
            touched.add(offset)
            struct.pack_into("<f", buffer, offset, value)
    result = bytes(buffer)
    for pos, (before, after) in enumerate(zip(original, result)):
        if before != after and not any(start <= pos < start+4 for start in touched):
            raise ValueError("Unexpected modification outside approved serialized Location fields")
    return result


def export_translation_copy(source: Path, actors_file: Path, draft_file: Path,
                            output: Path, *, dry_run=False) -> dict:
    source = source.expanduser().resolve(strict=True)
    actors_file = actors_file.expanduser().resolve(strict=True)
    draft_file = draft_file.expanduser().resolve(strict=True)
    output = output.expanduser().resolve()
    if source.suffix.casefold() != ".gmp" or output.suffix.casefold() != ".gmp":
        raise ValueError("Both source and output must have a .gmp extension")
    if output.name.casefold() != source.name.casefold():
        raise ValueError("Output map must retain the original GMP filename for game testing")
    if output == source or source.parent == output.parent or source.parent in output.parents:
        raise ValueError("Save As must target a separate folder OUTSIDE the retail Maps directory")
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing map copy")
    if Path(draft_file).stat().st_size > 16_000_000:
        raise ValueError("Draft exceeds safety limit")
    actors_doc = json.loads(actors_file.read_text(encoding="utf8"))
    draft = json.loads(draft_file.read_text(encoding="utf8"))
    if Path(str(draft.get("map_cache", ""))).resolve() != actors_file.parent:
        raise ValueError("Draft belongs to a different DX2Ed map cache")
    pkg = Package(source)
    edits = plan_translation_changes(pkg, actors_doc, draft)
    modified = apply_location_plan(pkg.data, edits)
    summary = {
        "schema": "DX2Ed-native-save-as-experiment-v1",
        "game_verified": False,
        "status": "dry-run" if dry_run else "written-unverified",
        "source": str(source),
        "output": str(output),
        "source_sha256": _sha(pkg.data),
        "output_sha256": _sha(modified),
        "same_package_length": len(pkg.data) == len(modified),
        "translated_existing_actors": [
            {k: entry[k] for k in ("actor", "export", "before", "after")}
            for entry in edits
        ],
        "warnings": [
            "EXPERIMENTAL: Not tested inside retail Deus Ex: Invisible War.",
            "Only existing static mesh actors' serialized Location float fields are changed.",
            "No brushes, geometry, collision, rotation, scale or new actors are written.",
            "Never replace original game files without a verified backup and an isolated test install.",
        ],
    }
    if dry_run:
        return summary

    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = output.with_suffix(".dx2ed-manifest.json")
    if manifest.exists():
        raise FileExistsError("A previous DX2Ed save manifest already exists at output location")
    try:
        with output.open("xb") as handle:
            handle.write(modified)
        check = Package(output)
        if check.version != pkg.version or check.table_counts != pkg.table_counts or check.guid != pkg.guid:
            raise ValueError("Output package header or identity was altered")
        if len(check.data) != len(pkg.data) or _sha(check.data) != _sha(modified):
            raise ValueError("Output byte-for-byte verification failed")
        for entry in edits:
            exp = check.exports[entry["export"]-1]
            offsets = location_float_offsets(check, exp)
            for field, expected in zip(("X", "Y", "Z"), entry["after"]):
                actual = struct.unpack_from("<f", check.data, offsets[field])[0]
                if not math.isclose(actual, expected, abs_tol=0.01, rel_tol=0):
                    raise ValueError("Patched Location did not survive package reparse")
        manifest.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf8")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True, help="Original v95 GMP")
    p.add_argument("--actors", type=Path, required=True, help="DX2Ed actors.json for this GMP")
    p.add_argument("--draft", type=Path, help="Saved DX2Ed draft JSON")
    p.add_argument("--output", type=Path, help="Copy in an isolated folder")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--audit", action="store_true", help="Read-only audit of source Location fields")
    args = p.parse_args(argv)
    try:
        if args.audit:
            result = audit_native_locations(args.source, args.actors)
        else:
            if args.draft is None or args.output is None:
                p.error("Save As requires both --draft and --output; use --audit to inspect sources")
            result = export_translation_copy(
                args.source, args.actors, args.draft, args.output, dry_run=args.dry_run
            )
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
