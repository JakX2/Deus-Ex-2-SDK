#!/usr/bin/env python3
"""Experimental native DX2 GMP StaticMeshActor duplicate: source-pinned, no install.

This is deliberately NOT a general actor spawner. One already-placed,
locally-authored, state-idle and unlinked static prop is cloned at a translated
position. All original exports except Level stay byte-identical. The package
is reparsed by independent DX2/T3SDK readers, and T3SDK verifies the edit.
Requires a clean original DX2 v95 GMP; outputs only to an isolated directory.

Use --list to discover conservative candidates. --output explicitly requests
a candidate file (same GMP basename, no overwrites). Neither mode touches the
retail installation or claims runtime success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_package_roundtrip import (
    _parse_both, _validate_input, inspect_noop, sha256
)
from t3pack import apply_edits, verify_patch
from upkg import RF_HasStack
from upkgwrite import ActorEdit, LayoutError, PackageWriter, f32

SCHEMA = "DX2Ed-experimental-native-prop-duplicate-v1"
MAX_OFFSET = 4096.0
MAX_FILE = 256 * 1024 * 1024


def _pin(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("A lowercase 64-digit original GMP SHA-256 is required")
    return value


def _candidate(pkg, export_index: int):
    """Only a fully decoded, quiet, original StaticMeshActor with a Location."""
    if type(export_index) is not int or export_index < 1 or export_index > len(pkg.exports):
        raise ValueError("Original one-based export index is out of range")
    exp = pkg.exports[export_index - 1]
    if pkg.export_class(exp) != "StaticMeshActor":
        raise ValueError("Only existing native StaticMeshActor exports are allowed")
    if not exp.serial_size or not (exp.flags & RF_HasStack):
        raise ValueError("Source prop has no original serialized actor state")
    refs = pkg.level_actors()
    if refs is None or refs.count(export_index) != 1 or export_index in refs[:2]:
        raise ValueError("Source actor must occur exactly once beyond LevelInfo/brush")
    decoded = pkg.read_actor(exp)
    if decoded.parse_error or decoded.state is None:
        raise ValueError("Source actor does not decode exactly")
    if decoded.links or decoded.tail not in (b"", b"\x00" * 4):
        raise ValueError("Object links and unknown/nonzero native tails cannot be cloned")
    if not (decoded.state["node"] == -2 and decoded.state["state_node"] == -2
            and decoded.state["offset"] == -1 and decoded.state["latent_action"] == 0
            and decoded.state["probe_mask"] == 0xFFFFFFFFFFFFFFFF):
        raise ValueError("Source actor has active native/script state")
    # An existing authored tagged Location is mandatory: no field insertion.
    reader = ActorEdit(PackageWriter(pkg), exp)
    if reader.layout.props.find("Location") is None:
        raise ValueError("Source actor has no authored Location tag")
    xyz = reader.struct_values("Location", "Vector")
    if not all(math.isfinite(v) and abs(v) < 1_000_000 for v in xyz):
        raise ValueError("Source position is not finite or plausible")
    return exp, [float(v) for v in xyz]


def _destination(source: Path, output: Path):
    output = output.expanduser().resolve()
    if output.name.casefold() != source.name.casefold() or output.suffix.lower() != ".gmp":
        raise ValueError("Output must retain the exact original GMP filename")
    if (output == source or output.parent == source.parent
            or source.parent in output.parents):
        raise ValueError("Output must be outside the source map folder and descendants")
    # Never auto-install directly into ANY game copy, retail or test.
    parts = [x.casefold() for x in output.parent.parts]
    if "maps" in parts and "dx2" in parts and "content" in parts:
        raise ValueError("Output cannot target a game Content/DX2/Maps folder")
    manifest = output.with_suffix(".dx2ed-prop-clone.json")
    if output.exists() or manifest.exists():
        raise FileExistsError("Refusing to overwrite candidate GMP or manifest")
    return output, manifest


def clone_in_memory(source: Path, *, source_sha256: str, actor_export: int,
                    actor_name: str, delta: tuple[float, float, float]):
    source = _validate_input(Path(source))
    source_sha256 = _pin(source_sha256)
    raw = source.read_bytes()
    if sha256(raw) != source_sha256:
        raise ValueError("Original GMP SHA-256 mismatch")
    if type(actor_name) is not str or not actor_name or len(actor_name) > 150:
        raise ValueError("Exact original actor name required")
    if (len(delta) != 3 or not all(
            type(x) in (int, float) and math.isfinite(x) and abs(x) <= MAX_OFFSET
            for x in delta) or not any(delta)):
        raise ValueError("Supply finite translation components <= 4096 units and a nonzero change")

    noop, rewritten = inspect_noop(source)
    if rewritten != raw or noop["source_sha256"] != source_sha256:
        raise ValueError("Source is not a byte-identical GMP writer baseline")
    pkg, dx2 = _parse_both(source, raw)
    exp, before = _candidate(pkg, actor_export)
    if exp.name != actor_name or dx2.exports[actor_export - 1]["name"] != actor_name:
        raise ValueError("Original actor export/name identity mismatch")
    after = [f32(before[i] + delta[i]) for i in range(3)]
    if after == before:
        raise ValueError("Translation is lost to float32 precision")
    if not all(math.isfinite(x) and abs(x) <= 1_000_000 for x in after):
        raise ValueError("New location is outside supported bounds")

    edits = {"actors": {}, "added": [{"copy_of": actor_name,
             "location": after}], "removed": []}
    patch = apply_edits(pkg, edits)
    if len(patch.added) != 1 or patch.added[0] != len(pkg.exports):
        raise ValueError("The writer did not add exactly one final export")
    level = pkg.level()
    if level is None or patch.edited != [level.index]:
        raise ValueError("Only the original Level actor list may be rewritten")
    old_refs = pkg.level_actors()
    if patch.level_actors != old_refs + [len(pkg.exports) + 1]:
        raise ValueError("Cloned actor was not appended exactly once")
    candidate = patch.writer.write()
    if len(candidate) > MAX_FILE or candidate == raw:
        raise ValueError("Invalid candidate GMP length/content")
    # The independent DX2 parser needs a path, not only raw bytes.
    with tempfile.TemporaryDirectory(prefix="dx2ed-clone-") as root:
        temp = Path(root) / source.name
        temp.write_bytes(candidate)
        fresh_t3, fresh_dx2 = _parse_both(temp, candidate)
    problems = verify_patch(pkg, fresh_t3, patch)
    if problems:
        raise ValueError("T3SDK patched-package validation: " + "; ".join(problems[:6]))
    if (len(fresh_dx2.exports) != len(dx2.exports) + 1
            or len(fresh_dx2.names) != len(dx2.names) + 1
            or len(fresh_dx2.imports) != len(dx2.imports)
            or fresh_dx2.guid != dx2.guid):
        raise ValueError("Independent DX2 package metadata differs unexpectedly")
    for i, (old_e, new_e) in enumerate(zip(dx2.exports, fresh_dx2.exports)):
        if (old_e["name"], old_e["flags"], old_e["class_ref"]) != (
                new_e["name"], new_e["flags"], new_e["class_ref"]):
            raise ValueError(f"An existing export table identity changed at #{i+1}")
        if i != level.index and pkg.export_bytes(pkg.exports[i]) != fresh_t3.export_bytes(fresh_t3.exports[i]):
            raise ValueError(f"An existing export payload changed unexpectedly at #{i+1}")
    clone = fresh_t3.exports[-1]
    if fresh_t3.export_class(clone) != "StaticMeshActor":
        raise ValueError("New actor has unexpected class")
    cloned_actor = fresh_t3.read_actor(clone)
    if (cloned_actor.parse_error or cloned_actor.links
            or cloned_actor.tail != pkg.read_actor(exp).tail):
        raise ValueError("New actor has changed or unverified native data")
    report = {
        "schema": SCHEMA,
        "status": "binary-reparsed-runtime-unverified",
        "source_name": source.name, "source_sha256": source_sha256,
        "output_sha256": sha256(candidate),
        "new_actor_name": clone.name,
        "source_actor_name": actor_name, "source_actor_export": actor_export,
        "new_actor_export": len(fresh_t3.exports),
        "source_location": before, "new_location": after,
        "original_export_count": len(pkg.exports),
        "new_export_count": len(fresh_t3.exports),
        "level_actor_count_before": len(old_refs),
        "level_actor_count_after": len(fresh_t3.level_actors()),
        "original_bytes_unchanged": sha256(source.read_bytes()) == source_sha256,
        "runtime_game_verified": False,
        "game_installation_modified": False,
        "notes": ("Only source-verified StaticMeshActor with a verified neutral state, "
                  "no links, and zero or four-byte all-zero native tail retained; "
                  "not an IBD/BSP writer.")
    }
    if not report["original_bytes_unchanged"]:
        raise ValueError("Original GMP changed during clone preparation")
    return report, candidate


def find_candidates(source: Path, source_sha256: str, limit: int = 200):
    source = _validate_input(Path(source))
    _pin(source_sha256)
    if sha256(source.read_bytes()) != source_sha256:
        raise ValueError("Original GMP SHA-256 mismatch")
    _, data = inspect_noop(source)
    pkg, _ = _parse_both(source, data)
    matches = []
    for exp in pkg.exports:
        if pkg.export_class(exp) != "StaticMeshActor":
            continue
        try:
            _, location = _candidate(pkg, exp.index + 1)
        except (ValueError, LayoutError, IndexError, KeyError):
            continue
        decoded = pkg.read_actor(exp)
        mesh = decoded.block(56)
        mesh_name = None
        if mesh is not None and isinstance(mesh.value, list):
            mesh_name = next((str(field.value) for field in mesh.value
                              if field.name == "Name" and isinstance(field.value, str)), None)
        matches.append({"export": exp.index + 1, "actor": exp.name,
                        "location": location, "mesh": mesh_name})
        if len(matches) == limit:
            break
    return {"schema": SCHEMA, "status": "read-only-candidate-list",
            "source_sha256": source_sha256, "candidates": matches,
            "output_written": False}


def check_actor(source: Path, *, source_sha256: str,
                actor_export: int, actor_name: str) -> dict:
    """Read-only preflight before a Godot Save As dialog appears.

    The source identity is checked with both readers. This does not
    guarantee the full duplicate will serialize, but rejects known
    unsupported native/script state before asking for a destination.
    """
    source = _validate_input(Path(source))
    source_sha256 = _pin(source_sha256)
    raw = source.read_bytes()
    if sha256(raw) != source_sha256:
        raise ValueError("Original GMP SHA-256 mismatch; reopen the unchanged map")
    pkg, dx2 = _parse_both(source, raw)
    exp, location = _candidate(pkg, actor_export)
    if (exp.name != actor_name
            or dx2.exports[actor_export - 1]["name"] != actor_name):
        raise ValueError("Actor/export identity no longer matches the original GMP")
    return {"schema": SCHEMA, "status": "clone-source-eligible",
            "source_sha256": source_sha256,
            "actor": actor_name, "export": actor_export,
            "source_location": location, "output_written": False}


def write_isolated(source: Path, output: Path, **options):
    source = _validate_input(Path(source))
    output, manifest = _destination(source, Path(output))
    report, candidate = clone_in_memory(source, **options)
    if not report["original_bytes_unchanged"]:
        raise ValueError("Source bytes changed")
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open("xb") as handle:
            created = True
            handle.write(candidate)
        if output.read_bytes() != candidate:
            raise ValueError("Saved candidate failed SHA-256 confirmation")
        _parse_both(output, candidate)
        report["output_file"] = str(output)
        report["status"] = "isolated-GMP-created-runtime-unverified"
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
    p.add_argument("source", type=Path, help="Original user-owned DX2 GMP")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--list", action="store_true", help="Read-only candidate discovery")
    p.add_argument("--check-actor", action="store_true",
                   help="Read-only exact actor eligibility check for the Godot UI")
    p.add_argument("--actor-export", type=int)
    p.add_argument("--actor-name")
    p.add_argument("--dx", type=float, default=0.0)
    p.add_argument("--dy", type=float, default=0.0)
    p.add_argument("--dz", type=float, default=0.0)
    p.add_argument("--output", type=Path)
    a = p.parse_args(argv)
    if a.list and a.check_actor:
        p.error("--list and --check-actor cannot be combined")
    if (a.list or a.check_actor) and a.output is not None:
        p.error("Read-only inspection does not accept --output")
    if (not a.list and (a.actor_export is None or not a.actor_name)):
        p.error("Supply original --actor-export and --actor-name")
    try:
        if a.list:
            result = find_candidates(a.source, a.source_sha256)
        elif a.check_actor:
            result = check_actor(a.source, source_sha256=a.source_sha256,
                                 actor_export=a.actor_export, actor_name=a.actor_name)
        else:
            opts = dict(source_sha256=a.source_sha256,
                        actor_export=a.actor_export, actor_name=a.actor_name,
                        delta=(a.dx, a.dy, a.dz))
            if a.output is None:
                result, _ = clone_in_memory(a.source, **opts)
            else:
                result = write_isolated(a.source, a.output, **opts)
    except Exception as exc:
        # A rejected user-selected prop is expected, not a Python traceback.
        # Keep machine-readable errors so Godot can display the actual cause.
        print(json.dumps({"schema": SCHEMA, "status": "refused",
                          "reason": str(exc) or type(exc).__name__,
                          "error_type": type(exc).__name__,
                          "output_written": False}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
