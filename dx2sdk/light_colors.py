"""DX2SDK v0.7: existing authored LightColor (#116) *byte-field* editing.

Only source-placed actors with the verified exact 10-byte GameSys struct
containing LightBrightness, LightHue, LightSaturation (in that order) may
be changed. This is not a general struct writer or Light actor factory.

A separate T3SDK ActorEdit + PackageWriter rebuild must exactly match an
independent original-source-offset byte patch of the entire GMP before
isolated output is permitted. Never import/commit proprietary GMP files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .api import DX2Map
from .lights import _safe_copy_path
from dx2_gamesys_audit import scan_dx2_gamesys
from dx2_package_roundtrip import inspect_noop
from dx2inspect import Cursor, Package as DX2Package
from upkg import Package as T3Package
from upkgwrite import ActorEdit, PackageWriter

SCHEMA = "DX2SDK-source-existing-LightColor-v1"
PROPERTY_ID = 116
ENCODED_ID = (0x0008 << 16) | PROPERTY_ID
NESTED_NAMES = ("LightBrightness", "LightHue", "LightSaturation")
PUBLIC_NAMES = ("brightness", "hue", "saturation")
MAX_MANIFEST = 16_384


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _components(raw: bytes, names: list[str]) -> tuple[dict[str, int], dict[str, int]]:
    """Independently locate EXACT original three byte tags, not guessed offsets."""
    if len(raw) != 10:
        raise ValueError("LightColor is not the researched exact 10-byte struct")
    cur = Cursor(raw, 0, len(raw))
    values, offsets = {}, {}
    for native, public in zip(NESTED_NAMES, PUBLIC_NAMES):
        index = cur.ci()
        if not 0 <= index < len(names) or names[index] != native:
            raise ValueError("LightColor nested property names/order do not match original source")
        if cur.u8() != 0x01:  # unindexed ByteProperty with one-byte value
            raise ValueError("LightColor nested field has unsupported tag type/flags")
        offsets[public] = cur.at
        values[public] = cur.u8()
    terminator = cur.ci()
    if (not 0 <= terminator < len(names) or names[terminator] != "None"
            or cur.at != len(raw)):
        raise ValueError("LightColor nested tag list is not exactly terminated")
    return values, offsets


def _one_original(world: DX2Map, export: int, actor: str, t3: T3Package) -> dict:
    """Fail closed unless both readers agree on every original field and actor."""
    if (type(export) is not int or export < 1
            or export > len(world._package.exports)
            or type(actor) is not str or not actor):
        raise ValueError("Exact original one-based actor export and name required")
    scenes, _ = world._package.scene_actors()
    present = [row for row in scenes if row["export"] == export
               and row["name"] == actor]
    if len(present) != 1:
        raise ValueError("LightColor source actor is not uniquely positioned in the original Level")
    dxexp = world._package.exports[export - 1]
    t3exp = t3.exports[export - 1]
    if (dxexp["name"] != actor or t3exp.name != actor
            or t3.export_class(t3exp) != world._package.class_name(dxexp)):
        raise ValueError("LightColor source native actor export identity disagreement")
    records, _ = scan_dx2_gamesys(world._package, dxexp)
    matching = [rec for rec in records if rec["property_id"] == PROPERTY_ID]
    if len(matching) != 1:
        raise ValueError("LightColor must be exactly one pre-existing native GameSys block")
    rec = matching[0]
    if (rec["encoded_id"] != ENCODED_ID
            or rec["encoding_code"] != 8 or rec["type_word"] != 8
            or rec["runtime_flag"] or rec["version"] != 1
            or rec["payload_bytes"] != 10
            or not dxexp["offset"] <= rec["payload_offset"]
            or rec["payload_offset"] + 10 > dxexp["offset"] + dxexp["size"]):
        raise ValueError("Original LightColor has unsupported encoding, version or bounds")
    start = rec["payload_offset"]
    raw = world._package.data[start:start + 10]
    if _sha(raw) != rec["payload_sha256"]:
        raise ValueError("Original LightColor payload SHA mismatch")
    values, local_offsets = _components(raw, world._package.names)
    parsed = t3.read_actor(t3exp)
    if parsed.parse_error or not isinstance(parsed.gamesys, list):
        raise ValueError("Independent T3SDK actor LightColor parse failed")
    candidates = [b for b in parsed.gamesys if b.prop_id == PROPERTY_ID]
    if len(candidates) != 1:
        raise ValueError("T3SDK LightColor block duplicate or missing")
    block = candidates[0]
    if (block.id != ENCODED_ID or block.version != 1
            or block.kind != "struct" or block.data != raw
            or not isinstance(block.value, list)
            or len(block.value) != 3):
        raise ValueError("T3SDK LightColor raw and nested struct disagree")
    for i, tag in enumerate(block.value):
        if (tag.name != NESTED_NAMES[i] or tag.type != "Byte"
                or tag.array_index != 0 or tag.size != 1
                or type(tag.value) is not int
                or tag.value != values[PUBLIC_NAMES[i]]):
            raise ValueError("T3SDK LightColor nested Byte tags disagree")
    return {
        "actor": actor, "export": export,
        "actor_class": world._package.class_name(dxexp),
        "source_values": values,
        "offsets": {k: start + v for k, v in local_offsets.items()},
        "source_payload_sha256": rec["payload_sha256"],
        "encoded_property_id": ENCODED_ID, "property_version": 1,
        "source_exact_10byte_struct": True,
    }


def original_light_colors(world: DX2Map, *, limit: int = 100) -> dict:
    """List eligible placed original authorship, no map modification."""
    if type(limit) is not int or not 0 <= limit <= 1000:
        raise ValueError("Original LightColor listing limit must be 0..1000")
    world._check_original_unchanged()
    t3 = T3Package(world.source)
    native, failures = world._package.scene_actors()
    rows, blocked = [], 0
    for row in native:
        try:
            candidate = _one_original(world, row["export"], row["name"], t3)
            rows.append({
                "actor": candidate["actor"], "export": candidate["export"],
                "actor_class": candidate["actor_class"],
                "original_values": candidate["source_values"],
                "strict_existing_struct_writer_candidate": True,
                "actual_gameplay_effect_for_this_actor_verified": False,
            })
        except (ValueError, IndexError, EOFError):
            blocked += 1
    world._check_original_unchanged()
    return {
        "schema": SCHEMA, "status": "read-only-source-verified",
        "source_map": world.source.name, "source_sha256": world.source_sha256,
        "eligible_actor_count": len(rows), "refused_or_absent_count": blocked,
        "source_position_decode_failures": failures, "shown": rows[:limit],
        "read_only": True, "native_new_light_actor_creation_enabled": False,
        "gameplay_runtime_verified": False, "source_original_modified": False,
    }


def _check_values(expected: object, changes: object, source: dict) -> list[dict]:
    if (not isinstance(expected, (list, tuple)) or len(expected) != 3
            or any(type(x) is not int or not 0 <= x <= 255 for x in expected)):
        raise ValueError("Pin all three original LightColor bytes as integer 0..255")
    original = tuple(source[k] for k in PUBLIC_NAMES)
    if tuple(expected) != original:
        raise ValueError("Original LightColor triple differs from pinned expected source bytes")
    if (not isinstance(changes, dict) or not 1 <= len(changes) <= 3
            or any(k not in PUBLIC_NAMES or type(v) is not int or not 0 <= v <= 255
                   for k, v in changes.items())):
        raise ValueError("Edit only 1..3 known LightColor byte fields with integers 0..255")
    if any(changes[k] == source[k] for k in changes):
        raise ValueError("LightColor change must actually modify each requested source byte")
    return [{"field": k, "source": source[k], "replacement": changes[k]}
            for k in PUBLIC_NAMES if k in changes]


def _rebuild(world: DX2Map, candidate: dict, changes: list[dict], t3: T3Package) -> bytes:
    original = world._package.data
    record_offset = min(candidate["offsets"].values()) - 2
    # The original compact names are one-byte indices for the exact 10-byte
    # format, but their numeric indices are never hardcoded.
    original_payload = original[record_offset:record_offset + 10]
    edited_payload = bytearray(original_payload)
    direct = bytearray(original)
    for row in changes:
        at = candidate["offsets"][row["field"]]
        if (original[at] != row["source"] or at not in
                (record_offset + 2, record_offset + 5, record_offset + 8)):
            raise ValueError("Original LightColor relative byte offset changed")
        edited_payload[at - record_offset] = row["replacement"]
        direct[at] = row["replacement"]
    writer = PackageWriter(t3)
    original_actor = t3.exports[candidate["export"] - 1]
    edit = ActorEdit(writer, original_actor)
    hits = [b for b in edit.layout.blocks if (b.id & 0xffff) == PROPERTY_ID]
    if (len(hits) != 1 or hits[0].id != ENCODED_ID
            or hits[0].version != 1 or hits[0].data != original_payload):
        raise ValueError("T3SDK write object has incompatible original LightColor")
    edit.set_block(PROPERTY_ID, bytes(edited_payload), "existing_3_byte_LightColor")
    if not edit.commit():
        raise ValueError("LightColor writer made no original byte change")
    encoded = writer.write()
    if (encoded != bytes(direct) or len(encoded) != len(original)
            or writer.added_exports or writer.added_names):
        raise ValueError("Independent full-package LightColor serializers disagree")
    return encoded


def _proof(world: DX2Map, *, export: int, actor: str,
           expected: object, changes: object) -> tuple[dict, bytes]:
    world._check_original_unchanged()
    t3 = T3Package(world.source)
    candidate = _one_original(world, export, actor, t3)
    edits = _check_values(expected, changes, candidate["source_values"])
    noop, identical = inspect_noop(world.source)
    if (identical != world._package.data or
            noop["source_sha256"] != world.source_sha256
            or noop["byte_identical"] is not True):
        raise ValueError("LightColor source GMP failed byte-identical T3SDK no-op")
    revised = _rebuild(world, candidate, edits, t3)
    for row in edits:
        row["absolute_offset"] = candidate["offsets"][row["field"]]
    actual_diffs = [i for i, (a, b) in
                    enumerate(zip(world._package.data, revised)) if a != b]
    if (sorted(actual_diffs) != sorted(e["absolute_offset"] for e in edits)
            or len(revised) != len(world._package.data)):
        raise ValueError("LightColor output changed more than selected three byte fields")
    world._check_original_unchanged()
    proof = {
        "schema": SCHEMA, "status": "in-memory-exact-parity",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "actor": candidate["actor"], "actor_export": candidate["export"],
        "actor_class": candidate["actor_class"],
        "encoded_property_id": ENCODED_ID, "property_version": 1,
        "source_payload_sha256": candidate["source_payload_sha256"],
        "expected_source_values": {k: candidate["source_values"][k] for k in PUBLIC_NAMES},
        "edits": edits, "changed_bytes": len(edits),
        "output_sha256": _sha(revised),
        "dual_serializer_full_package_match": True,
        "original_map_modified": False, "new_light_actor_created": False,
        "gameplay_runtime_verified": False, "visible_lighting_effect_verified": False,
    }
    return proof, revised


def set_existing_light_color(
    world: DX2Map, *, export: int, actor: str, expected: tuple[int, int, int],
    changes: dict[str, int], output: str | Path, write: bool = False,
) -> dict:
    """Source-checked dry run by default; explicit isolated exact byte copy."""
    if type(write) is not bool:
        raise ValueError("write must be exactly Boolean")
    target = _safe_copy_path(world, output, exists=False)
    manifest = target.with_suffix(".dx2sdk-lightcolor.json")
    if manifest.exists():
        raise ValueError("Refusing to overwrite an existing LightColor manifest")
    proof, edited = _proof(world, export=export, actor=actor,
                           expected=expected, changes=changes)
    if not write:
        return {**proof, "status": "dry-run", "edited_package_written": False}
    world._check_original_unchanged()
    target.parent.mkdir(parents=True, exist_ok=True)
    created_map, created_manifest = False, False
    try:
        with target.open("xb") as file:
            created_map = True
            file.write(edited)
        if target.read_bytes() != edited:
            raise ValueError("Saved LightColor copy differs from verified edited data")
        reparse = DX2Package(target)
        source_pkg = world._package
        if (reparse.guid != source_pkg.guid or reparse.names != source_pkg.names
                or reparse.imports != source_pkg.imports
                or reparse.exports != source_pkg.exports):
            raise ValueError("Isolated LightColor map modified native package tables")
        doc = {**proof, "status": "isolated-GMP-written-runtime-unverified",
               "output": str(target), "edited_package_written": True}
        with manifest.open("x", encoding="utf8") as f:
            created_manifest = True
            json.dump(doc, f, indent=2, allow_nan=False, sort_keys=True)
            f.write("\n")
        verified = verify_saved_light_color(world, target)
        if not verified["verified_binary_structure"]:
            raise ValueError("Independent saved LightColor verification failed")
        return {**doc, "verified_binary_structure": True}
    except Exception:
        if created_manifest:
            manifest.unlink(missing_ok=True)
        if created_map:
            target.unlink(missing_ok=True)
        raise


def verify_saved_light_color(world: DX2Map, output: str | Path) -> dict:
    """Independently reconstruct entire saved GMP and reject forged sidecars."""
    world._check_original_unchanged()
    target = _safe_copy_path(world, output, exists=True)
    manifest = target.with_suffix(".dx2sdk-lightcolor.json")
    if not manifest.is_file() or not 0 < manifest.stat().st_size <= MAX_MANIFEST:
        raise ValueError("LightColor output has missing/oversized private manifest")
    doc = json.loads(manifest.read_text(encoding="utf8"))
    if (not isinstance(doc, dict)
            or doc.get("schema") != SCHEMA
            or doc.get("status") != "isolated-GMP-written-runtime-unverified"
            or doc.get("output") != str(target)
            or doc.get("source_map") != world.source.name
            or doc.get("source_sha256") != world.source_sha256
            or doc.get("encoded_property_id") != ENCODED_ID
            or doc.get("property_version") != 1
            or doc.get("edited_package_written") is not True
            or doc.get("original_map_modified") is not False
            or doc.get("new_light_actor_created") is not False
            or doc.get("gameplay_runtime_verified") is not False
            or doc.get("visible_lighting_effect_verified") is not False
            or doc.get("dual_serializer_full_package_match") is not True):
        raise ValueError("Untrusted LightColor manifest identity or runtime support claim")
    values = doc.get("expected_source_values")
    if not isinstance(values, dict) or set(values) != set(PUBLIC_NAMES):
        raise ValueError("Missing original three LightColor values")
    edits = doc.get("edits")
    if (not isinstance(edits, list) or not 1 <= len(edits) <= 3
            or any(not isinstance(e, dict) or set(e) !=
                   {"field", "source", "replacement", "absolute_offset"}
                   for e in edits)):
        raise ValueError("Untrusted LightColor original field edits")
    changes = {}
    for item in edits:
        if item["field"] in changes:
            raise ValueError("Duplicate LightColor byte edit")
        changes[item["field"]] = item["replacement"]
    expected = tuple(values[k] for k in PUBLIC_NAMES)
    if (type(doc.get("actor_export")) is not int
            or type(doc.get("actor")) is not str):
        raise ValueError("Invalid original LightColor export identity")
    report, rebuilt = _proof(
        world, export=doc["actor_export"], actor=doc["actor"],
        expected=expected, changes=changes)
    for key in ("source_payload_sha256", "actor_class", "edits",
                "changed_bytes", "output_sha256", "expected_source_values"):
        if doc.get(key) != report[key]:
            raise ValueError("Saved LightColor manifest does not match independent source replay")
    raw = target.read_bytes()
    if raw != rebuilt or _sha(raw) != doc["output_sha256"]:
        raise ValueError("Saved LightColor GMP differs from independent full-package replay")
    reparse = DX2Package(target)
    if (reparse.guid != world._package.guid
            or reparse.names != world._package.names
            or reparse.imports != world._package.imports
            or reparse.exports != world._package.exports):
        raise ValueError("Saved LightColor package tables changed")
    world._check_original_unchanged()
    return {
        "schema": SCHEMA, "verified_binary_structure": True,
        "source_map": world.source.name,
        "actor": doc["actor"], "actor_export": doc["actor_export"],
        "changed_bytes": len(edits), "unapproved_bytes": 0,
        "original_map_modified": False, "gameplay_runtime_verified": False,
        "native_light_spawn_enabled": False,
    }
