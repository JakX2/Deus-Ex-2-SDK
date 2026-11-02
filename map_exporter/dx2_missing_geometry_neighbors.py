#!/usr/bin/env python3
"""Find potentially omitted mesh actors beside a selected DX2Ed source actor.

This reads *existing, private* DX2Ed actors.json and scene.report.json.
It does not read, modify or redistribute the original game's GMP/IBD files.

Example:
    python dx2_missing_geometry_neighbors.py path/to/actors.json \\
      path/to/scene.report.json --actor StaticMeshActor__119 --radius 5
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from dx2coverage import summarize_mesh_export_coverage

SCALE = 0.01905


def _export_id(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or int(value) != value:
        return None
    return int(value)


def _location(actor):
    values = actor.get("location")
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return None
    if any(isinstance(x, bool) or not isinstance(x, (int, float))
           or not math.isfinite(x) for x in values):
        return None
    return tuple(float(x) * SCALE for x in values)


def neighbors(actors_doc, report, target, radius_m=5.0):
    if not isinstance(actors_doc, dict) or not isinstance(actors_doc.get("actors"), list):
        raise ValueError("Expected DX2Ed actors.json with actors list")
    if not isinstance(report, dict):
        raise ValueError("Expected scene.report.json object")
    if not isinstance(radius_m, (int, float)) or not math.isfinite(radius_m) or radius_m <= 0:
        raise ValueError("Radius must be positive and finite")
    actors = [a for a in actors_doc["actors"] if isinstance(a, dict)]
    selected = [a for a in actors if a.get("name") == target
                or (_export_id(a.get("export")) == _export_id(target)
                    if _export_id(target) is not None else False)]
    if len(selected) != 1:
        raise ValueError("Target actor must have exactly one matching source record")
    central = selected[0]
    here = _location(central)
    if here is None:
        raise ValueError("Target actor has no usable source location")

    # Export records are the only confirmed GLB placement IDs in the report.
    # If they are not present, the result is explicitly 'unknown', not 'missing'.
    placement = report.get("placement_actor_details")
    rendered = [a for a in placement if isinstance(a, dict)] if isinstance(placement, list) else []
    missing = report.get("missing_mesh_actors")
    missing = [a for a in missing if isinstance(a, dict)] if isinstance(missing, list) else []
    coverage = report.get("mesh_export_coverage")
    empty = coverage.get("empty_render_sections", []) if isinstance(coverage, dict) else []
    empty = [a for a in empty if isinstance(a, dict)]
    computed = summarize_mesh_export_coverage(actors, rendered, missing, empty)

    rendered_ids = {_export_id(a.get("export")) for a in rendered}
    missing_ids = {_export_id(a.get("export")) for a in missing}
    empty_ids = {_export_id(a.get("export")) for a in empty}
    entries = []
    for actor in actors:
        if actor is central or actor.get("class") != "StaticMeshActor":
            continue
        where = _location(actor)
        if where is None:
            continue
        gap = math.dist(here, where)
        if gap > radius_m:
            continue
        export = _export_id(actor.get("export"))
        if export in missing_ids:
            status = "missing_ibd_resource"
        elif export in empty_ids:
            status = "empty_render_sections"
        elif export in rendered_ids:
            status = "rendered"
        elif not actor.get("mesh"):
            status = "unresolved_gmp_mesh_reference"
        else:
            status = "unverified_no_render_record"
        entries.append({"actor": actor.get("name"), "export": export,
                        "mesh": actor.get("mesh"), "source_origin_distance_m": round(gap, 4),
                        "status": status, "location_ue": actor.get("location")})
    entries.sort(key=lambda a: (a["source_origin_distance_m"], str(a["actor"])))
    return {
        "schema": "DX2Ed-neighbor-geometry-audit-v1",
        "target": central.get("name"), "target_export": _export_id(central.get("export")),
        "source_map": actors_doc.get("meta", {}).get("source_map"),
        "target_location_ue": central.get("location"),
        "radius_m": radius_m,
        "placement_records_available": isinstance(placement, list),
        "read_only": True, "game_verified": False,
        "coverage": computed, "neighbors": entries,
        "caveat": (
            "Actor origin distance is not surface distance: large/pivot-offset meshes "
            "may touch the target from farther away. Missing BSP sections are not "
            "identifiable from this actor-only neighborhood report. Source-only "
            "classification cannot prove how the retail engine renders a surface."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actors_json", type=Path)
    parser.add_argument("scene_report_json", type=Path)
    parser.add_argument("--actor", default="StaticMeshActor__119")
    parser.add_argument("--radius", type=float, default=5.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    sources = (args.actors_json.resolve(), args.scene_report_json.resolve())
    if args.output and args.output.resolve() in sources:
        parser.error("Refusing to overwrite source audit inputs")
    try:
        actors_doc = json.loads(args.actors_json.read_text(encoding="utf-8"))
        report = json.loads(args.scene_report_json.read_text(encoding="utf-8"))
        result = neighbors(actors_doc, report, args.actor, args.radius)
        serial = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serial, encoding="utf-8")
            print(json.dumps({"status":"ok", "path":str(args.output),
                              "neighbor_count":len(result["neighbors"])}))
        else:
            print(serial, end="")
        return 0
    except (ValueError, TypeError, OSError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
