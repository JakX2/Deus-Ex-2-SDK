#!/usr/bin/env python3
"""Independent, read-only preflight for an experimental DX2 GameSys GMP edit.

Inputs: original user-owned DX2 GMP, separately saved candidate GMP and
adjacent dx2ed-gamesys-scalar.json manifest created by scalar_probe.py.

This checker reopens BOTH actual files with independently implemented DX2
and MIT T3SDK package readers, re-scans the original and changed GameSys
block, and requires the entire binary diff to be confined to ONE existing
4-byte int32/float32 payload. It does not trust manifest claims of success.

No files are changed. --report may create NEW JSON outside the source Maps
folder. A PASS is **binary compatibility preflight**, NEVER game loading
or gameplay verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_package_roundtrip import _parse_both, _validate_input
from dx2_gamesys_audit import scan_dx2_gamesys
from dx2_gamesys_scalar_probe import SCHEMA as SCALAR_SCHEMA, KIND

SCHEMA = "DX2Ed-Gamesys-runtime-preflight-v1"
MAX_MANIFEST_BYTES = 1_048_576


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_hash(raw: str, label: str) -> str:
    if not isinstance(raw, str) or len(raw) != 64 or any(c not in "0123456789abcdef" for c in raw):
        raise ValueError(f"Invalid {label}: expected lowercase SHA-256")
    return raw


def _read_manifest(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Missing or excessive GameSys scalar manifest")
    manifest = json.loads(path.read_text(encoding="utf8"))
    if not isinstance(manifest, dict):
        raise ValueError("GameSys scalar manifest must be an object")
    if (manifest.get("schema") != SCALAR_SCHEMA
            or manifest.get("status") != "written-isolated-runtime-unverified"
            or manifest.get("full_package_byte_match") is not True
            or manifest.get("edited_package_written") is not True
            or manifest.get("experimental_single_scalar_save_as") is not True
            or manifest.get("runtime_verified") is not False
            or manifest.get("native_gamesys_save_enabled") is not False):
        raise ValueError("Manifest is not a successful isolated, runtime-unverified single-scalar research save")
    return manifest


def _unique_block(pkg, export: dict, pid: int) -> dict:
    blocks, _ = scan_dx2_gamesys(pkg, export)
    hits = [b for b in blocks if b["property_id"] == pid]
    if len(hits) != 1:
        raise ValueError("GameSys property ID must occur exactly once in selected actor")
    return hits[0]


def verify_isolated_scalar(
    original: Path, candidate: Path, *, manifest_path: Path | None = None,
) -> dict:
    original = _validate_input(original)
    candidate = _validate_input(candidate)
    if (candidate == original
            or candidate.name.casefold() != original.name.casefold()
            or candidate.parent == original.parent
            or original.parent in candidate.parents):
        raise ValueError("Edited GMP must be a same-named copy outside the original Maps folder")
    manifest_path = (Path(manifest_path).expanduser().resolve()
                     if manifest_path is not None else candidate.with_suffix(".dx2ed-gamesys-scalar.json"))
    if manifest_path != candidate.with_suffix(".dx2ed-gamesys-scalar.json"):
        raise ValueError("Manifest must be the candidate GMP's adjacent exact-name report")
    record = _read_manifest(manifest_path)
    before, after = original.read_bytes(), candidate.read_bytes()
    source_sha, candidate_sha = digest(before), digest(after)

    for field, actual in (
        ("original_sha256", source_sha),
        ("reconstructed_sha256", candidate_sha),
        ("output_sha256", candidate_sha),
    ):
        if _check_hash(record.get(field), field) != actual:
            raise ValueError(f"Manifest {field} differs from actual original/edited GMP")
    if record.get("source_map") != original.name or Path(str(record.get("output", ""))).resolve() != candidate:
        raise ValueError("Manifest original map or edited output path does not match supplied files")
    if len(before) != len(after):
        raise ValueError("Modified GMP changed source byte length")
    if source_sha == candidate_sha:
        raise ValueError("Candidate GMP is unchanged")
    if type(record.get("actor_export")) is not int or record["actor_export"] < 1:
        raise ValueError("Manifest has invalid one-based actor export")
    if type(record.get("property_id")) is not int or not 0 < record["property_id"] <= 65535:
        raise ValueError("Manifest has invalid GameSys property ID")
    kind = record.get("kind")
    if kind not in KIND:
        raise ValueError("Manifest contains unsupported scalar encoding")
    encoding, fmt = KIND[kind]
    offset = record.get("original_payload_offset")
    if type(offset) is not int or offset < 0 or offset + 4 > len(before):
        raise ValueError("Manifest contains invalid scalar source byte offset")
    first = record.get("original_value_bytes")
    next_ = record.get("proposed_value_bytes")
    try:
        old_value, new_value = bytes.fromhex(first), bytes.fromhex(next_)
    except (TypeError, ValueError) as error:
        raise ValueError("Manifest contains malformed scalar bytes") from error
    if len(old_value) != 4 or len(new_value) != 4 or old_value == new_value:
        raise ValueError("Manifest scalar must describe an actual four-byte value change")
    if before[offset:offset + 4] != old_value or after[offset:offset + 4] != new_value:
        raise ValueError("Recorded scalar bytes do not match either actual GMP")
    if record.get("original_payload_sha256") != digest(old_value):
        raise ValueError("Manifest original GameSys payload hash mismatch")
    if kind == "float":
        if any(not math.isfinite(struct.unpack(fmt, raw)[0])
               for raw in (old_value, new_value)):
            raise ValueError("Float32 scalar is not finite")
    changed_offsets = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    if (not changed_offsets
            or any(not offset <= i < offset + 4 for i in changed_offsets)
            or record.get("changed_bytes") != len(changed_offsets)):
        raise ValueError("Edited GMP differs outside its four-byte GameSys scalar, or manifest diff count is wrong")

    # Strict package reader agreement separately for ACTUAL files on disk.
    a_t3, a_dx2 = _parse_both(original, before)
    b_t3, b_dx2 = _parse_both(candidate, after)
    if (len(a_dx2.exports) != len(b_dx2.exports)
            or a_dx2.guid != b_dx2.guid
            or a_dx2.names != b_dx2.names
            or a_t3.ion_extra != b_t3.ion_extra):
        raise ValueError("Edited GMP altered original package tables, GUID or fixed metadata")
    index = record["actor_export"] - 1
    if index >= len(a_dx2.exports):
        raise ValueError("Manifest actor export outside map export table")
    original_export, edited_export = a_dx2.exports[index], b_dx2.exports[index]
    if (original_export["name"] != record.get("actor")
            or edited_export["name"] != record.get("actor")
            or original_export["offset"] != edited_export["offset"]
            or original_export["size"] != edited_export["size"]
            or original_export["flags"] != edited_export["flags"]):
        raise ValueError("Selected actor export identity changed")
    original_block = _unique_block(a_dx2, original_export, record["property_id"])
    edited_block = _unique_block(b_dx2, edited_export, record["property_id"])
    if (original_block["payload_offset"] != offset
            or edited_block["payload_offset"] != offset
            or original_block["payload_bytes"] != 4
            or edited_block["payload_bytes"] != 4
            or original_block["encoded_id"] != record.get("encoded_property_id")
            or edited_block["encoded_id"] != original_block["encoded_id"]
            or original_block["version"] != record.get("property_version")
            or edited_block["version"] != original_block["version"]
            or original_block["encoding_code"] != encoding
            or original_block["runtime_flag"] or edited_block["runtime_flag"]
            or original_block["payload_sha256"] != digest(old_value)
            or edited_block["payload_sha256"] != digest(new_value)):
        raise ValueError("Original/edited native GameSys property framing mismatch")
    # Ensure a race/replacement did not change files during analysis.
    if digest(original.read_bytes()) != source_sha or digest(candidate.read_bytes()) != candidate_sha:
        raise ValueError("One of the GMPs changed during preflight")

    return {
        "schema": SCHEMA,
        "status": "binary-preflight-passed-runtime-not-tested",
        "original_file": str(original),
        "edited_file": str(candidate),
        "manifest_file": str(manifest_path),
        "original_sha256": source_sha,
        "edited_sha256": candidate_sha,
        "original_file_untouched": True,
        "source_map": original.name,
        "actor_export": index + 1,
        "actor": record["actor"],
        "actor_class": a_dx2.class_name(original_export),
        "property_id": record["property_id"],
        "encoded_property_id": original_block["encoded_id"],
        "property_version": original_block["version"],
        "scalar_type": kind,
        "original_value": struct.unpack(fmt, old_value)[0],
        "edited_value": struct.unpack(fmt, new_value)[0],
        "original_payload_offset": offset,
        "changed_byte_offsets": changed_offsets,
        "changed_bytes": len(changed_offsets),
        "full_package_length_unchanged": True,
        "package_parsers_agree": True,
        "source_and_edited_blocks_verified": True,
        "game_runtime_tested": False,
        "gameplay_effect_confirmed": False,
        "test_environment": "NOT TESTED",
        "warnings": [
            "PASS only means binary metadata, intended scalar and isolated copy match exactly.",
            "This does NOT verify the game can load the GMP or that the property affects gameplay.",
            "Install only in a disposable game copy, never the retail/source directory.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--report", type=Path, help="Write new JSON outside original map directory")
    args = parser.parse_args(argv)
    try:
        original, candidate = _validate_input(args.original), _validate_input(args.candidate)
        output = args.report.expanduser().resolve() if args.report else None
        if output is not None:
            if (output.suffix.casefold() != ".json"
                    or output in (original, candidate)
                    or output == candidate.with_suffix(".dx2ed-gamesys-scalar.json")
                    or original.parent in output.parents):
                raise ValueError("Report must be a separate new JSON outside source maps")
            if output.exists():
                raise FileExistsError("Refusing to overwrite existing binary preflight report")
        report = verify_isolated_scalar(original, candidate, manifest_path=args.manifest)
        if output is None:
            print(json.dumps(report, indent=2, allow_nan=False))
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf8") as f:
                json.dump(report, f, indent=2, allow_nan=False)
                f.write("\n")
            print(json.dumps({"status": report["status"], "report": str(output)}))
        return 0
    except (ValueError, TypeError, OSError, IndexError, EOFError, struct.error) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
