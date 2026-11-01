#!/usr/bin/env python3
"""Generate a private, textured GLB preview of ONE cataloged DX2 static mesh.

Only original IBD resource data supplied by the user is read. The preview is
not a Gamesys actor, cannot be compiled back into DX2, and is never published.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3] / "map_exporter"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from dx2bundles import parse_mesh
from dx2level import Builder, load_resource_index

SCHEMA = "DX2Ed-asset-catalog-v1"
MAX_BUNDLES = 64

def preview_path(catalog_path: Path, asset_name: str) -> Path:
    digest = hashlib.sha256(asset_name.encode("utf-8")).hexdigest()[:20]
    return catalog_path.parent / "asset_previews" / f"mesh_{digest}.glb"

def load_selected_asset(catalog: dict, name: str) -> dict:
    if catalog.get("schema") != SCHEMA or catalog.get("asset_payloads_included") is not False:
        raise ValueError("Unknown or unsafe asset catalog schema")
    resources = [a for a in catalog.get("assets", []) if
                 isinstance(a, dict) and a.get("name") == name and a.get("kind") == "staticmesh"]
    if len(resources) != 1:
        raise ValueError("Expected one staticmesh matching catalog name")
    return resources[0]

def source_bundle_paths(catalog_path: Path, catalog: dict) -> list[Path]:
    values = catalog.get("source_paths", [])
    if not isinstance(values, list) or not 0 < len(values) <= MAX_BUNDLES:
        raise ValueError("Catalog is missing source paths; reimport the GMP using latest DX2Ed")
    bundles = [Path(value).expanduser().resolve() for value in values]
    if any(not p.is_file() or p.suffix.casefold() not in (".ibd", ".zip") for p in bundles):
        raise ValueError("Missing or unsupported source bundle for preview")
    if any(p == catalog_path.resolve() for p in bundles):
        raise ValueError("Catalog cannot also be a bundle")
    return bundles

def export_asset_preview(catalog_file: Path, name: str) -> dict:
    catalog_file = catalog_file.expanduser().resolve()
    catalog = json.loads(catalog_file.read_text(encoding="utf8"))
    record = load_selected_asset(catalog, name)
    bundles = source_bundle_paths(catalog_file, catalog)
    output = preview_path(catalog_file, name)
    if output.is_file() and output.stat().st_size > 256:
        return {"status":"ok","cached":True,"glb":str(output),
                "mesh":name,"source":record["bundle"],"preview_only":True}
    _bundles, indexes, _collisions = load_resource_index(bundles)
    item = indexes[4].get(name.casefold())
    if item is None:
        raise ValueError("Selected mesh is absent from source IBD bundles")
    bundle, resource = item
    if (bundle.name != record.get("bundle") or
        int(resource.index) != int(record.get("resource_index", -1))):
        raise ValueError("Mesh identity differs from the original catalog; refresh the import")
    mesh = parse_mesh(bundle, resource)
    builder = Builder(indexes[4], indexes[10], indexes[8])
    mesh_id = builder.mesh_data(mesh, bundle.name)
    if mesh_id is None:
        raise ValueError("Mesh contains no exportable visible triangles")
    builder.node({"name":mesh.name,"mesh":mesh_id,
                  "extras":{"DX2PreviewOnly":True,"DX2AssetName":mesh.name,
                            "DX2IBDBundle":bundle.name}})
    output.parent.mkdir(parents=True, exist_ok=True)
    builder.save(output)
    return {"status":"ok","cached":False,"glb":str(output),
            "mesh":name,"source":bundle.name,"preview_only":True}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog",type=Path,required=True)
    p.add_argument("--name",required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(export_asset_preview(args.catalog,args.name)))
        return 0
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(json.dumps({"status":"error","message":str(exc)}),file=sys.stderr)
        return 1

if __name__=="__main__":
    sys.exit(main())
