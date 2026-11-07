"""Optional third-reader comparison using the checked-in Thief 3 UE95 parser.

Research only: even three concordant readers share reverse-engineered package
assumptions. All export owners remain *candidate* boundaries, not authenticated
DX2 BSP/zone records. No file writers or public SDK/UI hooks.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys
from typing import Any

from dx2_export_boundary_audit import audit_dx2_export_boundaries, ExportBoundaryError, MAX_SOURCE
from export_reader_concordance import compare_export_readers, ReaderConcordanceError

SCHEMA = "DX2SDK-thief-reference-export-concordance-v1"


def _source_module(path: Path, name: str):
    """Load checked-in source, not a runtime-site package of the same name."""
    spec = spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ReaderConcordanceError("checked-in source reader unavailable")
    module = module_from_spec(spec)
    # The Thief 3 reader uses dataclasses, which require the module to be
    # registered while the decorator resolves its annotations.
    previous = sys.modules.get(name)
    previous_path = list(sys.path)
    try:
        sys.modules[name] = module
        spec.loader.exec_module(module)
    except Exception:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise
    finally:
        # upkg.py imports its sibling t3common with a temporary path edit.
        # Restore import search state after module initialization.
        sys.path[:] = previous_path
    return module


def compare_thief_reference(dx2_package: Any, *, expected_sha256: str) -> dict:
    """Cross-check the original DX2 reader, strict audit, and T3 upkg table.

    Parse the SAME pinned immutable source bytes. Source original remains
    untouched. The public output never includes original names or payloads.
    """
    dx2 = compare_export_readers(dx2_package, expected_sha256=expected_sha256)
    source = dx2_package.data  # Already exact-bytes SHA-pinned in the first pass.
    try:
        strict = audit_dx2_export_boundaries(source, source_sha256=expected_sha256)
    except ExportBoundaryError as exc:
        raise ReaderConcordanceError("strict table audit rejected source") from exc
    upkg_path = Path(__file__).resolve().parents[2] / "third_party" / "t3sdk_assets" / "upkg.py"
    try:
        reference = _source_module(upkg_path, "_dx2sdk_private_thief3_upkg")
        t3 = reference.Package("synthetic-or-private-in-memory.gmp", data=source)
    except (OSError, ValueError, IndexError, EOFError, UnicodeError, ImportError) as exc:
        raise ReaderConcordanceError("Thief reference reader rejected source") from exc
    counts = strict["table_counts"]
    if (type(getattr(t3, "file_version", None)) is not int
            or t3.file_version != dx2["version"]
            or type(getattr(t3, "licensee_version", None)) is not int
            or t3.licensee_version != dx2["licensee"]):
        raise ReaderConcordanceError("Thief reference version/licensee disagreement")
    if (type(getattr(t3, "names", None)) is not list
            or type(getattr(t3, "imports", None)) is not list
            or type(getattr(t3, "exports", None)) is not list
            or (len(t3.names), len(t3.imports), len(t3.exports))
            != (counts["names"], counts["imports"], counts["exports"])):
        raise ReaderConcordanceError("Thief reference decoded table count disagreement")
    table_starts = (
        ("name_offset", "names"),
        ("import_offset", "imports"),
        ("export_offset", "exports"),
    )
    for attr, region in table_starts:
        value = getattr(t3, attr, None)
        if type(value) is not int or value != strict["table_ranges"][region]["offset"]:
            raise ReaderConcordanceError("Thief reference table start disagreement")
    expected_header_end = strict["table_ranges"]["header"]["length"]
    if (type(getattr(t3, "header_size", None)) is not int
            or t3.header_size != expected_header_end):
        raise ReaderConcordanceError("Thief reference header end disagreement")
    for attr, region in (("import_end", "imports"), ("export_end", "exports")):
        value = getattr(t3, attr, None)
        original = strict["table_ranges"][region]
        if type(value) is not int or value != original["offset"] + original["length"]:
            raise ReaderConcordanceError("Thief reference table end disagreement")
    expected_owners = {e["export"] - 1: (e["offset"], e["length"])
                       for e in strict["candidate_export_envelopes"]}
    empty = 0
    for original_zero_based, row in enumerate(t3.exports):
        index = getattr(row, "index", None)
        length = getattr(row, "serial_size", None)
        offset = getattr(row, "serial_offset", None)
        if (type(index) is not int or index != original_zero_based
                or type(length) is not int or length < 0
                or type(offset) is not int or offset < 0):
            raise ReaderConcordanceError("Thief reference export identity invalid")
        if length == 0:
            empty += 1
            if offset != 0 or index in expected_owners:
                raise ReaderConcordanceError("Thief reference zero-size export mismatch")
        elif expected_owners.get(index) != (offset, length):
            raise ReaderConcordanceError("Thief reference export offset/length disagreement")
    if empty + len(expected_owners) != len(t3.exports):
        raise ReaderConcordanceError("Thief reference export coverage disagreement")
    return {
        "schema": SCHEMA,
        "source_sha256": expected_sha256,
        "source_size": len(source),
        "version": dx2["version"],
        "licensee": dx2["licensee"],
        "table_counts": counts,
        "matched_nonempty_exports": len(expected_owners),
        "zero_length_exports_not_owners": empty,
        "dx2_legacy_and_strict_concordant": True,
        "thief3_reference_table_concordant": True,
        "source_original_modified": False,
        "export_envelopes_independently_verified": False,
        "native_bsp_leaf_zone_decoded": False,
        "runtime_game_verified": False,
        "writable": False,
    }


def compare_local_thief_reference(path: Path, *, expected_sha256: str) -> dict:
    """Owner-only local read; never writes any output file or exports assets."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_SOURCE:
        raise ReaderConcordanceError("missing or oversized local package")
    legacy_path = Path(__file__).resolve().parents[2] / "map_exporter" / "dx2inspect.py"
    try:
        legacy = _source_module(legacy_path, "_dx2sdk_private_dx2inspect")
        pkg = legacy.Package(path)
    except (OSError, ValueError, IndexError, EOFError) as exc:
        raise ReaderConcordanceError("DX2 legacy reader rejected local source") from exc
    return compare_thief_reference(pkg, expected_sha256=expected_sha256)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", required=True, type=Path,
                        help="Explicit local owner-provided .gmp/.d2u input, read-only")
    parser.add_argument("--sha256", required=True,
                        help="Owner independently calculated lowercase SHA-256")
    args = parser.parse_args()
    try:
        result = compare_local_thief_reference(args.map, expected_sha256=args.sha256)
    except ReaderConcordanceError as exc:
        parser.exit(status=2, message="Thief reference concordance rejected: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
