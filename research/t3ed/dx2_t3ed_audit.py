#!/usr/bin/env python3
"""Read-only audit of Unreal package headers and editor configuration.

This does not launch T3Ed, alter installed games, or claim T3Ed compatibility.
"""
import argparse
import json
import struct
from pathlib import Path
from zipfile import ZipFile

MAGIC = 0x9E2A83C1

def package_summary(data):
    if len(data) < 8:
        return {"valid": False, "reason": "header too short"}
    magic, version, licensee = struct.unpack_from("<IHH", data)
    return {
        "valid": magic == MAGIC,
        "magic": f"0x{magic:08x}",
        "unreal_package_version": version,
        "ion_storm_licensee_version": licensee,
    }

def ini_summary(data):
    section = ""
    entries = []
    for line in data.decode("latin-1", "replace").splitlines():
        line = line.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith("[") and "]" in line:
            section = line[1:line.index("]")].strip()
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            if key.strip().lower() in ("editpackages", "editorengine", "gamemapext", "editormapext"):
                entries.append({"section": section, "key": key.strip(), "value": value.strip()})
    return entries

def get_suffix(zipfile, suffix):
    for item in zipfile.infolist():
        if item.filename.lower().endswith(suffix.lower()):
            return item.filename, zipfile.read(item)
    raise ValueError(f"Missing required file ending in {suffix!r}")

def audit(t3_zip, dx2_zip, dx2_map):
    with ZipFile(t3_zip) as t3, ZipFile(dx2_zip) as dx2:
        t3_name, t3ed = get_suffix(t3, "/t3ed.exe")
        t3_ini_name, t3_ini = get_suffix(t3, "/default.ini")
        dx2_ini_name, dx2_ini = get_suffix(dx2, "/default.ini")
        result = {
            "read_only": True,
            "editor": {
                "archive_member": t3_name,
                "size": len(t3ed),
                "ascii_reference_counts": {
                    s: t3ed.count(s.encode("ascii"))
                    for s in ("T3Game", "T3Gamesys", "T3GamePhysics", "DX2Game", "DX2Gamesys")
                },
            },
            "editor_ini": {
                "thief3": {"path": t3_ini_name, "fields": ini_summary(t3_ini)},
                "dx2": {"path": dx2_ini_name, "fields": ini_summary(dx2_ini)},
            },
            "packages": {
                "dx2_sample_map": package_summary(dx2_map.read_bytes()[:64]),
            },
        }
        for name, archive, suffix in (
            ("dx2_editor", dx2, "/editor.d2u"),
            ("dx2_engine", dx2, "/engine.d2u"),
            ("t3_reference_map", t3, "/auldale1.unr"),
        ):
            member, data = get_suffix(archive, suffix)
            result["packages"][name] = {"path": member, **package_summary(data)}
        return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t3-editor-zip", type=Path, required=True)
    parser.add_argument("--dx2-system-zip", type=Path, required=True)
    parser.add_argument("--dx2-map", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.t3_editor_zip, args.dx2_system_zip, args.dx2_map)
    report = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(report)

if __name__ == "__main__":
    main()
