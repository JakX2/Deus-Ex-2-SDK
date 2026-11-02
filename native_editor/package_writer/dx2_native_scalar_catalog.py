#!/usr/bin/env python3
"""Read-only inventory of EXISTING 32-bit tagged scalar actor properties.

This is a source-driven menu for future DX2Ed inspector features. It is NOT
a list of safe or gameplay-understood properties. No game files are written.
Only fields agreed by the independent DX2 offset reader and T3SDK's strict
actor layout are included. Duplicate, nested, array and GameSys fields are
not silently treated as regular scalar tags.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_scalar_property_probe import (  # noqa: E402
    _native_scalar_offset, _parse_both, _validate_input, PT_FLOAT, PT_INT,
)
from dx2inspect import HAS_STACK  # noqa: E402
from upkgwrite import parse_object  # noqa: E402

SCHEMA = "DX2Ed-existing-native-scalar-inventory-v1"


def inventory_scalar_properties(source: Path) -> dict:
    source = _validate_input(source)
    raw = source.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    t3, dx2 = _parse_both(source, raw)
    actors_scanned = 0
    skipped_actors = 0
    entries = []
    for index, (texp, dexp) in enumerate(zip(t3.exports, dx2.exports), start=1):
        if not (dexp["flags"] & HAS_STACK) or dexp["size"] <= 0:
            continue
        actors_scanned += 1
        data = t3.export_bytes(texp)
        try:
            layout = parse_object(data, texp.flags, lambda i: t3.names[i])
            if layout.encode() != data:
                raise ValueError("original actor layout is not byte-identical")
            frequencies = Counter(t.name for t in layout.props.tags)
            for tag in layout.props.tags:
                if tag.ptype not in (PT_FLOAT, PT_INT) or len(tag.value) != 4:
                    continue
                if tag.array_raw or frequencies[tag.name] != 1:
                    continue
                offset = _native_scalar_offset(dx2, dexp, tag.name, tag.ptype)
                if raw[offset:offset+4] != tag.value:
                    raise ValueError("T3SDK/DX2 reader disagree on tagged scalar payload")
                value = struct.unpack("<f" if tag.ptype == PT_FLOAT else "<i", tag.value)[0]
                entries.append({
                    "actor": dexp["name"], "class": dx2.class_name(dexp),
                    "export": index, "property": tag.name,
                    "kind": "float" if tag.ptype == PT_FLOAT else "int",
                    "value": value, "raw_hex": tag.value.hex(),
                    "offset": offset,
                    "verified_top_level_tag": True,
                    "runtime_semantics_verified": False,
                })
        except (ValueError, IndexError, EOFError, struct.error) as exc:
            # No partial values for an object whose binary layout we cannot
            # independently validate. Count failures; don't guess fields.
            skipped_actors += 1
    return {
        "schema": SCHEMA,
        "read_only": True,
        "source_map": source.name,
        "source_sha256": sha,
        "licensee_version": dx2.licensee,
        "actors_scanned": actors_scanned,
        "actors_unparsed": skipped_actors,
        "scalar_fields_found": len(entries),
        "property_counts": dict(sorted(Counter(e["property"] for e in entries).items())),
        "fields": entries,
        "runtime_semantics_verified": False,
        "native_property_write_enabled": False,
        "warnings": [
            "Only original existing top-level 32-bit int/float tags are inventoried.",
            "A readable scalar tag is not proof its gameplay behavior is understood.",
            "Nested structs, arrays, GameSys blocks, booleans, unknown fields and scripts remain out of scope.",
            "To test an individual field in memory, use dx2_scalar_property_probe.py with pinned source SHA.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, help="Optional research JSON (never a GMP)")
    args = parser.parse_args(argv)
    try:
        if args.output is not None:
            output = args.output.expanduser().resolve()
            if output.suffix.casefold() != ".json" or output == args.source.expanduser().resolve():
                raise ValueError("Research output must be a separate .json file")
            if output.exists():
                raise FileExistsError("Refusing to overwrite existing research JSON")
        report = inventory_scalar_properties(args.source)
        result = json.dumps(report, indent=2, allow_nan=False)
        if args.output is None:
            print(result)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as f:
                f.write(result + "\n")
            print(json.dumps({
                "status": "ok", "output": str(output),
                "scalar_fields_found": report["scalar_fields_found"],
                "source_sha256": report["source_sha256"],
            }))
        return 0
    except (OSError, ValueError, IndexError, EOFError, struct.error) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
