#!/usr/bin/env python3
"""Source-pinned read-only DX2 TriggerScript/AI browser; no gameplay writes."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import zipfile

SCHEMA = "DX2Ed-original-gameplay-catalog-v1"
TSD_SIGNATURES = (b"1FFE2FST", b"0FFE2FST", b"0FFE1FST")
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_UNCOMPRESSED = 128 * 1024 * 1024
MAX_ENTRY = 2 * 1024 * 1024
MAX_ACTOR_JSON = 64 * 1024 * 1024
MAX_MAP = 32 * 1024 * 1024
MAX_SCRIPTS = 5000
UTF16_TOKEN = re.compile(rb"(?:[\x20-\x7e]\x00){3,}")


def hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def _tokens(raw: bytes) -> list[str]:
    return [m.group().decode("utf-16le") for m in UTF16_TOKEN.finditer(raw)]


def parse_tsd(name: str, raw: bytes) -> dict:
    if len(raw) < 24 or raw[:8] not in TSD_SIGNATURES:
        raise ValueError("Unrecognized DX2 TriggerScript definition header")
    texts = _tokens(raw)
    if not texts:
        raise ValueError("TriggerScript definition has no string data")
    script_id = PurePosixPath(name).stem
    if script_id.casefold() != texts[0].casefold():
        raise ValueError("TriggerScript name disagrees with source filename")
    conditions = sorted(set(s for s in texts if s.startswith("kTCT_")))[:50]
    actions = sorted(set(s for s in texts if s.startswith("kTAT_")))[:80]
    return {"id": script_id, "title": texts[1][:180] if len(texts) > 1 else "",
            "archive_member": name, "format": raw[:8].decode("ascii"),
            "conditions": conditions, "actions": actions, "size_bytes": len(raw)}


def audit_actor_cache(map_file: Path, actors_file: Path) -> tuple[dict, list[dict]]:
    if (map_file.suffix.lower() != ".gmp" or map_file.stat().st_size > MAX_MAP
            or actors_file.stat().st_size > MAX_ACTOR_JSON):
        raise ValueError("Source GMP or actor cache is invalid or too large")
    document = json.loads(actors_file.read_text(encoding="utf8"))
    if not isinstance(document, dict) or not isinstance(document.get("actors"), list):
        raise ValueError("Invalid original actors.json")
    meta = document.get("meta", {})
    if not isinstance(meta, dict):
        raise ValueError("Actor metadata missing")
    digest = hash_path(map_file)
    if (meta.get("source_sha256", meta.get("map_sha256")) != digest
            or str(meta.get("source_map", meta.get("map", ""))).casefold() != map_file.name.casefold()):
        raise ValueError("Original actor cache does not match the selected GMP SHA/name")
    actors = document["actors"]
    if len(actors) > 30000:
        raise ValueError("Excessive map actor count")
    seen = set()
    candidates = []
    scripted = []
    for actor in actors:
        if not isinstance(actor, dict) or type(actor.get("export")) is not int:
            raise ValueError("Malformed original map actor")
        idx = actor["export"]
        if idx <= 0 or idx in seen:
            raise ValueError("Duplicated or invalid actor export number")
        seen.add(idx)
        props = actor.get("game_properties", [])
        if not isinstance(props, list):
            raise ValueError("Malformed original actor game properties")
        layers = [p["value"] for p in props if isinstance(p, dict)
                  and p.get("id") == 82 and isinstance(p.get("value"), str)]
        if "AI" in layers:
            candidates.append({"actor": actor.get("name"), "class": actor.get("class"),
                               "export": idx, "original_layer": "AI",
                               "position": actor.get("location"),
                               "spawnable_verified": False})
        serialized = actor.get("trigger_script_serialized")
        if serialized is not None:
            scripted.append({"actor": actor.get("name"), "class": actor.get("class"),
                             "export": idx, "raw_property": serialized,
                             "script_names_resolved": False})
    return {"sha256": digest, "map": map_file.name,
            "actors_count": len(actors)}, [candidates, scripted]


def build_catalog(map_file: Path, actors_file: Path, script_zip: Path) -> dict:
    map_file, actors_file, script_zip = (Path(x).expanduser().resolve(strict=True)
                                         for x in (map_file, actors_file, script_zip))
    source, (npc, scripted) = audit_actor_cache(map_file, actors_file)
    if script_zip.suffix.lower() != ".zip" or script_zip.stat().st_size > MAX_ARCHIVE:
        raise ValueError("TriggerScript ZIP is invalid or too large")
    definitions = []
    total = 0
    with zipfile.ZipFile(script_zip) as archive:
        members = archive.infolist()
        if len(members) > 6000:
            raise ValueError("Too many ZIP members")
        entries = [x for x in members if x.filename.startswith("Defs/")
                   and x.filename.casefold().endswith(".tsd")]
        if not 1 <= len(entries) <= MAX_SCRIPTS:
            raise ValueError("Missing original Defs/*.tsd files")
        names = set()
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (entry.is_dir() or len(path.parts) != 2
                    or any(part in (".", "..") for part in path.parts)
                    or entry.file_size < 24 or entry.file_size > MAX_ENTRY
                    or entry.flag_bits & 1):
                raise ValueError("Unsafe TriggerScript ZIP entry")
            total += entry.file_size
            if total > MAX_UNCOMPRESSED:
                raise ValueError("TriggerScript archive exceeds read-only limit")
            if entry.filename.casefold() in names:
                raise ValueError("Ambiguous case-folded TriggerScript names")
            names.add(entry.filename.casefold())
            definitions.append(parse_tsd(entry.filename, archive.read(entry)))
    definitions.sort(key=lambda x: x["id"].casefold())
    return {"schema": SCHEMA, "read_only": True,
            "map": source["map"], "map_sha256": source["sha256"],
            "source_actor_count": source["actors_count"],
            "script_archive_name": script_zip.name,
            "script_archive_sha256": hash_path(script_zip),
            "script_definitions": definitions, "ai_layer_candidates": npc,
            "actors_with_serialized_script_data": scripted,
            "counts": {"scripts": len(definitions), "ai_candidates": len(npc),
                       "raw_script_fields": len(scripted)},
            "bindings_verified": False, "spawn_enabled": False,
            "warnings": [
                "These are original TriggerScript definitions, not executable modifications.",
                "A raw TriggerScript array index is NOT a TS_ script ID without a verified mission logic index.",
                "Original AI layer membership is NOT proof that an actor is a spawnable NPC.",
                "NPC creation and TriggerScript assignment to GMP are disabled pending original binding validation."
            ]}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--map", type=Path, required=True)
    p.add_argument("--actors", type=Path, required=True)
    p.add_argument("--scripts", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        destination = a.output.expanduser().resolve()
        srcs = [x.expanduser().resolve(strict=True) for x in (a.map,a.actors,a.scripts)]
        if destination.suffix.casefold() != ".json" or destination in srcs:
            raise ValueError("Output must be a separate private JSON file")
        doc = build_catalog(*srcs)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(doc, ensure_ascii=True, indent=2), encoding="utf8")
        print(json.dumps({"status":"ok","schema":SCHEMA,"output":str(destination),
                          "counts":doc["counts"],"read_only":True}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status":"refused","error":str(exc)[:300]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
