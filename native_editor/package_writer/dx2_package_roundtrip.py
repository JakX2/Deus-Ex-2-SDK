#!/usr/bin/env python3
"""DX2 v95 package NO-OP writer adapter, using MIT-licensed T3SDK code.

This is a deliberately narrow first bridge to T3SDK's package writer.
No mutations are permitted. The writer must reconstruct every source byte
exactly and an independent DX2 parser must agree on the package identity.

This is NOT a gameplay-verified DX2 compiler or edited-actor serializer.

CLI:
  python native_editor/package_writer/dx2_package_roundtrip.py audit retail.gmp
  python native_editor/package_writer/dx2_package_roundtrip.py copy retail.gmp --output /isolated/M1_map.gmp
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
T3SDK = ROOT / "third_party" / "t3sdk_assets"
MAP_EXPORTER = ROOT / "map_exporter"
for dependency in (str(T3SDK), str(MAP_EXPORTER)):
    if dependency not in sys.path:
        sys.path.insert(0, dependency)

from upkg import Package as T3Package  # noqa: E402
from upkgwrite import PackageWriter, first_difference  # noqa: E402
from dx2inspect import Package as DX2Package  # noqa: E402

SCHEMA = "DX2Ed-T3SDK-noop-package-roundtrip-v1"
MAX_PACKAGE_BYTES = 256 * 1024 * 1024
SUPPORTED_LICENSEES = frozenset((68, 69))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_input(source: Path) -> Path:
    source = source.expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.casefold() != ".gmp":
        raise ValueError("Source must be an existing DX2 .gmp file")
    if not 0 < source.stat().st_size <= MAX_PACKAGE_BYTES:
        raise ValueError("Source GMP exceeds supported size limits")
    return source


def _parse_both(source: Path, raw: bytes) -> tuple[T3Package, DX2Package]:
    # Independent SDK implementation prevents an upstream writer and its
    # paired reader from jointly accepting a mistaken file interpretation.
    t3 = T3Package(source, data=raw)
    dx2 = DX2Package(source)
    if raw != dx2.data:
        raise ValueError("Source changed while independent DX2 parser read it")
    if t3.file_version != 95 or dx2.version != 95:
        raise ValueError("Only Ion Storm v95 GMP packages are supported")
    if t3.licensee_version not in SUPPORTED_LICENSEES or dx2.licensee != t3.licensee_version:
        raise ValueError("Not a supported DX2 licensee version (68 or 69)")
    if (len(t3.names), len(t3.imports), len(t3.exports)) != dx2.table_counts:
        raise ValueError("Original T3SDK and DX2 parsers disagree on table counts")
    if t3.guid.hex() != dx2.guid:
        raise ValueError("Original T3SDK and DX2 parsers disagree on GUID")
    if t3.names != dx2.names:
        raise ValueError("Original T3SDK and DX2 parsers disagree on package names")
    for i, (a, b) in enumerate(zip(t3.exports, dx2.exports)):
        if a.name != b["name"] or a.serial_offset != b["offset"] or a.serial_size != b["size"]:
            raise ValueError(f"Original parsers disagree on export {i + 1}")
    return t3, dx2


def inspect_noop(source: Path) -> tuple[dict, bytes]:
    """Rebuild in memory; fail closed unless both parsers and every byte agree."""
    source = _validate_input(source)
    raw = source.read_bytes()
    t3, _ = _parse_both(source, raw)
    writer = PackageWriter(t3)
    rewritten = writer.write()
    difference = first_difference(raw, rewritten)
    if difference is not None:
        raise ValueError(
            f"T3SDK package no-op rewrite changed bytes at offset {difference}; "
            "DX2 output blocked"
        )
    if len(raw) != len(rewritten):
        raise ValueError("T3SDK package no-op rewrite changed file length")
    report = {
        "schema": SCHEMA, "status": "byte-identical",
        "source": str(source), "source_sha256": sha256(raw),
        "reconstructed_sha256": sha256(rewritten),
        "bytes": len(raw), "package_version": t3.file_version,
        "licensee_version": t3.licensee_version,
        "package_guid": t3.guid.hex(),
        "name_count": len(t3.names),
        "import_count": len(t3.imports),
        "export_count": len(t3.exports),
        "byte_identical": True,
        "edited_exports": 0, "added_exports": 0,
        "source_modified": False,
        "runtime_game_verified": False,
        "writer": "T3SDK upkgwrite.PackageWriter (MIT, vendored unchanged)",
        "notes": [
            "Exact package no-op reserialization only; no actor, geometry or scripts are edited.",
            "An independent DX2 reader agrees on source GUID, names and export table metadata.",
            "Byte identity does not demonstrate in-game loading of edited packages.",
            "IBD resources and BSP/collision rebuilding are separate future work.",
        ],
    }
    return report, rewritten


def _check_copy_destination(source: Path, output: Path) -> Path:
    output = output.expanduser().resolve()
    if output.suffix.casefold() != ".gmp" or output.name.casefold() != source.name.casefold():
        raise ValueError("Copy must retain the exact source GMP filename and extension")
    if output == source or output.parent == source.parent or source.parent in output.parents:
        raise ValueError("Output must be outside the original source map directory")
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing GMP")
    if output.with_suffix(".dx2ed-roundtrip.json").exists():
        raise FileExistsError("Refusing to overwrite an existing round-trip manifest")
    return output


def write_noop_copy(source: Path, output: Path) -> dict:
    """Write an identical copy elsewhere, preserving original GMP untouched."""
    source = _validate_input(source)
    output = _check_copy_destination(source, output)
    report, rewritten = inspect_noop(source)
    # Recheck source before saving to prevent stale-source races.
    if sha256(source.read_bytes()) != report["source_sha256"]:
        raise ValueError("Source GMP changed after preflight audit")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = output.with_suffix(".dx2ed-roundtrip.json")
    try:
        with output.open("xb") as handle:
            handle.write(rewritten)
        actual = output.read_bytes()
        if actual != rewritten:
            raise ValueError("Disk copy differs from rebuilt package")
        # Independently validate the saved artifact.
        _parse_both(output, actual)
        report.update(status="written-identical-unverified", output=str(output),
                      output_sha256=sha256(actual), runtime_game_verified=False)
        with manifest.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except Exception:
        # Only delete the copy we created; never delete preexisting paths.
        output.unlink(missing_ok=True)
        raise
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="Read-only byte-identical no-op audit")
    audit.add_argument("source", type=Path)
    copy = sub.add_parser("copy", help="Write a byte-identical GMP into a separate folder")
    copy.add_argument("source", type=Path)
    copy.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "audit":
            report, _ = inspect_noop(args.source)
        else:
            report = write_noop_copy(args.source, args.output)
        print(json.dumps(report, indent=2))
        return 0
    except (OSError, ValueError, IndexError, OverflowError) as err:
        print(json.dumps({"status": "error", "error": str(err)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
