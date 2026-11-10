#!/usr/bin/env python3
"""Experimental atomic native DX2 StaticMeshActor move/copy/unplace plan.

This is a small, deliberately constrained GMP Level/actor serializer for
research on user-owned DX2 v95 maps, NOT a general T3Ed-level compiler.
Only original placed/unlinked StaticMeshActor sources are accepted.

A plan may combine existing-actor translations, new duplicate exports and
Level-reference unplacement in ONE GMP. Only isolated, same-basename GMPs
can be created. No IBD, BSP, collision baking, gamesys or scripts are written.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_actor_clone_probe import (
    _candidate, _destination, _neutral_clone_payload, _pin, MAX_FILE,
    MAX_OFFSET,
)
from dx2_actor_unplace_probe import _baseline
from dx2_package_roundtrip import _parse_both, _validate_input, sha256
from t3pack import apply_edits, verify_patch
from upkgwrite import ActorEdit, PackageWriter, f32

SCHEMA = "DX2Ed-experimental-native-prop-change-plan-v1"
MANIFEST_SUFFIX = ".dx2ed-native-prop-plan.json"
MAX_PER_KIND = 8
MAX_TOTAL = 16
MAX_PLAN_BYTES = 128 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024


def _exact_keys(record, expected, label):
    if not isinstance(record, dict) or set(record) != set(expected):
        raise ValueError(f"{label} requires exact keys {', '.join(sorted(expected))}")


def _position_delta(value, label):
    if (type(value) is not list or len(value) != 3
            or any(type(x) not in (int, float)
                   or not math.isfinite(x) or abs(x) > MAX_OFFSET
                   for x in value)
            or not any(value)):
        raise ValueError(f"{label}: expected nonzero finite X/Y/Z delta <= 4096")
    return [float(x) for x in value]


def _plan(plan):
    """Validate exact versioned JSON before reading potentially large sources."""
    _exact_keys(plan, ("schema", "moves", "copies", "unplaces"), "plan")
    if plan["schema"] != SCHEMA:
        raise ValueError("Unsupported native prop change plan schema")
    counts = []
    for key in ("moves", "copies", "unplaces"):
        val = plan[key]
        if type(val) is not list or len(val) > MAX_PER_KIND:
            raise ValueError(f"Plan {key} requires <= {MAX_PER_KIND} entries")
        counts.append(len(val))
    if sum(counts) > MAX_TOTAL or sum(count > 0 for count in counts) < 2:
        raise ValueError("The first combined writer needs 2 different operation kinds, <= 16 edits")
    result = {"schema": SCHEMA, "moves": [], "copies": [], "unplaces": []}
    seen_moved = set()
    seen_unplaced = set()
    for kind in ("moves", "copies", "unplaces"):
        for row in plan[kind]:
            keys = ("actor", "export") if kind == "unplaces" else ("actor", "export", "delta")
            _exact_keys(row, keys, kind)
            actor, export = row["actor"], row["export"]
            if type(actor) is not str or not actor or len(actor) > 150:
                raise ValueError(f"{kind}: exact original actor name required")
            if type(export) is not int or export < 1:
                raise ValueError(f"{kind}: positive original one-based export ID required")
            normalized = {"actor": actor, "export": export}
            if kind != "unplaces":
                normalized["delta"] = _position_delta(row["delta"], kind)
            if kind == "moves":
                if export in seen_moved:
                    raise ValueError("One original actor cannot be moved twice")
                seen_moved.add(export)
            if kind == "unplaces":
                if export in seen_unplaced:
                    raise ValueError("One original actor cannot be unplaced twice")
                seen_unplaced.add(export)
            result[kind].append(normalized)
    if seen_moved & seen_unplaced:
        raise ValueError("Cannot move and unplace the same original actor in one plan")
    return result


def _source_actors(pkg, native, plan):
    """Independently authenticate every referenced source actor identity."""
    sources = {}
    for kind in ("moves", "copies", "unplaces"):
        for row in plan[kind]:
            idx = row["export"]
            if idx not in sources:
                exp, before = _candidate(pkg, idx)
                sources[idx] = {"exp": exp, "before": before}
            exp = sources[idx]["exp"]
            if (exp.name != row["actor"]
                    or native.exports[idx - 1]["name"] != row["actor"]):
                raise ValueError(f"{kind}: source actor export/name does not match original")
    return sources


def compile_in_memory(source: Path, *, source_sha256: str, plan: dict):
    """One controlled T3SDK edit transaction with independent DX2 reparse."""
    safe_plan = _plan(plan)
    source, raw, pkg, native = _baseline(source, _pin(source_sha256))
    old_refs = pkg.level_actors()
    level = pkg.level()
    if old_refs is None or level is None:
        raise ValueError("Original map Level list is unavailable")
    sources = _source_actors(pkg, native, safe_plan)
    moved = {}
    copied = []
    unplaced = {row["export"] for row in safe_plan["unplaces"]}
    for row in safe_plan["moves"]:
        exp_id = row["export"]
        before = sources[exp_id]["before"]
        after = [f32(before[i] + row["delta"][i]) for i in range(3)]
        if after == before or any(not math.isfinite(v) or abs(v) > 1_000_000 for v in after):
            raise ValueError("Existing prop translation disappears in float32 or exceeds map bounds")
        moved[exp_id] = {"actor": row["actor"], "before": before, "after": after}
    for row in safe_plan["copies"]:
        before = sources[row["export"]]["before"]
        after = [f32(before[i] + row["delta"][i]) for i in range(3)]
        if after == before or any(not math.isfinite(v) or abs(v) > 1_000_000 for v in after):
            raise ValueError("New prop location disappears in float32 or exceeds map bounds")
        copied.append({
            "source_export": row["export"], "source_actor": row["actor"],
            "before": before, "after": after,
        })
    edits = {
        "actors": {row["actor"]: {"location": moved[row["export"]]["after"]}
                   for row in safe_plan["moves"]},
        "added": [{"copy_of": row["source_actor"], "location": row["after"]}
                  for row in copied],
        "removed": [row["actor"] for row in safe_plan["unplaces"]],
    }
    patch = apply_edits(pkg, edits)
    new_indices = list(range(len(pkg.exports), len(pkg.exports) + len(copied)))
    expected_refs = [ref for ref in old_refs if ref not in unplaced]
    expected_refs.extend(idx + 1 for idx in new_indices)
    edited_expected = {idx - 1 for idx in moved}
    if copied or unplaced:
        edited_expected.add(level.index)
    if (patch.added != new_indices or set(patch.edited) != edited_expected
            or patch.removed != edits["removed"]
            or patch.level_actors != (expected_refs if (copied or unplaced) else None)):
        raise ValueError("T3SDK writer altered an unexpected export or Level reference")
    if len(patch.edited) != len(edited_expected):
        raise ValueError("T3SDK changed an export more than once")

    for idx, row in zip(new_indices, copied):
        original_state = pkg.read_actor(sources[row["source_export"]]["exp"]).state
        normalized, _ = _neutral_clone_payload(
            patch.writer.object_data(idx), original_state)
        patch.writer.set_object(idx, normalized)

    candidate = patch.writer.write()
    if candidate == raw or len(candidate) > MAX_FILE:
        raise ValueError("Native plan candidate is unchanged or oversized")
    with tempfile.TemporaryDirectory(prefix="dx2ed-prop-plan-") as folder:
        staged = Path(folder) / source.name
        staged.write_bytes(candidate)
        newer, native_new = _parse_both(staged, candidate)
    failed = verify_patch(pkg, newer, patch)
    if failed:
        raise ValueError("Independent T3SDK patch verification failed: " + "; ".join(failed[:6]))
    if (len(newer.exports) != len(pkg.exports) + len(copied)
            or len(native_new.exports) != len(native.exports) + len(copied)
            or len(newer.names) != len(pkg.names) + len(copied)
            or len(newer.imports) != len(pkg.imports)
            or native_new.guid != native.guid
            or newer.level_actors() != expected_refs):
        raise ValueError("Native package table or Level actor membership changed unexpectedly")

    for i, (old, fresh) in enumerate(zip(pkg.exports, newer.exports)):
        if (old.name != fresh.name or old.class_ref != fresh.class_ref
                or old.flags != fresh.flags):
            raise ValueError(f"Existing export #{i+1} identity differs")
        before_bytes = pkg.export_bytes(old)
        after_bytes = newer.export_bytes(fresh)
        if i + 1 in moved:
            restored_writer = PackageWriter(newer)
            editor = ActorEdit(restored_writer, fresh)
            editor.set_location(moved[i+1]["before"])
            editor.commit()
            if restored_writer.object_data(i) != before_bytes:
                raise ValueError(f"Existing actor #{i+1} changed outside Location")
        elif i != level.index and after_bytes != before_bytes:
            raise ValueError(f"Untouched original export #{i+1} changed")

    for idx, row in zip(new_indices, copied):
        clone = newer.exports[idx]
        src = sources[row["source_export"]]["exp"]
        decoded = newer.read_actor(clone)
        source_actor = pkg.read_actor(src)
        if (newer.export_class(clone) != "StaticMeshActor"
                or decoded.parse_error or decoded.links
                or decoded.tail != source_actor.tail or decoded.state is None
                or decoded.state["latent_action"] != 0):
            raise ValueError("New cloned actor has unsupported native data")
        reverse_writer = PackageWriter(newer)
        reverse = ActorEdit(reverse_writer, clone)
        reverse.set_location(row["before"])
        reverse.commit()
        expected, _ = _neutral_clone_payload(pkg.export_bytes(src), source_actor.state)
        if reverse_writer.object_data(idx) != expected:
            raise ValueError("New actor clone differs outside Location and neutral latent frame")
        row["new_export"] = idx + 1
        row["new_actor"] = clone.name

    if sha256(source.read_bytes()) != source_sha256:
        raise ValueError("Original GMP source changed during native plan")
    report = {
        "schema": SCHEMA, "status": "binary-reparsed-runtime-unverified",
        "source_name": source.name, "source_sha256": source_sha256,
        "output_sha256": sha256(candidate),
        "original_export_count": len(pkg.exports),
        "new_export_count": len(newer.exports),
        "level_actor_count_before": len(old_refs),
        "level_actor_count_after": len(expected_refs),
        "moved": [{"actor": row["actor"], "export": index,
                   "before": row["before"], "after": row["after"]}
                  for index, row in moved.items()],
        "copied": copied,
        "unplaced": [{"actor": row["actor"], "export": row["export"]}
                     for row in safe_plan["unplaces"]],
        "plan": safe_plan, "original_source_unchanged": True,
        "all_changes_scope_verified": True, "native_actor_exports_deleted": False,
        "incoming_references_verified": False,
        "runtime_game_verified": False, "game_installation_modified": False,
        "output_written": False,
        "notes": ("Only original static prop translations, neutral-state clones and "
                  "Level-list unplacement. Incoming references, IBD, BSP and runtime "
                  "game acceptance have not been verified."),
    }
    return report, candidate


def _manifest_path(output: Path) -> Path:
    return output.with_suffix(MANIFEST_SUFFIX)


def verify_saved_plan(source: Path, output: Path, *, source_sha256: str) -> dict:
    """Replay from original, compare EVERY candidate byte, not merely hashes."""
    source = _validate_input(Path(source))
    source_sha256 = _pin(source_sha256)
    output = Path(output).expanduser().resolve(strict=True)
    if (output == source or output.name.casefold() != source.name.casefold()
            or source.parent == output.parent or source.parent in output.parents):
        raise ValueError("Verification requires an isolated same-name GMP")
    manifest = _manifest_path(output)
    if not manifest.is_file() or not 0 < manifest.stat().st_size <= MAX_MANIFEST_BYTES:
        raise ValueError("Missing or oversized native plan manifest")
    record = json.loads(manifest.read_text(encoding="utf8"))
    if (not isinstance(record, dict) or record.get("schema") != SCHEMA
            or record.get("status") != "isolated-GMP-created-runtime-unverified"
            or record.get("source_sha256") != source_sha256
            or record.get("source_name") != source.name
            or record.get("output_file") != str(output)
            or record.get("runtime_game_verified") is not False
            or record.get("game_installation_modified") is not False
            or record.get("original_source_unchanged") is not True
            or record.get("all_changes_scope_verified") is not True
            or record.get("native_actor_exports_deleted") is not False
            or record.get("incoming_references_verified") is not False):
        raise ValueError("Native plan manifest source identity and safety flags differ")
    expected, rebuilt = compile_in_memory(
        source, source_sha256=source_sha256, plan=record.get("plan"))
    actual = output.read_bytes()
    if (actual != rebuilt or sha256(actual) != record.get("output_sha256")
            or any(record.get(key) != expected[key] for key in (
                "original_export_count", "new_export_count", "level_actor_count_before",
                "level_actor_count_after", "moved", "copied", "unplaced"))):
        raise ValueError("Native plan GMP differs from original-reconstructed whole-file proof")
    return {
        "schema": SCHEMA, "status": "binary-verified-runtime-unverified",
        "source_sha256": source_sha256, "output_sha256": sha256(actual),
        "all_candidate_bytes_replayed": True, "native_actor_exports_deleted": False,
        "incoming_references_verified": False,
        "runtime_game_verified": False, "game_installation_modified": False,
    }


def save_isolated(source: Path, output: Path, *, source_sha256: str, plan: dict):
    source = _validate_input(Path(source))
    output, legacy_clone_manifest = _destination(source, Path(output))
    manifest = _manifest_path(output)
    if manifest.exists() or legacy_clone_manifest.exists():
        raise FileExistsError("Refusing existing candidate provenance manifest")
    report, candidate = compile_in_memory(
        source, source_sha256=source_sha256, plan=plan)
    output.parent.mkdir(parents=True, exist_ok=True)
    written_output = False
    written_manifest = False
    try:
        with output.open("xb") as stream:
            written_output = True
            stream.write(candidate)
        if sha256(output.read_bytes()) != report["output_sha256"]:
            raise ValueError("On-disk GMP checksum differs")
        report["status"] = "isolated-GMP-created-runtime-unverified"
        report["output_written"] = True
        report["output_file"] = str(output)
        with manifest.open("x", encoding="utf8") as stream:
            written_manifest = True
            json.dump(report, stream, indent=2)
            stream.write("\n")
        verify_saved_plan(source, output, source_sha256=source_sha256)
    except Exception:
        if written_manifest:
            manifest.unlink(missing_ok=True)
        if written_output:
            output.unlink(missing_ok=True)
        raise
    return report


def _read_plan(path: Path):
    path = Path(path)
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_PLAN_BYTES:
        raise ValueError("Missing or oversized JSON native prop plan")
    return _plan(json.loads(path.read_text(encoding="utf8")))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="User-owned original DX2 GMP")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--plan-json", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.verify:
            if args.plan_json is not None or args.output is None:
                raise ValueError("--verify requires only --output, not --plan-json")
            result = verify_saved_plan(args.source, args.output,
                                       source_sha256=args.source_sha256)
        else:
            if args.plan_json is None:
                raise ValueError("--plan-json is required for native prop changes")
            plan = _read_plan(args.plan_json)
            opts = {"source_sha256": args.source_sha256, "plan": plan}
            if args.output is None:
                result, _ = compile_in_memory(args.source, **opts)
            else:
                result = save_isolated(args.source, args.output, **opts)
    except Exception as exc:
        print(json.dumps({"schema": SCHEMA, "status": "refused",
                          "reason": str(exc) or type(exc).__name__,
                          "output_written": False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
