#!/usr/bin/env python3
"""Stage *only explicitly SHA-pinned* original DX2 EXEs/DLLs from a private ZIP.

No original binaries, unpacked ZIP members, or detailed paths go to stdout.
A Google Drive file ID is a locator, NOT a credential or permission control.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

MAX_TARGETS = 8
MAX_ZIP_BYTES = 512 * 1024 * 1024
MAX_MEMBER_BYTES = 192 * 1024 * 1024
MAX_MANIFEST_BYTES = 16384
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.(?:exe|dll)", re.I)
SHA_RE = re.compile(r"[0-9a-f]{64}")


class OriginalPEError(ValueError):
    pass


def load_expectations(manifest: Path) -> dict[str, tuple[int, str]]:
    if (not manifest.is_file() or manifest.is_symlink() or
            not 2 <= manifest.stat().st_size <= MAX_MANIFEST_BYTES):
        raise OriginalPEError("Private expected-hash manifest invalid")
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise OriginalPEError("Expected-hash manifest is not JSON") from exc
    if (type(raw) is not list or not 1 <= len(raw) <= MAX_TARGETS):
        raise OriginalPEError("Expected 1-8 original PE records")
    expected: dict[str, tuple[int, str]] = {}
    for row in raw:
        if (type(row) is not dict or set(row) != {"name", "size", "sha256"} or
                type(row["name"]) is not str or not NAME_RE.fullmatch(row["name"]) or
                type(row["size"]) is not int or not 128 <= row["size"] <= MAX_MEMBER_BYTES or
                type(row["sha256"]) is not str or not SHA_RE.fullmatch(row["sha256"])):
            raise OriginalPEError("Original PE record has invalid name, size or SHA256")
        key = row["name"].lower()
        if key in expected:
            raise OriginalPEError("Duplicate expected original PE name")
        expected[key] = (row["size"], row["sha256"])
    return expected


def _is_pe(blob: bytes) -> bool:
    if len(blob) < 128 or blob[:2] != b"MZ":
        return False
    pe_offset = int.from_bytes(blob[0x3C:0x40], "little")
    return 0x40 <= pe_offset <= len(blob) - 24 and blob[pe_offset:pe_offset+4] == b"PE\x00\x00"


def stage_archive(archive: Path, manifest: Path, output_dir: Path) -> list[dict]:
    if (not archive.is_file() or archive.is_symlink() or
            not 0 < archive.stat().st_size <= MAX_ZIP_BYTES):
        raise OriginalPEError("Private original ZIP missing or oversized")
    expected = load_expectations(manifest)
    output_dir = Path(output_dir)
    if output_dir.exists() and (not output_dir.is_dir() or output_dir.is_symlink() or
                                 any(output_dir.iterdir())):
        raise OriginalPEError("Staging destination must be new or empty")
    # Validate ALL matching files before writing anything, fail-closed.
    found: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(archive) as z:
            entries = z.infolist()
            if len(entries) > 50000:
                raise OriginalPEError("Original ZIP has too many entries")
            for info in entries:
                if info.is_dir():
                    continue
                normalized = info.filename.replace("\\", "/")
                parts = PurePosixPath(normalized).parts
                if (not parts or any(x in ("..", ".") for x in parts) or
                        normalized.startswith("/") or
                        (len(parts) > 0 and ":" in parts[0])):
                    raise OriginalPEError("Unsafe ZIP member path")
                # POSIX symlink entries are refused even if their hash is pinned.
                if (info.create_system == 3 and
                        stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK):
                    raise OriginalPEError("ZIP contains a symbolic link")
                name = parts[-1].lower()
                if name not in expected:
                    continue
                size, sha = expected[name]
                if name in found:
                    raise OriginalPEError("Duplicate PE target in original ZIP")
                if info.file_size != size or info.file_size > MAX_MEMBER_BYTES:
                    raise OriginalPEError("Original PE size mismatch")
                with z.open(info) as stream:
                    content = stream.read(size + 1)
                if (len(content) != size or not _is_pe(content) or
                        hashlib.sha256(content).hexdigest() != sha):
                    raise OriginalPEError("Original PE full SHA256 or signature mismatch")
                found[name] = content
    except (zipfile.BadZipFile, RuntimeError, EOFError, OSError) as exc:
        raise OriginalPEError("Original ZIP invalid or Drive download unavailable") from exc
    if set(found) != set(expected):
        raise OriginalPEError("Original ZIP is missing required SHA-pinned PE inputs")
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=False) if not output_dir.exists() else None
    output_dir.chmod(0o700)
    results = []
    for name in sorted(found):
        path = output_dir / name
        with path.open("xb") as stream:
            stream.write(found[name])
        path.chmod(0o600)
        results.append({"name": name, "size": len(found[name]),
                        "sha256": hashlib.sha256(found[name]).hexdigest(),
                        "stage": "verified-private"})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = stage_archive(args.archive, args.manifest, args.output_dir)
        print(json.dumps({"status": "verified-originals-staged",
                          "target_count": len(result)}))
        return 0
    except (OriginalPEError, OSError) as exc:
        reason = str(exc) if isinstance(exc, OriginalPEError) else "Private staging I/O failure"
        print(json.dumps({"status": "refused", "reason": reason}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
