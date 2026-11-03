#!/usr/bin/env python3
"""Experimental multi-StaticMeshActor GMP clone, isolated output only.

Accepts a JSON plan with 2..8 source-verified original actor copies. Reuses
the v3 single-actor safety gate, neutralizes only NEW native state, and
checks every original export remains unchanged except the Level actor list.
This is a research writer, not yet wired to Godot's Save Map UI.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_actor_clone_probe import (
    _candidate, _destination, _neutral_clone_payload, _pin, MAX_FILE,
    MAX_OFFSET,
)
from dx2_package_roundtrip import _parse_both, _validate_input, inspect_noop, sha256
from t3pack import apply_edits, verify_patch
from upkgwrite import ActorEdit, PackageWriter, f32

SCHEMA = "DX2Ed-experimental-multi-prop-duplicate-v1"
MAX_COPIES = 8


def clone_many_in_memory(source: Path, *, source_sha256: str, copies: list):
    source = _validate_input(Path(source))
    source_sha256 = _pin(source_sha256)
    raw = source.read_bytes()
    if sha256(raw) != source_sha256:
        raise ValueError("Original GMP SHA-256 mismatch")
    if not isinstance(copies, list) or not 2 <= len(copies) <= MAX_COPIES:
        raise ValueError("Requires 2..8 source-verified static prop copies")
    no_op, no_op_bytes = inspect_noop(source)
    if no_op_bytes != raw or no_op["source_sha256"] != source_sha256:
        raise ValueError("Original GMP fails byte-identical no-op verification")
    pkg, dx2 = _parse_both(source, raw)
    old_refs = pkg.level_actors()
    level = pkg.level()
    if level is None or old_refs is None:
        raise ValueError("Map contains no verifiable Level actor list")
    prepared = []
    for number, row in enumerate(copies, 1):
        if not isinstance(row, dict) or set(row) != {"actor", "export", "delta"}:
            raise ValueError(f"Copy {number}: exact actor/export/delta fields required")
        name, export, delta = row["actor"], row["export"], row["delta"]
        if type(name) is not str or not name or len(name) > 150:
            raise ValueError(f"Copy {number}: invalid original actor name")
        if type(export) is not int:
            raise ValueError(f"Copy {number}: original export must be an integer")
        if (not isinstance(delta, (list, tuple)) or len(delta) != 3
                or not all(type(v) in (int, float) and math.isfinite(v)
                           and abs(v) <= MAX_OFFSET for v in delta)
                or not any(delta)):
            raise ValueError(f"Copy {number}: nonzero finite delta within 4096 Unreal units required")
        exp, before = _candidate(pkg, export)
        if (exp.name != name or dx2.exports[export - 1]["name"] != name):
            raise ValueError(f"Copy {number}: actor/export source identity mismatch")
        after = [f32(before[i] + delta[i]) for i in range(3)]
        if after == before or not all(math.isfinite(x) and abs(x) <= 1_000_000 for x in after):
            raise ValueError(f"Copy {number}: translated position is invalid")
        prepared.append((exp, before, after))
    edits = {"actors": {}, "added": [
        {"copy_of": exp.name, "location": after}
        for exp, _, after in prepared
    ], "removed": []}
    patch = apply_edits(pkg, edits)
    new_indices = list(range(len(pkg.exports), len(pkg.exports) + len(prepared)))
    if (patch.added != new_indices or patch.edited != [level.index]
            or patch.level_actors != old_refs + [i+1 for i in new_indices]):
        raise ValueError("Writer added unexpected exports or Level actor references")
    for index, (exp, _, _) in zip(new_indices, prepared):
        original_state = pkg.read_actor(exp).state
        payload, _ = _neutral_clone_payload(
            patch.writer.object_data(index), original_state)
        patch.writer.set_object(index, payload)
    candidate = patch.writer.write()
    if candidate == raw or len(candidate) > MAX_FILE:
        raise ValueError("Multi-clone output length/content invalid")
    with tempfile.TemporaryDirectory(prefix="dx2ed-multi-clone-") as tmp:
        temp = Path(tmp) / source.name
        temp.write_bytes(candidate)
        newer, native = _parse_both(temp, candidate)
    problems = verify_patch(pkg, newer, patch)
    if problems:
        raise ValueError("T3SDK multi-clone validation failed: " + "; ".join(problems[:6]))
    if (len(native.exports) != len(dx2.exports) + len(prepared)
            or len(native.names) != len(dx2.names) + len(prepared)
            or len(native.imports) != len(dx2.imports)
            or native.guid != dx2.guid):
        raise ValueError("Independent DX2 package tables changed unexpectedly")
    for i, (old_e, new_e) in enumerate(zip(dx2.exports, native.exports)):
        if ((old_e["name"], old_e["flags"], old_e["class_ref"])
                != (new_e["name"], new_e["flags"], new_e["class_ref"])):
            raise ValueError(f"Existing export #{i+1} identity changed")
        if (i != level.index and
                pkg.export_bytes(pkg.exports[i]) != newer.export_bytes(newer.exports[i])):
            raise ValueError(f"Existing export #{i+1} payload modified")
    rows = []
    for index, (source_exp, before, after) in zip(new_indices, prepared):
        clone = newer.exports[index]
        decoded = newer.read_actor(clone)
        source_actor = pkg.read_actor(source_exp)
        if (newer.export_class(clone) != "StaticMeshActor"
                or decoded.parse_error or decoded.links
                or decoded.tail != source_actor.tail
                or decoded.state["latent_action"] != 0):
            raise ValueError(f"New export #{index+1} has unexpected class/state/tail")
        inverse = PackageWriter(newer)
        editor = ActorEdit(inverse, clone)
        editor.set_location(before)
        editor.commit()
        restored = inverse.object_data(index)
        normalized, _ = _neutral_clone_payload(
            pkg.export_bytes(source_exp), source_actor.state)
        if restored != normalized:
            raise ValueError(f"New export #{index+1} contains unexpected data changes")
        rows.append({"source_export": source_exp.index+1,
                     "source_actor": source_exp.name,
                     "new_export": index+1, "new_actor": clone.name,
                     "before": before, "after": after,
                     "source_latent_action": source_actor.state["latent_action"],
                     "clone_latent_action": 0, "payload_provenance_verified": True})
    if sha256(source.read_bytes()) != source_sha256:
        raise ValueError("Source GMP changed during operation")
    return ({
        "schema": SCHEMA, "status": "binary-reparsed-runtime-unverified",
        "source_name": source.name, "source_sha256": source_sha256,
        "output_sha256": sha256(candidate), "copies": rows,
        "original_export_count": len(pkg.exports),
        "new_export_count": len(newer.exports),
        "level_actor_count_before": len(old_refs),
        "level_actor_count_after": len(newer.level_actors()),
        "original_bytes_unchanged": True, "game_installation_modified": False,
        "runtime_game_verified": False,
    }, candidate)


def save_isolated(source: Path, output: Path, *, source_sha256: str, copies: list):
    source = _validate_input(Path(source))
    output, legacy_manifest = _destination(source, Path(output))
    manifest = output.with_suffix(".dx2ed-multi-prop-clone.json")
    if manifest.exists() or legacy_manifest.exists():
        raise FileExistsError("Refusing existing output verification manifest")
    report, data = clone_many_in_memory(
        source, source_sha256=source_sha256, copies=copies)
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open("xb") as handle:
            created = True
            handle.write(data)
        if sha256(output.read_bytes()) != report["output_sha256"]:
            raise ValueError("Saved candidate hash mismatch")
        _parse_both(output, data)
        report["status"] = "isolated-GMP-created-runtime-unverified"
        report["output_file"] = str(output)
        with manifest.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--copies-json", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    try:
        plan = json.loads(args.copies_json.read_text(encoding="utf-8"))
        if (not isinstance(plan, dict) or set(plan) != {"schema", "copies"}
                or plan["schema"] != SCHEMA):
            raise ValueError("Invalid exact multi-prop plan schema")
        options = {"source_sha256": args.source_sha256, "copies": plan["copies"]}
        if args.output is None:
            result, _ = clone_many_in_memory(args.source, **options)
        else:
            result = save_isolated(args.source, args.output, **options)
    except Exception as exc:
        print(json.dumps({"schema": SCHEMA, "status": "refused",
                          "reason": str(exc) or type(exc).__name__,
                          "output_written": False}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
