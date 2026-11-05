"""DX2SDK: source-only original GMP actor catalog builder.

Unlike DX2Ed's Godot scene importer, this creates a read-only actors.json
using only the owner's original GMP, optionally with their original System
package declarations. No mission IBD/GLB preview or Godot runtime required.

All data derives from the source native export and tagged/GameSys decoders.
Unrecognized records and failed binary Location audits are EXCLUDED from
writable-candidate counts; no values are invented to fill gaps.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct

from .api import DX2Map, MAX_GMP
from dx2inspect import Package
from dx2_actor_explorer import actor_records
from dx2_gameplay_catalog import audit_actor_cache, hash_path
from dx2_native_save_as import location_float_offsets

SCHEMA = "DX2SDK-original-GMP-actor-cache-v1"
MAX_ROWS = 30000
MAX_JSON = 64 * 1024 * 1024


def _private_output(world: DX2Map, output: str | Path) -> Path:
    path = Path(output).expanduser().resolve()
    if path.name.casefold() != "actors.json":
        raise ValueError("Original actor catalog must be a fresh actors.json in its own private folder")
    if (path.exists() or path == world.source or
            path.parent == world.source.parent or
            world.source.parent in path.parents):
        raise ValueError("Refusing existing output or original Maps-folder catalog output")
    # Original game can have multiple content roots, so refuse outputs
    # under ANY recognizable game Maps tree, not only this map's tree.
    parts = tuple(x.casefold() for x in path.parent.parts)
    if any(parts[i:i+3] == ("content", "dx2", "maps")
           for i in range(max(0, len(parts) - 2))):
        raise ValueError("Never write actor cache into a game Content/DX2/Maps directory")
    return path


def _verify_system_source(system: str | Path | None) -> Path | None:
    if system is None:
        return None
    path = Path(system).expanduser().resolve(strict=True)
    if path.is_dir():
        # Optional owner-original System directory. Code that parses the
        # script declarations is read-only. Never traverse arbitrary trees.
        if not any((path / name).is_file() for name in
                   ("Engine.d2u", "DX2Game.d2u", "DX2Gamesys.d2u")):
            raise ValueError("Optional System directory has no original known DX2 declaration packages")
    elif path.is_file():
        if path.suffix.casefold() != ".json" or not 0 < path.stat().st_size <= 8_000_000:
            raise ValueError("Provide an original System directory or bounded DX2 property catalog JSON")
    else:
        raise ValueError("System source must be a directory or JSON catalog")
    return path


def scan_original_actor_catalog(
    world: DX2Map, *,
    system: str | Path | None = None,
) -> dict:
    """Return a source-pinned owner-private actors.json document, no file writes.

    This calls the independent original UE95 readers and cross-checks
    every returned actor export/name/class/position against the actual native
    package. GameSys property values are observations, not runtime bindings.
    """
    world._check_original_unchanged()
    if world.source.stat().st_size > MAX_GMP:
        raise ValueError("Original GMP exceeds supported SDK scan size")
    system_path = _verify_system_source(system)
    original = Package(world.source)
    meta, rows = actor_records(world.source, system_path)
    if (not isinstance(rows, list) or len(rows) > MAX_ROWS
            or meta.get("map_sha256") != world.source_sha256
            or meta.get("package_version") != 95
            or meta.get("licensee_version") != original.licensee
            or meta.get("map", "").casefold() != world.source.name.casefold()):
        raise ValueError("Independent original actor source scan does not match GMP")
    native_rows, native_failures = original.scene_actors()
    native = {row["export"]: row for row in native_rows}
    if len(native) != len(native_rows):
        raise ValueError("Original native scene actors contain duplicate export references")
    if len(rows) != len(native_rows):
        raise ValueError("Independent actor scan omitted native positioned objects")
    used = set()
    names = set()
    writable = 0
    opaque = 0
    for row in rows:
        idx = row.get("export")
        name = row.get("name")
        if (type(idx) is not int or idx not in native or idx in used
                or not isinstance(name, str) or not name or name in names
                or idx > len(original.exports)
                or row.get("class") != native[idx]["class"]
                or name != native[idx]["name"]):
            raise ValueError("Independent actor scan has invalid original native export identity")
        used.add(idx)
        names.add(name)
        position = row.get("location")
        if (not isinstance(position, list) or len(position) != 3
                or any(type(x) not in (float, int) or not math.isfinite(x)
                       for x in position)):
            raise ValueError("Original actor scan has incomplete/unsafe native position")
        # Compare direct, decoded native coordinates. The reader returns
        # rounded native X/Y/Z for the scene-only view; an exact tagged
        # Location is preferred when available. All differences must stay
        # within the original view's round-off tolerance.
        for x, axis in zip(position, ("xyz")):
            if abs(float(x) - float(native[idx][axis])) > 0.01:
                raise ValueError("Original native actor location diverges between two readers")
        row["native_location_writer_candidate"] = False
        row["native_location_writer_reason"] = "outside_source_verified_StaticMeshActor_scope"
        if row["class"] == "StaticMeshActor" and row.get("mesh"):
            try:
                offsets = location_float_offsets(original, original.exports[idx - 1])
                if all(abs(struct.unpack_from("<f", original.data, offsets[axis])[0]
                           - float(position[k])) <= 0.005
                       for k, axis in enumerate("XYZ")):
                    row["native_location_writer_candidate"] = True
                    row["native_location_writer_reason"] = "original_tagged_Location_fields_verified"
                    writable += 1
                else:
                    row["native_location_writer_reason"] = "original_Location_differs_from_decoder"
            except (ValueError, IndexError, struct.error):
                row["native_location_writer_reason"] = "ambiguous_native_Location_property"
        elif row["class"] == "StaticMeshActor":
            row["native_location_writer_reason"] = "source_mesh_reference_unresolved"
            opaque += 1
        if "game_properties" not in row or "trigger_script_serialized" not in row:
            raise ValueError("Original actor cache omitted original GameSys observations")
        if row.get("script_ids") or row.get("scripts"):
            # This source-only builder does not accept speculative linked
            # mission logic indexes: script assignment is not known.
            raise ValueError("Source-only actor cache must not claim runtime script mappings")
    if used != set(native):
        raise ValueError("Original actor scan did not cover all positioned native exports")
    if hash_path(world.source) != world.source_sha256:
        raise ValueError("Original GMP changed during source actor scan")
    cache_meta = dict(meta)
    cache_meta.update({
        "schema": SCHEMA,
        "source_sha256": world.source_sha256,
        "source_map": world.source.name,
        "source_only_catalog": True,
        "original_asset_files_modified": False,
        "runtime_actor_script_links_verified": False,
        "native_actor_spawn_supported": False,
        "native_location_writer_candidates": writable,
        "unresolved_source_static_meshes": opaque,
        "actor_source_decode_failures": native_failures,
        "optional_owner_system_catalog": system_path is not None,
        "warnings": [
            "The actor cache is a read-only source-derived catalog, not an edited map.",
            "GameSys TriggerScripts arrays are original serialized evidence, not confirmed runtime script bindings.",
            "Writable-candidate means original Location float layout is source-verified, not runtime-gameplay verified.",
            "Unresolved source mesh references are not automatically assigned a mesh.",
        ],
    })
    doc = {"meta": cache_meta, "actors": rows}
    # Existing SDK writer and script browser must independently accept the
    # newly generated cache without relaxing any SHA/actor constraints.
    encoded = json.dumps(doc, ensure_ascii=True, allow_nan=False).encode("utf8")
    if len(encoded) > MAX_JSON:
        raise ValueError("Generated actor catalog exceeds safe JSON size")
    return doc


def write_original_actor_catalog(
    world: DX2Map, output: str | Path, *,
    system: str | Path | None = None,
) -> dict:
    """Write a fresh actors.json outside any game Maps folder, never overwrite."""
    target = _private_output(world, output)
    doc = scan_original_actor_catalog(world, system=system)
    # Revalidate at final write boundary, then atomically create.
    world._check_original_unchanged()
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(doc, indent=2, ensure_ascii=True, allow_nan=False)
           + "\n").encode("utf8")
    if len(raw) > MAX_JSON:
        raise ValueError("Generated catalog exceeds safe JSON size")
    with target.open("xb") as f:
        f.write(raw)
    try:
        audit_actor_cache(world.source, target)
        # Verify it is immediately usable as an SDK map-scoped cache.
        DX2Map.open(world.source, target)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {
        "schema": SCHEMA,
        "status": "private_original_actor_cache_written",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "catalog_sha256": hashlib.sha256(raw).hexdigest(),
        "actor_count": len(doc["actors"]),
        "writer_candidate_count": doc["meta"]["native_location_writer_candidates"],
        "unresolved_static_mesh_count": doc["meta"]["unresolved_source_static_meshes"],
        "original_source_modified": False,
        "gameplay_runtime_verified": False,
        "script_runtime_binding_verified": False,
    }
