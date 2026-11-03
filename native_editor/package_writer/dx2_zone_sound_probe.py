#!/usr/bin/env python3
"""Experimental DX2 ZoneProperties audio-schema edit; isolated GMP only.

This does NOT create sound emitters or compile .csc files. It rewrites one
original authored, non-runtime string in an existing ZoneProperties actor,
using a replacement already observed in the same property of this map.
Every other serialized object and native field is independently verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
for folder in (HERE, HERE.parents[1] / "third_party" / "t3sdk_assets"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from dx2_actor_clone_probe import _destination, _pin
from dx2_package_roundtrip import _parse_both, _validate_input, inspect_noop, sha256
from t3pack import apply_edits, verify_patch
from upkgwrite import ActorEdit, PackageWriter

SCHEMA = "DX2Ed-experimental-existing-zone-schema-v1"
AUDIO_PROPERTIES = {
    1287: "StreamSchema1",
    1286: "StreamSchema2",
    1467: "NonStreamSchema1",
}
SOUND_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,95}\Z")
RESERVED = {"silence", "inaccessible", "outside_world", "elevator"}


def _zone_property(pkg, export_num: int, actor_name: str, pid: int):
    if type(export_num) is not int or not 1 <= export_num <= len(pkg.exports):
        raise ValueError("Original one-based zone export index out of range")
    if pid not in AUDIO_PROPERTIES:
        raise ValueError("Only first-party DX2 ZoneProperties sound schema fields are allowed")
    exp = pkg.exports[export_num - 1]
    if exp.name != actor_name or pkg.export_class(exp) != "ZoneProperties":
        raise ValueError("Exact original ZoneProperties actor/export identity required")
    refs = pkg.level_actors()
    if refs is None or refs.count(export_num) != 1 or export_num in refs[:2]:
        raise ValueError("Original sound-zone actor must occur exactly once in Level")
    actor = pkg.read_actor(exp)
    if actor.state is None or actor.parse_error or actor.links or actor.tail not in (b"", b"\0" * 4):
        raise ValueError("Zone actor has unverified native content or links")
    blocks = [b for b in actor.gamesys if b.prop_id == pid]
    if len(blocks) != 1 or blocks[0].kind != "string" or blocks[0].runtime:
        raise ValueError("Sound field must be exactly one authored, non-runtime string")
    if not isinstance(blocks[0].value, str):
        raise ValueError("Original sound field is not a decoded string")
    return exp, actor, blocks[0]


def _allowed_existing_schemas(pkg, pid: int) -> set[str]:
    refs = set(pkg.level_actors() or [])
    out = set()
    for exp in pkg.exports:
        if exp.index + 1 not in refs or pkg.export_class(exp) != "ZoneProperties":
            continue
        actor = pkg.read_actor(exp)
        if actor.parse_error:
            continue
        for block in actor.gamesys:
            if block.prop_id == pid and block.kind == "string" and not block.runtime:
                if isinstance(block.value, str) and SOUND_NAME.fullmatch(block.value):
                    if block.value.casefold() not in RESERVED:
                        out.add(block.value)
    return out


def compare_zone_schema(source: Path, *, source_sha256: str, actor_export: int,
                        actor_name: str, property_id: int, expect: str,
                        replace: str) -> tuple[dict, bytes]:
    source = _validate_input(Path(source))
    source_sha256 = _pin(source_sha256)
    original = source.read_bytes()
    if sha256(original) != source_sha256:
        raise ValueError("Original GMP SHA-256 mismatch")
    noop_report, noop = inspect_noop(source)
    if noop != original or noop_report["source_sha256"] != source_sha256:
        raise ValueError("Original GMP not proven byte-identical under no-op writer")
    pkg, independent = _parse_both(source, original)
    exp, actor, block = _zone_property(pkg, actor_export, actor_name, property_id)
    if type(expect) is not str or expect != block.value:
        raise ValueError("Expected original sound schema string does not match GMP")
    if (type(replace) is not str or not SOUND_NAME.fullmatch(replace)
            or replace == expect or replace not in _allowed_existing_schemas(pkg, property_id)):
        raise ValueError("Replacement must be another named schema already used by this exact property in the original map")
    patch = apply_edits(pkg, {
        "actors": {actor_name: {"gamesys": {f"prop{property_id}": replace}}},
        "added": [], "removed": []
    })
    if patch.edited != [exp.index] or patch.added or patch.removed or patch.level_actors is not None:
        raise ValueError("Sound schema writer attempted changes beyond one original actor")
    candidate = patch.writer.write()
    if candidate == original:
        raise ValueError("Sound schema writer performed no modification")
    with tempfile.TemporaryDirectory(prefix="dx2ed-zone-audio-") as td:
        temp = Path(td) / source.name
        temp.write_bytes(candidate)
        newer, native = _parse_both(temp, candidate)
    problems = verify_patch(pkg, newer, patch)
    if problems:
        raise ValueError("Original-format T3SDK patch verification failed: " + "; ".join(problems[:5]))
    if (len(newer.exports) != len(pkg.exports)
            or len(native.exports) != len(independent.exports)
            or native.guid != independent.guid
            or len(newer.names) != len(pkg.names) or len(newer.imports) != len(pkg.imports)
            or newer.level_actors() != pkg.level_actors()):
        raise ValueError("Sound zone edit changed package tables, GUID or Level membership")
    for before, after in zip(pkg.exports, newer.exports):
        if (before.name != after.name or before.class_ref != after.class_ref
                or before.flags != after.flags):
            raise ValueError("Original actor export identity changed")
        if before.index != exp.index and pkg.export_bytes(before) != newer.export_bytes(after):
            raise ValueError(f"Unrelated original export #{before.index+1} changed")
    new_exp, new_actor, changed = _zone_property(newer, actor_export, actor_name, property_id)
    if (changed.value != replace or changed.version != block.version
            or changed.id != block.id or new_actor.state != actor.state
            or new_actor.links != actor.links or new_actor.tail != actor.tail):
        raise ValueError("Sound change altered original actor state, block encoding or native data")
    # Undo only the one audio field on the newly serialized actor and
    # demand exact original actor payload bytes, even if string lengths differ.
    back = PackageWriter(newer)
    undo = ActorEdit(back, new_exp)
    undo.set_block(property_id, block.data, f"revert_{property_id}")
    undo.commit()
    if back.object_data(new_exp.index) != pkg.export_bytes(exp):
        raise ValueError("Reverse audio change did not reproduce exact original actor bytes")
    if sha256(source.read_bytes()) != source_sha256:
        raise ValueError("Original GMP changed during experiment")
    report = {
        "schema": SCHEMA, "status": "in-memory-verified-runtime-unverified",
        "source_map": source.name, "source_sha256": source_sha256,
        "output_sha256": sha256(candidate), "actor": actor_name,
        "actor_export": actor_export, "actor_class": "ZoneProperties",
        "property_id": property_id, "property_name": AUDIO_PROPERTIES[property_id],
        "original_schema": expect, "replacement_schema": replace,
        "allowed_replacements": sorted(_allowed_existing_schemas(pkg, property_id)),
        "same_native_state": True, "original_exports_preserved_except_target": True,
        "reverse_payload_parity": True, "source_modified": False,
        "game_installation_modified": False, "runtime_verified": False,
        "creates_sound_emitter": False
    }
    return report, candidate


def write_isolated(source: Path, output: Path, **kwargs):
    source = _validate_input(Path(source))
    output, old_manifest = _destination(source, Path(output))
    manifest = output.with_suffix(".dx2ed-sound-zone.json")
    if manifest.exists() or old_manifest.exists():
        raise FileExistsError("Refusing existing sound-zone output report")
    result, candidate = compare_zone_schema(source, **kwargs)
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open("xb") as handle:
            created = True
            handle.write(candidate)
        if sha256(output.read_bytes()) != result["output_sha256"]:
            raise ValueError("Written sound-zone GMP hash mismatch")
        _parse_both(output, candidate)
        result.update({"status": "isolated-gmp-written-runtime-unverified",
                       "output": str(output)})
        with manifest.open("x", encoding="utf8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--actor-export", type=int, required=True)
    parser.add_argument("--actor-name", required=True)
    parser.add_argument("--property-id", type=int, choices=tuple(AUDIO_PROPERTIES), required=True)
    parser.add_argument("--expect", required=True)
    parser.add_argument("--replace", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    kw = dict(source_sha256=args.source_sha256,
              actor_export=args.actor_export, actor_name=args.actor_name,
              property_id=args.property_id, expect=args.expect, replace=args.replace)
    try:
        if args.output is None:
            result, _ = compare_zone_schema(args.source, **kw)
        else:
            result = write_isolated(args.source, args.output, **kw)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as ex:
        print(json.dumps({"schema": SCHEMA, "status": "refused",
                          "reason": str(ex)[:500], "output_written": False}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
