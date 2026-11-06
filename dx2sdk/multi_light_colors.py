"""DX2SDK v0.8: source-locked 2..8 existing LightColor actor edits.

Batch authoring is limited to source-original, already-positioned actors
with the exact GameSys #116 nested three-Byte 10-byte LightColor layout.
No arbitrary actor spawning, GameSys insertion, Level ref/zone update,
light baking, BSP/collision or runtime behavior inference.

A single T3SDK structured package rebuild must match an independent
set of original-offset byte patches across the entire resulting GMP.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

from .api import DX2Map
from .lights import _safe_copy_path
from .light_colors import (
    ENCODED_ID, PROPERTY_ID, PUBLIC_NAMES, _check_values, _one_original,
)
from dx2_package_roundtrip import inspect_noop
from dx2inspect import Package as DX2Package
from upkg import Package as T3Package
from upkgwrite import ActorEdit, PackageWriter

PLAN_SCHEMA = "DX2SDK-source-multi-LightColor-plan-v1"
SCHEMA = "DX2SDK-source-multi-LightColor-copy-v1"
MAX_COPIES = 8
MAX_JSON = 64 * 1024


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _plan_path(world: DX2Map, file: str | Path, *, exists: bool) -> Path:
    path = Path(file).expanduser().resolve()
    parts = tuple(x.casefold() for x in path.parent.parts)
    if (path.suffix.casefold() != ".json" or path.is_file() != exists
            or path.parent == world.source.parent
            or world.source.parent in path.parents
            or any(parts[i:i + 3] == ("content", "dx2", "maps")
                   for i in range(max(0, len(parts) - 2)))
            or (exists and not 0 < path.stat().st_size <= MAX_JSON)):
        raise ValueError("LightColor plan must be a fresh private bounded JSON outside game Maps")
    return path


def _source_rows(
    world: DX2Map, rows: Sequence[dict], t3: T3Package,
) -> tuple[list[dict], list[dict]]:
    if (not isinstance(rows, (list, tuple))
            or not 2 <= len(rows) <= MAX_COPIES):
        raise ValueError("LightColor batch requires 2..8 existing original actors")
    scenes, failed = world._package.scene_actors()
    if failed:
        # An incomplete original placed Level inventory cannot authorize a
        # multi-actor edit, even when individual target exports appear valid.
        raise ValueError("Original Level actor position decode is incomplete")
    placed = {(r["export"], r["name"]) for r in scenes}
    if len(placed) != len(scenes):
        raise ValueError("Original Level actors contain duplicate identities")
    used = set()
    normalized, details = [], []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
                "actor", "export", "expected", "changes"}:
            raise ValueError("LightColor row requires actor/export/expected/changes only")
        export, actor = row["export"], row["actor"]
        if (type(export) is not int or export in used
                or type(actor) is not str or not actor or len(actor) > 180):
            raise ValueError("LightColor batch actor export/name is invalid or repeated")
        used.add(export)
        candidate = _one_original(world, export, actor, t3, placed=placed)
        edits = _check_values(row["expected"], row["changes"],
                              candidate["source_values"])
        expected = [candidate["source_values"][k] for k in PUBLIC_NAMES]
        changes = {edit["field"]: edit["replacement"] for edit in edits}
        normalized.append({
            "actor": actor, "export": export,
            "expected": expected, "changes": changes,
        })
        details.append({"candidate": candidate, "edits": edits})
    return normalized, details


def _proof(world: DX2Map, rows: Sequence[dict]) -> tuple[dict, bytes]:
    world._check_original_unchanged()
    t3 = T3Package(world.source)
    normalized, details = _source_rows(world, rows, t3)
    baseline, noop = inspect_noop(world.source)
    original = world._package.data
    if (noop != original or baseline["source_sha256"] != world.source_sha256
            or baseline["byte_identical"] is not True):
        raise ValueError("Original LightColor batch GMP failed T3SDK no-op parity")
    writer = PackageWriter(t3)
    direct = bytearray(original)
    allowed = set()
    edits = []
    for row, info in zip(normalized, details):
        exp = t3.exports[row["export"] - 1]
        src = info["candidate"]
        start = src["offsets"]["brightness"] - 2
        original_payload = original[start:start + 10]
        modified_payload = bytearray(original_payload)
        for edit in info["edits"]:
            at = src["offsets"][edit["field"]]
            if (at in allowed or original[at] != edit["source"]
                    or at not in (start + 2, start + 5, start + 8)):
                raise ValueError("Overlapping or displaced LightColor original byte")
            allowed.add(at)
            direct[at] = edit["replacement"]
            modified_payload[at - start] = edit["replacement"]
            edits.append({
                "actor": row["actor"], "export": row["export"],
                "field": edit["field"], "source": edit["source"],
                "replacement": edit["replacement"], "absolute_offset": at,
            })
        actor_editor = ActorEdit(writer, exp)
        hits = [b for b in actor_editor.layout.blocks
                if (b.id & 0xffff) == PROPERTY_ID]
        if (len(hits) != 1 or hits[0].id != ENCODED_ID or hits[0].version != 1
                or hits[0].data != original_payload):
            raise ValueError("T3SDK original batch LightColor property disagrees")
        actor_editor.set_block(
            PROPERTY_ID, bytes(modified_payload), "source_existing_LightColor_batch")
        if not actor_editor.commit():
            raise ValueError("LightColor batch actor writer failed to commit")
    packed = writer.write()
    if (packed != bytes(direct) or len(packed) != len(original)
            or writer.added_names or writer.added_exports):
        raise ValueError("Independent batch LightColor full GMP serializers disagree")
    changed = {i for i, (a,b) in enumerate(zip(original, packed)) if a != b}
    if changed != allowed or not 2 <= len(normalized) <= MAX_COPIES:
        raise ValueError("Unauthorized original package byte changed in batch")
    world._check_original_unchanged()
    report = {
        "schema": SCHEMA,
        "status": "dry-run",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "actors": normalized, "edited_actor_count": len(normalized),
        "field_edits": edits, "changed_bytes": len(changed),
        "output_sha256": _sha(packed),
        "independent_full_package_byte_match": True,
        "source_original_modified": False,
        "gameplay_runtime_verified": False,
        "native_light_spawn_enabled": False,
        "native_bsp_or_zone_rebuild_enabled": False,
    }
    return report, packed


def build_lightcolor_plan(world: DX2Map, rows: Sequence[dict]) -> dict:
    """Validate an authoring plan against the unchanged original; no writes."""
    verified, _ = _proof(world, rows)
    return {
        "schema": PLAN_SCHEMA,
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "actors": verified["actors"],
        "source_only_plan": True,
        "gameplay_runtime_verified": False,
        "native_light_spawn_enabled": False,
        "native_bsp_or_zone_rebuild_enabled": False,
    }


def write_lightcolor_plan(
    world: DX2Map, rows: Sequence[dict], output: str | Path,
) -> dict:
    """Create a NEW source-pinned private JSON; never write in retail Maps."""
    path = _plan_path(world, output, exists=False)
    doc = build_lightcolor_plan(world, rows)
    raw = (json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) +
           "\n").encode("utf8")
    if len(raw) > MAX_JSON:
        raise ValueError("LightColor project plan exceeds supported size")
    world._check_original_unchanged()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
    return doc


def load_lightcolor_plan(world: DX2Map, file: str | Path) -> list[dict]:
    """Recheck every original actor, field, source value and disable flag."""
    path = _plan_path(world, file, exists=True)
    doc = json.loads(path.read_text("utf8"))
    if (not isinstance(doc, dict) or set(doc) != {
                "schema", "source_map", "source_sha256", "actors",
                "source_only_plan", "gameplay_runtime_verified",
                "native_light_spawn_enabled", "native_bsp_or_zone_rebuild_enabled"}
            or doc["schema"] != PLAN_SCHEMA
            or doc["source_map"] != world.source.name
            or doc["source_sha256"] != world.source_sha256
            or doc["source_only_plan"] is not True
            or doc["gameplay_runtime_verified"] is not False
            or doc["native_light_spawn_enabled"] is not False
            or doc["native_bsp_or_zone_rebuild_enabled"] is not False):
        raise ValueError("Untrusted LightColor project plan or false runtime capability")
    actual = build_lightcolor_plan(world, doc["actors"])
    if actual != doc:
        raise ValueError("LightColor plan differs from exact original source reconstruction")
    return actual["actors"]


def apply_lightcolor_plan(
    world: DX2Map, file: str | Path, output: str | Path,
    *, write: bool = False,
) -> dict:
    """One isolated output GMP for 2..8 original authored LightColor edits."""
    if type(write) is not bool:
        raise ValueError("write requires exactly Boolean")
    target = _safe_copy_path(world, output, exists=False)
    manifest = target.with_suffix(".dx2sdk-multi-lightcolor.json")
    if manifest.exists():
        raise ValueError("Refusing to overwrite existing multi-LightColor report")
    plan_file = _plan_path(world, file, exists=True)
    plan_hash = _sha(plan_file.read_bytes())
    rows = load_lightcolor_plan(world, plan_file)
    proof, candidate = _proof(world, rows)
    if not write:
        return {**proof, "edited_package_written": False}
    world._check_original_unchanged()
    if _sha(plan_file.read_bytes()) != plan_hash:
        raise ValueError("Private LightColor plan changed before isolated save")
    target.parent.mkdir(parents=True, exist_ok=True)
    wrote_map = wrote_manifest = False
    try:
        with target.open("xb") as handle:
            wrote_map = True
            handle.write(candidate)
        if target.read_bytes() != candidate:
            raise ValueError("Saved LightColor group GMP differs from in-memory parity image")
        reparse = DX2Package(target)
        original = world._package
        if (reparse.guid != original.guid or reparse.exports != original.exports
                or reparse.names != original.names
                or reparse.imports != original.imports):
            raise ValueError("Batch LightColor output changed original package tables")
        recorded = {
            **proof, "status": "isolated-GMP-written-runtime-unverified",
            "output": str(target), "plan_sha256": plan_hash,
            "edited_package_written": True,
        }
        with manifest.open("x", encoding="utf8") as f:
            wrote_manifest = True
            json.dump(recorded, f, indent=2, allow_nan=False, sort_keys=True)
            f.write("\n")
        check = verify_saved_multi_lightcolor(world, target)
        if check["verified_binary_structure"] is not True:
            raise ValueError("Saved group LightColor source replay failed")
        return {**recorded, "verified_binary_structure": True}
    except Exception:
        if wrote_manifest:
            manifest.unlink(missing_ok=True)
        if wrote_map:
            target.unlink(missing_ok=True)
        raise


def verify_saved_multi_lightcolor(world: DX2Map, output: str | Path) -> dict:
    """Entire saved GMP must equal one independent 2..8-source edit replay."""
    world._check_original_unchanged()
    path = _safe_copy_path(world, output, exists=True)
    manifest = path.with_suffix(".dx2sdk-multi-lightcolor.json")
    if not manifest.is_file() or not 0 < manifest.stat().st_size <= MAX_JSON:
        raise ValueError("Missing or excessive multi-LightColor GMP manifest")
    doc = json.loads(manifest.read_text("utf8"))
    if (not isinstance(doc, dict)
            or doc.get("schema") != SCHEMA
            or doc.get("status") != "isolated-GMP-written-runtime-unverified"
            or doc.get("source_map") != world.source.name
            or doc.get("source_sha256") != world.source_sha256
            or doc.get("output") != str(path)
            or doc.get("edited_package_written") is not True
            or doc.get("independent_full_package_byte_match") is not True
            or doc.get("source_original_modified") is not False
            or doc.get("gameplay_runtime_verified") is not False
            or doc.get("native_light_spawn_enabled") is not False
            or doc.get("native_bsp_or_zone_rebuild_enabled") is not False
            or not isinstance(doc.get("plan_sha256"), str)
            or len(doc["plan_sha256"]) != 64):
        raise ValueError("Multi-LightColor manifest has untrusted source/runtime claims")
    proof, rebuilt = _proof(world, doc.get("actors"))
    for key in ("actors", "edited_actor_count", "field_edits",
                "changed_bytes", "output_sha256"):
        if doc.get(key) != proof[key]:
            raise ValueError("Multi-LightColor manifest differs from independent original")
    raw = path.read_bytes()
    if raw != rebuilt or _sha(raw) != doc["output_sha256"]:
        raise ValueError("Saved multi-LightColor GMP diverges from original-source full replay")
    source, edited = world._package, DX2Package(path)
    if (source.guid != edited.guid or source.exports != edited.exports
            or source.names != edited.names or source.imports != edited.imports):
        raise ValueError("Saved multi-LightColor native package tables changed")
    world._check_original_unchanged()
    return {
        "schema": SCHEMA, "verified_binary_structure": True,
        "edited_actor_count": len(proof["actors"]),
        "changed_bytes": proof["changed_bytes"], "unapproved_bytes": 0,
        "source_map": world.source.name, "source_original_modified": False,
        "gameplay_runtime_verified": False,
        "native_bsp_or_zone_rebuild_enabled": False,
    }
