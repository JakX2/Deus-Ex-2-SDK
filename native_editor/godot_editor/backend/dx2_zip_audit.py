#!/usr/bin/env python3
"""Read-only inventory of DX2 source ZIPs; never extracts or uploads game assets.

Designed for club.zip, maps.zip, and System.zip. Works with nested archive
paths in a ZIP, but does not recursively inspect ZIPs within ZIPs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

RESOURCE_EXTENSIONS = {".gmp", ".ibd", ".d2u", ".u", ".ini"}
DEFAULT_MAP = "M1_Seattle_Club.gmp"
DEFAULT_BUNDLE = "m1_club.ibd"
VERIFY_LIMIT = 512 * 1024 * 1024


def safe_member_path(name: str) -> bool:
    """Reject path traversal, absolute paths, drives and embedded NULs."""
    fixed = name.replace("\\", "/")
    if not fixed or fixed.startswith("/") or "\x00" in fixed:
        return False
    parts = fixed.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    if re.match(r"^[A-Za-z]:", parts[0]):
        return False
    return True


def resource_kind(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/")).suffix.casefold()


def audit_zip(path: Path, target_names: set[str], verify: bool = False) -> dict:
    """Read the central directory only, except optional targeted CRC checks."""
    result = {
        "archive": str(path),
        "ok": False,
        "files": 0,
        "uncompressed_bytes": 0,
        "compressed_bytes": 0,
        "resource_counts": {},
        "target_matches": [],
        "examples": [],
        "warnings": [],
    }
    try:
        with zipfile.ZipFile(path) as z:
            infos = [info for info in z.infolist() if not info.is_dir()]
            result["files"] = len(infos)
            result["uncompressed_bytes"] = sum(i.file_size for i in infos)
            result["compressed_bytes"] = sum(i.compress_size for i in infos)
            resource_counts = Counter()
            seen = set()
            examples = defaultdict(list)
            for info in infos:
                name = info.filename
                if not safe_member_path(name):
                    result["warnings"].append("Unsafe member path: " + repr(name))
                    continue
                folded = name.casefold()
                if folded in seen:
                    result["warnings"].append("Duplicate internal path: " + name)
                seen.add(folded)
                kind = resource_kind(name)
                if kind in RESOURCE_EXTENSIONS:
                    resource_counts[kind] += 1
                    if len(examples[kind]) < 12:
                        examples[kind].append(name)
                if info.flag_bits & 1:
                    result["warnings"].append("Encrypted entry: " + name)
                if info.file_size > 32 * 1024 * 1024 and info.compress_size and info.file_size > info.compress_size * 1000:
                    result["warnings"].append("Extreme expansion ratio: " + name)
                basename = PurePosixPath(name.replace("\\", "/")).name.casefold()
                if basename in target_names:
                    match = {
                        "path": name, "basename": basename,
                        "bytes": info.file_size, "encrypted": bool(info.flag_bits & 1),
                        "crc_checked": False,
                    }
                    if verify:
                        if info.file_size > VERIFY_LIMIT:
                            result["warnings"].append("Skipped CRC verification (size limit): " + name)
                        elif info.flag_bits & 1:
                            result["warnings"].append("Skipped CRC verification (encrypted): " + name)
                        else:
                            try:
                                with z.open(info) as reader:
                                    while reader.read(1024 * 1024):
                                        pass
                                match["crc_checked"] = True
                            except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
                                result["warnings"].append("CRC/read failure for " + name + ": " + str(exc))
                    result["target_matches"].append(match)
            result["resource_counts"] = dict(sorted(resource_counts.items()))
            result["examples"] = [{"type": k, "paths": v} for k, v in sorted(examples.items())]
            result["ok"] = True
    except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        result["warnings"].append(type(exc).__name__ + ": " + str(exc))
    return result


def audit_archives(paths: list[Path], target_map: str = DEFAULT_MAP,
                   target_bundle: str = DEFAULT_BUNDLE, verify: bool = False) -> dict:
    wanted = {target_map.casefold(), target_bundle.casefold()}
    archives = [audit_zip(p, wanted, verify) for p in paths]
    occurrences = defaultdict(list)
    for row in archives:
        for match in row["target_matches"]:
            occurrences[match["basename"]].append({
                "archive": row["archive"], "member": match["path"],
                "bytes": match["bytes"], "crc_checked": match["crc_checked"],
            })
    found = {name: occurrences.get(name, []) for name in sorted(wanted)}
    # Finding both names does not imply their contents or resource references
    # are valid. Keep this an explicit name-only preflight.
    ready = all(found[name] for name in wanted)
    return {
        "schema": "DX2Ed-archive-audit-v1",
        "scope": "ZIP central-directory inventory only, not GMP/IBD content decoding",
        "read_only": True,
        "target_map": target_map,
        "target_bundle": target_bundle,
        "named_pair_present": bool(ready),
        "targets": found,
        "archives": archives,
        "warnings": ([] if ready else ["Target GMP/IBD names not both found; check spelling or archive contents."]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archives", nargs="+", type=Path, help="Local ZIP archives to inspect")
    ap.add_argument("--target-map", default=DEFAULT_MAP)
    ap.add_argument("--target-bundle", default=DEFAULT_BUNDLE)
    ap.add_argument("--verify-target-crc", action="store_true",
                    help="Stream only named target files to check their ZIP CRCs, with a 512 MiB per-file limit")
    ap.add_argument("--output", type=Path, help="Write JSON diagnostics; no game file contents included")
    ns = ap.parse_args(argv)
    report = audit_archives(ns.archives, ns.target_map, ns.target_bundle, ns.verify_target_crc)
    payload = json.dumps(report, indent=2)
    if ns.output:
        dest = ns.output.expanduser().resolve()
        # Never replace any of the supplied archives.
        if dest in {a.expanduser().resolve() for a in ns.archives}:
            ap.error("Report output cannot replace a source archive")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if all(x["ok"] for x in report["archives"]) else 1


if __name__ == "__main__":
    sys.exit(main())
