"""Opt-in, read-only concordance of two checked-in DX2 package table readers.

This cross-checks the legacy Package export rows against the stricter v0.21
candidate audit for the SAME immutable bytes. The readers share format
assumptions, so agreement does not authenticate retail export ownership.
No native BSP/zone decoding, game runtime validation, or source writes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from typing import Any

from dx2_export_boundary_audit import (
    ExportBoundaryError, MAX_SOURCE, audit_dx2_export_boundaries,
)

SCHEMA = "DX2SDK-export-reader-concordance-v1"


class ReaderConcordanceError(ValueError):
    """The two package readers disagree or the evidence is insufficient."""


def _integer(value: Any) -> bool:
    return type(value) is int


def compare_export_readers(reader_package: Any, *, expected_sha256: str) -> dict:
    """Compare legacy Package data with strict audit, rejecting every mismatch.

    The legacy Package instance must already have read the source. Reuse
    *exactly* its immutable bytes to avoid a two-read source drift window.
    Never return serialized payloads, native names, or raw byte previews.
    """
    source = getattr(reader_package, "data", None)
    if type(source) is not bytes or len(source) > MAX_SOURCE:
        raise ReaderConcordanceError("legacy reader has no bounded immutable source")
    if (type(expected_sha256) is not str
            or len(expected_sha256) != 64
            or any(c not in "0123456789abcdef" for c in expected_sha256)
            or sha256(source).hexdigest() != expected_sha256):
        raise ReaderConcordanceError("legacy source hash disagrees with expected SHA-256")
    try:
        strict = audit_dx2_export_boundaries(source, source_sha256=expected_sha256)
    except ExportBoundaryError as exc:
        raise ReaderConcordanceError("strict package boundary audit rejected source") from exc
    if (not _integer(getattr(reader_package, "version", None))
            or reader_package.version != strict["package_version"]
            or not _integer(getattr(reader_package, "licensee", None))
            or reader_package.licensee != strict["licensee_version"]):
        raise ReaderConcordanceError("package version/licensee disagreement")
    counts = strict["table_counts"]
    expected_counts = (counts["names"], counts["imports"], counts["exports"])
    legacy_counts = getattr(reader_package, "table_counts", None)
    if (type(legacy_counts) is not tuple or len(legacy_counts) != 3
            or any(not _integer(x) for x in legacy_counts)
            or legacy_counts != expected_counts):
        raise ReaderConcordanceError("header table count disagreement")
    names = getattr(reader_package, "names", None)
    imports = getattr(reader_package, "imports", None)
    exports = getattr(reader_package, "exports", None)
    if (type(names) is not list or type(imports) is not list
            or type(exports) is not list
            or (len(names), len(imports), len(exports)) != expected_counts):
        raise ReaderConcordanceError("decoded table count disagreement")
    candidate = {e["export"]: (e["offset"], e["length"])
                 for e in strict["candidate_export_envelopes"]}
    # The original one-based export order is part of the source evidence.
    empty = 0
    for original_index, row in enumerate(exports, 1):
        if type(row) is not dict:
            raise ReaderConcordanceError("invalid legacy export row")
        index, size, offset = (row.get("index"), row.get("size"), row.get("offset"))
        if (not _integer(index) or not _integer(size) or not _integer(offset)
                or index != original_index or size < 0 or offset < 0):
            raise ReaderConcordanceError("invalid legacy export identity or size")
        if size == 0:
            empty += 1
            if offset != 0 or index in candidate:
                raise ReaderConcordanceError("zero-sized export cannot own a byte span")
        elif candidate.get(index) != (offset, size):
            raise ReaderConcordanceError("export offset/length disagreement")
    if len(candidate) + empty != len(exports):
        raise ReaderConcordanceError("export ownership coverage disagreement")
    return {
        "schema": SCHEMA,
        "source_sha256": expected_sha256,
        "source_size": len(source),
        "version": strict["package_version"],
        "licensee": strict["licensee_version"],
        "table_counts": counts,
        "matched_nonempty_exports": len(candidate),
        "zero_length_exports_not_owners": empty,
        "strict_structure_passed": True,
        "legacy_reader_concordant": True,
        # Two implementations share UE95 assumptions. This is NOT external
        # verification of proprietary DX2 native export / BSP semantics.
        "export_envelopes_independently_verified": False,
        "native_bsp_leaf_zone_decoded": False,
        "runtime_game_verified": False,
        "writable": False,
        "source_original_modified": False,
    }


def compare_local_package(path: Path, *, expected_sha256: str) -> dict:
    """Opt-in local diagnostic. No files are written and no source is printed."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_SOURCE:
        raise ReaderConcordanceError("missing or oversized local package")
    # Load the existing independent, checked-in reader without modifying it.
    inspector = Path(__file__).resolve().parents[2] / "map_exporter" / "dx2inspect.py"
    spec = spec_from_file_location("_dx2sdk_concordance_legacy_reader", inspector)
    if spec is None or spec.loader is None:
        raise ReaderConcordanceError("legacy package reader unavailable")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        pkg = module.Package(path)
    except (OSError, ValueError, IndexError) as exc:
        raise ReaderConcordanceError("legacy package reader rejected local source") from exc
    return compare_export_readers(pkg, expected_sha256=expected_sha256)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", required=True, type=Path,
                        help="Local owner-provided GMP/D2U; opened read-only")
    parser.add_argument("--sha256", required=True,
                        help="Lowercase SHA-256 calculated independently by owner")
    args = parser.parse_args()
    try:
        report = compare_local_package(args.map, expected_sha256=args.sha256)
    except ReaderConcordanceError as exc:
        parser.exit(status=2, message="Export reader concordance rejected: " + str(exc) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
