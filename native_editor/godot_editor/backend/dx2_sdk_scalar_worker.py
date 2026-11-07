#!/usr/bin/env python3
"""DX2Ed v0.14: one source-original UE95 native numeric tagged property GUI bridge.

Original StaticMeshActor with a VERIFIED matching owner actors.json only.
No generic actor/class/GameSys writer, new tag, runtime field discovery,
BSP/collision change, proprietary asset distribution or runtime assurance.

list/fields read original only. preview is an in-memory 4-byte bounded
source patch after T3SDK no-op baseline; apply explicitly writes a fresh
same-basename isolated GMP, a private manifest and independently verifies
EVERY original package byte. The original source and cache stay unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dx2sdk import DX2Map  # noqa: E402
from dx2sdk.api import _safe_output  # noqa: E402
from dx2sdk.scalars import SCHEMA, _encode  # noqa: E402

BRIDGE_SCHEMA = "DX2Ed-GUI-original-native-scalar-worker-v1"
MAX_REQUEST_BYTES = 4096
MAX_ACTORS_SHOWN = 1000


def _pin(value: object, what: str) -> str:
    if (type(value) is not str or len(value) != 64 or
            any(ch not in "0123456789abcdef" for ch in value)):
        raise ValueError(what + " requires lowercase 64-character SHA-256")
    return value


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _original(args: argparse.Namespace) -> DX2Map:
    source_sha = _pin(args.source_sha256, "Original GMP")
    cache_sha = _pin(args.actors_sha256, "Original actor cache")
    world = DX2Map.open(args.map, args.actors)
    if world.source_sha256 != source_sha or world._actor_cache_sha256 != cache_sha:
        raise ValueError("Original GMP or source-bound actors.json cache changed after scan")
    if (world.actors_file is None or world._cache is None or
            not world.actors_file.is_file() or
            _sha_file(world.actors_file) != cache_sha):
        raise ValueError("Verified original actors.json is required")
    world._check_original_unchanged()
    return world


def _unique_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON request field is not permitted")
        result[name] = value
    return result


def _request(value: object) -> dict:
    if (type(value) is not str or
            not 0 < len(value.encode("utf8")) <= MAX_REQUEST_BYTES):
        raise ValueError("Scalar GUI edit request exceeds bounded JSON size")
    doc = json.loads(
        value, parse_constant=lambda x: (_ for _ in ()).throw(
            ValueError("Nonfinite JSON scalar values are unsupported")),
        object_pairs_hook=_unique_pairs)
    if (not isinstance(doc, dict) or set(doc) != {
            "actor", "export", "property", "type", "expected", "replacement"}):
        raise ValueError("Scalar edit must pin actor/export/property/type/original/new value")
    if (type(doc["actor"]) is not str or not 0 < len(doc["actor"]) <= 180 or
            type(doc["export"]) is not int or doc["export"] <= 0 or
            type(doc["property"]) is not str or not 0 < len(doc["property"]) <= 128 or
            doc["type"] not in ("int32", "float32")):
        raise ValueError("Unknown original native scalar actor, export or field type")
    if doc["type"] == "int32":
        if (type(doc["expected"]) is not int or
                type(doc["replacement"]) is not int):
            raise ValueError("Int32 scalar GUI values must be actual integers")
    else:
        if (type(doc["expected"]) not in (int, float) or
                type(doc["replacement"]) not in (int, float) or
                not math.isfinite(float(doc["expected"])) or
                not math.isfinite(float(doc["replacement"]))):
            raise ValueError("Float32 scalar GUI values must be finite numeric values")
    return doc


def _actor(world: DX2Map, actor: str, export: int) -> dict:
    native = world.actors(actor_class="StaticMeshActor", limit=30000)
    if native.get("read_only") is not True or native.get("map") != world.source.name:
        raise ValueError("Original native actor membership audit refused")
    matches = [x for x in native["shown"] if
               x.get("name") == actor and x.get("export") == export and
               x.get("class") == "StaticMeshActor"]
    if len(matches) != 1:
        raise ValueError("Actor/export is not a unique original placed StaticMeshActor")
    return matches[0]


def _fields(world: DX2Map, actor: str, export: int) -> dict:
    native = _actor(world, actor, export)
    doc = world.native_scalar_fields(actor)
    if (doc.get("schema") != SCHEMA or
            doc.get("status") != "original_scalar_field_inventory" or
            doc.get("actor_name") != actor or
            doc.get("original_map") != world.source.name or
            doc.get("original_map_sha256") != world.source_sha256 or
            doc.get("read_only") is not True or
            doc.get("runtime_game_verified") is not False or
            doc.get("native_gamesys_or_script_writer_enabled") is not False or
            not isinstance(doc.get("fields"), list) or len(doc["fields"]) > 256):
        raise ValueError("Source-tagged native scalar inspector returned untrusted fields")
    used = set()
    for row in doc["fields"]:
        if (not isinstance(row, dict) or set(row) !=
                {"property", "type", "source_value"} or
                type(row["property"]) is not str or row["property"] in used or
                row["type"] not in ("int32", "float32")):
            raise ValueError("Native scalar source metadata is duplicate or unrecognized")
        used.add(row["property"])
        _encode(row["source_value"], 2 if row["type"] == "int32" else 4)
    return {**doc, "export": native["export"]}


def perform(args: argparse.Namespace) -> dict:
    world = _original(args)
    base = {
        "bridge_schema": BRIDGE_SCHEMA,
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "actors_sha256": world._actor_cache_sha256,
        "source_original_modified": False,
        "runtime_game_verified": False,
        "native_gamesys_or_script_writer_enabled": False,
        "native_new_actor_creation_enabled": False,
        "bsp_collision_rebuild_enabled": False,
    }
    if args.action == "list":
        source = world.actors(actor_class="StaticMeshActor", limit=MAX_ACTORS_SHOWN)
        seen = set()
        eligible = []
        for row in source["shown"]:
            if (row.get("class") != "StaticMeshActor" or
                    type(row.get("export")) is not int or
                    type(row.get("name")) is not str):
                raise ValueError("Untrusted original StaticMeshActor inventory")
            key = (row["export"], row["name"])
            if key in seen:
                raise ValueError("Duplicate source StaticMeshActor identity")
            seen.add(key)
            eligible.append({
                "actor": row["name"], "export": row["export"],
                "actor_class": "StaticMeshActor",
            })
        world._check_original_unchanged()
        return {
            **base, "action": "list", "schema": SCHEMA,
            "status": "original_staticmeshactor_list",
            "actors": eligible, "shown_count": len(eligible),
            "read_decode_failures": source["read_decode_failures"],
            "read_only": True,
            "source_actor_cache_verified": True,
        }
    if (args.action == "fields" and type(args.actor) is str
            and type(args.export) is int and args.export > 0):
        doc = _fields(world, args.actor, args.export)
        world._check_original_unchanged()
        return {**base, "action": "fields", **doc}
    if args.action not in ("preview", "apply") or not args.output:
        raise ValueError("Scalar GUI needs an eligible field or explicit preview/apply output")
    req = _request(args.request_json)
    original = _fields(world, req["actor"], req["export"])
    found = [f for f in original["fields"] if
             f["property"] == req["property"] and f["type"] == req["type"]]
    if len(found) != 1 or found[0]["source_value"] != req["expected"]:
        raise ValueError("Native property type or original serialized value differs from pinned GUI edit")
    kind = 2 if req["type"] == "int32" else 4
    _encode(req["expected"], kind)
    replacement, replacement_bytes = _encode(req["replacement"], kind)
    expected_bytes = _encode(found[0]["source_value"], kind)[1]
    if replacement_bytes == expected_bytes:
        raise ValueError("Native scalar GUI edit must change its four-byte source field")
    target = _safe_output(world.source, args.output)
    manifest = target.with_suffix(".dx2sdk-scalar.json")
    if manifest.exists():
        raise ValueError("Existing native scalar private manifest cannot be overwritten")
    changes = {req["actor"]: {req["property"]: req["replacement"]}}
    report = world.save_as_scalar_changes(changes, target, write=args.action == "apply")
    if (report.get("schema") != SCHEMA or
            report.get("source_sha256") != world.source_sha256 or
            report.get("source_actor_cache_sha256") != world._actor_cache_sha256 or
            report.get("edited_field_count") != 1 or
            report.get("original_size") != len(world._package.data) or
            not 1 <= report.get("changed_byte_count", 0) <= 4 or
            report.get("source_original_modified") is not False or
            report.get("runtime_game_verified") is not False or
            report.get("native_script_writer_enabled") is not False or
            report.get("bsp_collision_rebuild_enabled") is not False or
            not isinstance(report.get("edits"), list) or
            len(report["edits"]) != 1):
        raise ValueError("Native scalar source writer returned untrusted patch proof")
    edit = report["edits"][0]
    if (edit.get("actor") != req["actor"] or
            edit.get("export") != req["export"] or
            edit.get("property") != req["property"] or
            edit.get("before_value") != found[0]["source_value"] or
            edit.get("after_value") != replacement or
            edit.get("native_kind") != kind):
        raise ValueError("Native scalar patch lost original property identity")
    if args.action == "preview":
        if (report.get("status") != "dry-run" or
                report.get("independent_byte_validation") is not False or
                target.exists() or manifest.exists()):
            raise ValueError("Scalar preview unexpectedly wrote or claimed independent validation")
        return {
            **base, "action": "preview", "schema": SCHEMA,
            "status": "dry-run", "actor": req["actor"],
            "export": req["export"], "property": req["property"],
            "type": req["type"],
            "expected": req["expected"], "replacement": replacement,
            "output": str(target), "changed_byte_count": report["changed_byte_count"],
            "source_noop_T3SDK_parity_verified": True,
            "edited_package_written": False,
            "saved_binary_structure_verified": False,
        }
    if (report.get("status") != "written-unverified-gameplay" or
            report.get("independent_byte_validation") is not True):
        raise ValueError("Scalar isolated Save As failed independent original-byte verification")
    final = world.verify_saved_scalar_changes(target)
    if (final.get("verified_binary_structure") is not True or
            final.get("changed_fields") != 1 or
            final.get("changed_bytes") != report["changed_byte_count"] or
            final.get("unapproved_bytes") != 0 or
            final.get("runtime_game_verified") is not False or
            final.get("source_original_modified") is not False):
        raise ValueError("Saved scalar GMP diverged from original authenticated one-field patch")
    return {
        **base, "action": "apply", "schema": SCHEMA,
        "status": "isolated-native-scalar-verified-runtime-unverified",
        "actor": req["actor"], "export": req["export"],
        "property": req["property"], "type": req["type"],
        "expected": req["expected"], "replacement": replacement,
        "output": str(target), "changed_byte_count": report["changed_byte_count"],
        "source_noop_T3SDK_parity_verified": True,
        "saved_binary_structure_verified": True,
        "independent_saved_whole_GMP_byte_verification": True,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("list", "fields", "preview", "apply"))
    p.add_argument("--map", required=True)
    p.add_argument("--actors", required=True, help="Original source-verified private actors.json")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--actors-sha256", required=True)
    p.add_argument("--actor", help="Exact original StaticMeshActor name for field inventory")
    p.add_argument("--export", type=int, help="Original one-based export index for field inventory")
    p.add_argument("--request-json", help="Strict one-property original-bounded scalar replacement")
    p.add_argument("--output", help="Fresh isolated GMP, same basename as owner original")
    return p


def main(argv=None) -> int:
    try:
        args = parser().parse_args(argv)
        doc = perform(args)
        print(json.dumps(doc, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
        print(json.dumps({
            "bridge_schema": BRIDGE_SCHEMA,
            "status": "refused",
            "reason": str(exc)[:400],
            "source_original_modified": False,
            "runtime_game_verified": False,
            "native_gamesys_or_script_writer_enabled": False,
        }, sort_keys=True, allow_nan=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
