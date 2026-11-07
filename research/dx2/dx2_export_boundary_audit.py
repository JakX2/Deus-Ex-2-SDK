"""Experimental, read-only structural audit of DX2 v95 export byte ranges.

Parses a restricted, synthetic-tested UE95/Ion Storm package table layout.
Successfully parsing a header does NOT authenticate BSP/zone semantics, retail
compatibility, or the provenance of any arbitrary opaque observation. No writes.
"""
from __future__ import annotations

from hashlib import sha256
import struct

MAGIC = 0x9E2A83C1
MAX_SOURCE = 128 * 1024 * 1024
MAX_ENTRIES = 100_000
MAX_GENERATIONS = 4096
MAX_NAME_BYTES = 4096
SCHEMA = "DX2SDK-experimental-export-boundary-audit-v1"


class ExportBoundaryError(ValueError):
    """Invalid or ambiguous DX2 export boundary evidence."""


class _Reader:
    def __init__(self, data: bytes, offset: int = 0):
        self.data = data
        self.at = offset

    def raw(self, size: int) -> bytes:
        if size < 0 or self.at > len(self.data) or size > len(self.data) - self.at:
            raise ExportBoundaryError("truncated package table")
        start = self.at
        self.at += size
        return self.data[start:self.at]

    def u32(self) -> int:
        return struct.unpack("<I", self.raw(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.raw(4))[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.raw(2))[0]

    def ci(self) -> int:
        """Reject noncanonical and oversized signed compact indices."""
        first = self.raw(1)[0]
        raw = bytearray((first,))
        sign = bool(first & 0x80)
        value = first & 0x3f
        if first & 0x40:
            for i in range(4):
                b = self.raw(1)[0]
                raw.append(b)
                value |= (b & 0x7f) << (6 + 7 * i)
                if not (b & 0x80):
                    break
            else:
                raise ExportBoundaryError("invalid compact index continuation")
        if value > (0x80000000 if sign else 0x7fffffff):
            raise ExportBoundaryError("compact index overflow")
        # Canonical form disallows negative zero and redundant continuation.
        v = -value if sign else value
        magnitude = abs(v)
        canonical = bytearray()
        a = magnitude & 0x3f
        magnitude >>= 6
        canonical.append(a | (0x80 if v < 0 else 0) | (0x40 if magnitude else 0))
        while magnitude:
            b = magnitude & 0x7f
            magnitude >>= 7
            canonical.append(b | (0x80 if magnitude else 0))
        if bytes(raw) != bytes(canonical):
            raise ExportBoundaryError("noncanonical compact index")
        return v

    def name(self) -> None:
        size = self.ci()
        if size == 0:
            raise ExportBoundaryError("zero-length package name")
        count = size if size > 0 else -2 * size
        if count > MAX_NAME_BYTES:
            raise ExportBoundaryError("name exceeds audit bound")
        raw = self.raw(count)
        if size > 0 and (not raw or raw[-1] != 0):
            raise ExportBoundaryError("unterminated ANSI name")
        if size < 0 and (len(raw) < 2 or raw[-2:] != b"\0\0"):
            raise ExportBoundaryError("unterminated UTF16 name")
        # A terminator inside the declared name body makes the record ambiguous.
        if size > 0 and b"\0" in raw[:-1]:
            raise ExportBoundaryError("embedded ANSI name terminator")
        if size < 0 and any(raw[i:i + 2] == b"\0\0"
                            for i in range(0, len(raw) - 2, 2)):
            raise ExportBoundaryError("embedded UTF16 name terminator")
        if size < 0:
            try:
                raw[:-2].decode("utf-16-le", errors="strict")
            except UnicodeDecodeError as exc:
                raise ExportBoundaryError("invalid UTF16 name encoding") from exc


def _check_ref(value: int, imports: int, exports: int) -> None:
    if value < -imports or value > exports:
        raise ExportBoundaryError("out-of-range object reference")


def _overlap_free(ranges: list[tuple[int, int, str]]) -> None:
    ranges.sort(key=lambda x: (x[0], x[1], x[2]))
    for index in range(1, len(ranges)):
        if ranges[index][0] < ranges[index - 1][1]:
            raise ExportBoundaryError("overlapping header/table/payload ranges")


def audit_dx2_export_boundaries(source: bytes, *, source_sha256: str) -> dict:
    """Validate only candidate export table ranges in immutable source bytes.

    A valid report has export_envelopes_independently_verified=False:
    structural self-consistency is not evidence of authentic retail semantics.
    """
    if type(source) is not bytes or len(source) > MAX_SOURCE:
        raise ExportBoundaryError("source must be bounded immutable bytes")
    if (type(source_sha256) is not str or len(source_sha256) != 64
            or any(c not in "0123456789abcdef" for c in source_sha256)
            or sha256(source).hexdigest() != source_sha256):
        raise ExportBoundaryError("source SHA-256 mismatch")
    r = _Reader(source)
    if r.u32() != MAGIC:
        raise ExportBoundaryError("wrong package magic")
    version, licensee, _flags = r.u16(), r.u16(), r.u32()
    if version != 95 or licensee not in (68, 69):
        raise ExportBoundaryError("unsupported DX2 package version/licensee")
    nc, no, ec, eo, ic, io = (r.u32() for _ in range(6))
    if any(n > MAX_ENTRIES for n in (nc, ec, ic)):
        raise ExportBoundaryError("unbounded table entries")
    # Known DX2 v95 candidate: dword before GUID, two dwords after gens.
    r.u32()
    r.raw(16)
    generations = r.u32()
    if generations > MAX_GENERATIONS:
        raise ExportBoundaryError("unbounded generations")
    r.raw(generations * 8)
    r.raw(8)
    header_end = r.at
    if no != header_end:
        raise ExportBoundaryError("ambiguous DX2 header/name table boundary")
    for offset in (no, io, eo):
        if offset < header_end or offset > len(source):
            raise ExportBoundaryError("table begins outside payload area")
    names = _Reader(source, no)
    for _ in range(nc):
        names.name()
        names.u32()
    imports = _Reader(source, io)
    for _ in range(ic):
        cp, cn, outer, name = imports.ci(), imports.ci(), imports.i32(), imports.ci()
        if any(n < 0 or n >= nc for n in (cp, cn, name)):
            raise ExportBoundaryError("out-of-range import name index")
        _check_ref(outer, ic, ec)
    exports = _Reader(source, eo)
    envelopes = []
    for export_index in range(1, ec + 1):
        class_ref, super_ref, outer, name = (exports.ci(), exports.ci(), exports.i32(), exports.ci())
        exports.u32()  # flags
        length = exports.ci()
        offset = exports.ci() if length else 0
        if name < 0 or name >= nc:
            raise ExportBoundaryError("out-of-range export name index")
        for ref in (class_ref, super_ref, outer):
            _check_ref(ref, ic, ec)
        if length < 0 or offset < 0 or offset > len(source) or length > len(source) - offset:
            raise ExportBoundaryError("invalid export byte range")
        if length:
            envelopes.append({"export": export_index, "offset": offset, "length": length})
    regions = [
        (0, header_end, "header"),
        (no, names.at, "names"),
        (io, imports.at, "imports"),
        (eo, exports.at, "exports"),
    ]
    ranges = [(start, end, label) for start, end, label in regions if start < end]
    ranges += [(e["offset"], e["offset"] + e["length"], "export-payload")
               for e in envelopes]
    _overlap_free(ranges)
    return {
        "schema": SCHEMA,
        "source_sha256": source_sha256,
        "source_size": len(source),
        "package_version": version,
        "licensee_version": licensee,
        "table_counts": {"names": nc, "imports": ic, "exports": ec},
        "table_ranges": {label: {"offset": start, "length": end - start}
                         for start, end, label in regions},
        "candidate_export_envelopes": envelopes,
        "table_structural_checks_passed": True,
        "export_envelopes_independently_verified": False,
        "native_bsp_leaf_zone_decoded": False,
        "runtime_game_verified": False,
        "writable": False,
        "source_original_modified": False,
    }
