#!/usr/bin/env python3
"""DX2 source-declared GameSys properties from ORIGINAL .d2u TextBuffers.

Adapt source parser, not T3's class table: reuse upstream MIT T3SDK's
t3props.parse_declarations against original DX2 System packages. Keep
multiple declarations by the same numeric ID as ambiguity evidence rather
than silently selecting a guessed class. No original .uc source is copied
into the result, and no DX2/T3 game files are modified.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for directory in (ROOT / "actor_explorer", ROOT / "map_exporter",
                  ROOT / "third_party" / "t3sdk_assets"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from dx2catalog import source_packages  # noqa: E402
from dx2inspect import Package  # noqa: E402
from t3props import parse_declarations  # noqa: E402

SCHEMA = "DX2Ed-gamesys-declarations-v1"
MAX_OUTPUT_BYTES = 128_000_000


def build_gamesys_declarations(system: Path) -> dict:
    system = Path(system)
    by_id = defaultdict(list)
    package_stats = {}
    scripts_read = 0
    parse_warnings = []
    for source, basename in source_packages(system):
        pkg = Package(source)
        count = 0
        parsed_scripts = 0
        for exp in pkg.exports:
            if pkg.class_name(exp) != "TextBuffer" or not exp["size"]:
                continue
            try:
                text = pkg.script_text(exp)
            except (ValueError, IndexError) as error:
                parse_warnings.append(f"{basename} TextBuffer export #{exp['index']}: {error}")
                continue
            if not text:
                continue
            scripts_read += 1
            parsed_scripts += 1
            match = re.search(r"\bclass\s+([A-Za-z_]\w*)\s+extends\s+([A-Za-z_]\w*)", text, re.I)
            cls = match.group(1) if match else (
                pkg.ref_name(exp["outer"]) if exp["outer"] else exp["name"]
            )
            declarations = parse_declarations(Path(basename).stem, cls, text)
            for entry in declarations:
                record = asdict(entry)
                record["script_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
                record["package_source"] = basename
                by_id[entry.id].append(record)
                count += 1
        package_stats[basename] = {
            "text_buffers_decoded": parsed_scripts,
            "property_declarations": count,
            "package_version": pkg.version,
            "licensee": pkg.licensee,
            "package_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    if not package_stats:
        raise ValueError("No recognized original DX2 .d2u packages found")
    props = {}
    conflicts = []
    for pid, declarations in sorted(by_id.items()):
        unique = {(rec["name"].casefold(), rec["type"].casefold()) for rec in declarations}
        if len(unique) > 1:
            conflicts.append({"id": pid, "declarations": declarations})
            continue
        first = declarations[0]
        props[str(pid)] = {
            "id": pid, "name": first["name"], "type": first["type"],
            "category": first["category"],
            "kind": first["kind"], "description": first["description"],
            "declared_in": first["owner"],
            "package": first["package_source"],
            "source_declaration_count": len(declarations),
            "additional_declarers": sorted({rec["owner"] for rec in declarations[1:]}),
            "source_verified": True,
            "runtime_value_verified": False,
        }
    return {
        "schema": SCHEMA,
        "read_only": True,
        "source": system.name,
        "text_buffers_read": scripts_read,
        "source_property_declarations": sum(map(len, by_id.values())),
        "unique_property_ids": len(by_id),
        "unambiguous_property_ids": len(props),
        "conflicting_property_ids": conflicts,
        "properties": props,
        "packages": package_stats,
        "warnings": parse_warnings + [
            "Property definitions come from the user's DX2 .d2u source TextBuffers.",
            "Declared type/category do not prove which actors inherit a property.",
            "Array element types are declarations, not verified serialized element boundaries.",
            "No original UnrealScript source text is copied to the JSON output.",
        ],
        "native_gamesys_write_enabled": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("system", type=Path, help="Original user-owned System folder or ZIP")
    p.add_argument("--output", type=Path, required=True, help="Fresh JSON filename")
    args = p.parse_args(argv)
    try:
        src = args.system.expanduser().resolve(strict=True)
        dest = args.output.expanduser().resolve()
        if dest.suffix.casefold() != ".json" or dest == src or (src.is_dir() and src in dest.parents):
            raise ValueError("Output must be separate new JSON outside original System folder")
        if dest.exists():
            raise FileExistsError("Refusing to replace existing GameSys declaration report")
        report = build_gamesys_declarations(src)
        data = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if len(data.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ValueError("Excessively large source declaration report")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("x", encoding="utf-8") as f:
            f.write(data)
        print(json.dumps({
            "status": "ok", "source_property_ids": report["unambiguous_property_ids"],
            "conflicting_ids": len(report["conflicting_property_ids"]),
            "output": str(dest),
        }))
        return 0
    except (OSError, ValueError, IndexError, UnicodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
