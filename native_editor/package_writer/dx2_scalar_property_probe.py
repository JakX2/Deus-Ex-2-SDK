#!/usr/bin/env python3
"""Read-only T3SDK vs DX2 comparison for EXISTING 32-bit actor scalar tags.

This probes strict native Unreal tagged int32/float32 fields in a user-owned
DX2 v95 GMP. It never creates an edited GMP, overwrites source files, inserts
missing properties, changes actor names, or edits nested/array/GameSys data.

It performs the same one-field edit in memory via:
  A: independent DX2 tagged-property byte-offset reader + 4-byte replacement
  B: upstream T3SDK ActorEdit/PackageWriter object serializer
and refuses unless BOTH complete package byte streams are identical.

The property's gameplay meaning is NOT verified; this is a serialization
compatibility experiment, not permission to install edited packages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BACKEND = ROOT / "native_editor" / "godot_editor" / "backend"
for folder in (HERE, BACKEND):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from dx2_package_roundtrip import _parse_both, _validate_input  # noqa: E402
from dx2_native_save_as import _tagged_entries  # noqa: E402
from dx2inspect import Cursor, HAS_STACK  # noqa: E402
from upkgwrite import ActorEdit, PackageWriter, first_difference  # noqa: E402

SCHEMA = "DX2Ed-T3SDK-scalar-property-parity-v1"
MAX_ABS_FLOAT = 1000000.0
PT_INT = 2
PT_FLOAT = 4
VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _value_bytes(kind: str, value: object) -> bytes:
    if kind == "int":
        if type(value) is not int or not -(2 ** 31) <= value < 2 ** 31:
            raise ValueError("Integer value must be an int32 (booleans not accepted)")
        return struct.pack("<i", value)
    if kind != "float" or isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Float value must be finite and numeric")
    number = float(value)
    if not math.isfinite(number) or abs(number) > MAX_ABS_FLOAT:
        raise ValueError("Float value out of supported range")
    packed = struct.pack("<f", number)
    if not math.isfinite(struct.unpack("<f", packed)[0]):
        raise ValueError("Float32 value overflows")
    return packed


def _native_scalar_offset(pkg, exp: dict, property_name: str, expected_type: int) -> int:
    """Independently identify a single original top-level scalar tag payload."""
    if exp["size"] <= 0 or not (exp["flags"] & HAS_STACK):
        raise ValueError("Selected export is not a serialized state-frame actor")
    c = Cursor(pkg.data, exp["offset"], exp["offset"] + exp["size"])
    node = c.ci()
    c.ci()
    c.u64()
    c.u32()
    if node:
        c.ci()
    matching = [
        (kind, size, offset)
        for name, kind, size, offset in _tagged_entries(pkg, c)
        if name == property_name
    ]
    if len(matching) != 1:
        raise ValueError("The original actor must have exactly one existing tagged property with this name")
    kind, size, offset = matching[0]
    if kind != expected_type or size != 4 or offset < exp["offset"] or offset + 4 > exp["offset"] + exp["size"]:
        raise ValueError("Selected property is not a standalone 4-byte int32/float32 field")
    return offset


def compare_scalar(
    source: Path, actor_export: int, actor_name: str, property_name: str,
    kind: str, expected: object, replacement: object, *,
    source_sha256: str,
) -> dict:
    """Compare two independent serializers; NEVER saves the edited bytes."""
    source = _validate_input(source)
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("Must supply exact lowercase original GMP SHA-256")
    original = source.read_bytes()
    actual_hash = hashlib.sha256(original).hexdigest()
    if actual_hash != source_sha256:
        raise ValueError("Original GMP SHA-256 does not match requested source")
    if type(actor_export) is not int or actor_export <= 0:
        raise ValueError("actor_export must be a positive one-based export index")
    if not all(isinstance(x, str) and VALID_IDENTIFIER.fullmatch(x)
               for x in (actor_name, property_name)):
        raise ValueError("Actor and property must be exact simple source identifiers")
    if kind not in ("int", "float"):
        raise ValueError("Supported source scalar type must be int or float")
    wanted_type = PT_INT if kind == "int" else PT_FLOAT
    expected_bytes = _value_bytes(kind, expected)
    replacement_bytes = _value_bytes(kind, replacement)
    if expected_bytes == replacement_bytes:
        raise ValueError("No change in the original scalar float32/int32 bytes")
    t3, dx2 = _parse_both(source, original)
    if actor_export > len(dx2.exports):
        raise ValueError("Actor export number is outside original table")
    exp = dx2.exports[actor_export - 1]
    if exp["name"] != actor_name:
        raise ValueError("Original export name does not match selected actor")
    t3exp = t3.exports[actor_export - 1]
    if t3exp.name != actor_name or not t3exp.flags & HAS_STACK:
        raise ValueError("T3SDK export identity or actor state frame differs")
    absolute = _native_scalar_offset(dx2, exp, property_name, wanted_type)
    if original[absolute:absolute + 4] != expected_bytes:
        raise ValueError("Pinned original scalar value does not match its source bytes")

    # Independent source-byte editor. Changes only four original bytes.
    direct = bytearray(original)
    direct[absolute:absolute + 4] = replacement_bytes

    # T3SDK structured actor serializer must return exactly the same entire
    # package. Editing an existing tag does not insert names or change length.
    writer = PackageWriter(t3)
    actor = ActorEdit(writer, t3exp)
    matches = [tag for tag in actor.layout.props.tags if tag.name == property_name]
    if len(matches) != 1:
        raise ValueError("Structured parser sees duplicate or missing scalar tags")
    tag = matches[0]
    if tag.ptype != wanted_type or len(tag.value) != 4 or tag.array_raw:
        raise ValueError("T3SDK disagrees on scalar type, size or array index")
    if tag.value != expected_bytes:
        raise ValueError("T3SDK disagrees with independent DX2 original scalar value")
    if kind == "float":
        actor.set_tagged_float(property_name, struct.unpack("<f", replacement_bytes)[0])
    else:
        tag.value = replacement_bytes
        actor.changes.append(property_name + ": int32 replacement (in-memory only)")
    if not actor.commit():
        raise ValueError("Structured actor serializer made no change")
    rebuilt = writer.write()
    if rebuilt != bytes(direct):
        offset = first_difference(rebuilt, bytes(direct))
        raise ValueError(f"Independent actor serializers disagree at byte {offset}")
    if len(rebuilt) != len(original) or writer.added_exports or writer.added_names:
        raise ValueError("Unexpected package growth or source table changes")
    changes = [i for i, (a, b) in enumerate(zip(original, rebuilt)) if a != b]
    if not changes or any(not absolute <= p < absolute + 4 for p in changes):
        raise ValueError("Unexpected changes outside exact original property bytes")
    if hashlib.sha256(source.read_bytes()).hexdigest() != actual_hash:
        raise ValueError("Source changed during in-memory property comparison")
    return {
        "schema": SCHEMA, "status": "in-memory-match-only",
        "source_filename": source.name, "source_sha256": actual_hash,
        "actor_export": actor_export, "actor_name": actor_name,
        "actor_class": dx2.class_name(exp),
        "property": property_name, "scalar_type": kind,
        "field_absolute_offset": absolute,
        "original_bytes_hex": expected_bytes.hex(),
        "replacement_bytes_hex": replacement_bytes.hex(),
        "changed_bytes": len(changes),
        "source_bytes": len(original),
        "edited_in_memory_sha256": hashlib.sha256(rebuilt).hexdigest(),
        "serializers_agree_byte_for_byte": True,
        "source_modified": False,
        "edited_package_written": False,
        "runtime_game_verified": False,
        "gameplay_property_semantics_verified": False,
        "notes": [
            "Only one existing top-level tagged four-byte int or float is tested.",
            "Unknown fields, actor state frame, native tails and GameSys data stay byte-identical.",
            "This is NOT a native Save As, and does not validate runtime game behavior.",
        ],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--source-sha256", required=True, help="SHA256 of original GMP")
    p.add_argument("--actor-export", type=int, required=True, help="One-based original export index")
    p.add_argument("--actor-name", required=True)
    p.add_argument("--property", required=True)
    p.add_argument("--kind", choices=("int", "float"), required=True)
    p.add_argument("--expect", required=True)
    p.add_argument("--replace", required=True)
    args = p.parse_args(argv)
    try:
        scalar = int if args.kind == "int" else float
        report = compare_scalar(
            args.source, args.actor_export, args.actor_name,
            args.property, args.kind, scalar(args.expect),
            scalar(args.replace), source_sha256=args.source_sha256,
        )
        print(json.dumps(report, indent=2))
        return 0
    except (OSError, ValueError, OverflowError, IndexError, EOFError, struct.error) as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
