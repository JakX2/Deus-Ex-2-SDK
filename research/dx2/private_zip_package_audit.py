"""Privacy-preserving, read-only concordance scan of a local DX2 ZIP archive.

Checks the three experimental DX2/T3 source readers on each eligible package
member entirely in memory, without extraction. Emits aggregate counts only;
never prints original member names, offsets, payload bytes or local paths.

Research only. A passing map is not evidence of native BSP/zone ownership,
runtime compatibility, or write permission.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import stat
from zipfile import BadZipFile, ZipFile, ZIP_DEFLATED, ZIP_STORED

from dx2_export_boundary_audit import MAX_SOURCE
from export_reader_concordance import ReaderConcordanceError
from thief3_export_concordance import _source_module, compare_thief_reference

SCHEMA = "DX2SDK-private-zip-package-concordance-v1"
MAX_ARCHIVE_BYTES = 384 * 1024 * 1024
MAX_ENTRIES = 4096
MAX_PACKAGES = 512
MAX_TOTAL_UNCOMPRESSED = 2 * 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200


class PrivateZipAuditError(ValueError):
    """Unsafe, ambiguous or unsupported local archive input."""


def _is_safe_member(info) -> bool:
    # No extraction occurs, but still reject surprising names and symlinks.
    path = info.filename.replace("\\", "/")
    components = path.split("/")
    mode = (info.external_attr >> 16) & 0xffff
    return (bool(path) and not path.startswith("/")
            and not any(c in ("", ".", "..") for c in components)
            and not (info.create_system == 3 and stat.S_ISLNK(mode)))


def inspect_private_zip_bytes(
    source: bytes, *,
    expected_sha256: str | None = None,
    max_files: int = 256,
) -> dict:
    """Inspect only exact immutable bytes, with bounded member reads.

    An expected SHA is optional; when omitted, digest identity is derived
    from these same immutable archive bytes (not independently verified).
    """
    if type(source) is not bytes or len(source) > MAX_ARCHIVE_BYTES:
        raise PrivateZipAuditError("invalid or oversized immutable ZIP input")
    if type(max_files) is not int or not 1 <= max_files <= MAX_PACKAGES:
        raise PrivateZipAuditError("invalid bounded package count")
    digest = sha256(source).hexdigest()
    supplied = expected_sha256 is not None
    if supplied:
        if (type(expected_sha256) is not str
                or len(expected_sha256) != 64
                or any(c not in "0123456789abcdef" for c in expected_sha256)
                or expected_sha256 != digest):
            raise PrivateZipAuditError("ZIP SHA-256 mismatch")
    try:
        archive = ZipFile(BytesIO(source), "r")
    except (BadZipFile, OSError, ValueError) as exc:
        raise PrivateZipAuditError("invalid ZIP central directory") from exc

    counters = Counter()
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            raise PrivateZipAuditError("too many ZIP directory entries")
        seen = set()
        for info in infos:
            # Even a normal ZIP can legally repeat names, but that makes
            # ownership ambiguous, so fail closed without emitting names.
            key = info.filename.replace("\\", "/").casefold()
            if key in seen:
                raise PrivateZipAuditError("ambiguous duplicate ZIP member names")
            seen.add(key)
        eligible = [i for i in infos if not i.is_dir()
                    and i.filename.lower().endswith((".gmp", ".d2u"))]
        if not eligible:
            raise PrivateZipAuditError("no explicit GMP/D2U package members")
        if len(eligible) > max_files:
            raise PrivateZipAuditError("package count exceeds explicit limit")
        if sum(i.file_size for i in eligible) > MAX_TOTAL_UNCOMPRESSED:
            raise PrivateZipAuditError("uncompressed package budget exceeded")
        counters["eligible_packages"] = len(eligible)
        # Stable traversal is internal only; original member names are never
        # sent back to the caller as a list or copied into an artifact.
        eligible.sort(key=lambda i: (i.filename.casefold(), i.filename))
        legacy_path = (Path(__file__).resolve().parents[2] / "map_exporter"
                       / "dx2inspect.py")
        legacy = _source_module(legacy_path, "_dx2sdk_zip_in_memory_package")
        for info in eligible:
            if not _is_safe_member(info):
                counters["unsafe_entry_rejected"] += 1
                continue
            if (info.flag_bits & 1
                    or info.compress_type not in (ZIP_STORED, ZIP_DEFLATED)):
                counters["unsupported_entry_rejected"] += 1
                continue
            if (info.file_size > MAX_SOURCE
                    or info.file_size > MAX_COMPRESSION_RATIO
                    * max(1, info.compress_size)):
                counters["oversized_or_high_ratio_rejected"] += 1
                continue
            try:
                # ZipFile.open() uses the central-directory ZipInfo object,
                # so duplicate names cannot silently select another entry.
                with archive.open(info, "r") as stream:
                    member = stream.read(MAX_SOURCE + 1)
                if len(member) != info.file_size:
                    raise BadZipFile("member size mismatch")
            except (BadZipFile, OSError, EOFError, RuntimeError, ValueError):
                counters["unreadable_entry_rejected"] += 1
                continue
            # The legacy Package only receives a fixed synthetic label and
            # immutable package data. It must not reopen or write a ZIP member.
            try:
                package = legacy.Package("source-in-memory.gmp", data=member)
            except (ValueError, IndexError, EOFError, OSError):
                counters["legacy_reader_rejected"] += 1
                continue
            try:
                compare_thief_reference(
                    package, expected_sha256=sha256(member).hexdigest())
            except ReaderConcordanceError:
                counters["cross_reader_rejected"] += 1
                continue
            counters["three_reader_concordant"] += 1

    category_names = (
        "eligible_packages",
        "three_reader_concordant",
        "legacy_reader_rejected",
        "cross_reader_rejected",
        "unreadable_entry_rejected",
        "oversized_or_high_ratio_rejected",
        "unsafe_entry_rejected",
        "unsupported_entry_rejected",
    )
    result_counts = {name: counters[name] for name in category_names}
    if sum(value for key, value in result_counts.items()
           if key != "eligible_packages") != result_counts["eligible_packages"]:
        raise PrivateZipAuditError("incomplete audit outcome accounting")
    return {
        "schema": SCHEMA,
        "status": "aggregate-only",
        "archive_sha256_pinned_to_immutable_bytes": True,
        "archive_sha256_independently_supplied": supplied,
        "package_source_bytes_verified_per_reader": True,
        "zip_member_payloads_written_to_disk": False,
        "package_files_modified": False,
        "package_names_and_offsets_emitted": False,
        "archive_entries_total": len(infos),
        "counts": result_counts,
        "export_envelopes_independently_verified": False,
        "native_bsp_leaf_zone_decoded": False,
        "runtime_game_verified": False,
        "writable": False,
    }


def inspect_private_zip_file(
    path: Path, *,
    expected_sha256: str | None = None,
    max_files: int = 256,
) -> dict:
    """One opt-in local file read, preserving input bytes without extraction."""
    path = Path(path)
    try:
        details = path.lstat()
        if not stat.S_ISREG(details.st_mode) or details.st_size > MAX_ARCHIVE_BYTES:
            raise PrivateZipAuditError("input is not a bounded regular ZIP file")
        with path.open("rb") as handle:
            source = handle.read(MAX_ARCHIVE_BYTES + 1)
    except OSError as exc:
        raise PrivateZipAuditError("cannot read local ZIP input") from exc
    return inspect_private_zip_bytes(
        source, expected_sha256=expected_sha256, max_files=max_files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path,
                        help="Explicit local DX2 map ZIP (read-only; no extraction)")
    parser.add_argument("--sha256", default=None,
                        help="Optional independently calculated lowercase ZIP SHA")
    parser.add_argument("--max-files", type=int, default=256,
                        help="Maximum eligible package members, 1..512")
    args = parser.parse_args()
    try:
        report = inspect_private_zip_file(
            args.archive, expected_sha256=args.sha256,
            max_files=args.max_files)
    except PrivateZipAuditError as exc:
        parser.exit(status=2, message="Private ZIP audit rejected: " + str(exc) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
