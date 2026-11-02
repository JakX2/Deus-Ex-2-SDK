#!/usr/bin/env python3
"""DX2 GameSys float32/int32 in-memory dual-serializer parity gate.

Requires an original v95 DX2 GMP, its exact SHA-256, original actor export
number/name, unique existing GameSys property ID, exact original numeric
value and proposed replacement. Original source is never modified and the
edited GMP is never written by this tool.

The two independent paths are:
  * DX2SDK's tagged-actor scanner, which identifies a four-byte payload
    by its original encoded ID/version/offset and patches only those bytes.
  * MIT T3SDK's ActorEdit.set_block + PackageWriter, which reserializes
    the original actor and GMP.
Only a FULL-PACKAGE byte-for-byte match counts as success.

This is a binary serialization experiment, NOT a gameplay-safe authoring
feature or permission to install edited maps. Arrays, structs, names,
references, bools, byte-sized values and all property insertions are denied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_package_roundtrip import inspect_noop, _parse_both, _validate_input
from dx2_gamesys_audit import scan_dx2_gamesys
from dx2inspect import HAS_STACK
from upkgwrite import ActorEdit, PackageWriter, first_difference

SCHEMA = "DX2Ed-Gamesys-scalar-dual-writer-v1"
KIND = {"float": (0x0010, "<f"), "int": (0x0020, "<i")}
MAX_FLOAT = 1_000_000.0


def scalar_bytes(kind: str, value: object) -> bytes:
    if kind == "int":
        if type(value) is not int or not -(1 << 31) <= value < (1 << 31):
            raise ValueError("Int GameSys value must be an exact signed int32")
        return struct.pack("<i", value)
    if kind != "float" or type(value) not in (int, float):
        raise ValueError("Float GameSys value must be a finite number")
    number = float(value)
    if not math.isfinite(number) or abs(number) > MAX_FLOAT:
        raise ValueError("Float GameSys value outside finite supported range")
    packed = struct.pack("<f", number)
    if not math.isfinite(struct.unpack("<f", packed)[0]):
        raise ValueError("Float32 value overflow")
    return packed


def compare_gamesys_scalar(
    source: Path, *, source_sha256: str, actor_export: int,
    actor_name: str, property_id: int, kind: str, expected: object,
    replacement: object,
) -> dict:
    source = _validate_input(source)
    if (not isinstance(source_sha256, str) or len(source_sha256) != 64
            or any(c not in "0123456789abcdef" for c in source_sha256)):
        raise ValueError("Supply the lowercase original source SHA-256")
    before = source.read_bytes()
    actual_sha = hashlib.sha256(before).hexdigest()
    if actual_sha != source_sha256:
        raise ValueError("Original source GMP SHA-256 mismatch")
    if type(actor_export) is not int or actor_export < 1:
        raise ValueError("Actor export must be a positive one-based number")
    if type(property_id) is not int or not 0 < property_id < 65536:
        raise ValueError("GameSys property ID must be a 16-bit positive integer")
    if not isinstance(actor_name, str) or not actor_name.strip():
        raise ValueError("Original actor name is required")
    if kind not in KIND:
        raise ValueError("Only existing int32 and float32 GameSys values are supported")
    raw_expected = scalar_bytes(kind, expected)
    raw_after = scalar_bytes(kind, replacement)
    if raw_after == raw_expected:
        raise ValueError("Proposed edit is identical at the original source byte level")

    # A fully byte-exact no-op reconstruction is the baseline acceptance gate.
    baseline, reconstructed = inspect_noop(source)
    if reconstructed != before or baseline["source_sha256"] != actual_sha:
        raise ValueError("Original package failed no-op writer baseline")

    t3, dx2 = _parse_both(source, before)
    if actor_export > len(dx2.exports):
        raise ValueError("Actor export not found in original map")
    source_exp = dx2.exports[actor_export - 1]
    t3exp = t3.exports[actor_export - 1]
    if (source_exp["name"] != actor_name or t3exp.name != actor_name
            or source_exp["size"] <= 0 or not source_exp["flags"] & HAS_STACK):
        raise ValueError("Original actor export/name/state-frame identity mismatch")

    records, _ = scan_dx2_gamesys(dx2, source_exp)
    candidates = [b for b in records if b["property_id"] == property_id]
    if len(candidates) != 1:
        raise ValueError("Property must exist exactly once in the original actor")
    record = candidates[0]
    expected_type_word, encoding = KIND[kind]
    if (record["encoding_code"] != expected_type_word
            or record["runtime_flag"] or record["payload_bytes"] != 4):
        raise ValueError("Original GameSys block is not a unique non-runtime four-byte scalar of the requested type")
    at = record["payload_offset"]
    if (at < source_exp["offset"] or at + 4 > source_exp["offset"] + source_exp["size"]
            or before[at:at + 4] != raw_expected
            or hashlib.sha256(raw_expected).hexdigest() != record["payload_sha256"]):
        raise ValueError("Pinned scalar value does not match original actor payload")

    writer = PackageWriter(t3)
    actor = ActorEdit(writer, t3exp)
    matches = [b for b in actor.layout.blocks if b.id & 0xffff == property_id]
    if (len(matches) != 1 or matches[0].id != record["encoded_id"]
            or matches[0].version != record["version"]
            or matches[0].data != raw_expected):
        raise ValueError("T3SDK original actor block differs from independent DX2 reader")
    actor.set_block(property_id, raw_after, f"existing_{kind}_id_{property_id}")
    if not actor.commit():
        raise ValueError("GameSys actor serializer did not commit existing scalar")
    edited = writer.write()

    # The independent DX2 path does not use T3SDK's layout or writer.
    patched = before[:at] + raw_after + before[at + 4:]
    if edited != patched:
        raise ValueError(
            f"Independent GameSys serializers disagree at byte "
            f"{first_difference(edited, patched)}; output blocked"
        )
    if len(edited) != len(before) or writer.added_names or writer.added_exports:
        raise ValueError("GameSys edit unexpectedly grew package tables or changed size")
    changed = [i for i, (a, b) in enumerate(zip(edited, before)) if a != b]
    if not changed or any(not at <= p < at + 4 for p in changed):
        raise ValueError("GameSys edit modified bytes outside the original scalar value")
    if hashlib.sha256(source.read_bytes()).hexdigest() != actual_sha:
        raise ValueError("Original GMP source changed during in-memory test")

    return {
        "schema": SCHEMA, "status": "in-memory-match-only",
        "source_map": source.name, "original_sha256": actual_sha,
        "actor_export": actor_export, "actor": actor_name,
        "actor_class": dx2.class_name(source_exp),
        "property_id": property_id,
        "encoded_property_id": record["encoded_id"],
        "property_version": record["version"],
        "kind": kind,
        "original_value_bytes": raw_expected.hex(),
        "proposed_value_bytes": raw_after.hex(),
        "original_payload_sha256": record["payload_sha256"],
        "original_payload_offset": at,
        "changed_bytes": len(changed),
        "reconstructed_sha256": hashlib.sha256(edited).hexdigest(),
        "full_package_byte_match": True,
        "original_source_modified": False,
        "edited_package_written": False,
        "native_gamesys_save_enabled": False,
        "runtime_verified": False,
        "notes": [
            "One pre-existing fixed-width GameSys scalar was modified in memory.",
            "Upstream T3SDK ActorEdit and independent DX2 bytes agree over the full GMP.",
            "This does NOT establish valid gameplay semantics or in-game compatibility.",
        ],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--actor-export", type=int, required=True)
    p.add_argument("--actor-name", required=True)
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--kind", choices=("int", "float"), required=True)
    p.add_argument("--expect", required=True)
    p.add_argument("--replace", required=True)
    args = p.parse_args(argv)
    try:
        convert = int if args.kind == "int" else float
        report = compare_gamesys_scalar(
            args.source, source_sha256=args.source_sha256,
            actor_export=args.actor_export, actor_name=args.actor_name,
            property_id=args.property_id, kind=args.kind,
            expected=convert(args.expect), replacement=convert(args.replace))
        print(json.dumps(report, indent=2))
        return 0
    except (OSError, ValueError, TypeError, IndexError, EOFError, OverflowError, struct.error) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
