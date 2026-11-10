#!/usr/bin/env python3
"""Read-only conservative incoming reference audit for one original DX2 actor.

Recognizes only EXPLICIT native UE2 export references: object/class tagged
properties (including decoded nested structs), object/class GameSys blocks,
decoded GameSys structs, object link lists, actor state-frame node pointers,
and package export class/super/outer references.

An absence of hits is NOT proof of no incoming references: untyped arrays,
native tails, opaque GameSys data, IBD script resources and runtime
relationships are NOT decoded. This audit never changes GMPs or labels a
retail game behavior as verified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_actor_clone_probe import _candidate, _pin
from dx2_package_roundtrip import _validate_input, _parse_both, inspect_noop, sha256
from upkg import Package, Property, RF_HasStack

SCHEMA = "DX2Ed-native-explicit-incoming-reference-audit-v1"
MAX_HITS = 128
MAX_PROPERTY_DEPTH = 24


def scan_package(pkg: Package, target_export: int) -> dict:
    """Collect EXPLICIT external references; never assert full coverage."""
    if type(target_export) is not int or not 1 <= target_export <= len(pkg.exports):
        raise ValueError("Target export ID is out of range")
    target = pkg.exports[target_export - 1]
    hits: list[dict] = []
    truncated = False
    undecoded = 0
    scanned = 0

    def add(source, field: str, scope: str):
        nonlocal truncated
        if len(hits) >= MAX_HITS:
            truncated = True
            return
        hits.append({
            "source_export": source.index + 1,
            "source_actor": source.name,
            "source_class": pkg.export_class(source),
            "field": field[:180],
            "kind": scope,
        })

    def inspect_values(value, source, path: str, depth: int = 0):
        nonlocal undecoded
        if depth >= MAX_PROPERTY_DEPTH:
            undecoded += 1
            return
        if not isinstance(value, list):
            undecoded += 1
            return
        for item in value:
            if not isinstance(item, Property):
                undecoded += 1
                continue
            location = f"{path}.{item.name}[{item.array_index}]"
            if item.type in ("Object", "Class"):
                if isinstance(item.value, dict) and type(item.value.get("ref")) is int:
                    if item.value["ref"] == target_export:
                        add(source, location, f"tagged-{item.type.lower()}")
                elif item.value is not None:
                    undecoded += 1
            elif item.type == "Struct":
                if isinstance(item.value, list):
                    inspect_values(item.value, source, location, depth + 1)
                else:
                    undecoded += 1
            elif item.type in ("Array", "Map", "FixedArray"):
                undecoded += 1  # Element types unknown; raw bytes are not object refs.

    level = pkg.level()
    for exp in pkg.exports:
        if exp.index + 1 == target_export:
            continue
        # These are independent package metadata object references.
        for name, value in (
            ("export.class_ref", exp.class_ref),
            ("export.super_ref", exp.super_ref),
            ("export.package", exp.package),
        ):
            if value == target_export:
                add(exp, name, "export-metadata")
        if not exp.serial_size or exp == level:
            continue
        if not exp.flags & RF_HasStack:
            undecoded += 1
            continue
        scanned += 1
        decoded = pkg.read_actor(exp)
        if decoded.parse_error:
            undecoded += 1
            continue
        if decoded.state:
            for name in ("node", "state_node"):
                if decoded.state.get(name) == target_export:
                    add(exp, "state." + name, "script-frame")
        for i, ref in enumerate(decoded.links):
            if ref == target_export:
                add(exp, f"object_links[{i}]", "link")
        inspect_values(decoded.properties, exp, "tag")
        for block in decoded.gamesys:
            path = f"gamesys.{block.prop_id}"
            if block.kind in ("object", "class"):
                if isinstance(block.value, dict) and type(block.value.get("ref")) is int:
                    if block.value["ref"] == target_export:
                        add(exp, path, f"gamesys-{block.kind}")
                elif block.value is not None:
                    undecoded += 1
            elif block.kind == "struct":
                inspect_values(block.value, exp, path)
            elif block.kind == "array":
                # A compact-index array may contain objects OR name indices:
                # without the GameSys declaration, treating it as one is unsafe.
                undecoded += 1
            elif block.kind.startswith("type"):
                undecoded += 1
        if decoded.tail:
            undecoded += 1  # Class-specific native bytes, not proof of refs.

    return {
        "schema": SCHEMA,
        "target_actor": target.name,
        "target_export": target_export,
        "confirmed_incoming_count": len(hits),
        "confirmed_incoming_references": hits,
        "hit_list_truncated": truncated,
        "scanned_actor_exports": scanned,
        "opaque_or_untyped_scopes": undecoded,
        "incoming_references_verified": False,
        "scan_scope": "explicit-GMP-references-only; no IBD/unknown native/array guarantee",
        "safe_to_unplace_claimed": False,
        "runtime_game_verified": False,
    }


def require_no_explicit_incoming(pkg: Package, target_export: int) -> dict:
    result = scan_package(pkg, target_export)
    if result["confirmed_incoming_count"] or result["hit_list_truncated"]:
        hit = result["confirmed_incoming_references"][0]
        raise ValueError(
            "Unplace refused: explicit incoming actor reference from "
            f"{hit['source_actor']} (export {hit['source_export']}) at {hit['field']}")
    return result


def audit_original(source: Path, *, source_sha256: str, actor_export: int,
                   actor_name: str) -> dict:
    source = _validate_input(Path(source))
    pin = _pin(source_sha256)
    raw = source.read_bytes()
    if sha256(raw) != pin:
        raise ValueError("Source GMP SHA-256 mismatch")
    baseline, rewritten = inspect_noop(source)
    if rewritten != raw or baseline["source_sha256"] != pin:
        raise ValueError("Original GMP has no byte-identical no-op baseline")
    pkg, native = _parse_both(source, raw)
    exp, loc = _candidate(pkg, actor_export)
    if type(actor_name) is not str or exp.name != actor_name:
        raise ValueError("Original actor/export name does not match")
    if native.exports[actor_export - 1]["name"] != actor_name:
        raise ValueError("Independent DX2 export name differs")
    result = scan_package(pkg, actor_export)
    result.update({
        "source_name": source.name, "source_sha256": pin,
        "source_location": loc, "original_gmp_modified": False,
        "explicit_incoming_blocker": bool(result["confirmed_incoming_count"]
                                          or result["hit_list_truncated"]),
    })
    if sha256(source.read_bytes()) != pin:
        raise ValueError("Source GMP changed during incoming reference audit")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--actor-export", required=True, type=int)
    parser.add_argument("--actor-name", required=True)
    args = parser.parse_args(argv)
    try:
        report = audit_original(
            args.source, source_sha256=args.source_sha256,
            actor_export=args.actor_export, actor_name=args.actor_name)
    except Exception as exc:
        print(json.dumps({"schema": SCHEMA, "status": "refused",
                          "reason": str(exc) or type(exc).__name__,
                          "original_gmp_modified": False}))
        return 2
    report["status"] = ("explicit-incoming-reference-found"
                        if report["explicit_incoming_blocker"]
                        else "no-explicit-incoming-reference-found-coverage-incomplete")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
