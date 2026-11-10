#!/usr/bin/env python3
"""Research-only DX2 GMP static-prop unplace, not an engine-native delete.

Remove exactly ONE eligible existing StaticMeshActor from the original
Level actor reference list while preserving every original actor export.
The source GMP is read-only. A new GMP can only be written outside any
game Maps directory. This is an isolated hypothesis, NOT runtime verified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_actor_clone_probe import _candidate, _destination, _pin, MAX_FILE
from dx2_package_roundtrip import _parse_both, _validate_input, inspect_noop, sha256
from dx2_incoming_ref_audit import require_no_explicit_incoming
from t3pack import apply_edits, verify_patch

SCHEMA = "DX2Ed-experimental-static-prop-unplace-v1"
MANIFEST_SUFFIX = ".dx2ed-prop-unplace.json"
MAX_MANIFEST = 1_048_576


def _baseline(source: Path, source_sha256: str):
    source = _validate_input(Path(source))
    source_sha256 = _pin(source_sha256)
    original = source.read_bytes()
    if sha256(original) != source_sha256:
        raise ValueError("Original GMP SHA-256 mismatch")
    no_op, reconstructed = inspect_noop(source)
    if reconstructed != original or no_op["source_sha256"] != source_sha256:
        raise ValueError("Source GMP has no byte-identical writer baseline")
    pkg, native = _parse_both(source, original)
    return source, original, pkg, native


def check_actor(source: Path, *, source_sha256: str,
                actor_export: int, actor_name: str) -> dict:
    """Read-only source gate; incoming game references are still unknown."""
    source, raw, pkg, native = _baseline(source, source_sha256)
    if type(actor_name) is not str or not actor_name or len(actor_name) > 150:
        raise ValueError("Exact original actor name is required")
    exp, location = _candidate(pkg, actor_export)
    if (exp.name != actor_name
            or native.exports[actor_export - 1]["name"] != actor_name):
        raise ValueError("Original actor export/name identity mismatch")
    level = pkg.level()
    refs = pkg.level_actors()
    if level is None or refs is None or refs.count(actor_export) != 1:
        raise ValueError("Actor is not exactly once in the original Level list")
    if actor_export in refs[:2]:
        raise ValueError("Cannot remove protected LevelInfo or builder entry")
    audit = require_no_explicit_incoming(pkg, actor_export)
    return {
        "schema": SCHEMA, "status": "unplace-source-eligible",
        "source_name": source.name, "source_sha256": sha256(raw),
        "actor": actor_name, "export": actor_export, "source_location": location,
        "level_actor_count_before": len(refs),
        "level_actor_count_after": len(refs) - 1,
        "original_export_count": len(pkg.exports),
        "output_written": False, "runtime_game_verified": False,
        "incoming_references_verified": False,
        "explicit_incoming_references_checked": True,
        "explicit_incoming_reference_count": 0,
        "incoming_reference_opaque_scopes": audit["opaque_or_untyped_scopes"],
        "native_actor_deleted": False,
    }


def unplace_in_memory(source: Path, *, source_sha256: str,
                      actor_export: int, actor_name: str):
    """Create only the Level-ref-list edit, with independent package checks."""
    proof = check_actor(source, source_sha256=source_sha256,
                        actor_export=actor_export, actor_name=actor_name)
    source, original, pkg, native = _baseline(source, source_sha256)
    old_refs = pkg.level_actors()
    level = pkg.level()
    if level is None or old_refs is None:
        raise ValueError("Original map Level actor list unavailable")
    patch = apply_edits(pkg, {"actors": {}, "added": [], "removed": [actor_name]})
    expected_refs = [ref for ref in old_refs if ref != actor_export]
    if (patch.removed != [actor_name] or patch.added
            or patch.edited != [level.index]
            or patch.level_actors != expected_refs
            or len(old_refs) != len(expected_refs) + 1):
        raise ValueError("Writer attempted a change beyond one Level-list removal")
    candidate = patch.writer.write()
    if candidate == original or len(candidate) > MAX_FILE:
        raise ValueError("Unplace candidate package is unchanged or oversized")
    with tempfile.TemporaryDirectory(prefix="dx2ed-unplace-") as tmp:
        staged = Path(tmp) / source.name
        staged.write_bytes(candidate)
        fresh, fresh_native = _parse_both(staged, candidate)
    failures = verify_patch(pkg, fresh, patch)
    if failures:
        raise ValueError("Level-reference writer parity failed: " + "; ".join(failures[:6]))
    if (fresh.level_actors() != expected_refs
            or len(fresh.exports) != len(pkg.exports)
            or len(fresh.names) != len(pkg.names)
            or len(fresh.imports) != len(pkg.imports)
            or fresh_native.guid != native.guid
            or fresh_native.table_counts != native.table_counts):
        raise ValueError("Native map metadata/Level list differs from expected removal")
    for before, after in zip(pkg.exports, fresh.exports):
        if (before.name != after.name or before.class_ref != after.class_ref
                or before.flags != after.flags):
            raise ValueError("Existing export identity changed during unplace")
        if before.index != level.index and pkg.export_bytes(before) != fresh.export_bytes(after):
            raise ValueError("Original actor payload was unexpectedly modified")
    if pkg.export_bytes(pkg.exports[actor_export - 1]) != fresh.export_bytes(fresh.exports[actor_export - 1]):
        raise ValueError("Removed actor's serialized source export was altered")
    if sha256(source.read_bytes()) != source_sha256:
        raise ValueError("Source GMP changed while preparing unplace")
    return {
        **proof,
        "status": "binary-reparsed-runtime-unverified",
        "output_sha256": sha256(candidate),
        "output_bytes": len(candidate),
        "level_ref_removed": True,
        "all_original_actor_payloads_preserved": True,
        "native_actor_deleted": False,
        "output_written": False,
        "notes": (
            "Only one Level actor reference is removed; the source export is NOT deleted. "
            "DX2 native references, gameplay behavior, save/load and collision are NOT verified."
        ),
    }, candidate


def _manifest_for(output: Path) -> Path:
    return output.with_suffix(MANIFEST_SUFFIX)


def verify_saved_unplace(source: Path, output: Path, *, source_sha256: str) -> dict:
    """Independently replay from original and compare the whole saved GMP."""
    source = _validate_input(Path(source))
    output = Path(output).expanduser().resolve(strict=True)
    if (output == source or output.suffix.casefold() != ".gmp"
            or output.name.casefold() != source.name.casefold()
            or source.parent == output.parent or source.parent in output.parents):
        raise ValueError("Verifier requires an isolated, same-named GMP copy")
    manifest = _manifest_for(output)
    if not manifest.is_file() or not 0 < manifest.stat().st_size <= MAX_MANIFEST:
        raise ValueError("Missing or oversized unplace manifest")
    recorded = json.loads(manifest.read_text(encoding="utf-8"))
    if (not isinstance(recorded, dict)
            or recorded.get("schema") != SCHEMA
            or recorded.get("status") != "isolated-GMP-created-runtime-unverified"
            or recorded.get("source_name") != source.name
            or recorded.get("source_sha256") != source_sha256
            or recorded.get("output_file") != str(output)
            or recorded.get("runtime_game_verified") is not False
            or recorded.get("native_actor_deleted") is not False
            or recorded.get("incoming_references_verified") is not False
            or recorded.get("all_original_actor_payloads_preserved") is not True):
        raise ValueError("Unplace manifest does not match original and isolated output")
    actor = recorded.get("actor")
    export = recorded.get("export")
    if type(actor) is not str or type(export) is not int:
        raise ValueError("Manifest lacks exact original actor identity")
    expected, regenerated = unplace_in_memory(
        source, source_sha256=source_sha256,
        actor_export=export, actor_name=actor)
    actual = output.read_bytes()
    if (actual != regenerated
            or sha256(actual) != recorded.get("output_sha256")
            or recorded.get("level_actor_count_before") != expected["level_actor_count_before"]
            or recorded.get("level_actor_count_after") != expected["level_actor_count_after"]
            or recorded.get("original_export_count") != expected["original_export_count"]):
        raise ValueError("Saved unplace GMP differs from independently replayed source edit")
    return {
        "schema": SCHEMA, "status": "binary-verified-runtime-unverified",
        "source_sha256": source_sha256,
        "output_sha256": sha256(actual),
        "actor": actor, "export": export,
        "original_export_preserved": True,
        "level_ref_removed": True,
        "native_actor_deleted": False,
        "incoming_references_verified": False,
        "runtime_game_verified": False,
    }


def write_isolated(source: Path, output: Path, *, source_sha256: str,
                   actor_export: int, actor_name: str) -> dict:
    source = _validate_input(Path(source))
    output, clone_manifest = _destination(source, Path(output))
    manifest = _manifest_for(output)
    if manifest.exists() or clone_manifest.exists():
        raise FileExistsError("Refusing to overwrite an existing research manifest")
    report, data = unplace_in_memory(
        source, source_sha256=source_sha256,
        actor_export=actor_export, actor_name=actor_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    wrote_output = False
    wrote_manifest = False
    try:
        with output.open("xb") as stream:
            wrote_output = True
            stream.write(data)
        if sha256(output.read_bytes()) != report["output_sha256"]:
            raise ValueError("On-disk isolated unplace GMP SHA-256 mismatch")
        report["status"] = "isolated-GMP-created-runtime-unverified"
        report["output_written"] = True
        report["output_file"] = str(output)
        with manifest.open("x", encoding="utf-8") as stream:
            wrote_manifest = True
            json.dump(report, stream, indent=2)
            stream.write("\n")
        verify_saved_unplace(source, output, source_sha256=source_sha256)
    except Exception:
        if wrote_manifest:
            manifest.unlink(missing_ok=True)
        if wrote_output:
            output.unlink(missing_ok=True)
        raise
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original user-owned DX2 GMP")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--actor-export", type=int)
    parser.add_argument("--actor-name")
    parser.add_argument("--check-actor", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.verify:
            if args.output is None:
                raise ValueError("--verify requires --output")
            result = verify_saved_unplace(
                args.source, args.output, source_sha256=args.source_sha256)
        else:
            if args.actor_export is None or not args.actor_name:
                raise ValueError("Supply original --actor-export and --actor-name")
            options = dict(source_sha256=args.source_sha256,
                           actor_export=args.actor_export, actor_name=args.actor_name)
            if args.check_actor:
                if args.output is not None:
                    raise ValueError("Read-only preflight does not accept --output")
                result = check_actor(args.source, **options)
            elif args.output is not None:
                result = write_isolated(args.source, args.output, **options)
            else:
                result, _ = unplace_in_memory(args.source, **options)
    except Exception as exc:
        print(json.dumps({"schema": SCHEMA, "status": "refused",
                          "reason": str(exc) or type(exc).__name__,
                          "output_written": False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
