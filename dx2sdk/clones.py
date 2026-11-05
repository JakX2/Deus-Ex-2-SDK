"""DX2SDK original StaticMeshActor *duplicate of existing prop* public adapter.

Wrap the older, source-verified MIT T3SDK v95 actor clone research writer.
The source actor must be fully decoded, neutral/state-idle and unlinked.
Only the NEW clone export receives a normalized latent action frame;
pre-existing exports remain identical (except the Level actor references).

Source-only binary proof does NOT guarantee retail engine gameplay or
collision acceptance. Never installs into retail Maps. No arbitrary NPC,
AI, linked actors, brushes, resource bundles or script editing.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Sequence

from .api import DX2Map, _safe_output
from dx2_actor_clone_probe import (
    SCHEMA, clone_in_memory, find_candidates, write_isolated,
)

MAX_DELTA = 4096.0
MAX_MANIFEST = 2 * 1024 * 1024


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _delta_xyz(delta: Sequence[float]) -> tuple[float, float, float]:
    if (not isinstance(delta, (list, tuple)) or len(delta) != 3
            or any(type(x) not in (int, float) or not math.isfinite(x)
                   or abs(x) > MAX_DELTA for x in delta)
            or not any(delta)):
        raise ValueError("Clone delta requires nonzero finite native X/Y/Z, each within 4096 units")
    return tuple(float(x) for x in delta)


def source_clone_candidates(world: DX2Map, *, limit: int = 200) -> dict:
    """Find only original sources eligible for the conservative clone writer."""
    world._check_original_unchanged()
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Clone candidate limit must be 1..1000")
    evidence = find_candidates(
        world.source, world.source_sha256, limit=limit)
    if (evidence.get("schema") != SCHEMA
            or evidence.get("status") != "read-only-candidate-list"
            or evidence.get("source_sha256") != world.source_sha256
            or evidence.get("output_written") is not False):
        raise ValueError("Native clone research source inspection failed")
    return {
        "schema": SCHEMA, "status": "source-verified-static-prop-candidates",
        "source_map": world.source.name, "original_sha256": world.source_sha256,
        "candidates": evidence["candidates"],
        "read_only": True, "gameplay_runtime_verified": False,
        "native_arbitrary_actor_spawning_enabled": False,
    }


def clone_static_prop(
    world: DX2Map, *, original_export: int, original_actor: str,
    delta_native_xyz: Sequence[float], output: str | Path,
    write: bool = False,
) -> dict:
    """Prepare source-safe duplicate; explicit write creates isolated GMP."""
    world._check_original_unchanged()
    dest = _safe_output(world.source, output)
    xyz = _delta_xyz(delta_native_xyz)
    if (type(original_export) is not int or
            not 1 <= original_export <= len(world._package.exports) or
            type(original_actor) is not str or not original_actor):
        raise ValueError("Exact original source actor export and name required")
    exp = world._package.exports[original_export - 1]
    if (exp["name"] != original_actor or
            world._package.class_name(exp) != "StaticMeshActor"):
        raise ValueError("Source native actor export/class/name mismatch")
    opts = {
        "source_sha256": world.source_sha256,
        "actor_export": original_export,
        "actor_name": original_actor,
        "delta": xyz,
    }
    if not write:
        result, _ = clone_in_memory(world.source, **opts)
    else:
        result = write_isolated(world.source, dest, **opts)
        try:
            check = verify_saved_clone(world, dest)
            if not check["verified_binary_structure"]:
                raise ValueError("Output native clone is not independently verified")
        except Exception:
            dest.with_suffix(".dx2ed-prop-clone.json").unlink(missing_ok=True)
            dest.unlink(missing_ok=True)
            raise
        result["independent_verified_binary_structure"] = True
    if (result.get("schema") != SCHEMA or
            result.get("runtime_game_verified") is not False or
            result.get("game_installation_modified") is not False or
            result.get("original_bytes_unchanged") is not True or
            result.get("clone_payload_provenance_verified") is not True or
            result.get("clone_frame_normalized") is not True):
        raise ValueError("Native clone lacked original source or normalized frame verification")
    return result


def verify_saved_clone(world: DX2Map, output: str | Path) -> dict:
    """Rebuild candidate *from original* and compare entire saved GMP bytes.

    Unlike trusting a reported SHA, this replays the native clone patch
    from unchanged original resources using a new T3SDK/UE95 read pass.
    No other source or destination files are edited by this verification.
    """
    world._check_original_unchanged()
    dest = Path(output).expanduser().resolve(strict=True)
    if dest.name.casefold() != world.source.name.casefold() or dest == world.source:
        raise ValueError("Native clone output must retain original GMP basename")
    manifest = dest.with_suffix(".dx2ed-prop-clone.json")
    if not manifest.is_file() or not 0 < manifest.stat().st_size <= MAX_MANIFEST:
        raise ValueError("Missing/oversized native clone provenance manifest")
    report = json.loads(manifest.read_text("utf8"))
    if (not isinstance(report, dict)
            or report.get("schema") != SCHEMA
            or report.get("status") != "isolated-GMP-created-runtime-unverified"
            or report.get("runtime_game_verified") is not False
            or report.get("game_installation_modified") is not False
            or report.get("original_bytes_unchanged") is not True
            or report.get("clone_payload_provenance_verified") is not True
            or report.get("clone_frame_normalized") is not True
            or report.get("source_name") != world.source.name
            or report.get("source_sha256") != world.source_sha256
            or report.get("output_file") != str(dest)):
        raise ValueError("Clone manifest source/validation identity mismatch")
    old = report.get("source_location")
    new = report.get("new_location")
    if (not isinstance(old, list) or not isinstance(new, list)
            or len(old) != 3 or len(new) != 3
            or any(type(x) not in (int, float) or not math.isfinite(x)
                   for x in old + new)):
        raise ValueError("Clone manifest lacks exact original/final coordinates")
    dx = tuple(float(new[i]) - float(old[i]) for i in range(3))
    dx = _delta_xyz(dx)
    actor = report.get("source_actor_name")
    export = report.get("source_actor_export")
    if type(actor) is not str or type(export) is not int:
        raise ValueError("Clone report lacks original actor identity")
    expected, bytes_expected = clone_in_memory(
        world.source, source_sha256=world.source_sha256,
        actor_export=export, actor_name=actor, delta=dx)
    actual = dest.read_bytes()
    if (actual != bytes_expected
            or _sha(actual) != report.get("output_sha256")
            or report.get("new_actor_name") != expected["new_actor_name"]
            or report.get("new_actor_export") != expected["new_actor_export"]
            or report.get("new_location") != expected["new_location"]
            or report.get("new_export_count") != expected["new_export_count"]):
        raise ValueError("Saved native clone deviates from independent source reconstruction")
    return {
        "schema": SCHEMA, "verified_binary_structure": True,
        "original_source_sha256": world.source_sha256,
        "original_export": export,
        "new_export": expected["new_actor_export"],
        "original_export_untouched": True,
        "new_clone_state_normalized": True,
        "gameplay_runtime_verified": False,
        "native_arbitrary_actor_spawning_enabled": False,
        "original_game_assets_modified": False,
    }
