"""Fail-closed opaque byte-span observations for future BSP/zone research.

This deliberately does NOT discover native package/export boundaries, identify
BSP leaves/zones, or parse arbitrary offsets from a retail GMP. The caller
must independently authenticate each section envelope. No file writes.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping

SCHEMA = "DX2SDK-opaque-source-span-observation-v1"
MAX_SPANS = 64
MAX_ENVELOPES = 64
MAX_PREVIEW = 32
MAX_SOURCE_BYTES = 128 * 1024 * 1024


class SpanEvidenceError(ValueError):
    """A caller-supplied opaque envelope is not independently credible."""


def _uint(value: object, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise SpanEvidenceError("expected bounded nonnegative integer")
    return value


def observe_opaque_spans(
    source: bytes,
    *,
    source_sha256: str,
    package_identity: str,
    spans: Iterable[Mapping[str, object]],
    preview_bytes: int = 0,
    export_envelopes: Iterable[Mapping[str, object]] | None = None,
) -> dict:
    """Return deterministic, read-only source-bound opaque span metadata.

    All spans must provide a positive export index, nonempty unique evidence
    identifier and explicit offset/length. Nonempty disjoint spans only.
    This is an *observation* API, never a native BSP/zone decoder.
    """
    if type(source) is not bytes or len(source) > MAX_SOURCE_BYTES:
        raise SpanEvidenceError("source must be bounded immutable bytes")
    if (type(source_sha256) is not str or len(source_sha256) != 64
            or any(c not in "0123456789abcdef" for c in source_sha256)
            or sha256(source).hexdigest() != source_sha256):
        raise SpanEvidenceError("source SHA-256 mismatch")
    if (type(package_identity) is not str or not package_identity
            or len(package_identity) > 128
            or any(ord(c) < 33 or ord(c) > 126 for c in package_identity)):
        raise SpanEvidenceError("invalid package identity")
    preview = _uint(preview_bytes)
    if preview > MAX_PREVIEW:
        raise SpanEvidenceError("hex preview exceeds opt-in bound")
    # Optional negative-control containment, never an authenticated native
    # package parser. All caller-declared export owners must be disjoint.
    owners: dict[int, tuple[int, int]] = {}
    if export_envelopes is not None:
        try:
            owner_iter = iter(export_envelopes)
        except TypeError as exc:
            raise SpanEvidenceError("invalid export envelope iterable") from exc
        for envelope in owner_iter:
            if len(owners) >= MAX_ENVELOPES:
                raise SpanEvidenceError("too many export envelopes")
            if not isinstance(envelope, Mapping):
                raise SpanEvidenceError("export envelope must be a mapping")
            export = _uint(envelope.get("export"), positive=True)
            offset = _uint(envelope.get("offset"))
            length = _uint(envelope.get("length"), positive=True)
            if export > 0x7fffffff or export in owners:
                raise SpanEvidenceError("invalid or duplicate export owner")
            if offset > len(source) or length > len(source) - offset:
                raise SpanEvidenceError("export envelope exceeds source bytes")
            owners[export] = (offset, offset + length)
        intervals = sorted(owners.values())
        if any(intervals[i][0] < intervals[i - 1][1]
               for i in range(1, len(intervals))):
            raise SpanEvidenceError("ambiguous overlapping export envelopes")
    rows = []
    try:
        iterator = iter(spans)
    except TypeError as exc:
        raise SpanEvidenceError("invalid span iterable") from exc
    for entry in iterator:
        if len(rows) >= MAX_SPANS:
            raise SpanEvidenceError("too many opaque spans")
        if not isinstance(entry, Mapping):
            raise SpanEvidenceError("span must be a mapping")
        export = _uint(entry.get("export"), positive=True)
        if export > 0x7fffffff:
            raise SpanEvidenceError("export exceeds signed 32-bit range")
        offset = _uint(entry.get("offset"))
        length = _uint(entry.get("length"), positive=True)
        evidence = entry.get("evidence")
        if (type(evidence) is not str or not evidence or len(evidence) > 128
                or any(ord(c) < 33 or ord(c) > 126 for c in evidence)):
            raise SpanEvidenceError("missing independent envelope evidence")
        if offset > len(source) or length > len(source) - offset:
            raise SpanEvidenceError("span exceeds source bytes")
        if export_envelopes is not None:
            owner = owners.get(export)
            if owner is None or offset < owner[0] or offset + length > owner[1]:
                raise SpanEvidenceError("span escapes its declared export envelope")
        rows.append((offset, offset + length, export, evidence))
    rows.sort()
    seen_evidence = set()
    for i, (start, end, export, evidence) in enumerate(rows):
        if evidence in seen_evidence:
            raise SpanEvidenceError("duplicate envelope evidence")
        seen_evidence.add(evidence)
        if i and start < rows[i - 1][1]:
            raise SpanEvidenceError("overlapping source spans")
    observations = []
    for start, end, export, evidence in rows:
        record = {
            "export": export,
            "offset": start,
            "length": end - start,
            "evidence": evidence,
            "classification": "unknown-payload",
            "writable": False,
        }
        if preview:
            record["hex_preview"] = source[start:min(end, start + preview)].hex()
        observations.append(record)
    return {
        "schema": SCHEMA,
        "source_sha256": source_sha256,
        "source_size": len(source),
        "package_identity": package_identity,
        "source_original_modified": False,
        "native_bsp_leaf_zone_decoded": False,
        "runtime_game_verified": False,
        "writable": False,
        "caller_export_envelopes_checked": export_envelopes is not None,
        "export_envelopes_independently_verified": False,
        "observations": observations,
    }


def observe_opaque_file(
    path: Path,
    *,
    expected_sha256: str,
    package_identity: str,
    spans: Iterable[Mapping[str, object]],
    preview_bytes: int = 0,
) -> dict:
    """Explicit local read only. Source SHA is rechecked before observing."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
        raise SpanEvidenceError("missing or oversized original source")
    with path.open("rb") as handle:
        source = handle.read(MAX_SOURCE_BYTES + 1)
    return observe_opaque_spans(
        source, source_sha256=expected_sha256,
        package_identity=package_identity, spans=spans,
        preview_bytes=preview_bytes, export_envelopes=export_envelopes,
    )
