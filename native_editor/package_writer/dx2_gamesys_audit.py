#!/usr/bin/env python3
"""Verify DX2 GameSys block boundaries independently of T3SDK's actor reader.

This is a source-only, read-only native property audit. It pairs:
- DX2SDK's own tagged-property parser + independently bounded u32 block scan
- unmodified MIT T3SDK actor/GamesysBlock reader
- optional source-declared .d2u property names (dx2catalog)
- optional source-hash-pinned existing DX2Ed actors.json.

It records original byte offsets, full encoded IDs, low-word property IDs,
high-word type bits, version and source hashes. It does NOT enable edits,
interpret array element types, resolve scripted behavior or make a native
package writer available to the editor.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for directory in (HERE, ROOT / "map_exporter", ROOT / "actor_explorer",
                  ROOT / "native_editor" / "godot_editor" / "backend"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from dx2_package_roundtrip import _parse_both, _validate_input  # noqa: E402
from dx2_native_save_as import _tagged_entries  # noqa: E402
from dx2inspect import Cursor, HAS_STACK  # noqa: E402

SCHEMA = "DX2Ed-native-gamesys-block-audit-v1"
MAX_BLOCKS_PER_ACTOR = 20000
MAX_JSON_BYTES = 64_000_000


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_dx2_gamesys(pkg, actor: dict) -> tuple[list[dict], int]:
    """Independently locate native GameSys records; no T3SDK helpers used."""
    start, length = actor["offset"], actor["size"]
    if length <= 0 or not actor["flags"] & HAS_STACK:
        raise ValueError("Not a nonempty actor with native state frame")
    cursor = Cursor(pkg.data, start, start + length)
    node = cursor.ci()
    cursor.ci()
    cursor.u64()
    cursor.u32()
    if node:
        cursor.ci()
    for _ in _tagged_entries(pkg, cursor):
        pass
    records: list[dict] = []
    for _ in range(MAX_BLOCKS_PER_ACTOR):
        if cursor.stop - cursor.at < 4:
            raise ValueError("GameSys list lacks native zero terminator")
        header_at = cursor.at
        encoded_id = cursor.u32()
        if not encoded_id:
            return records, header_at
        if cursor.stop - cursor.at < 8:
            raise ValueError("Incomplete native GameSys record header")
        version = cursor.u32()
        size = cursor.u32()
        if size > cursor.stop - cursor.at:
            raise ValueError("GameSys payload extends beyond actor export")
        payload_at = cursor.at
        payload = cursor.get(size)
        records.append({
            "encoded_id": encoded_id,
            "property_id": encoded_id & 0xffff,
            "type_word": (encoded_id >> 16) & 0xffff,
            "encoding_code": (encoded_id >> 16) & 0x0fff,
            "runtime_flag": bool((encoded_id >> 16) & 0x4000),
            "version": version,
            "header_offset": header_at,
            "payload_offset": payload_at,
            "payload_bytes": size,
            "payload_sha256": _hash(payload),
        })
    raise ValueError("GameSys block count exceeds safety limit")


def _safe_preview(block) -> object:
    """Display basic original values, but never guess array/struct semantics."""
    kind = block.kind
    if kind in ("int", "float", "bitfield", "bool", "byte", "name", "string"):
        value = block.value
        if isinstance(value, (int, float, str)) and (
            not isinstance(value, float) or math.isfinite(value)
        ):
            return value
    if kind in ("object", "class") and (
        block.value is None or isinstance(block.value, dict)
    ):
        return block.value
    return None


def _read_declarations(system_source: Path | None) -> tuple[dict, dict | None]:
    if system_source is None:
        return {}, None
    from dx2catalog import build_catalog
    system_source = system_source.expanduser().resolve(strict=True)
    if system_source.suffix.casefold() == ".json":
        if system_source.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("Source declaration catalog is too large")
        catalog = json.loads(system_source.read_text(encoding="utf-8"))
    else:
        catalog = build_catalog(system_source)
    if catalog.get("schema") != "dx2-catalog-0.1":
        raise ValueError("Unsupported DX2 source declaration catalog")
    return catalog.get("properties", {}), {
        "schema": catalog["schema"],
        "source": system_source.name,
        "property_ids": len(catalog.get("properties", {})),
        "declaration_warnings": len(catalog.get("warnings", [])),
        "source_read_only": True,
    }


def _read_actor_cache(actors_file: Path | None, source: Path, raw: bytes) -> tuple[dict, dict | None]:
    if actors_file is None:
        return {}, None
    actors_file = actors_file.expanduser().resolve(strict=True)
    if actors_file.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("Cached actor data exceeds size limit")
    data = json.loads(actors_file.read_text(encoding="utf-8"))
    meta = data.get("meta")
    if not isinstance(meta, dict) or meta.get("source_sha256", meta.get("map_sha256")) != _hash(raw):
        raise ValueError("Cached actor map identity SHA-256 differs from original GMP")
    if str(meta.get("source_map", meta.get("map", ""))).casefold() != source.name.casefold():
        raise ValueError("Cached actor map filename differs from original GMP")
    actors = data.get("actors")
    if not isinstance(actors, list):
        raise ValueError("Invalid cached actor records")
    mapping = {}
    for actor in actors:
        if not isinstance(actor, dict):
            raise ValueError("Invalid cached actor")
        export = actor.get("export")
        if type(export) is not int or export in mapping:
            raise ValueError("Duplicate or invalid cached original actor export")
        mapping[export] = actor
    return mapping, {
        "source_file": actors_file.name, "cached_actors": len(mapping),
        "source_sha256_verified": True,
    }


def audit_gamesys(
    source: Path, *, system_source: Path | None = None,
    actors_file: Path | None = None, strict: bool = True
) -> dict:
    """Inspect all state-frame actors, preserving known/unknown source bytes."""
    source = _validate_input(source)
    raw = source.read_bytes()
    t3, dx2 = _parse_both(source, raw)
    declarations, source_catalog = _read_declarations(system_source)
    cached, cached_info = _read_actor_cache(actors_file, source, raw)
    findings = []
    issues = []
    categories = Counter()
    source_actors_checked = 0
    missing_cached_properties = 0
    declared_matches = 0
    for export_id, (texp, dxexp) in enumerate(zip(t3.exports, dx2.exports), start=1):
        if not dxexp["size"] or not dxexp["flags"] & HAS_STACK:
            continue
        source_actors_checked += 1
        try:
            records, terminator_at = scan_dx2_gamesys(dx2, dxexp)
            actor = t3.read_actor(texp)
            if actor.parse_error:
                raise ValueError(f"T3SDK actor parse failed: {actor.parse_error}")
            if len(records) != len(actor.gamesys):
                raise ValueError("DX2SDK and T3SDK GameSys record counts disagree")
            cached_actor = cached.get(export_id)
            if cached_actor is not None and cached_actor.get("name") != dxexp["name"]:
                raise ValueError("Cached actor export/name identity differs")
            observed = cached_actor.get("game_properties") if cached_actor else None
            if observed is not None and not isinstance(observed, list):
                raise ValueError("Cached source actor properties are malformed")
            if observed is not None and len(observed) != len(records):
                raise ValueError("Cached source GameSys block count differs")
            for index, (rec, block) in enumerate(zip(records, actor.gamesys)):
                payload_at = rec["payload_offset"]
                payload = raw[payload_at:payload_at + rec["payload_bytes"]]
                if (rec["encoded_id"] != block.id or rec["version"] != block.version
                        or payload != block.data):
                    raise ValueError(f"GameSys block #{index} differs between independent readers")
                kind = block.kind
                categories[kind] += 1
                decl = declarations.get(str(block.prop_id), {})
                if isinstance(decl, dict) and decl:
                    declared_matches += 1
                item = {
                    **rec, "actor": dxexp["name"],
                    "actor_class": dx2.class_name(dxexp),
                    "export": export_id, "source_block_index": index,
                    "encoding": kind,
                    "source_declared_name": decl.get("name") if isinstance(decl, dict) else None,
                    "source_declared_type": decl.get("type") if isinstance(decl, dict) else None,
                    "source_declared_in": decl.get("declared_in") if isinstance(decl, dict) else None,
                    "preview_value": _safe_preview(block),
                    "value_has_verified_gameplay_semantics": False,
                    "native_edit_supported": False,
                }
                if observed is not None:
                    cache_rec = observed[index]
                    if (not isinstance(cache_rec, dict) or cache_rec.get("id") != block.prop_id
                            or cache_rec.get("version") != block.version
                            or cache_rec.get("encoding") != kind):
                        raise ValueError(f"Cached GameSys property #{index} differs from original")
                    item["cached_actor_index_agrees"] = True
                findings.append(item)
            # Some original objects have no GameSys records, which is valid.
        except (ValueError, IndexError, EOFError, struct.error) as exc:
            issues.append({"actor": dxexp["name"], "export": export_id, "reason": str(exc)})
            if strict:
                raise ValueError(
                    f"Could not independently verify original actor export #{export_id} "
                    f"({dxexp['name']}): {exc}"
                ) from exc
    if _hash(source.read_bytes()) != _hash(raw):
        raise ValueError("Original GMP changed during read-only audit")
    return {
        "schema": SCHEMA,
        "read_only": True,
        "source_map": source.name, "source_sha256": _hash(raw),
        "package_version": dx2.version,
        "licensee_version": dx2.licensee,
        "state_frame_actors_checked": source_actors_checked,
        "actor_verification_errors": len(issues),
        "issues": issues,
        "verified_game_properties": len(findings),
        "property_type_counts": dict(sorted(categories.items())),
        "property_ids_seen": len({e["property_id"] for e in findings}),
        "property_ids_with_source_declarations": len(
            {e["property_id"] for e in findings if e["source_declared_name"]}),
        "blocks_with_source_declared_names": declared_matches,
        "system_declaration_catalog": source_catalog,
        "actor_cache": cached_info,
        "fields": findings,
        "native_gamesys_write_supported": False,
        "runtime_game_verified": False,
        "warnings": [
            "Block IDs, byte extents, names and raw types are independently verified.",
            "Source declaration names are not proof of actor inheritance or gameplay semantics.",
            "Preview values are source decoder interpretations; no nested/array editing is supported.",
            "Native writes and in-game compatibility remain unverified.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original user-owned DX2 v95 GMP")
    parser.add_argument("--system", type=Path, help="Original System folder or ZIP of .d2u packages, or a dx2-catalog JSON")
    parser.add_argument("--actors", type=Path, help="Optional original source-hash-bound actors.json")
    parser.add_argument("--output", type=Path, help="Separate new JSON diagnostic report")
    parser.add_argument("--allow-partial", action="store_true", help="Record incomplete actors rather than fail closed; diagnostic only")
    args = parser.parse_args(argv)
    try:
        output = args.output.expanduser().resolve() if args.output else None
        if output is not None:
            forbidden = {args.source.expanduser().resolve()}
            if args.system is not None:
                forbidden.add(args.system.expanduser().resolve())
            if args.actors is not None:
                forbidden.add(args.actors.expanduser().resolve())
            if output.suffix.casefold() != ".json" or output in forbidden:
                raise ValueError("Output must be separate new JSON, never an original source")
            if output.exists():
                raise FileExistsError("Refusing to overwrite existing research JSON")
        report = audit_gamesys(args.source, system_source=args.system,
                               actors_file=args.actors,
                               strict=not args.allow_partial)
        data = json.dumps(report, indent=2, allow_nan=False)
        if output is None:
            print(data)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as f:
                f.write(data + "\n")
            print(json.dumps({
                "status": "ok", "output": str(output),
                "game_properties": report["verified_game_properties"],
                "state_frame_actors": report["state_frame_actors_checked"],
                "source_sha256": report["source_sha256"],
            }))
        return 0
    except (OSError, ValueError, IndexError, EOFError, OverflowError, struct.error) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
