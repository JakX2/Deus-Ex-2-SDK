"""Exact original DX2 Level MOPP terminal instruction byte provenance.

This is a read-only index of source-observed MOPP leaf opcodes, not a
collision writer, a Havok compiler, or proof of native runtime behavior.
"""
from __future__ import annotations

import hashlib

from .bsp_mopp_plane_impact import (
    _source_triangle_rows, compare_original_plane_mopp_impact,
)
from dx2scene import find_bsp
from inspect_mopp_bytecode_roundtrip import _decode, inspect_code_roundtrip, inspect_level_envelope
from inspect_level_mopp_triangle_tree import trace_mopp_code

SCHEMA = "DX2SDK-original-MOPP-terminal-instruction-provenance-v1"
MAX_SELECTED_TRIANGLES = 32


def _selected_ids(triangle_ids: object, triangle_count: int) -> list[int]:
    if (not isinstance(triangle_ids, (list, tuple))
            or not 1 <= len(triangle_ids) <= MAX_SELECTED_TRIANGLES
            or any(type(value) is not int or not 0 <= value < triangle_count
                   for value in triangle_ids)
            or len(set(triangle_ids)) != len(triangle_ids)):
        raise ValueError("Select 1..32 unique original flattened triangle ordinals")
    return list(triangle_ids)


def index_mopp_terminal_instructions(code: bytes, triangle_count: int) -> dict[int, dict]:
    """Locate original terminal PC/base/operand without emitting any mutation.

    Independently compares *every* terminal against the existing original
    CFG and complete byte-identical MOPP instruction reconstruction.
    """
    validated = inspect_code_roundtrip(code, triangle_count)
    reference = trace_mopp_code(code, triangle_count)
    leaves: dict[int, dict] = {}
    visited: set[tuple[int, int]] = set()
    pending = [(0, 0)]
    while pending:
        pc, base = pending.pop()
        if (pc, base) in visited:
            continue
        if len(visited) >= reference["reachable_instruction_states"]:
            raise ValueError("MOPP terminal index exceeds independently validated CFG")
        visited.add((pc, base))
        record = _decode(code, pc)
        role, values, size = record["role"], record["operands"], record["size"]
        end = pc + size
        targets: list[tuple[int, int]] = []
        if role == "forward":
            targets = [(end, base)]
        elif role in ("jump8", "jump16"):
            targets = [(end + values[0], base)]
        elif role in ("addbase8", "addbase16"):
            targets = [(end, base + values[0])]
        elif role == "setbase32":
            targets = [(end, values[0])]
        elif role == "split8plus3":
            targets = [(end, base), (end + values[2], base)]
        elif role == "split8plus2":
            targets = [(end, base), (end + values[1], base)]
        elif role == "twojump16":
            targets = [(end + values[2], base), (end + values[3], base)]
        elif role in ("leaf_inline", "leaf_imm"):
            delta = (record["opcode"] - 0x30 if role == "leaf_inline"
                     else values[0])
            triangle_id = base + delta
            if not 0 <= triangle_id < triangle_count or triangle_id in leaves:
                raise ValueError("Original MOPP leaf ID invalid or not uniquely encoded")
            leaves[triangle_id] = {
                "flattened_triangle_id": triangle_id,
                "instruction_offset_in_code": pc,
                "instruction_size_bytes": size,
                "leaf_opcode": f"0x{record['opcode']:02x}",
                "leaf_encoding": role,
                "source_output_base": base,
                "source_encoded_delta": delta,
                "encoded_delta_offset_in_code": pc if role == "leaf_inline" else pc + 1,
                "encoded_delta_size_bytes": size if role == "leaf_inline" else size - 1,
                "source_operand_big_endian": role == "leaf_imm",
                "native_mopp_leaf_patch_authorized": False,
            }
        else:
            raise ValueError("Unexpected source MOPP control-flow role")
        for target, next_base in targets:
            if not pc < target < len(code) or not 0 <= next_base <= 0xffffffff:
                raise ValueError("Original MOPP branch target/base outside validated code")
            pending.append((target, next_base))
    if (len(visited) != reference["reachable_instruction_states"]
            or len(leaves) != validated["reachable_triangle_leaves"]
            or sorted(leaves) != reference["reachable_terminal_triangle_ids"]
            or not validated["code_byte_identical"]
            or not validated["control_flow_matches_original_decoder"]):
        raise ValueError("Original MOPP terminal opcode offsets disagree with native CFG")
    return leaves


def inspect_level_mopp_terminal_bytes(
    level: bytes, blocks: list[dict], triangle_ids: object,
    *, level_export_offset: int | None = None,
) -> dict:
    """Map bounded original triangle IDs to exact Level MOPP opcode offsets.

    Export offsets are optional for synthetic Level fixture testing; a real
    DX2Map source supplies an independently checked original GMP offset.
    """
    if type(level) is not bytes:
        raise ValueError("Original immutable Level bytes required")
    if level_export_offset is not None and (
            type(level_export_offset) is not int or level_export_offset < 0):
        raise ValueError("Invalid original Level export offset")
    rows, provenance = _source_triangle_rows(level, blocks)
    requested = _selected_ids(triangle_ids, len(rows))
    envelope = inspect_level_envelope(level, blocks)
    start = envelope["envelope_start_in_level"] + 24
    end = start + envelope["code_length_bytes"]
    if end + 12 != len(level) or start < 0:
        raise ValueError("Original MOPP instruction bytes escape Level payload")
    code = level[start:end]
    if hashlib.sha256(code).hexdigest() != envelope["code_sha256"]:
        raise ValueError("Original Level MOPP code changed during inspection")
    indexed = index_mopp_terminal_instructions(code, len(rows))
    if (len(indexed) != provenance["mopp_leaves_with_render_section_attribution"]
            or any(row["original_mopp_terminal_leaf_present"] !=
                   (row["flattened_triangle_id"] in indexed) for row in rows)):
        raise ValueError("Original Level provenance/terminal instruction IDs disagree")
    selected = []
    for triangle_id in requested:
        row = rows[triangle_id]
        leaf = indexed.get(triangle_id)
        entry = {
            **row,
            "mopp_terminal_instruction_present": leaf is not None,
            "missing_terminal_is_source_degenerate_triangle": leaf is None,
            "mopp_opcode_offset_in_level": (
                start + leaf["instruction_offset_in_code"] if leaf else None),
            "mopp_encoded_delta_offset_in_level": (
                start + leaf["encoded_delta_offset_in_code"] if leaf else None),
            "mopp_opcode_absolute_offset_in_gmp": (
                level_export_offset + start + leaf["instruction_offset_in_code"]
                if leaf and level_export_offset is not None else None),
            "mopp_encoded_delta_absolute_offset_in_gmp": (
                level_export_offset + start + leaf["encoded_delta_offset_in_code"]
                if leaf and level_export_offset is not None else None),
            "provenance_pair_absolute_offset_in_gmp": (
                level_export_offset + row["provenance_pair_offset_in_level"]
                if level_export_offset is not None else None),
            "source_terminal": dict(leaf) if leaf is not None else None,
        }
        selected.append(entry)
    return {
        "schema": SCHEMA,
        "status": "read-only-original-MOPP-terminal-instruction-byte-index",
        "source_level_sha256": hashlib.sha256(level).hexdigest(),
        "original_level_export_offset_in_gmp": level_export_offset,
        "mopp_code_sha256": envelope["code_sha256"],
        "original_code_start_in_level": start,
        "original_code_bytes": envelope["code_length_bytes"],
        "original_flat_triangle_count": len(rows),
        "original_terminal_instruction_count": len(indexed),
        "selected_flat_triangle_ids": requested,
        "selected": selected,
        "native_BSP_or_MOPP_writer_enabled": False,
        "native_Havok_collision_rebuild_verified": False,
        "original_level_modified": False,
        "retail_runtime_verified": False,
    }


def inspect_original_mopp_terminal_bytes(world, triangle_ids: object) -> dict:
    """Source-bound original GMP Level export and exact leaf opcode provenance."""
    world._check_original_unchanged()
    pkg = world._package
    if hashlib.sha256(pkg.data).hexdigest() != world.source_sha256:
        raise ValueError("Loaded native GMP data differs from opened original source")
    levels = [(i, exp) for i, exp in enumerate(pkg.exports, 1)
              if pkg.class_name(exp) == "Level" and exp["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected one original nonempty Level export")
    level_export, exp = levels[0]
    offset, size = exp["offset"], exp["size"]
    if (type(offset) is not int or type(size) is not int
            or offset < 0 or size < 0 or offset + size > len(pkg.data)):
        raise ValueError("Original Level payload has invalid native GMP bounds")
    level = pkg.payload(exp)
    if level != pkg.data[offset:offset+size]:
        raise ValueError("Original Level export byte offsets disagree with source GMP")
    report = inspect_level_mopp_terminal_bytes(
        level, find_bsp(pkg), triangle_ids, level_export_offset=offset)
    if report["source_level_sha256"] != hashlib.sha256(level).hexdigest():
        raise ValueError("Independent original Level SHA-256 mismatch")
    world._check_original_unchanged()
    return {
        **report,
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "original_level_export": level_export,
        "original_level_export_size_bytes": size,
        "original_package_bytes_modified": False,
        "limitations": [
            "This is the original native MOPP terminal opcode/operand location, not an editable collision shape.",
            "Output-base arithmetic and branch-dependent MOPP traversal prohibit naïve leaf byte patches.",
            "Source triangle ordinal and Level provenance mapping are validated, but BSP surface ownership is not.",
            "No changed geometry, collision cooking, original GMP write or retail runtime test.",
        ],
    }


def inspect_original_plane_affected_terminal_bytes(world, *, node: int, replacement) -> dict:
    """Join v0.72 hypothetical BSP impact to actual source leaf opcode locations."""
    world._check_original_unchanged()
    impact = compare_original_plane_mopp_impact(world, node=node, replacement=replacement)
    lost = impact["lost_candidate_mopp_id_examples"]
    gained = impact["gained_candidate_mopp_id_examples"]
    ids = sorted({row["flattened_triangle_id"]
                  for row in lost + gained if row["original_mopp_terminal_leaf_present"]})
    indexed = (inspect_original_mopp_terminal_bytes(world, ids) if ids else None)
    if indexed and indexed["source_sha256"] != impact["source_sha256"]:
        raise ValueError("Original Model/Level source hash differs between independent inspections")
    located = ({row["flattened_triangle_id"]: row for row in indexed["selected"]}
               if indexed else {})
    def evidence(rows):
        out = []
        for row in rows:
            record = located.get(row["flattened_triangle_id"])
            if row["original_mopp_terminal_leaf_present"] != (record is not None):
                raise ValueError("BSP candidate and source MOPP terminal membership disagree")
            if record is not None and (
                    record["render_locator"] != row["render_locator"]
                    or record["source_provenance_block_field_a"] !=
                    row["source_provenance_block_field_a"]
                    or record["source_provenance_section_field_b"] !=
                    row["source_provenance_section_field_b"]):
                raise ValueError("Original source render/MOPP attribution differs between audits")
            out.append({**row, "terminal_instruction": (
                {
                    "mopp_opcode_absolute_offset_in_gmp":
                        record["mopp_opcode_absolute_offset_in_gmp"],
                    "mopp_encoded_delta_absolute_offset_in_gmp":
                        record["mopp_encoded_delta_absolute_offset_in_gmp"],
                    "source_terminal": record["source_terminal"],
                } if record else None),
                "native_collision_writer_enabled": False})
        return out
    world._check_original_unchanged()
    return {
        **impact,
        "schema": SCHEMA,
        "status": "read-only-BSP-candidate-to-native-MOPP-terminal-opcode-provenance",
        "lost_candidate_mopp_id_examples": evidence(lost),
        "gained_candidate_mopp_id_examples": evidence(gained),
        "source_mopp_code_sha256": indexed["mopp_code_sha256"] if indexed else None,
        "original_source_modified": False,
        "native_BSP_or_MOPP_writer_enabled": False,
        "native_Havok_collision_rebuild_verified": False,
        "retail_runtime_verified": False,
    }
