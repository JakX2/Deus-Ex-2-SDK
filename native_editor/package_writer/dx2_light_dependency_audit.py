#!/usr/bin/env python3
"""Original DX2 Light actor dependency inventory, strictly read-only.

New native Light spawning is intentionally disabled: actor Location does not
establish Region.iLeaf or ZoneNumberLow at a *new* position, and existing
Light state frames cannot safely be treated like StaticMeshActor frames.
No GMP or IBD bytes are ever emitted. Requires the user's own original map.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_package_roundtrip import _parse_both, _validate_input, inspect_noop, sha256
from dx2_actor_clone_probe import _pin
from upkg import prop_value, struct_fields, RF_HasStack

SCHEMA = "DX2Ed-original-light-dependency-audit-v1"


def _reference(pkg, obj, *, cls: str) -> dict:
    if not isinstance(obj, dict) or type(obj.get("ref")) is not int:
        raise ValueError("Expected original tagged object reference to " + cls)
    n = obj["ref"]
    if n <= 0 or n > len(pkg.exports):
        raise ValueError("Invalid positive map-local " + cls + " reference")
    target = pkg.exports[n - 1]
    if pkg.export_class(target) != cls or obj.get("name") != target.name:
        raise ValueError("Original tagged reference class/name does not match " + cls)
    return {"export": n, "name": target.name, "class": cls}


def inspect_light(pkg, exp, level_members: list[int]) -> dict:
    if pkg.export_class(exp) != "Light":
        raise ValueError("Not a native Light class")
    export = exp.index + 1
    if level_members.count(export) != 1:
        raise ValueError("Light must occur exactly once in original Level membership")
    if not exp.serial_size or not exp.flags & RF_HasStack:
        raise ValueError("Original Light has no native actor state")
    a = pkg.read_actor(exp)
    if a.parse_error or not isinstance(a.state, dict):
        raise ValueError("Original Light actor has undecoded native state")
    location = struct_fields(prop_value(a.properties, "Location"))
    if (set(location) != {"X", "Y", "Z"}
            or any(type(location[k]) not in (int, float) or not math.isfinite(location[k])
                   for k in ("X", "Y", "Z"))):
        raise ValueError("Original light is missing finite Location XYZ")
    region = struct_fields(prop_value(a.properties, "Region"))
    if not {"Zone", "iLeaf", "ZoneNumberLow"}.issubset(region):
        raise ValueError("Original Light Region lacks required BSP leaf and zone fields")
    if (type(region["iLeaf"]) is not int or type(region["ZoneNumberLow"]) is not int
            or region["iLeaf"] < 0 or not 0 <= region["ZoneNumberLow"] <= 255):
        raise ValueError("Invalid original Light BSP leaf/zone index")
    zone = _reference(pkg, region["Zone"], cls="LevelInfo")
    level = _reference(pkg, prop_value(a.properties, "Level"), cls="LevelInfo")
    physics = _reference(pkg, prop_value(a.properties, "PhysicsVolume"),
                         cls="DefaultPhysicsVolume")
    if zone["export"] != level["export"]:
        raise ValueError("Original Light Region.Zone differs from Level reference")
    state = a.state
    required = ("node", "state_node", "probe_mask", "latent_action", "offset")
    if any(type(state.get(x)) is not int for x in required):
        raise ValueError("Unknown original native frame layout")
    return {
        "actor": exp.name, "export": export, "class": "Light",
        "location_unreal": [location[k] for k in ("X", "Y", "Z")],
        "physics_volume": physics,
        "level": level, "region_zone": zone,
        "region_leaf": region["iLeaf"],
        "region_zone_number_low": region["ZoneNumberLow"],
        "b_dynamic_light": prop_value(a.properties, "bDynamicLight"),
        "b_sent_spawn_notification": prop_value(a.properties, "bSentSpawnNotification"),
        "state_frame": {key: state[key] for key in required},
        "tagged_object_references_checked": True,
        "native_links": len(a.links),
        "unknown_native_tail_bytes": a.tail.hex(),
        "region_for_new_position_verified": False,
        "state_frame_clone_verified": False,
        "light_clone_enabled": False,
        "blocker": "BSP point-to-leaf/zone reconstruction and native state-frame initialization required"
    }


def inspect_original_lights(source: Path, *, source_sha256: str,
                            actor_export: int | None = None) -> dict:
    source = _validate_input(Path(source))
    original = source.read_bytes()
    expected_hash = _pin(source_sha256)
    if sha256(original) != expected_hash:
        raise ValueError("Original source GMP SHA-256 mismatch")
    no_op, rewritten = inspect_noop(source)
    if rewritten != original or no_op["source_sha256"] != expected_hash:
        raise ValueError("Original GMP failed exact no-op writer proof")
    pkg, independent = _parse_both(source, original)
    refs = pkg.level_actors()
    if refs is None:
        raise ValueError("Original map has no Level actor list")
    if actor_export is not None and (type(actor_export) is not int
                                      or not 1 <= actor_export <= len(pkg.exports)):
        raise ValueError("Original Light export index is invalid")
    all_rows = []
    for exp in pkg.exports:
        if exp.index + 1 not in refs or pkg.export_class(exp) != "Light":
            continue
        all_rows.append(inspect_light(pkg, exp, refs))
    if not all_rows:
        raise ValueError("No original Light actors with valid Level membership")
    selected = all_rows
    if actor_export is not None:
        selected = [row for row in all_rows if row["export"] == actor_export]
        if len(selected) != 1:
            raise ValueError("Requested original export is not a placed Light")
    if sha256(source.read_bytes()) != expected_hash:
        raise ValueError("Source GMP changed during read-only Light audit")
    zones = sorted(set(row["region_zone_number_low"] for row in all_rows))
    leaves = sorted(set(row["region_leaf"] for row in all_rows))
    return {
        "schema": SCHEMA, "status": "read-only-source-verified",
        "source_map": source.name, "source_sha256": expected_hash,
        "source_export_count": len(independent.exports),
        "source_light_count": len(all_rows),
        "distinct_zone_numbers": zones,
        "distinct_bsp_leaf_count": len(leaves),
        "lights": selected,
        "source_modified": False, "game_installation_modified": False,
        "created_actor_count": 0, "native_light_spawn_enabled": False,
        "warnings": [
            "Original Light actors store Region.iLeaf and ZoneNumberLow, which must be recomputed for placement.",
            "Original Light state frames have not been proven safe for cloning.",
            "This is an original-package dependency inventory, not a BSP point/leaf resolver.",
            "Lights cannot be added to a retail GMP by this read-only tool."
        ]
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--actor-export", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = inspect_original_lights(args.source, source_sha256=args.source_sha256,
                                         actor_export=args.actor_export)
        if args.output is not None:
            output = args.output.expanduser().resolve()
            original = args.source.expanduser().resolve()
            if output.suffix.casefold() != ".json" or output == original:
                raise ValueError("Audit output must be a separate JSON file")
            if any(x.casefold() in ("content", "dx2", "maps") for x in output.parent.parts):
                raise ValueError("Audit output cannot target the retail game content folder")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf8") as handle:
                json.dump(result, handle, indent=2)
                handle.write("\n")
            print(json.dumps({"schema":SCHEMA,"status":result["status"],
                              "output":str(output),"lights":len(result["lights"]),
                              "source_light_count":result["source_light_count"],
                              "native_light_spawn_enabled":False}))
        else:
            print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(json.dumps({"schema":SCHEMA,"status":"refused",
                          "reason":str(exc)[:400],"output_written":False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
