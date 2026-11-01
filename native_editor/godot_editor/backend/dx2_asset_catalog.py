#!/usr/bin/env python3
"""Read-only DX2 IBD asset catalog for the future T3Ed-style Asset Browser.

Produces names, types, sizes and sources only. No assets are extracted,
re-encoded, uploaded, or embedded. First bundle wins for duplicate type/name,
matching the map exporter's resource lookup policy.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[3] / "map_exporter"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from dx2bundles import load_bundles

SCHEMA = "DX2Ed-asset-catalog-v1"


def catalog_from_bundles(bundles) -> dict:
    seen: dict[tuple[int, str], dict] = {}
    collisions: list[dict] = []
    totals = Counter()
    for bundle in bundles:
        for resource in bundle.resources:
            key = (int(resource.typ), resource.name.casefold())
            totals[resource.kind] += 1
            if key in seen:
                collisions.append({
                    "name": resource.name, "kind": resource.kind,
                    "selected_source": seen[key]["bundle"],
                    "shadowed_source": bundle.name,
                })
                continue
            seen[key] = {
                "name": resource.name,
                "kind": resource.kind,
                "type_id": int(resource.typ),
                "bundle": bundle.name,
                "resource_index": int(resource.index),
                "bytes": int(resource.size),
            }
    assets = sorted(seen.values(), key=lambda rec: (rec["kind"], rec["name"].casefold(), rec["bundle"].casefold()))
    return {
        "schema": SCHEMA,
        "read_only": True,
        "asset_payloads_included": False,
        "assets": assets,
        "counts_by_kind": dict(sorted(Counter(a["kind"] for a in assets).items())),
        "source_entry_counts": dict(sorted(totals.items())),
        "name_collisions": collisions,
        "collision_count": len(collisions),
        "source_bundles": [b.name for b in bundles],
    }


def catalog_from_paths(paths: list[Path]) -> dict:
    if not paths:
        raise ValueError("At least one IBD bundle is required")
    bundles = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix.casefold() not in (".ibd", ".zip"):
            raise ValueError("Expected an IBD file or ZIP archive: " + str(path))
        bundles.extend(load_bundles(path))
    return catalog_from_bundles(bundles)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args(argv)
    output = options.output.expanduser().resolve()
    sources = [source.expanduser().resolve() for source in options.bundle]
    if output in sources or output.suffix.lower() != ".json":
        parser.error("Catalog output must be a JSON file separate from the source bundles")
    try:
        catalog = catalog_from_paths(sources)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf8")
        print(json.dumps({
            "status": "ok", "output": str(output),
            "assets": len(catalog["assets"]),
            "collisions": catalog["collision_count"],
        }))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
