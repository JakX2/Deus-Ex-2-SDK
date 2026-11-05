"""DX2SDK experimental existing native *tagged* scalar Save As.

Supports only original placed, source-catalog-verified StaticMeshActors, only
already-authored top-level UE95 IntProperty (kind 2) / FloatProperty (kind 4)
with an exact four-byte payload and no indexed array flag.

This is NOT GameSys block editing, booleans, scripts, class creation, resource
rebuild, collision synthesis or retail gameplay verification. Writes only
a fresh isolated GMP and a separate independent binary-verification manifest.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Mapping

from .api import DX2Map, _safe_output
from dx2inspect import Cursor, HAS_STACK, Package
from dx2_package_roundtrip import inspect_noop

SCHEMA = "DX2SDK-native-tagged-scalar-copy-v1"
MAX_EDITS = 256
MAX_ACTOR_EXPORT_BYTES = 16 * 1024 * 1024
MAX_MANIFEST = 3 * 1024 * 1024
FORBIDDEN = frozenset({
    "location", "rotation", "drawscale3d", "collisionradius",
    "collisionheight", "physics", "mesh", "staticmesh", "brush",
})


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _native_tags(pkg: Package, exp: dict) -> list[dict]:
    if (exp["size"] <= 0 or exp["size"] > MAX_ACTOR_EXPORT_BYTES
            or pkg.version != 95):
        raise ValueError("Unsupported original actor export or UE package version")
    cursor = Cursor(pkg.data, exp["offset"], exp["offset"] + exp["size"])
    if exp["flags"] & HAS_STACK:
        node = cursor.ci()
        cursor.ci()
        cursor.u64()
        cursor.u32()
        if node:
            cursor.ci()
    tags = []
    for _ in range(100000):
        index = cursor.ci()
        if not 0 <= index < len(pkg.names):
            raise ValueError("Original tagged property name index out of range")
        name = pkg.names[index]
        if name == "None":
            return tags
        info = cursor.u8()
        kind = info & 15
        size_kind = (info >> 4) & 7
        indexed = bool(info & 128)
        if kind == 10:
            struct_name = cursor.ci()
            if not 0 <= struct_name < len(pkg.names):
                raise ValueError("Original native struct-name reference invalid")
        if size_kind < 5:
            size = (1, 2, 4, 12, 16)[size_kind]
        elif size_kind == 5:
            size = cursor.u8()
        elif size_kind == 6:
            size = cursor.u16()
        else:
            size = cursor.u32()
        if indexed and kind != 3:
            first = cursor.u8()
            if first & 128:
                if first & 64:
                    cursor.get(3)
                else:
                    cursor.get(1)
        offset = cursor.at
        cursor.get(size)
        tags.append({
            "property": name, "native_kind": kind, "size": size,
            "offset": offset, "has_array_or_special_flag": indexed,
        })
    raise ValueError("Original actor tagged property list is unterminated")


def _source_actor(world: DX2Map, name: str) -> tuple[dict, dict]:
    world._check_original_unchanged()
    if world._cache is None or world.actors_file is None:
        raise ValueError("Source-matched original actors.json is required for scalar edits")
    if type(name) is not str or not name:
        raise ValueError("Exact original actor name is required")
    matches = [actor for actor in world._cache["actors"]
               if actor.get("name") == name]
    if len(matches) != 1:
        raise ValueError("Original actor name absent or ambiguous")
    actor = matches[0]
    export = actor.get("export")
    if (type(export) is not int or not 1 <= export <= len(world._package.exports)
            or actor.get("class") != "StaticMeshActor"):
        raise ValueError("Scalar editing requires a source-verified existing StaticMeshActor")
    exp = world._package.exports[export - 1]
    if (exp["name"] != name or world._package.class_name(exp) != "StaticMeshActor"):
        raise ValueError("Original native actor export identity mismatch")
    # A catalog's mesh display name can be unresolved or user-edited.
    # Never use it as an authorization criterion for original binary edits.
    # Verify source actor placement/location against the unchanged GMP itself.
    scenes, _ = world._package.scene_actors()
    matches = [item for item in scenes
               if item["export"] == export and item["name"] == name
               and item["class"] == "StaticMeshActor"]
    cached = actor.get("location")
    if (len(matches) != 1 or not isinstance(cached, list)
            or len(cached) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   for v in cached)
            or any(abs(float(cached[i]) - float(matches[0][axis])) > 0.01
                   for i, axis in enumerate("xyz"))):
        raise ValueError("Original positioned actor does not match source-native Location identity")
    return actor, exp


def _numeric_candidates(world: DX2Map, name: str) -> list[dict]:
    actor, exp = _source_actor(world, name)
    tags = _native_tags(world._package, exp)
    names = {}
    for tag in tags:
        names[tag["property"]] = names.get(tag["property"], 0) + 1
    result = []
    for tag in tags:
        prop = tag["property"]
        kind = tag["native_kind"]
        if (names[prop] != 1 or tag["has_array_or_special_flag"]
                or prop.casefold() in FORBIDDEN or kind not in (2, 4)
                or tag["size"] != 4):
            continue
        fmt = "<i" if kind == 2 else "<f"
        number = struct.unpack_from(fmt, world._package.data, tag["offset"])[0]
        if not math.isfinite(float(number)):
            continue
        result.append({
            "property": prop,
            "type": "int32" if kind == 2 else "float32",
            "kind": kind,
            "offset": tag["offset"],
            "source_value": number,
            "native_editable_experimental": True,
        })
    return result


def original_scalar_fields(world: DX2Map, actor_name: str) -> dict:
    """Source-verified, existing scalar tag inventory. Does not write."""
    rows = _numeric_candidates(world, actor_name)
    return {
        "schema": SCHEMA, "status": "original_scalar_field_inventory",
        "actor_name": actor_name, "original_map": world.source.name,
        "original_map_sha256": world.source_sha256,
        "fields": [{k: row[k] for k in
                    ("property", "type", "source_value")}
                   for row in rows],
        "read_only": True, "runtime_game_verified": False,
        "native_gamesys_or_script_writer_enabled": False,
    }


def _encode(value: object, kind: int) -> tuple[float | int, bytes]:
    if kind == 2:
        if type(value) is not int or not -2147483648 <= value <= 2147483647:
            raise ValueError("Native int32 tagged scalar requires signed 32-bit integer")
        return value, struct.pack("<i", value)
    if kind == 4:
        if (type(value) not in (int, float)
                or not math.isfinite(float(value))
                or abs(float(value)) > 1_000_000):
            raise ValueError("Native float32 scalar requires finite numeric value <= 1 million")
        packed = struct.pack("<f", float(value))
        number = struct.unpack("<f", packed)[0]
        if not math.isfinite(number):
            raise ValueError("Float32 scalar failed finite source representation")
        return number, packed
    raise ValueError("Only existing UE95 native kind 2/4 numeric properties are supported")


def _make_edits(world: DX2Map, changes: Mapping[str, Mapping[str, object]]) -> list[dict]:
    if (not isinstance(changes, Mapping)
            or not 1 <= len(changes) <= MAX_EDITS):
        raise ValueError("Requires 1..256 original actor scalar edits")
    edits = []
    touched = set()
    for actor_name, properties in changes.items():
        if not isinstance(properties, Mapping) or not properties:
            raise ValueError("Each source actor must specify original tagged fields")
        actor, exp = _source_actor(world, actor_name)
        fields = {tag["property"]: tag for tag in _numeric_candidates(world, actor_name)}
        for prop, value in properties.items():
            if type(prop) is not str or prop not in fields:
                raise ValueError("Requested property is absent or not a safe 4-byte native scalar")
            tag = fields[prop]
            new_value, new_bytes = _encode(value, tag["kind"])
            offset = tag["offset"]
            if offset in touched:
                raise ValueError("Duplicate native scalar field write")
            touched.add(offset)
            before = world._package.data[offset:offset + 4]
            if new_bytes == before:
                raise ValueError("Native scalar edit is identical to original")
            edits.append({
                "actor": actor_name,
                "actor_class": "StaticMeshActor",
                "export": actor["export"],
                "property": prop,
                "native_kind": tag["kind"],
                "offset": offset,
                "before_value": tag["source_value"],
                "after_value": new_value,
                "before_hex": before.hex(),  # private manifest, original data, never CLI
                "after_hex": new_bytes.hex(),  # private manifest, original data, never CLI
            })
            if len(edits) > MAX_EDITS:
                raise ValueError("Native scalar edit plan exceeds 256 fields")
    return sorted(edits, key=lambda row: (row["export"], row["offset"]))


def _manifest(output: Path) -> Path:
    return output.with_suffix(".dx2sdk-scalar.json")


def save_as_scalar_copy(
    world: DX2Map, changes: Mapping[str, Mapping[str, object]],
    output: str | Path, *, write: bool = False,
) -> dict:
    """Dry-run by default; explicit source-checked scalar save to isolated GMP."""
    world._check_original_unchanged()
    target = _safe_output(world.source, output)
    manifest = _manifest(target)
    if manifest.exists():
        raise ValueError("Refusing to overwrite existing native scalar copy manifest")
    edits = _make_edits(world, changes)
    # Reconstruct an exact no-change original GMP through the independent
    # MIT T3SDK writer *before* enabling any native scalar change.
    noop, identical = inspect_noop(world.source)
    if (identical != world._package.data or
            noop["source_sha256"] != world.source_sha256 or
            noop["byte_identical"] is not True):
        raise ValueError("Original GMP does not pass independent no-op writer baseline")
    original = world._package.data
    patched = bytearray(original)
    allowed = set()
    for row in edits:
        where = row["offset"]
        new_bytes = bytes.fromhex(row["after_hex"])
        if where < 0 or where + 4 > len(patched):
            raise ValueError("Native scalar position is beyond original map extent")
        for pos in range(where, where + 4):
            if pos in allowed:
                raise ValueError("Overlapping native scalar edit byte range")
            allowed.add(pos)
        patched[where:where + 4] = new_bytes
    changed = {index for index, (a, b) in
               enumerate(zip(original, patched)) if a != b}
    if not changed or changed - allowed or len(patched) != len(original):
        raise ValueError("Native scalar output changed unauthorized source bytes")
    report = {
        "schema": SCHEMA, "status": "dry-run" if not write else "written-unverified-gameplay",
        "source": str(world.source), "output": str(target),
        "source_sha256": world.source_sha256,
        "source_actor_cache_sha256": world._actor_cache_sha256,
        "output_sha256": _hash(bytes(patched)),
        "original_size": len(original),
        "edited_field_count": len(edits),
        "changed_byte_count": len(changed),
        "edits": edits,
        "source_original_modified": False,
        "independent_byte_validation": False,
        "runtime_game_verified": False,
        "native_script_writer_enabled": False,
        "bsp_collision_rebuild_enabled": False,
        "warnings": [
            "EXPERIMENTAL direct native tagged scalar field patch, not runtime-gameplay validated.",
            "No original game file is overwritten; only an isolated GMP copy may be written.",
            "No native GameSys properties, scripts, actor creation or BSP/Havok rebuild.",
        ],
    }
    if not write:
        return report
    # Do not rely on a stale SHA check performed only at constructor time.
    world._check_original_unchanged()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as f:
            f.write(patched)
        check = Package(target)
        if (check.version != world._package.version
                or check.licensee != world._package.licensee
                or check.guid != world._package.guid
                or check.table_counts != world._package.table_counts
                or check.exports != world._package.exports
                or check.names != world._package.names
                or check.imports != world._package.imports
                or check.data != bytes(patched)):
            raise ValueError("Native output package reparse/structure mismatch")
        with manifest.open("x", encoding="utf8") as f:
            json.dump(report, f, indent=2, sort_keys=True, allow_nan=False)
        verify = verify_scalar_copy(world, target)
        if not verify["verified_binary_structure"]:
            raise ValueError("Independent scalar output verification failed")
    except Exception:
        # A failed unverified candidate is never left in the output folder.
        manifest.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    report["independent_byte_validation"] = True
    report["independent_verified_changed_bytes"] = verify["changed_bytes"]
    return report


def verify_scalar_copy(world: DX2Map, output: str | Path) -> dict:
    """Read fresh source/output packages; independently verify every byte."""
    world._check_original_unchanged()
    target = Path(output).expanduser().resolve(strict=True)
    if (target.name.casefold() != world.source.name.casefold()
            or target == world.source):
        raise ValueError("Scalar output must retain original GMP basename")
    manifest = _manifest(target)
    if not manifest.is_file() or not 0 < manifest.stat().st_size <= MAX_MANIFEST:
        raise ValueError("Missing or oversized private scalar copy manifest")
    data = json.loads(manifest.read_text("utf8"))
    if (data.get("schema") != SCHEMA
            or data.get("status") != "written-unverified-gameplay"
            or data.get("runtime_game_verified") is not False
            or data.get("native_script_writer_enabled") is not False
            or data.get("bsp_collision_rebuild_enabled") is not False
            or data.get("source_original_modified") is not False
            or data.get("source") != str(world.source)
            or data.get("output") != str(target)
            or data.get("source_sha256") != world.source_sha256
            or data.get("source_actor_cache_sha256") != world._actor_cache_sha256):
        raise ValueError("Untrusted scalar manifest or source identity")
    original, edited = world._package, Package(target)
    if (original.version != 95 or original.licensee not in (68, 69)
            or edited.version != original.version
            or edited.licensee != original.licensee
            or original.guid != edited.guid
            or original.table_counts != edited.table_counts
            or original.names != edited.names
            or original.imports != edited.imports
            or original.exports != edited.exports
            or len(original.data) != len(edited.data)
            or len(edited.data) != data.get("original_size")
            or _hash(edited.data) != data.get("output_sha256")):
        raise ValueError("Native package structure or file SHA differs from manifest")
    rows = data.get("edits")
    if (not isinstance(rows, list) or not 1 <= len(rows) <= MAX_EDITS
            or data.get("edited_field_count") != len(rows)):
        raise ValueError("Invalid edited scalar field count")
    accepted = set()
    candidates_by_actor = {}
    changed_positions = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid scalar manifest field")
        name = row.get("actor")
        prop = row.get("property")
        if (type(name) is not str or type(prop) is not str
                or row.get("actor_class") != "StaticMeshActor"):
            raise ValueError("Scalar manifest actor/field invalid")
        if name not in candidates_by_actor:
            a, _ = _source_actor(world, name)
            candidates_by_actor[name] = (
                a, {f["property"]: f for f in _numeric_candidates(world, name)})
        actor, fields = candidates_by_actor[name]
        field = fields.get(prop)
        if (field is None or type(row.get("export")) is not int
                or row["export"] != actor["export"]
                or type(row.get("offset")) is not int
                or row["offset"] != field["offset"]
                or row.get("native_kind") != field["kind"]
                or row.get("before_value") != field["source_value"]):
            raise ValueError("Scalar manifest differs from original native actor/field")
        expected, raw = _encode(row.get("after_value"), field["kind"])
        if expected != row.get("after_value"):
            raise ValueError("Scalar manifest target field is not native representable")
        offset = field["offset"]
        before = original.data[offset:offset + 4]
        after = edited.data[offset:offset + 4]
        if (row.get("before_hex") != before.hex()
                or row.get("after_hex") != raw.hex()
                or after != raw or before == after):
            raise ValueError("Native scalar original/target bytes differ from manifest")
        for pos in range(offset, offset + 4):
            if pos in accepted:
                raise ValueError("Overlapping or duplicate native scalar edits")
            accepted.add(pos)
    for i, (a, b) in enumerate(zip(original.data, edited.data)):
        if a != b:
            changed_positions.add(i)
            if i not in accepted:
                raise ValueError("Unapproved native byte changed outside original scalar field")
    if not changed_positions or data.get("changed_byte_count") != len(changed_positions):
        raise ValueError("Native scalar patch changed-byte count mismatch")
    return {
        "schema": SCHEMA,
        "verified_binary_structure": True,
        "runtime_game_verified": False,
        "source_map": world.source.name,
        "changed_fields": len(rows),
        "changed_bytes": len(changed_positions),
        "unapproved_bytes": 0,
        "script_writer_enabled": False,
        "source_original_modified": False,
    }
