"""DX2SDK v0.5 source-locked 2..8 existing StaticMeshActor clone plans.

Reuses the separately tested conservative native T3SDK multi-clone research
writer. This is NOT arbitrary actor spawning; each copy must be based on an
already placed, idle, unlinked, source-original StaticMeshActor. No runtime
game, physics or BSP validity is claimed.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Sequence

from .api import DX2Map, _safe_output
from dx2_actor_multi_clone_probe import (
    SCHEMA as NATIVE_SCHEMA,
    MAX_COPIES, clone_many_in_memory, save_isolated,
)

PLAN_SCHEMA = "DX2SDK-source-multi-static-prop-clone-plan-v1"
MAX_PLAN = 256 * 1024
MAX_MANIFEST = 3 * 1024 * 1024


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clone_rows(world: DX2Map, copies: Sequence[dict]) -> list[dict]:
    world._check_original_unchanged()
    if not isinstance(copies, (list, tuple)) or not 2 <= len(copies) <= MAX_COPIES:
        raise ValueError("Batch prop clone requires exactly 2..8 original source copies")
    result = []
    for row in copies:
        if not isinstance(row, dict) or set(row) != {"actor", "export", "delta"}:
            raise ValueError("Every static-prop clone row requires actor/export/delta only")
        name, export, delta = row["actor"], row["export"], row["delta"]
        if (type(name) is not str or not name or len(name) > 150
                or type(export) is not int
                or not 1 <= export <= len(world._package.exports)
                or not isinstance(delta, (list, tuple)) or len(delta) != 3
                or any(type(x) not in (int, float)
                       or not math.isfinite(x) or abs(x) > 4096 for x in delta)
                or not any(delta)):
            raise ValueError("Malformed original actor/export or out-of-range clone delta")
        exp = world._package.exports[export - 1]
        if (world._package.class_name(exp) != "StaticMeshActor"
                or exp["name"] != name):
            raise ValueError("Clone row disagrees with original native actor class/export/name")
        result.append({
            "actor": name, "export": export,
            "delta": [float(x) for x in delta],
        })
    return result


def build_multi_clone_plan(world: DX2Map, copies: Sequence[dict]) -> dict:
    """Validate entire source-based clone plan in memory. Never write output."""
    rows = _clone_rows(world, copies)
    report, _ = clone_many_in_memory(
        world.source, source_sha256=world.source_sha256, copies=rows)
    if (report.get("schema") != NATIVE_SCHEMA
            or report.get("runtime_game_verified") is not False
            or report.get("original_bytes_unchanged") is not True
            or len(report.get("copies", [])) != len(rows)):
        raise ValueError("Native original multi-clone provenance check refused")
    return {
        "schema": PLAN_SCHEMA,
        "source_map": world.source.name,
        "source_map_sha256": world.source_sha256,
        "copies": rows,
        "original_source_read_only": True,
        "runtime_game_verified": False,
        "native_arbitrary_actor_spawning_enabled": False,
        "native_script_writer_enabled": False,
        "native_collision_bsp_writer_enabled": False,
    }


def write_multi_clone_plan(
    world: DX2Map, copies: Sequence[dict], output: str | Path,
) -> dict:
    """Write a NEW private source-SHA-bound JSON clone plan only."""
    doc = build_multi_clone_plan(world, copies)
    target = Path(output).expanduser().resolve()
    if (target.suffix.casefold() != ".json" or target.exists()
            or target.parent == world.source.parent
            or world.source.parent in target.parents):
        raise ValueError("Clone plan must be a fresh private JSON outside original Maps")
    parts = tuple(p.casefold() for p in target.parent.parts)
    if any(parts[i:i + 3] == ("content", "dx2", "maps")
           for i in range(max(0, len(parts) - 2))):
        raise ValueError("No clone-plan JSON may be written to any game Maps directory")
    raw = (json.dumps(doc, indent=2, sort_keys=True,
                      ensure_ascii=True, allow_nan=False) + "\n").encode("utf8")
    if len(raw) > MAX_PLAN:
        raise ValueError("Clone plan exceeds supported size")
    world._check_original_unchanged()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as output_file:
        output_file.write(raw)
    return doc


def load_multi_clone_plan(world: DX2Map, file: str | Path) -> list[dict]:
    """Check original map identity and all exact plan flags before use."""
    world._check_original_unchanged()
    path = Path(file).expanduser().resolve(strict=True)
    if (path.suffix.casefold() != ".json"
            or not 0 < path.stat().st_size <= MAX_PLAN):
        raise ValueError("Source clone plan must be a bounded JSON file")
    doc = json.loads(path.read_text("utf8"))
    if (not isinstance(doc, dict)
            or set(doc) != {
                "schema", "source_map", "source_map_sha256", "copies",
                "original_source_read_only", "runtime_game_verified",
                "native_arbitrary_actor_spawning_enabled",
                "native_script_writer_enabled",
                "native_collision_bsp_writer_enabled"}
            or doc["schema"] != PLAN_SCHEMA
            or doc["source_map"] != world.source.name
            or doc["source_map_sha256"] != world.source_sha256
            or doc["original_source_read_only"] is not True
            or doc["runtime_game_verified"] is not False
            or doc["native_arbitrary_actor_spawning_enabled"] is not False
            or doc["native_script_writer_enabled"] is not False
            or doc["native_collision_bsp_writer_enabled"] is not False):
        raise ValueError("Clone plan source or native capability declaration mismatched")
    return _clone_rows(world, doc["copies"])


def duplicate_existing_static_props(
    world: DX2Map, copies: Sequence[dict], output: str | Path,
    *, write: bool = False,
) -> dict:
    """Dry-run batch 2..8 native original source copies; explicit isolated write."""
    world._check_original_unchanged()
    dest = _safe_output(world.source, output)
    rows = _clone_rows(world, copies)
    if not write:
        report, _ = clone_many_in_memory(
            world.source, source_sha256=world.source_sha256, copies=rows)
    else:
        report = save_isolated(
            world.source, dest, source_sha256=world.source_sha256, copies=rows)
        try:
            result = verify_saved_multi_clone(world, dest)
            if result["verified_binary_structure"] is not True:
                raise ValueError("Saved source-based multi-clone failed independent binary replay")
        except Exception:
            dest.with_suffix(".dx2ed-multi-prop-clone.json").unlink(missing_ok=True)
            dest.unlink(missing_ok=True)
            raise
        report["independent_full_binary_verification"] = True
    if (report.get("schema") != NATIVE_SCHEMA
            or report.get("runtime_game_verified") is not False
            or report.get("original_bytes_unchanged") is not True
            or report.get("game_installation_modified") is not False
            or len(report.get("copies", [])) != len(rows)
            or not all(r.get("payload_provenance_verified") is True
                       for r in report["copies"])):
        raise ValueError("Original native multi-clone lacked required source safety evidence")
    return report


def apply_multi_clone_plan(
    world: DX2Map, plan_file: str | Path, output: str | Path,
    *, write: bool = False,
) -> dict:
    """Apply a verified private plan; no writable output unless explicit."""
    return duplicate_existing_static_props(
        world, load_multi_clone_plan(world, plan_file),
        output, write=write)


def verify_saved_multi_clone(world: DX2Map, output: str | Path) -> dict:
    """Independently regenerate and compare every saved native byte."""
    world._check_original_unchanged()
    dest = Path(output).expanduser().resolve(strict=True)
    if dest.name.casefold() != world.source.name.casefold() or dest == world.source:
        raise ValueError("Multi-clone output must retain source GMP basename")
    manifest = dest.with_suffix(".dx2ed-multi-prop-clone.json")
    if not manifest.is_file() or not 0 < manifest.stat().st_size <= MAX_MANIFEST:
        raise ValueError("Missing/oversized original multi-prop clone manifest")
    doc = json.loads(manifest.read_text("utf8"))
    if (not isinstance(doc, dict) or doc.get("schema") != NATIVE_SCHEMA
            or doc.get("status") != "isolated-GMP-created-runtime-unverified"
            or doc.get("runtime_game_verified") is not False
            or doc.get("game_installation_modified") is not False
            or doc.get("original_bytes_unchanged") is not True
            or doc.get("source_name") != world.source.name
            or doc.get("source_sha256") != world.source_sha256
            or doc.get("output_file") != str(dest)
            or not isinstance(doc.get("copies"), list)
            or not 2 <= len(doc["copies"]) <= MAX_COPIES):
        raise ValueError("Original multi-clone source or manifest claim inconsistent")
    rows = []
    for item in doc["copies"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid original multi-clone manifest row")
        before, after = item.get("before"), item.get("after")
        if (not isinstance(before, list) or not isinstance(after, list)
                or len(before) != 3 or len(after) != 3
                or any(type(x) not in (int, float) or not math.isfinite(x)
                       for x in before + after)):
            raise ValueError("Multi-clone manifest has invalid original/new location")
        delta = [float(after[i]) - float(before[i]) for i in range(3)]
        rows.append({
            "actor": item.get("source_actor"), "export": item.get("source_export"),
            "delta": delta,
        })
    source_rows = _clone_rows(world, rows)
    expected, candidate = clone_many_in_memory(
        world.source, source_sha256=world.source_sha256, copies=source_rows)
    saved = dest.read_bytes()
    if (saved != candidate or _sha(saved) != doc.get("output_sha256")
            or expected["new_export_count"] != doc.get("new_export_count")
            or expected["level_actor_count_after"] !=
                doc.get("level_actor_count_after")
            or len(expected["copies"]) != len(doc["copies"])):
        raise ValueError("Saved multi-prop GMP deviates from original source replay")
    for a, b in zip(expected["copies"], doc["copies"]):
        if (a["source_export"] != b.get("source_export")
                or a["new_export"] != b.get("new_export")
                or a["new_actor"] != b.get("new_actor")
                or a["before"] != b.get("before")
                or a["after"] != b.get("after")
                or b.get("clone_latent_action") != 0
                or b.get("payload_provenance_verified") is not True):
            raise ValueError("New cloned export identities or original-state proof differ")
    return {
        "schema": NATIVE_SCHEMA, "verified_binary_structure": True,
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "new_actor_count": len(rows),
        "original_exports_preserved": True,
        "new_clones_state_normalized": True,
        "gameplay_runtime_verified": False,
        "native_arbitrary_actor_spawning_enabled": False,
        "original_game_assets_modified": False,
    }
