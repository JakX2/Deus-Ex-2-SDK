"""Source-locked DX2 Light dependency audit and existing bLightOn Boolean gate.

Light actors carry BSP Region leaf/zone and unsafe-to-clone state frames.
The bLightOn field can also exist on non-Light fixture actors. These are
different operations: Light inspection never writes, and the switch writer
only changes an existing authored one-byte GameSys ID 1487 value.
All evidence comes from the original GMP, never from a guessed property.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .api import DX2Map, MAX_GMP
from dx2_light_dependency_audit import inspect_original_lights
from dx2_gamesys_bool_probe import compare_existing_bool, save_isolated_bool
from dx2_gamesys_audit import scan_dx2_gamesys

SWITCH_ID = 1487  # Engine.Actor.bLightOn, original DX2 declaration
SWITCH_SCHEMA = "DX2SDK-original-bLightOn-v1"
MAX_MANIFEST = 64 * 1024


def _private_report(world: DX2Map, output: str | Path) -> Path:
    dest = Path(output).expanduser().resolve()
    parts = tuple(p.casefold() for p in dest.parent.parts)
    if (dest.suffix.casefold() != ".json" or dest.exists()
            or dest.parent == world.source.parent
            or world.source.parent in dest.parents
            or any(parts[i:i + 3] == ("content", "dx2", "maps")
                   for i in range(max(0, len(parts) - 2)))):
        raise ValueError("Light audit requires a fresh private JSON outside every game Maps folder")
    return dest


def audit_original_lights(world: DX2Map, *, export: int | None = None) -> dict:
    """Inspect real original Light Region, state and reference dependencies."""
    world._check_original_unchanged()
    report = inspect_original_lights(
        world.source, source_sha256=world.source_sha256, actor_export=export)
    world._check_original_unchanged()
    return report


def export_original_lights(
    world: DX2Map, output: str | Path, *, export: int | None = None,
) -> dict:
    """Create a new private evidence JSON, never touch any retail GMP."""
    target = _private_report(world, output)
    report = audit_original_lights(world, export=export)
    world._check_original_unchanged()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf8") as file:
        json.dump(report, file, indent=2, allow_nan=False)
        file.write("\n")
    return report


def _placed_switch_candidates(world: DX2Map) -> tuple[list[dict], int]:
    """Only unique, authored, existing one-byte bLightOn records qualify."""
    world._check_original_unchanged()
    actors, failed = world._package.scene_actors()
    found = []
    for row in actors:
        exp = world._package.exports[row["export"] - 1]
        records, _ = scan_dx2_gamesys(world._package, exp)
        hits = [x for x in records if x["property_id"] == SWITCH_ID]
        if len(hits) != 1:
            continue
        x = hits[0]
        offset = x["payload_offset"]
        if (x["encoding_code"] != 0x80 or x["type_word"] != 0x80
                or x["runtime_flag"] or x["payload_bytes"] != 1
                or not exp["offset"] <= offset < exp["offset"] + exp["size"]
                or world._package.data[offset] not in (0, 1)):
            continue
        found.append({
            "actor": row["name"], "export": row["export"],
            "actor_class": row["class"], "property_id": SWITCH_ID,
            "original_value": bool(world._package.data[offset]),
            "native_one_byte_source_verified": True,
            "runtime_lighting_effect_verified": False,
        })
    world._check_original_unchanged()
    return sorted(found, key=lambda x: x["export"]), failed


def original_light_switches(world: DX2Map, *, limit: int = 100) -> dict:
    """Enumerate eligible source bLightOn records, without requiring Godot."""
    if type(limit) is not int or not 0 <= limit <= 1000:
        raise ValueError("Light switch listing limit must be 0..1000")
    found, failed = _placed_switch_candidates(world)
    return {
        "schema": SWITCH_SCHEMA, "status": "read-only-source-verified",
        "source_map": world.source.name, "source_sha256": world.source_sha256,
        "candidate_count": len(found), "shown": found[:limit],
        "native_actor_decode_failures": failed,
        "read_only": True, "original_map_modified": False,
        "runtime_lighting_effect_verified": False,
        "new_light_actor_creation_enabled": False,
    }


def _checked_identity(world: DX2Map, export: int, actor: str, expected: bool) -> None:
    if (type(export) is not int or type(actor) is not str or not actor
            or type(expected) is not bool):
        raise ValueError("Exact original actor export/name and true/false source value required")
    matches, _ = _placed_switch_candidates(world)
    if not any(x["export"] == export and x["actor"] == actor
               and x["original_value"] is expected for x in matches):
        raise ValueError("Original placed actor has no matching authored bLightOn value")


def _safe_copy_path(world: DX2Map, output: str | Path, *, exists: bool) -> Path:
    path = Path(output).expanduser().resolve()
    parts = tuple(p.casefold() for p in path.parent.parts)
    if (path.name.casefold() != world.source.name.casefold()
            or path.suffix.casefold() != ".gmp" or path == world.source
            or path.parent == world.source.parent
            or world.source.parent in path.parents
            or any(parts[i:i + 3] == ("content", "dx2", "maps")
                   for i in range(max(0, len(parts) - 2)))
            or path.is_file() != exists
            or (exists and not 0 < path.stat().st_size <= MAX_GMP)):
        raise ValueError("Light switch GMP must use a fresh private copy with original map basename")
    return path


def set_existing_light_switch(
    world: DX2Map, *, export: int, actor: str, expected: bool,
    output: str | Path, write: bool = False,
) -> dict:
    """Default dry-run; isolated authored bLightOn flip only with write=True."""
    if type(write) is not bool:
        raise ValueError("write must be exactly a Boolean")
    world._check_original_unchanged()
    _checked_identity(world, export, actor, expected)
    target = _safe_copy_path(world, output, exists=False)
    report_path = target.with_suffix(".dx2ed-gamesys-bool.json")
    if report_path.exists():
        raise ValueError("Refusing overwrite of existing light switch manifest")
    params = {
        "source_sha256": world.source_sha256,
        "actor_export": export, "actor_name": actor,
        "property_id": SWITCH_ID, "expected": expected,
        "replacement": not expected,
    }
    proof = compare_existing_bool(world.source, **params)
    if not write:
        return {
            "schema": SWITCH_SCHEMA, "status": "dry-run",
            "actor": actor, "export": export,
            "original_value": expected, "proposed_value": not expected,
            "source_map_sha256": world.source_sha256,
            "independent_full_package_byte_match":
                proof["independent_full_package_byte_match"],
            "changed_bytes": proof["changed_bytes"],
            "edited_package_written": False,
            "runtime_lighting_effect_verified": False,
        }
    world._check_original_unchanged()
    saved = save_isolated_bool(world.source, target, **params)
    try:
        verified = verify_saved_light_switch(world, target)
        if not verified["verified_binary_structure"]:
            raise ValueError("Independent saved light-switch verification failed")
    except Exception:
        target.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)
        raise
    return {
        "schema": SWITCH_SCHEMA,
        "status": "isolated-boolean-gmp-written-runtime-unverified",
        "actor": actor, "export": export,
        "original_value": expected, "new_value": not expected,
        "changed_bytes": saved["changed_bytes"],
        "verified_binary_structure": True,
        "edited_package_written": True,
        "original_map_modified": False,
        "runtime_lighting_effect_verified": False,
    }


def verify_saved_light_switch(world: DX2Map, output: str | Path) -> dict:
    """Rebuild exact source one-byte change and compare whole saved GMP."""
    world._check_original_unchanged()
    target = _safe_copy_path(world, output, exists=True)
    report_path = target.with_suffix(".dx2ed-gamesys-bool.json")
    if (not report_path.is_file()
            or not 0 < report_path.stat().st_size <= MAX_MANIFEST):
        raise ValueError("Missing or oversized private bLightOn manifest")
    report = json.loads(report_path.read_text(encoding="utf8"))
    actor, export = report.get("actor"), report.get("actor_export")
    before, after = report.get("original_value"), report.get("replacement_value")
    if (report.get("property_id") != SWITCH_ID
            or type(before) is not bool or type(after) is not bool
            or after is not (not before)
            or report.get("original_sha256") != world.source_sha256
            or report.get("source_map") != world.source.name
            or report.get("status") != "isolated-boolean-gmp-written-runtime-unverified"
            or report.get("edited_package_written") is not True
            or report.get("game_runtime_verified") is not False
            or report.get("independent_full_package_byte_match") is not True):
        raise ValueError("Saved bLightOn report is not source-bound or has unsafe claims")
    _checked_identity(world, export, actor, before)
    proof = compare_existing_bool(
        world.source, source_sha256=world.source_sha256,
        actor_export=export, actor_name=actor,
        property_id=SWITCH_ID, expected=before, replacement=after)
    original = world.source.read_bytes()
    offset = proof["original_payload_offset"]
    changed = b"\x01" if after else b"\x00"
    expected_bytes = original[:offset] + changed + original[offset + 1:]
    actual = target.read_bytes()
    digest = hashlib.sha256(actual).hexdigest()
    if (actual != expected_bytes
            or digest != report.get("output_sha256")
            or digest != report.get("reconstructed_sha256")
            or report.get("original_payload_offset") != offset
            or report.get("original_payload_sha256") != proof["original_payload_sha256"]
            or report.get("encoded_property_id") != proof["encoded_property_id"]
            or report.get("property_version") != proof["property_version"]
            or report.get("actor_class") != proof["actor_class"]
            or report.get("changed_bytes") != 1
            or report.get("changed_byte_offsets") != [offset]):
        raise ValueError("Saved light switch GMP/report differs from independent source replay")
    world._check_original_unchanged()
    return {
        "schema": SWITCH_SCHEMA, "verified_binary_structure": True,
        "source_map": world.source.name, "actor": actor, "export": export,
        "changed_bytes": 1, "unapproved_bytes": 0,
        "original_map_modified": False,
        "runtime_lighting_effect_verified": False,
        "native_new_light_actor_creation_enabled": False,
    }
