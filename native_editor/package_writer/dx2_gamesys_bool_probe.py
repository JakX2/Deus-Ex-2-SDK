#!/usr/bin/env python3
"""DX2 existing GameSys one-byte Boolean exact parity and isolated Save-As.

A *separate* experimental gate. Does NOT modify the previously verified
float32/int32 writer, nor enable Godot Inspector edits. Requires an exact
original v95 DX2 GMP SHA, one-based export and exact actor name, a unique
pre-existing non-runtime Boolean GameSys block (type 0x0080), and exact
original 00/01 bytes. All whole-package bytes must match independent DX2
byte-offset patching and the MIT T3SDK ActorEdit serializer.

No package insertion, class spawning, IBD changes, other type writes, or
in-place edits. The optional --output must be same map name in an
isolated directory and is explicitly NOT verified to load in-game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_package_roundtrip import _parse_both, _validate_input, inspect_noop
from dx2_gamesys_audit import scan_dx2_gamesys
from dx2inspect import HAS_STACK
from upkg import Package as T3Package
from upkgwrite import ActorEdit, PackageWriter, first_difference

SCHEMA = "DX2Ed-Gamesys-existing-bool-parity-v1"
ENCODING_BOOL = 0x0080
MAX_SOURCE_SIZE = 256 * 1024 * 1024


def exact_bool_byte(value: object) -> bytes:
    if type(value) is not bool:
        raise ValueError("Boolean GameSys value must be exactly true or false")
    return b"\x01" if value else b"\x00"


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compare_existing_bool(
    source: Path, *, source_sha256: str, actor_export: int,
    actor_name: str, property_id: int, expected: bool, replacement: bool,
) -> dict:
    source = _validate_input(source)
    if (not isinstance(source_sha256, str) or len(source_sha256) != 64
            or any(c not in "0123456789abcdef" for c in source_sha256)):
        raise ValueError("Original GMP requires exact lowercase SHA-256")
    if type(actor_export) is not int or actor_export < 1:
        raise ValueError("Actor export must be one-based positive integer")
    if type(property_id) is not int or not (0 < property_id <= 65535):
        raise ValueError("Property must be positive 16-bit GameSys ID")
    if not isinstance(actor_name, str) or not actor_name.strip():
        raise ValueError("Original actor name is required")
    old, new = exact_bool_byte(expected), exact_bool_byte(replacement)
    if old == new:
        raise ValueError("Proposed Boolean value is identical to original")
    raw = source.read_bytes()
    if _hash(raw) != source_sha256:
        raise ValueError("Original GMP SHA-256 mismatch")
    baseline, no_op = inspect_noop(source)
    if no_op != raw or baseline["source_sha256"] != source_sha256:
        raise ValueError("Original GMP failed exact no-op package reconstruction")
    t3, dx2 = _parse_both(source, raw)
    if actor_export > len(dx2.exports):
        raise ValueError("Original actor export index not found")
    a, b = dx2.exports[actor_export - 1], t3.exports[actor_export - 1]
    if (a["name"] != actor_name or b.name != actor_name
            or a["size"] <= 0 or not (a["flags"] & HAS_STACK)):
        raise ValueError("Original state-frame actor export/name mismatch")
    records, _ = scan_dx2_gamesys(dx2, a)
    hits = [x for x in records if x["property_id"] == property_id]
    if len(hits) != 1:
        raise ValueError("Original actor must contain exactly one GameSys property with this ID")
    block = hits[0]
    offset = block["payload_offset"]
    if (block["encoding_code"] != ENCODING_BOOL
            or block["type_word"] != ENCODING_BOOL
            or block["runtime_flag"]
            or block["payload_bytes"] != 1):
        raise ValueError("Existing GameSys property is not an authored one-byte Boolean")
    if (offset < a["offset"] or offset + 1 > a["offset"] + a["size"]
            or raw[offset:offset+1] != old
            or block["payload_sha256"] != _hash(old)):
        raise ValueError("Pinned original Boolean value or payload offset mismatch")

    # MIT T3SDK's actual structured serializer. The original game data is
    # strictly re-encoded with all unrecognized bytes preserved.
    writer = PackageWriter(t3)
    edit = ActorEdit(writer, b)
    matches = [x for x in edit.layout.blocks if (x.id & 65535) == property_id]
    if (len(matches) != 1
            or matches[0].id != block["encoded_id"]
            or matches[0].version != block["version"]
            or matches[0].data != old):
        raise ValueError("T3SDK and independent DX2 actor Boolean block disagree")
    edit.set_block(property_id, new, f"existing_bool_{property_id}")
    if not edit.commit():
        raise ValueError("Structured GameSys Boolean edit was not committed")
    built = writer.write()

    # This second serializer patches exactly the independently scanned
    # original one-byte payload and never calls PackageWriter.
    direct = raw[:offset] + new + raw[offset+1:]
    if built != direct:
        raise ValueError(f"Independent Boolean serializers disagree at byte {first_difference(built, direct)}")
    changes = [i for i, (x, y) in enumerate(zip(raw, built)) if x != y]
    if changes != [offset] or len(built) != len(raw):
        raise ValueError("Boolean edit changed something beyond its original one-byte payload")
    if writer.added_exports or writer.added_names:
        raise ValueError("Boolean edit unexpectedly expanded original package tables")
    if _hash(source.read_bytes()) != source_sha256:
        raise ValueError("Original GMP changed during in-memory comparison")
    return {
        "schema": SCHEMA, "status": "in-memory-exact-parity",
        "source_map": source.name, "original_sha256": source_sha256,
        "actor_export": actor_export, "actor": actor_name,
        "actor_class": dx2.class_name(a),
        "property_id": property_id, "encoded_property_id": block["encoded_id"],
        "property_version": block["version"], "kind": "bool",
        "original_value": expected, "replacement_value": replacement,
        "original_value_bytes": old.hex(), "replacement_value_bytes": new.hex(),
        "original_payload_offset": offset, "original_payload_sha256": _hash(old),
        "changed_byte_offsets": changes, "changed_bytes": 1,
        "source_bytes": len(raw), "reconstructed_sha256": _hash(built),
        "independent_full_package_byte_match": True,
        "source_modified": False, "edited_package_written": False,
        "game_runtime_verified": False, "gameplay_effect_verified": False,
        "native_godot_gamesys_write_enabled": False,
    }


def save_isolated_bool(
    source: Path, output: Path, *, source_sha256: str, actor_export: int,
    actor_name: str, property_id: int, expected: bool, replacement: bool,
) -> dict:
    """Standalone experimental copy, NEVER a normal Godot Save As."""
    source = _validate_input(source)
    output = Path(output).expanduser().resolve()
    if (output.suffix.lower() != ".gmp"
            or output.name.casefold() != source.name.casefold()
            or output == source or output.parent == source.parent
            or source.parent in output.parents):
        raise ValueError("Output must be a separate folder, outside source Maps, retaining exact original map basename")
    report_path = output.with_suffix(".dx2ed-gamesys-bool.json")
    if output.exists() or report_path.exists():
        raise FileExistsError("Refusing to overwrite existing Boolean map or verification report")
    report = compare_existing_bool(
        source, source_sha256=source_sha256, actor_export=actor_export,
        actor_name=actor_name, property_id=property_id,
        expected=expected, replacement=replacement)
    original = source.read_bytes()
    offset = report["original_payload_offset"]
    old, new = exact_bool_byte(expected), exact_bool_byte(replacement)
    if (_hash(original) != source_sha256
            or original[offset:offset+1] != old):
        raise ValueError("Original source changed after Boolean dual writer check")
    candidate = original[:offset] + new + original[offset+1:]
    if _hash(candidate) != report["reconstructed_sha256"]:
        raise ValueError("Edited GMP differs from independently verified Boolean image")
    checked = T3Package(source, data=candidate)
    unmodified = T3Package(source, data=original)
    if (checked.guid != unmodified.guid or checked.names != unmodified.names
            or len(checked.exports) != len(unmodified.exports)):
        raise ValueError("Edited GMP altered package header or tables")
    if _hash(source.read_bytes()) != source_sha256:
        raise ValueError("Original source changed before isolated Boolean Save As")
    output.parent.mkdir(parents=True, exist_ok=True)
    created_output = False
    created_report = False
    try:
        with output.open("xb") as f:
            created_output = True
            f.write(candidate)
        actual = output.read_bytes()
        if actual != candidate:
            raise ValueError("Isolated Boolean output did not match verified candidate")
        _, parsed = _parse_both(output, actual)
        exp = parsed.exports[actor_export-1]
        hits, _ = scan_dx2_gamesys(parsed, exp)
        selected = [x for x in hits if x["property_id"] == property_id]
        if (exp["name"] != actor_name or len(selected) != 1
                or selected[0]["encoded_id"] != report["encoded_property_id"]
                or selected[0]["version"] != report["property_version"]
                or selected[0]["payload_offset"] != offset
                or actual[offset:offset+1] != new):
            raise ValueError("Edited disk GMP failed independent DX2 GameSys Boolean block verification")
        report.update({
            "status": "isolated-boolean-gmp-written-runtime-unverified",
            "output": str(output), "output_sha256": _hash(actual),
            "edited_package_written": True, "game_runtime_verified": False,
        })
        with report_path.open("x", encoding="utf8") as f:
            created_report = True
            json.dump(report, f, indent=2)
            f.write("\n")
        return report
    except Exception:
        if created_report:
            report_path.unlink(missing_ok=True)
        if created_output:
            output.unlink(missing_ok=True)
        raise


def _bool_arg(raw: str) -> bool:
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise argparse.ArgumentTypeError("Use only true or false, lowercase")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--actor-export", type=int, required=True)
    parser.add_argument("--actor-name", required=True)
    parser.add_argument("--property-id", type=int, required=True)
    parser.add_argument("--expect", type=_bool_arg, required=True)
    parser.add_argument("--replace", type=_bool_arg, required=True)
    parser.add_argument("--output", type=Path, help="Isolated experimental GMP only; not retail Maps")
    args = parser.parse_args(argv)
    try:
        options = dict(source_sha256=args.source_sha256,
                       actor_export=args.actor_export, actor_name=args.actor_name,
                       property_id=args.property_id, expected=args.expect,
                       replacement=args.replace)
        if args.output is None:
            result = compare_existing_bool(args.source, **options)
        else:
            result = save_isolated_bool(args.source, args.output, **options)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError, IndexError, EOFError, struct.error) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
