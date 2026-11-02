#!/usr/bin/env python3
"""Build a strictly read-only Godot-sidecar for source-verifiable DX2 GameSys.

Only original data from a source-SHA-bound actors.json and independently
verified GMP + DX2 script declaration audit is displayed. Classes come
from the original DX2Gamesys.d2u when supplied. This output NEVER changes
the editor's existing class-template or actor draft schemas.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
for folder in (ROOT / "native_editor" / "package_writer",):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

SCHEMA = "DX2Ed-gamesys-inspector-sidecar-v1"
MAX_SOURCE_BYTES = 96_000_000
MAX_ACTORS = 30000
MAX_ARCHETYPES = 12000


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble_inspector(
    map_source: Path, actors_doc: dict, audit: dict,
    archetypes: dict | None = None,
) -> dict:
    """Join only verified source-backed records by GMP identity and export.

    Does not guess how D_* archetypes bind to placed actors. All metadata
    remains read-only; no draft/writer controls consume this sidecar.
    """
    map_source = Path(map_source)
    source_sha = _digest(map_source)
    if (audit.get("schema") != "DX2Ed-native-gamesys-block-audit-v1"
            or not audit.get("read_only")
            or audit.get("source_sha256") != source_sha
            or audit.get("source_map", "").casefold() != map_source.name.casefold()
            or audit.get("actor_verification_errors") != 0):
        raise ValueError("GameSys binary audit does not match original GMP source")
    meta = actors_doc.get("meta", {})
    if (not isinstance(meta, dict)
            or meta.get("source_sha256", meta.get("map_sha256")) != source_sha
            or str(meta.get("source_map", meta.get("map", ""))).casefold()
               != map_source.name.casefold()):
        raise ValueError("Actor cache does not match verified original GMP")
    actors = actors_doc.get("actors")
    if not isinstance(actors, list) or len(actors) > MAX_ACTORS:
        raise ValueError("Invalid or excessive actor cache")
    source_actors = {}
    for actor in actors:
        if not isinstance(actor, dict) or type(actor.get("export")) is not int:
            raise ValueError("Bad actor cache export")
        export = actor["export"]
        if export in source_actors or not isinstance(actor.get("name"), str):
            raise ValueError("Duplicate or invalid actor identity")
        source_actors[export] = actor
    by_export = defaultdict(list)
    for field in audit.get("fields", []):
        if not isinstance(field, dict) or type(field.get("export")) is not int:
            raise ValueError("Invalid original GameSys audit field")
        by_export[field["export"]].append(field)
    visible = {}
    for export, actor in source_actors.items():
        original_blocks = actor.get("game_properties", [])
        if not isinstance(original_blocks, list):
            raise ValueError("Invalid cached original GameSys property array")
        checked = by_export.get(export, [])
        if len(checked) != len(original_blocks):
            raise ValueError(f"Actor export {export}: original block count mismatch")
        rows = []
        for position, (field, original) in enumerate(zip(checked, original_blocks)):
            if (not isinstance(original, dict)
                    or field.get("actor") != actor["name"]
                    or field.get("source_block_index") != position
                    or field.get("property_id") != original.get("id")
                    or field.get("version") != original.get("version")):
                raise ValueError(f"Actor export {export}: original property identity mismatch")
            if not field.get("payload_sha256") or field.get("payload_offset", -1) < 0:
                raise ValueError("Missing original native payload evidence")
            rows.append({
                "id": field["property_id"],
                "name": field.get("source_declared_name") or original.get("name"),
                "declared_type": field.get("source_declared_type"),
                "declared_in": field.get("source_declared_in"),
                "encoding": field.get("encoding"),
                "source_value": original.get("value"),
                "version": field["version"],
                "encoded_id": field["encoded_id"],
                "payload_offset": field["payload_offset"],
                "payload_bytes": field["payload_bytes"],
                "source_payload_sha256": field["payload_sha256"],
                "source_block_index": position,
                "native_edit_supported": False,
            })
        visible[str(export)] = {
            "name": actor["name"],
            "class": actor.get("class"),
            "export": export,
            "properties": rows,
            "property_count": len(rows),
            "bound_to_original_actor": True,
        }
    original_classes = []
    if archetypes is not None:
        if (archetypes.get("schema") != "DX2Ed-gamesys-archetype-research-v1"
                or not archetypes.get("read_only")
                or archetypes.get("counts", {}).get("classes_unparsed", 1) != 0
                or not isinstance(archetypes.get("archetypes"), list)
                or len(archetypes["archetypes"]) > MAX_ARCHETYPES):
            raise ValueError("Original DX2Gamesys archetype audit is incomplete or invalid")
        for cls in archetypes["archetypes"]:
            if not isinstance(cls, dict):
                raise ValueError("Original DX2Gamesys archetype record is malformed")
            original_classes.append({
                "class": cls.get("class"),
                "display_name": cls.get("display_name"),
                "parent": cls.get("parent"),
                "source_ancestry": cls.get("source_ancestry", []),
                "inheritance_complete": bool(cls.get("inheritance_complete", False)),
                "recovered_dx2_layout": bool(cls.get("original_t3sdk_grouped_layout_recovered", False)),
                "local_defaults": cls.get("local_defaults", []),
                "local_property_count": cls.get("local_property_count", 0),
                "spawnable_verified": False,
                "native_edit_supported": False,
            })
    return {
        "schema": SCHEMA,
        "source_map": map_source.name,
        "source_sha256": source_sha,
        "original_gmp_audit_schema": audit["schema"],
        "original_game_properties": audit.get("verified_game_properties", 0),
        "matched_scene_actors": len(visible),
        "actors": visible,
        "archetypes": original_classes,
        "original_gamesys_sha256": archetypes.get("original_package_sha256") if archetypes else None,
        "read_only": True,
        "native_game_editing_enabled": False,
        "native_archetype_spawning_enabled": False,
        "actor_to_archetype_binding_verified": False,
        "warnings": [
            "Native offsets and values are original source evidence; NOT writable properties.",
            "Original D_* archetype hierarchy is separate from placed actors until native bindings are proven.",
            "Do not derive executable scripts or actor construction from a numeric or display-name match.",
        ],
    }


def build_inspector_sidecar(map_source: Path, actor_cache: Path, system_source: Path, output: Path) -> dict:
    map_source = Path(map_source).resolve(strict=True)
    actor_cache = Path(actor_cache).resolve(strict=True)
    system_source = Path(system_source).resolve(strict=True)
    output = Path(output).resolve()
    if (output.suffix.casefold() != ".json" or output in (map_source, actor_cache, system_source)
            or (system_source.is_dir() and system_source in output.parents)):
        raise ValueError("Output must be new JSON separate from original game sources")
    if output.exists():
        raise FileExistsError("Refusing to overwrite existing GameSys Inspector sidecar")
    if actor_cache.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Actor cache exceeds research limit")
    actors_doc = json.loads(actor_cache.read_text(encoding="utf8"))
    from dx2_gamesys_audit import audit_gamesys
    from dx2_gamesys_archetype_audit import analyze_archetypes
    audit = audit_gamesys(map_source, system_source=system_source,
                          actors_file=actor_cache, strict=True)
    if system_source.suffix.casefold() == ".json":
        archetypes = None  # A source catalog JSON does not contain original .d2u binaries.
    else:
        archetypes = analyze_archetypes(system_source)
    result = assemble_inspector(map_source, actors_doc, audit, archetypes)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=True, allow_nan=False)
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--map", required=True, type=Path)
    p.add_argument("--actors", required=True, type=Path)
    p.add_argument("--system", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        result = build_inspector_sidecar(args.map, args.actors, args.system, args.output)
        print(json.dumps({
            "status": "ok", "actors": result["matched_scene_actors"],
            "archetypes": len(result["archetypes"]),
            "read_only": True,
        }))
        return 0
    except (OSError, ValueError, IndexError, TypeError, KeyError) as error:
        print(json.dumps({"status": "error", "message": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
