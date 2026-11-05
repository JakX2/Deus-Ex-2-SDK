#!/usr/bin/env python3
"""Bind an owner-original TriggerScript ZIP definition to a real IBD entry.

Source-only verification of *resource identity*, not the runtime binding of
an actor's GameSys TriggerScripts numeric indices or the compilation of an
editable .tsd. Reads the unchanged GMP, source-matched actors.json,
original TriggerScript.zip and one original IBD; writes a private JSON report
outside the retail game directories. Never modifies any game resource.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_TOOLS = ROOT / "tools" / "scripts"
if str(SCRIPT_TOOLS) not in sys.path:
    sys.path.insert(0, str(SCRIPT_TOOLS))

from dx2_script_bundle_probe import parse_tsd_resources
from dx2_gameplay_catalog import build_catalog
from dx2_actor_script_name_candidates import inspect_original_package

SCHEMA = "DX2Ed-original-IBD-TriggerScript-resource-evidence-v1"
MAX_IBD = 512 * 1024 * 1024
MAX_MATCHES = 6000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_evidence(map_file: Path, actors_file: Path, scripts_file: Path,
                   ibd_file: Path) -> dict:
    """Compare verified original resource payloads by exact script name.

    The standalone TSD has a 12-byte source header; the original IBD
    stores the payload following this header. Exact byte equality is
    independent of any assumptions about event execution or actor indices.
    """
    map_file, actors_file, scripts_file, ibd_file = (
        Path(p).expanduser().resolve(strict=True)
        for p in (map_file, actors_file, scripts_file, ibd_file))
    if (ibd_file.suffix.casefold() != ".ibd" or
            ibd_file.stat().st_size <= 0 or
            ibd_file.stat().st_size > MAX_IBD):
        raise ValueError("Original resource bundle must be a bounded .ibd")
    original = build_catalog(map_file, actors_file, scripts_file)
    original_ids = {row["id"].casefold(): row
                    for row in original["script_definitions"]}
    if len(original_ids) != len(original["script_definitions"]):
        raise ValueError("Ambiguous original TriggerScript filename case")
    original_blob = ibd_file.read_bytes()
    meta, resources = parse_tsd_resources(
        original_blob, bundle_name=ibd_file.name)
    if len(resources) > MAX_MATCHES:
        raise ValueError("Too many original TriggerScript resource entries")

    rows = []
    seen_zip = set()
    with zipfile.ZipFile(scripts_file) as archive:
        members = {item.filename.casefold(): item for item in archive.infolist()
                   if item.filename.startswith("Defs/") and
                   item.filename.casefold().endswith(".tsd")}
        for script_key, record in sorted(resources.items()):
            definition = original_ids.get(script_key)
            row = {
                "script_id": record["name"],
                "ibd_resource_index": record["index"],
                "ibd_payload_size": record["size"],
                "ibd_payload_sha256": sha256(original_blob[
                    record["offset"]:record["offset"] + record["size"]]),
                "standalone_source_name_matched": definition is not None,
                "standalone_tsd_payload_byte_equal": False,
                "status": "not_in_original_zip",
            }
            if definition is not None:
                key = definition["archive_member"].casefold()
                entry = members.get(key)
                if entry is None:
                    raise ValueError("Source archive member disappeared after validation")
                standalone = archive.read(entry)
                # TSD v0/v1 source header is exactly 12 bytes. Compare
                # the entire source payload, not an unverified float offset.
                source_payload = standalone[12:]
                embedded = original_blob[
                    record["offset"]:record["offset"] + record["size"]]
                equal = source_payload == embedded
                row["standalone_tsd_payload_byte_equal"] = equal
                row["status"] = "exact_payload" if equal else "different_payload"
                row["source_payload_size"] = len(source_payload)
                row["source_payload_sha256"] = sha256(source_payload)
                seen_zip.add(key)
            rows.append(row)
    status_counts = {
        "exact_payload": sum(r["status"] == "exact_payload" for r in rows),
        "different_payload": sum(r["status"] == "different_payload" for r in rows),
        "not_in_original_zip": sum(r["status"] == "not_in_original_zip" for r in rows),
        "source_definitions_not_in_ibd": len(original_ids) - len(seen_zip),
    }
    if status_counts["source_definitions_not_in_ibd"] < 0:
        raise ValueError("Duplicate source script identifiers in IBD")
    # Independent original GMP actor property decoding. A numeric array
    # slot that happens to match a package name is ONLY a candidate, not a
    # proven FName/script binding. Preserve exact source resource evidence
    # even if a particular actor native payload cannot be re-decoded.
    actor_name_slots = inspect_original_package(
        map_file, original["actors_with_serialized_script_data"],
        original["script_definitions"], rows)
    return {
        "schema": SCHEMA, "read_only": True,
        "source_map": original["map"],
        "source_map_sha256": original["map_sha256"],
        "script_archive_name": original["script_archive_name"],
        "script_archive_sha256": original["script_archive_sha256"],
        "ibd_name": ibd_file.name,
        "ibd_sha256": sha256(original_blob),
        "ibd_resource_count": meta["resource_count"],
        "counts": status_counts, "entries": rows,
        "original_actor_name_slot_probe": actor_name_slots,
        "native_actor_script_indices_resolved": False,
        "actor_to_script_binding_verified": False,
        "native_script_writer_enabled": False,
        "original_game_assets_modified": False,
        "gameplay_runtime_verified": False,
        "warnings": [
            "Exact payload bytes prove resource identity, NOT that a map actor runs a given script.",
            "Numeric GameSys TriggerScripts array elements remain unresolved original references.",
            "A name at the same numeric position in the original Unreal name table is not proof this raw array stores FName indices.",
            "This evidence report does not compile or modify DX2 scripts or IBD packages.",
        ],
    }


def export_report(map_file: Path, actors_file: Path, scripts_file: Path,
                  ibd_file: Path, output: Path) -> dict:
    sources = [Path(p).expanduser().resolve(strict=True)
               for p in (map_file, actors_file, scripts_file, ibd_file)]
    target = Path(output).expanduser().resolve()
    # Never write into the original game source directory, its descendants
    # OR its ancestor install/content directories. The actors.json cache is
    # private editor data, so it need not impose the same ancestor boundary.
    protected = tuple(p.parent for p in (sources[0], sources[2], sources[3]))
    if (target.suffix.casefold() != ".json" or target.exists()
            or any(target == src for src in sources)
            or any(folder == target.parent or folder in target.parents
                   or target.parent in folder.parents for folder in protected)):
        raise ValueError("New private JSON must be outside original source directories")
    doc = build_evidence(*sources)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf8") as stream:
        json.dump(doc, stream, indent=2, ensure_ascii=True, allow_nan=False)
    return doc


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--map", required=True, type=Path)
    p.add_argument("--actors", required=True, type=Path)
    p.add_argument("--scripts", required=True, type=Path)
    p.add_argument("--ibd", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    opts = p.parse_args(argv)
    try:
        report = export_report(opts.map, opts.actors, opts.scripts,
                               opts.ibd, opts.output)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        # Do not leak owner-local paths or original content in stdout.
        print(json.dumps({"status": "refused", "code": "source_or_resource_mismatch"}))
        return 2
    print(json.dumps({
        "status": "ok", "schema": SCHEMA,
        "read_only": True, "counts": report["counts"],
        "source_verified": True, "native_script_writer_enabled": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
