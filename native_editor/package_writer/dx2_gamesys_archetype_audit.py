#!/usr/bin/env python3
"""Read-only DX2Gamesys archetype/defaults inventory using upstream MIT T3SDK.

Supports original standalone System/DX2Gamesys.d2u or the user's own System
ZIP/folder. Reports original archetype display labels, parent class chain,
local default GameSys values and explicitly incomplete/failed class records.
It does NOT spawn actors, rebuild GameSys packages, infer playable defaults,
or silently treat missing parent classes as a verified inheritance chain.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for path in (HERE, ROOT / "third_party" / "t3sdk_assets"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from t3gamesys import Gamesys  # noqa: E402

SCHEMA = "DX2Ed-gamesys-archetype-research-v1"
MAX_GAMESYS_BYTES = 64_000_000


def _original_gamesys(system: Path) -> tuple[bytes, str]:
    system = Path(system).expanduser().resolve(strict=True)
    if system.is_dir():
        file = system / "DX2Gamesys.d2u"
        if not file.is_file():
            raise FileNotFoundError("Original DX2Gamesys.d2u not found in System folder")
        if file.stat().st_size > MAX_GAMESYS_BYTES:
            raise ValueError("Source GameSys package exceeds size limit")
        return file.read_bytes(), file.name
    if system.suffix.casefold() == ".d2u":
        if system.name.casefold() != "dx2gamesys.d2u":
            raise ValueError("Provide the original DX2Gamesys.d2u package")
        if system.stat().st_size > MAX_GAMESYS_BYTES:
            raise ValueError("Source GameSys package exceeds size limit")
        return system.read_bytes(), system.name
    if not zipfile.is_zipfile(system):
        raise ValueError("Expected the original System ZIP, directory or DX2Gamesys.d2u")
    with zipfile.ZipFile(system) as z:
        found = [x for x in z.infolist()
                 if not x.is_dir() and Path(x.filename.replace("\\", "/")).name.casefold() == "dx2gamesys.d2u"]
        if len(found) != 1:
            raise ValueError("System ZIP must contain exactly one DX2Gamesys.d2u")
        if found[0].file_size > MAX_GAMESYS_BYTES:
            raise ValueError("Nested original GameSys package exceeds size limit")
        return z.read(found[0]), found[0].filename


def ancestry_status(arch, mapping: dict) -> tuple[list[str], bool, str | None]:
    """Require a complete, successfully parsed D_* parent chain before resolve."""
    chain = []
    seen = set()
    current = arch
    while True:
        if current.name.casefold() in seen:
            return chain, False, "archetype inheritance cycle"
        seen.add(current.name.casefold())
        chain.append(current.name)
        if current.error:
            return chain, False, "archetype record has unparsed fields"
        parent = current.parent
        if not parent or not parent.upper().startswith("D_"):
            return chain, True, None
        if parent.upper() not in mapping:
            return chain, False, "D_* parent missing from source package"
        current = mapping[parent.upper()]


def analyze_archetypes(system: Path, *, declaration_catalog: Path | None = None) -> dict:
    original, member = _original_gamesys(system)
    catalog = {}
    if declaration_catalog is not None:
        file = declaration_catalog.expanduser().resolve(strict=True)
        if file.stat().st_size > 32_000_000:
            raise ValueError("Declaration catalog exceeds size limit")
        doc = json.loads(file.read_text(encoding="utf-8"))
        if doc.get("schema") not in ("DX2Ed-gamesys-declarations-v1", "dx2-catalog-0.1"):
            raise ValueError("Unsupported source declaration catalog")
        if doc.get("conflicting_property_ids"):
            raise ValueError("Conflicting GameSys source declarations")
        catalog = doc.get("properties", {})
    with tempfile.TemporaryDirectory(prefix="dx2archetype_") as temp:
        local = Path(temp) / "DX2Gamesys.d2u"
        local.write_bytes(original)
        reader = Gamesys(local)
    outputs = []
    counts = Counter()
    failures = []
    for name, arch in sorted(reader.archetypes.items()):
        chain, complete, reason = ancestry_status(arch, reader.archetypes)
        counts["classes_found"] += 1
        if arch.error:
            counts["classes_unparsed"] += 1
            failures.append({"class": name, "error": arch.error})
        else:
            counts["classes_locally_parsed"] += 1
        if complete:
            counts["complete_source_inheritance_chains"] += 1
        else:
            counts["incomplete_source_inheritance_chains"] += 1
        local_props = []
        if not arch.error:
            for pid, block in sorted(arch.blocks.items()):
                declared = catalog.get(str(pid), {})
                local_props.append({
                    "property_id": pid, "encoded_id": f"0x{block.id:08x}",
                    "version": block.version,
                    "encoding": block.kind, "payload_bytes": len(block.data),
                    "payload_sha256": hashlib.sha256(block.data).hexdigest(),
                    "source_declared_name": declared.get("name"),
                    "source_declared_type": declared.get("type"),
                    "native_edit_enabled": False,
                })
                counts["parsed_local_default_blocks"] += 1
        outputs.append({
            "class": arch.name, "display_name": arch.display if not arch.error else None,
            "parent": arch.parent, "local_property_count": len(local_props),
            "source_class_parsed": not bool(arch.error),
            "parse_error": arch.error,
            "source_ancestry": chain,
            "inheritance_complete": complete,
            "inheritance_issue": reason,
            "local_defaults": local_props,
            "spawnable_verified": False,
        })
    return {
        "schema": SCHEMA, "read_only": True,
        "original_source_member": member,
        "original_package_sha256": hashlib.sha256(original).hexdigest(),
        "counts": dict(sorted(counts.items())),
        "errors": failures, "archetypes": outputs,
        "source_declarations_supplied": bool(catalog),
        "native_archetype_creation_enabled": False,
        "native_gamesys_serialization_supported": False,
        "game_runtime_verified": False,
        "warnings": [
            "T3SDK's T3Gamesys class parser is reused against DX2 data; partial compatibility is diagnostic.",
            "An unparsed class or ancestor must not be used to infer complete inherited properties.",
            "Parsed source archetype/default blocks do not demonstrate runtime-safe actor spawning.",
            "No original game assets are modified or committed to the SDK.",
        ],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("system", type=Path)
    p.add_argument("--declarations", type=Path, help="Optional DX2 GameSys source declaration JSON")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        src = args.system.expanduser().resolve(strict=True)
        output = args.output.expanduser().resolve()
        if (output.suffix.casefold() != ".json" or output == src
                or (src.is_dir() and src in output.parents)
                or (args.declarations and output == args.declarations.expanduser().resolve())):
            raise ValueError("Report must be fresh JSON outside original input files")
        if output.exists():
            raise FileExistsError("Refusing to overwrite original or existing report")
        report = analyze_archetypes(src, declaration_catalog=args.declarations)
        data = json.dumps(report, indent=2, allow_nan=False)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as f:
            f.write(data + "\n")
        print(json.dumps({"status": "ok", "output": str(output),
                          "counts": report["counts"]}))
        return 0
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
