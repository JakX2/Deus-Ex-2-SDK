#!/usr/bin/env python3
"""DX2-specific read-only grouped GameSys default values in archetype UClasses.

Original DX2Gamesys D_* classes contain records of the form:
  u32 encoded_property_id, u32 element_count,
  repeat element_count: (u32 payload_size, payload_bytes)
and optionally a final u32 zero. An element_count of one looks identical
to the old T3SDK "version" field, but DX2 has 29-element vulnerability
structs and 3-element biomod descriptions / modifier structs.

This supplement ONLY recovers source classes the unmodified T3SDK parser
failed to read. It does not modify upstream code, write game packages,
infer class spawning, or treat grouped arrays as editable.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from t3common import Reader
from upkg import GamesysBlock, Package

# Original DX2 source findings. Reject other multi-element blocks until
# independently characterized, instead of guessing at their semantics.
VERIFIED_GROUP_COUNTS = {
    (0x000803BF, 29),  # vulnerability tagged struct entries
    (0x00040725, 3),   # biomod text entries
    (0x000804F0, 3),   # biomod tagged struct entries
    (0x000804BE, 3),   # biomod tagged struct entries
}
MAX_LINKS = 16384
MAX_GROUP_ELEMENTS = 256
MAX_GROUPS = 4096


def _bounded_list_count(value: int, category: str) -> int:
    if not 0 <= value <= MAX_LINKS:
        raise ValueError(f"Unreasonable {category} count")
    return value


def scan_grouped_defaults(pkg: Package, source_export) -> dict:
    """Reparse an original DX2 archetype and validate every byte boundary.

    Data from a failing T3SDK parser is not reused; the final cursor must
    reach the exact original export end, consuming optional zero sentinel.
    """
    if source_export.class_ref != 0 or not source_export.name.upper().startswith("D_"):
        raise ValueError("Only original D_* class exports can be audited")
    start, end = source_export.serial_offset, source_export.serial_offset + source_export.serial_size
    r = Reader(pkg.data, start, end)
    n = _bounded_list_count(r.u32(), "class link")
    for _ in range(n):
        r.index()
    for _ in range(5):
        r.index()
    for _ in range(2):
        r.i32()
    if r.i32() != 0:
        raise ValueError("Archetype class unexpectedly contains bytecode")
    r.u64()
    r.u64()
    r.u16()
    r.u32()
    r.u32()
    r.bytes(16)
    n = _bounded_list_count(r.index(), "class interface")
    for _ in range(n):
        r.index()
        r.u32()
        r.u32()
    n = _bounded_list_count(r.index(), "class package")
    for _ in range(n):
        r.index()
    r.index()
    r.index()
    display = r.fstring()
    defaults = pkg.read_properties(r, end)
    groups = []
    grouped_count = 0
    for _ in range(MAX_GROUPS):
        if r.remaining() == 0:
            break
        if r.remaining() < 4:
            raise ValueError("Incomplete grouped GameSys identifier")
        identifier_offset = r.pos
        encoded_id = r.u32()
        if encoded_id == 0:
            break
        if r.remaining() < 8:
            raise ValueError("Incomplete grouped GameSys count or first size")
        count = r.u32()
        if not 1 <= count <= MAX_GROUP_ELEMENTS:
            raise ValueError("GameSys element count is outside verified bounds")
        if count > 1 and (encoded_id, count) not in VERIFIED_GROUP_COUNTS:
            raise ValueError("Unknown multi-element GameSys encoding")
        elements = []
        for index in range(count):
            if r.remaining() < 4:
                raise ValueError("Missing length-prefixed GameSys element")
            size = r.u32()
            if size > r.remaining():
                raise ValueError("Grouped GameSys element exceeds original export")
            payload_offset = r.pos
            blob = r.bytes(size)
            block = GamesysBlock(encoded_id, count, blob)
            item = {
                "element_index": index,
                "payload_offset": payload_offset,
                "payload_bytes": size,
                "payload_sha256": hashlib.sha256(blob).hexdigest(),
            }
            if block.kind == "struct":
                sub = Reader(blob)
                fields = pkg.read_properties(sub, len(blob))
                if sub.remaining():
                    raise ValueError("Grouped tagged struct left unparsed bytes")
                item["typed_fields"] = [
                    {"name": prop.name, "type": prop.type,
                     "value": prop.value if isinstance(prop.value, (str, int, float, bool))
                     else None}
                    for prop in fields
                ]
            elif block.kind == "string":
                sub = Reader(blob)
                value = sub.fstring()
                if sub.remaining():
                    raise ValueError("Grouped string left unparsed bytes")
                item["string_value"] = value
            elements.append(item)
        if count > 1:
            grouped_count += 1
        groups.append({
            "encoded_id": encoded_id,
            "property_id": encoded_id & 0xFFFF,
            "encoding": block.kind,
            "element_count": count,
            "source_header_offset": identifier_offset,
            "elements": elements,
            "native_edit_enabled": False,
        })
    else:
        raise ValueError("Excessive GameSys property groups")
    if r.remaining() != 0:
        raise ValueError("Unparsed bytes after original archetype GameSys data")
    if not groups or grouped_count == 0:
        raise ValueError("No source-verified grouped property recovered")
    return {
        "display_name": display,
        "original_tagged_defaults_count": len(defaults),
        "groups": groups,
        "multi_element_group_count": grouped_count,
        "verified_original_byte_end": end,
        "source_layout_complete": True,
        "runtime_semantics_verified": False,
        "native_edit_enabled": False,
    }
