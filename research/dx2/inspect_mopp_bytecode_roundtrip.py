#!/usr/bin/env python3
"""Read-only, byte-exact DX2 Level MOPP instruction/envelope no-op reassembly.

All reachable instruction operands are decoded with source-observed widths;
unvisited bytes, if present, are retained verbatim. No edited collision,
runtime Havok contacts, physics materials, new MOPP builder, or GMP writes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import inspect_level_mopp_triangle_tree as mopp

SCHEMA = "DX2SDK-MOPP-source-instruction-noop-roundtrip-v1"
MAX_RECORDS = mopp.MAX_INSTRUCTION_STATES
MAX_GAPS = 300_000


def _operand_spec(op: int) -> tuple[tuple[int, ...], str]:
    """Big-endian source-operand widths. Uninterpreted bytes stay opaque."""
    if 0x01 <= op <= 0x04: return ((1, 1, 1), "forward")
    if op == 0x05: return ((1,), "jump8")
    if op == 0x06: return ((2,), "jump16")
    if op == 0x09: return ((1,), "addbase8")
    if op == 0x0a: return ((2,), "addbase16")
    if op == 0x0b: return ((4,), "setbase32")
    if 0x10 <= op <= 0x1c: return ((1, 1, 1), "split8plus3")
    if 0x20 <= op <= 0x22: return ((1, 1), "split8plus2")
    if 0x23 <= op <= 0x25: return ((1, 1, 2, 2), "twojump16")
    if 0x26 <= op <= 0x28: return ((1, 1), "forward")
    if 0x29 <= op <= 0x2b: return ((1, 1, 1, 1, 1, 1), "forward")
    if 0x30 <= op <= 0x4f: return ((), "leaf_inline")
    if 0x50 <= op <= 0x52: return ((op - 0x50 + 1,), "leaf_imm")
    raise ValueError(f"Unknown reachable MOPP opcode 0x{op:02x}")


def _decode(code: bytes, pc: int) -> dict:
    if not 0 <= pc < len(code):
        raise ValueError("Instruction pointer outside MOPP code")
    op = code[pc]
    widths, role = _operand_spec(op)
    size = 1 + sum(widths)
    if pc + size > len(code):
        raise ValueError("Truncated reachable MOPP operand")
    values, pos = [], pc + 1
    for width in widths:
        values.append(int.from_bytes(code[pos:pos+width], "big"))
        pos += width
    emit = bytes([op]) + b"".join(value.to_bytes(width, "big")
                                   for value, width in zip(values, widths))
    if emit != code[pc:pc+size]:
        raise ValueError("Reachable MOPP instruction re-emission mismatch")
    return {"pc": pc, "opcode": op, "size": size, "role": role,
            "operands": values, "emitted": emit}


def inspect_code_roundtrip(code: bytes, triangle_count: int) -> dict:
    """Independently check instruction spans against PR28's symbolic CFG."""
    reference = mopp.trace_mopp_code(code, triangle_count)
    if not isinstance(code, bytes):
        raise ValueError("Original MOPP code must be bytes")
    decoded, states, leaves = {}, set(), []
    claimed = bytearray(len(code))
    pending = [(0, 0)]
    while pending:
        pc, base = pending.pop()
        if (pc, base) in states:
            continue
        if len(states) >= MAX_RECORDS:
            raise ValueError("Excessive reachable MOPP states")
        states.add((pc, base))
        record = decoded.get(pc)
        if record is None:
            record = _decode(code, pc)
            for index in range(pc, pc + record["size"]):
                if claimed[index]:
                    raise ValueError(f"Overlapping reachable MOPP instructions at byte {index}")
                claimed[index] = 1
            decoded[pc] = record
        role, values = record["role"], record["operands"]
        end = pc + record["size"]
        if role == "forward":
            targets = [(end, base)]
        elif role in ("jump8", "jump16"):
            targets = [(end+values[0], base)]
        elif role in ("addbase8", "addbase16"):
            targets = [(end, base+values[0])]
        elif role == "setbase32":
            targets = [(end, values[0])]
        elif role == "split8plus3":
            targets = [(end, base), (end+values[2], base)]
        elif role == "split8plus2":
            targets = [(end, base), (end+values[1], base)]
        elif role == "twojump16":
            targets = [(end+values[2], base), (end+values[3], base)]
        elif role == "leaf_inline":
            leaves.append(base + record["opcode"] - 0x30)
            targets = []
        elif role == "leaf_imm":
            leaves.append(base + values[0])
            targets = []
        else:
            raise ValueError("Unknown MOPP control-flow role")
        for target, next_base in targets:
            if not pc < target < len(code):
                raise ValueError("Decoded MOPP jump target escapes stream")
            if not 0 <= next_base <= 0xffffffff:
                raise ValueError("Decoded MOPP output base escapes u32 range")
            pending.append((target, next_base))
    if (len(states) != reference["reachable_instruction_states"]
            or len(decoded) != reference["reachable_distinct_instruction_offsets"]
            or sorted(leaves) != reference["reachable_terminal_triangle_ids"]):
        raise ValueError("Reassembly graph disagrees with independent MOPP validator")
    reconstructed = bytearray(len(code))
    gaps, first_gap = [], None
    for i, used in enumerate(claimed):
        if not used:
            reconstructed[i] = code[i]
            if first_gap is None:
                first_gap = i
        elif first_gap is not None:
            gaps.append((first_gap, i))
            first_gap = None
    if first_gap is not None:
        gaps.append((first_gap, len(code)))
    if len(gaps) > MAX_GAPS:
        raise ValueError("Excessive unreachable MOPP byte ranges")
    for pc, record in sorted(decoded.items()):
        reconstructed[pc:pc+record["size"]] = record["emitted"]
    if bytes(reconstructed) != code:
        raise ValueError("MOPP no-op reassembly not byte-identical")
    roles = Counter(record["role"] for record in decoded.values())
    live_bytes = sum(claimed)
    return {
        "schema": SCHEMA,
        "code_sha256": hashlib.sha256(code).hexdigest(),
        "code_length_bytes": len(code),
        "reachable_instruction_states": len(states),
        "distinct_decoded_instruction_offsets": len(decoded),
        "reachable_instruction_bytes": live_bytes,
        "unvisited_bytes_preserved_opaque": len(code)-live_bytes,
        "unvisited_byte_span_count": len(gaps),
        "largest_unvisited_byte_span": max((b-a for a,b in gaps),default=0),
        "first_unvisited_spans": [{"start":a,"end":b} for a,b in gaps[:16]],
        "decoded_opcode_roles": dict(sorted(roles.items())),
        "reachable_triangle_leaves": len(leaves),
        "reassembled_code_sha256": hashlib.sha256(reconstructed).hexdigest(),
        "code_byte_identical": True,
        "control_flow_matches_original_decoder": True,
        "opaque_code_bytes_preserved_uninterpreted": True,
        "original_package_unchanged": True,
        "collision_writer_implemented": False,
    }


def inspect_level_envelope(level: bytes, blocks: list[dict]) -> dict:
    observed = mopp.inspect_mopp_link(level, blocks)
    start, end = (observed["mopp_code_start_in_level"],
                  observed["mopp_code_end_in_level"])
    code = level[start:end]
    result = inspect_code_roundtrip(code, observed["flat_triangles_prevalidated"])
    prefix = start - 24
    if prefix < 0 or end + 12 != len(level):
        raise ValueError("MOPP envelope must end at native Level payload boundary")
    original = level[prefix:]
    # Retain original float32 bits, not recalculated values.
    rebuilt = (struct.pack("<I", len(code)+20) + level[prefix+4:prefix+20]
               + struct.pack("<I", len(code)) + code + bytes(12))
    if original != rebuilt:
        raise ValueError("MOPP envelope no-op reconstruction disagrees with Level")
    return {
        **result, "source_level_sha256": hashlib.sha256(level).hexdigest(),
        "envelope_size_bytes": len(original),
        "envelope_start_in_level": prefix,
        "envelope_sha256": hashlib.sha256(original).hexdigest(),
        "reassembled_envelope_sha256": hashlib.sha256(rebuilt).hexdigest(),
        "envelope_byte_identical": True,
        "mopp_spatial_f32_bits_recomputed": False,
    }


def audit_map(path: Path) -> dict:
    if (not isinstance(path, Path) or not path.is_file()
            or path.suffix.lower() != ".gmp"
            or path.stat().st_size > mopp.flatcheck.MAX_MAP_BYTES):
        raise ValueError("Expected original user-owned DX2 GMP")
    project = Path(__file__).resolve().parents[2]
    exporter = project / "map_exporter"
    if str(exporter) not in sys.path:
        sys.path.insert(0, str(exporter))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg = Package(path)
    if pkg.version != 95 or pkg.licensee not in mopp.flatcheck.OBSERVED_LICENSEES:
        raise ValueError("Unsupported retail DX2 package version")
    levels = [e for e in pkg.exports if pkg.class_name(e) == "Level" and e["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected exactly one Level export")
    level = pkg.payload(levels[0])
    return {"file": path.name, "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
            "licensee": pkg.licensee, **inspect_level_envelope(level, find_bsp(pkg))}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path,
                        help="Write new JSON outside original map directories")
    args = parser.parse_args(argv)
    try:
        if not 1 <= len(args.maps) <= mopp.flatcheck.MAX_MAPS:
            raise ValueError("Expected 1..64 original GMPs")
        paths = [p.resolve() for p in args.maps]
        if len(set(paths)) != len(paths):
            raise ValueError("Repeated original GMP source path")
        rows = [audit_map(p) for p in paths]
        summary = Counter()
        for row in rows:
            summary["maps"] += 1
            summary["original_mopp_code_bytes"] += row["code_length_bytes"]
            summary["source_reachable_instruction_bytes"] += row["reachable_instruction_bytes"]
            summary["opaque_unvisited_bytes_preserved"] += row["unvisited_bytes_preserved_opaque"]
            summary["decoded_reachable_instructions"] += row["distinct_decoded_instruction_offsets"]
            summary["terminal_triangle_ids"] += row["reachable_triangle_leaves"]
        result = {"schema": SCHEMA, "read_only": True, "summary": dict(summary),
                  "maps": rows, "native_mopp_builder_or_collision_writer": False,
                  "retail_files_modified": False}
        if args.report:
            out = args.report.resolve()
            if (out.suffix.lower() != ".json"
                    or any(out == p or out.is_relative_to(p.parent) for p in paths)):
                raise ValueError("Report must be outside original map directories")
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2, allow_nan=False)
                handle.write("\n")
            print(json.dumps({"status":"ok", "report":str(out),
                              "summary":result["summary"]}))
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, IndexError, KeyError, TypeError,
            OverflowError, struct.error) as exc:
        print(json.dumps({"status":"refused", "reason":str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
