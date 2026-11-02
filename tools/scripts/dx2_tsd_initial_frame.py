"""Conservative DX2 TriggerScript (.tsd) binary framing (read-only).

Identifies validated source header, name, title, first uint32 fields,
first UTF-16LE condition/action symbol, and its neighboring uint32.
No expression tree, runtime link, execution order or param meaning
is inferred. Later bytes remain opaque.
"""
from __future__ import annotations

from collections import Counter
import struct

NAME_START_BY_MAGIC = {b"1FFE2FST": 20, b"0FFE2FST": 16, b"0FFE1FST": 16}
SCHEMA = "DX2Ed-TSD-initial-binary-frame-v1"


def _u32(raw: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(raw):
        raise ValueError(f"Truncated TSD uint32 at offset {offset}")
    return struct.unpack_from("<I", raw, offset)[0]


def _text(raw: bytes, offset: int, *, max_chars: int = 1024) -> tuple[str, int]:
    if offset < 0 or offset % 2:
        raise ValueError(f"Unaligned UTF-16LE TSD offset {offset}")
    start = offset
    while offset + 2 <= len(raw) and offset - start <= max_chars * 2:
        if raw[offset:offset+2] == b"\x00\x00":
            return raw[start:offset].decode("utf-16le", errors="strict"), offset + 2
        offset += 2
    raise ValueError(f"Unterminated UTF-16LE TSD string at offset {start}")


def inspect_tsd_initial_frame(raw: bytes, member: str = "<source>") -> dict:
    if len(raw) < 24 or raw[:8] not in NAME_START_BY_MAGIC:
        raise ValueError(f"{member}: unsupported or truncated TSD")
    name_start = NAME_START_BY_MAGIC[raw[:8]]
    declared = _u32(raw, name_start - 8)
    expected = len(raw) - (name_start - 4)
    if declared != expected:
        raise ValueError(f"{member}: declared TSD payload length mismatch")
    header_word = _u32(raw, name_start - 4)
    name, title_start = _text(raw, name_start)
    title, first_offset = _text(raw, title_start)
    first_word = _u32(raw, first_offset)
    offset = first_offset + 4

    record = {
        "schema": SCHEMA, "source_member": member,
        "header_magic": raw[:8].decode("ascii"),
        "source_name": name, "display_label": title,
        "name_utf16_offset": name_start, "title_utf16_offset": title_start,
        "header_unknown_word_u32": header_word,
        "first_word_offset": first_offset, "first_word_u32": first_word,
        "word_after_initial_zero": None,
        "first_symbol_utf16_offset": None, "first_symbol": None,
        "first_symbol_kind": "none",
        "word_after_first_symbol_offset": None,
        "word_after_first_symbol_u32": None,
        "interpretation": "raw_initial_fields",
        "graph_decoded": False,
    }
    if first_word == 0:
        following = _u32(raw, offset)
        record["word_after_initial_zero"] = following
        offset += 4
        if following == 0:
            record["interpretation"] = (
                "two_zero_words_at_end" if offset == len(raw)
                else "two_zero_words_with_unparsed_tail"
            )
        else:
            token_start = offset
            token, offset = _text(raw, offset)
            record["first_symbol_utf16_offset"] = token_start
            record["first_symbol"] = token
            record["first_symbol_kind"] = (
                "action_token" if token.startswith("kTAT_") else
                "condition_token_after_zero" if token.startswith("kTCT_") else
                "unknown_token"
            )
            record["interpretation"] = "zero_word_then_symbol"
    else:
        token_start = offset
        token, offset = _text(raw, offset)
        record["first_symbol_utf16_offset"] = token_start
        record["first_symbol"] = token
        record["first_symbol_kind"] = (
            "condition_token" if token.startswith("kTCT_") else
            "unknown_token"
        )
        record["interpretation"] = "nonzero_word_then_symbol"

    if record["first_symbol"] is not None and offset + 4 <= len(raw):
        record["word_after_first_symbol_offset"] = offset
        record["word_after_first_symbol_u32"] = _u32(raw, offset)
        offset += 4
    record["opaque_tail_offset"] = offset
    record["opaque_tail_bytes"] = len(raw) - offset
    return record


def summarize_initial_frames(frames: list[dict]) -> dict:
    word_counts = Counter(f["first_word_u32"] for f in frames)
    kinds = Counter(f["first_symbol_kind"] for f in frames)
    return {
        "schema": "DX2Ed-TSD-initial-binary-frame-summary-v1",
        "source_records_inspected": len(frames),
        "initial_word_histogram": {str(k): v for k, v in sorted(word_counts.items())},
        "initial_symbol_kind_histogram": dict(sorted(kinds.items())),
        "anomalous_source_records": [
            {"source_member": f["source_member"],
             "first_word_u32": f["first_word_u32"],
             "word_after_initial_zero": f["word_after_initial_zero"],
             "first_symbol": f["first_symbol"],
             "first_symbol_utf16_offset": f["first_symbol_utf16_offset"]}
            for f in frames if f["first_symbol_kind"] in
            ("condition_token_after_zero", "unknown_token")
        ],
        "initial_word_meaning_verified": False,
        "event_graph_decoded": False,
        "warning": (
            "Initial binary words are not proven condition/action counts. "
            "Opaque bytes may contain nested expression structure and typed values."
        ),
    }
