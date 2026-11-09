#!/usr/bin/env python3
"""Build a read-only DX2 MatLib catalog with verified local texture thumbnails.

The source IBD/Maps ZIP is opened by the existing DX2 texture parser. Only
small PNG previews and metadata are written to a separate private cache.
Original bundles are never modified and no native material writer exists.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
MAP_EXPORTER = ROOT / "map_exporter"
if str(MAP_EXPORTER) not in sys.path:
    sys.path.insert(0, str(MAP_EXPORTER))

import dx2textures

SCHEMA = "DX2Ed-MatLib-catalog-v1"
MAX_BUNDLES = 64
MAX_MATERIALS = 50_000
MAX_REFERENCED_TEXTURES = 100_000
MAX_PREVIEWS = 2_048
MAX_PREVIEW_PIXELS = 2_097_152
MAX_PREVIEW_SIDE = 96
MAX_PREVIEW_BYTES = 2 * 1024 * 1024
MAX_CATALOG_BYTES = 64 * 1024 * 1024


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def _source_identity(source_files: list[dict]) -> str:
    payload = json.dumps(source_files, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_catalog_from_inventory(
    textures: dict,
    materials: dict,
    duplicates: dict,
    skipped_textures: list[dict],
    source_files: list[dict],
    preview_dir: Path,
    max_previews: int = MAX_PREVIEWS,
) -> dict:
    """Convert the existing parser inventory into a bounded private sidecar."""
    if len(materials) > MAX_MATERIALS:
        raise ValueError("MatLib catalog exceeds the material safety limit")
    if not 0 <= max_previews <= MAX_PREVIEWS:
        raise ValueError("Preview count is outside the supported bound")

    preview_dir = Path(preview_dir).resolve()
    preview_dir.mkdir(parents=True, exist_ok=True)
    identity = _source_identity(source_files)

    referenced_names: set[str] = set()
    normalized_materials: list[tuple[str, dict, list[str]]] = []
    for key, material in materials.items():
        if not isinstance(material, dict):
            raise ValueError("Invalid MatLib record")
        stages = material.get("stages")
        if not isinstance(stages, list) or len(stages) != 9:
            raise ValueError("MatLib record does not contain the observed nine stage slots")
        stage_names: list[str] = []
        for name in stages:
            if name is None:
                name = ""
            if not isinstance(name, str) or len(name) > 260:
                raise ValueError("Invalid MatLib stage reference")
            stage_names.append(name)
            if name:
                referenced_names.add(name.casefold())
        normalized_materials.append((str(key), material, stage_names))

    if len(referenced_names) > MAX_REFERENCED_TEXTURES:
        raise ValueError("MatLib stage references exceed the texture safety limit")

    texture_records: dict[str, dict] = {}
    preview_count = 0
    for key in sorted(referenced_names):
        texture = textures.get(key)
        if texture is None:
            continue
        usage_code = int(texture.usage)
        if not 0 <= usage_code <= 0xFFFFFFFF:
            raise ValueError("Invalid texture usage code")
        record = {
            "name": texture.name,
            "format": texture.fmt,
            "width": int(texture.width),
            "height": int(texture.height),
            "usage_code": usage_code,
            "usage": dx2textures.USAGE.get(usage_code, str(usage_code)),
            "detail": int(texture.detail),
            "source_bundle": texture.source,
            "preview_path": "",
            "preview_sha256": "",
            "preview_omitted_reason": "",
        }
        if preview_count >= max_previews:
            record["preview_omitted_reason"] = "preview_count_limit"
        elif int(texture.width) * int(texture.height) > MAX_PREVIEW_PIXELS:
            record["preview_omitted_reason"] = "preview_pixel_limit"
        else:
            try:
                png = dx2textures.thumbnail(texture, max_side=MAX_PREVIEW_SIDE)
                if len(png) > MAX_PREVIEW_BYTES:
                    record["preview_omitted_reason"] = "preview_byte_limit"
                else:
                    filename = hashlib.sha256(
                        (identity + "\0" + texture.source + "\0" + texture.name).encode("utf-8")
                    ).hexdigest() + ".png"
                    target = preview_dir / filename
                    _atomic_write(target, png)
                    record["preview_path"] = preview_dir.name + "/" + filename
                    record["preview_sha256"] = hashlib.sha256(png).hexdigest()
                    preview_count += 1
            except (ValueError, IndexError, struct.error) as exc:
                record["preview_omitted_reason"] = "preview_decode_failed:" + type(exc).__name__
        texture_records[key] = record

    material_records: list[dict] = []
    unresolved_stage_count = 0
    stage_reference_count = 0
    for _key, material, stage_names in normalized_materials:
        stage_records: list[dict] = []
        for index, name in enumerate(stage_names):
            stage: dict = {"index": index, "name": name, "resolved": False}
            if name:
                stage_reference_count += 1
                texture_record = texture_records.get(name.casefold())
                if texture_record is None:
                    unresolved_stage_count += 1
                else:
                    stage["resolved"] = True
                    stage["texture"] = texture_record
            stage_records.append(stage)
        material_records.append({
            "name": str(material.get("name", "")),
            "source_bundle": str(material.get("source_bundle", "")),
            "version": int(material.get("version", 0)),
            "flags": int(material.get("flags", 0)),
            "stage_mask": int(material.get("stage_mask", 0)),
            "category_id": int(material.get("category_id", 0)),
            "source": str(material.get("source", "")),
            "colors": material.get("colors", []),
            "params": material.get("params", []),
            "stages": stage_records,
        })
    material_records.sort(key=lambda item: item["name"].casefold())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "native_writer_enabled": False,
        "source_bytes_modified": False,
        "asset_payloads_included": False,
        "preview_files_included": True,
        "catalog_id": identity,
        "source_files": source_files,
        "source_bundles": sorted({
            str(item.get("source_bundle", "")) for item in material_records
            if item.get("source_bundle")
        } | {
            str(item.get("source_bundle", "")) for item in texture_records.values()
            if item.get("source_bundle")
        }),
        "material_count": len(material_records),
        "texture_count": len(texture_records),
        "preview_count": preview_count,
        "stage_reference_count": stage_reference_count,
        "unresolved_stage_count": unresolved_stage_count,
        "duplicate_names": duplicates,
        "skipped_textures": skipped_textures[:1000],
        "materials": material_records,
        "textures": [texture_records[key] for key in sorted(texture_records)],
    }


def catalog_from_paths(
    paths: list[Path],
    output: Path,
    max_previews: int = MAX_PREVIEWS,
) -> dict:
    if not 1 <= len(paths) <= MAX_BUNDLES:
        raise ValueError("Supply between one and 64 IBD or ZIP bundles")
    sources = [Path(value).expanduser().resolve() for value in paths]
    output = Path(output).expanduser().resolve()
    if output.suffix.casefold() != ".json" or output in sources:
        raise ValueError("Catalog output must be a separate JSON file")
    source_files: list[dict] = []
    bundles = []
    for source in sources:
        if not source.is_file() or source.suffix.casefold() not in (".ibd", ".zip"):
            raise ValueError("Expected an existing .ibd or .zip source: " + source.name)
        source_files.append({
            "path": str(source),
            "sha256": _sha256_file(source),
            "bytes": int(source.stat().st_size),
        })
        bundles.extend(dx2textures.load_bundles(source))
    if not bundles:
        raise ValueError("No IBD bundles were found")
    textures, materials, duplicates, skipped = dx2textures.inventory(bundles)
    identity = _source_identity(source_files)
    preview_dir = output.parent / (output.stem + "_previews_" + identity[:12])
    catalog = build_catalog_from_inventory(
        textures, materials, duplicates, skipped, source_files, preview_dir, max_previews
    )
    catalog["source_bundles"] = sorted({bundle.name for bundle in bundles})
    payload = (json.dumps(catalog, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    if len(payload) > MAX_CATALOG_BYTES:
        raise ValueError("MatLib catalog exceeds the 64 MiB safety limit")
    _atomic_write(output, payload)
    return catalog



def _audit_uint32(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("Invalid MatLib audit " + field)
    return value


def audit_stage_mask_correspondence(materials: list) -> dict:
    """Compare raw low-nine stage-mask bits with non-empty ordered slot positions.

    Equality is an exploratory structural correlation only. It is not a
    shader-stage decode and does not establish runtime material behavior.
    """
    if not isinstance(materials, list) or len(materials) > MAX_MATERIALS:
        raise ValueError("Invalid MatLib audit material collection")
    slot_names = [Counter() for _ in range(9)]
    slot_usage = [Counter() for _ in range(9)]
    slot_named_counts = [0] * 9
    slot_resolved_counts = [0] * 9
    category_counts = Counter()
    flags_counts = Counter()
    exact_count = 0
    exact_nonempty_count = 0
    mismatch_count = 0
    high_bits_count = 0
    no_named_count = 0
    nonzero_without_named_count = 0
    named_without_low9_count = 0
    mismatch_examples = []

    for material in materials:
        if not isinstance(material, dict):
            raise ValueError("Invalid MatLib audit material record")
        name = material.get("name", "")
        if not isinstance(name, str) or not name or len(name) > 260:
            raise ValueError("Invalid MatLib audit material name")
        raw_mask = _audit_uint32(material.get("stage_mask"), "stage_mask")
        category = _audit_uint32(material.get("category_id", 0), "category_id")
        flags = _audit_uint32(material.get("flags", 0), "flags")
        stages = material.get("stages")
        if not isinstance(stages, list) or len(stages) != 9:
            raise ValueError("MatLib audit requires exactly nine ordered stage slots")

        named_mask = 0
        for slot_index, stage in enumerate(stages):
            if not isinstance(stage, dict):
                raise ValueError("Invalid MatLib audit stage record")
            if isinstance(stage.get("index"), bool) or stage.get("index") != slot_index:
                raise ValueError("MatLib audit stage order is invalid")
            stage_name = stage.get("name", "")
            if not isinstance(stage_name, str) or len(stage_name) > 260:
                raise ValueError("Invalid MatLib audit stage name")
            resolved = stage.get("resolved", False)
            if not isinstance(resolved, bool):
                raise ValueError("Invalid MatLib audit resolution flag")
            if stage_name:
                named_mask |= 1 << slot_index
                slot_named_counts[slot_index] += 1
                slot_names[slot_index][stage_name] += 1
            if resolved:
                texture = stage.get("texture")
                if not isinstance(texture, dict) or not stage_name:
                    raise ValueError("Resolved MatLib audit stage lacks a named texture")
                slot_resolved_counts[slot_index] += 1
                if "usage_code" in texture:
                    usage_code = _audit_uint32(texture["usage_code"], "texture usage_code")
                    slot_usage[slot_index][usage_code] += 1

        low9_mask = raw_mask & 0x1FF
        xor_mask = low9_mask ^ named_mask
        category_counts[category] += 1
        flags_counts[flags] += 1
        if xor_mask == 0:
            exact_count += 1
            if named_mask:
                exact_nonempty_count += 1
        else:
            mismatch_count += 1
            if len(mismatch_examples) < 8:
                mismatch_examples.append({
                    "name": name,
                    "raw_stage_mask": raw_mask,
                    "named_slot_mask": named_mask,
                    "low9_mask": low9_mask,
                    "xor_mask": xor_mask,
                })
        if raw_mask & ~0x1FF:
            high_bits_count += 1
        if named_mask == 0:
            no_named_count += 1
            if raw_mask != 0:
                nonzero_without_named_count += 1
        elif low9_mask == 0:
            named_without_low9_count += 1

    per_slot = []
    for slot_index in range(9):
        per_slot.append({
            "slot_index": slot_index,
            "named_count": slot_named_counts[slot_index],
            "resolved_count": slot_resolved_counts[slot_index],
            "usage_code_counts": [
                {
                    "code": code,
                    "parser_label": dx2textures.USAGE.get(code, str(code)),
                    "count": count,
                }
                for code, count in sorted(slot_usage[slot_index].items())
            ],
            "common_names": [
                {"name": value, "count": count}
                for value, count in slot_names[slot_index].most_common(5)
            ],
        })

    return {
        "schema": "DX2Ed-MatLib-stage-mask-audit-v1",
        "read_only": True,
        "native_writer_enabled": False,
        "source_bytes_modified": False,
        "material_count": len(materials),
        "exact_low9_match_count": exact_count,
        "exact_nonempty_low9_match_count": exact_nonempty_count,
        "mismatch_count": mismatch_count,
        "high_bits_set_count": high_bits_count,
        "no_named_slots_count": no_named_count,
        "nonzero_mask_without_named_slots_count": nonzero_without_named_count,
        "named_slots_without_low9_mask_count": named_without_low9_count,
        "per_slot": per_slot,
        "top_category_ids": [
            {"value": value, "count": count}
            for value, count in category_counts.most_common(8)
        ],
        "top_flags": [
            {"value": value, "count": count}
            for value, count in flags_counts.most_common(8)
        ],
        "mismatch_examples": mismatch_examples,
    }


def audit_catalog_file(path: Path) -> dict:
    """Read a bounded private catalog and return aggregate diagnostics only."""
    path = Path(path)
    if path.stat().st_size > MAX_CATALOG_BYTES:
        raise ValueError("MatLib audit catalog exceeds the 64 MiB limit")
    data = path.read_bytes()
    if len(data) > MAX_CATALOG_BYTES:
        raise ValueError("MatLib audit catalog exceeds the 64 MiB limit")
    try:
        catalog = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid MatLib audit catalog JSON") from exc
    if (not isinstance(catalog, dict)
            or catalog.get("schema") != SCHEMA
            or catalog.get("read_only") is not True
            or catalog.get("native_writer_enabled") is not False
            or catalog.get("source_bytes_modified") is not False):
        raise ValueError("MatLib audit requires a read-only source catalog")
    materials = catalog.get("materials")
    if catalog.get("material_count") != (len(materials) if isinstance(materials, list) else -1):
        raise ValueError("MatLib audit catalog material count is inconsistent")
    return audit_stage_mask_correspondence(materials)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", action="append", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-previews", type=int, default=MAX_PREVIEWS)
    parser.add_argument("--audit-catalog", type=Path,
                        help="Read-only stage-mask/slot audit of a private MatLib catalog")
    options = parser.parse_args(argv)
    try:
        if options.audit_catalog is not None:
            if options.bundle or options.output is not None:
                parser.error("--audit-catalog cannot be combined with --bundle/--output")
            report = audit_catalog_file(options.audit_catalog)
            print(json.dumps({"status": "ok", **report}, sort_keys=True))
            return 0
        if not options.bundle or options.output is None:
            parser.error("catalog creation requires --bundle and --output")
        catalog = catalog_from_paths(options.bundle, options.output, options.max_previews)
        print(json.dumps({
            "status": "ok",
            "output": str(options.output.expanduser().resolve()),
            "materials": catalog["material_count"],
            "referenced_textures": catalog["texture_count"],
            "previews": catalog["preview_count"],
            "unresolved_stage_references": catalog["unresolved_stage_count"],
            "source_bytes_modified": False,
            "native_writer_enabled": False,
        }))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, IndexError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
