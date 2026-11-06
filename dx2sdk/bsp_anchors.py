"""DX2SDK v0.10: source-authored native Light / BSP endpoint concordance.

An evidence atlas, NOT a BSP leaf resolver, light factory, or zone writer.
Original Light Region values are independent observations; hypothetical
compact BSP field 3/4 missing-branch terminals are not engine leaf IDs.

Use only the user's unchanged, SHA-pinned original UE95 GMP and the
source-validated World Model/node graph/zone-mask parsers from v0.9.
All outputs are read-only dictionaries or fresh private JSON.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .api import DX2Map
from .bsp_trace import _epsilon, _load_model, _point, _trace

SCHEMA = "DX2SDK-source-original-Light-BSP-terminal-atlas-v1"
DEFAULT_EPSILONS = (.001, .01, .1)
MAX_LIGHTS = 1000
MAX_PRIVATE_REPORT_BYTES = 12 * 1024 * 1024


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _epsilons(items: object) -> tuple[float, ...]:
    """Strict ordered sensitivity sweep, never quietly normalize bad input."""
    if (not isinstance(items, (list, tuple)) or
            not 2 <= len(items) <= 5):
        raise ValueError("BSP anchor atlas needs 2..5 strictly increasing epsilons")
    values = tuple(_epsilon(x) for x in items)
    if any(a >= b for a, b in zip(values, values[1:])):
        raise ValueError("BSP anchor tolerances must strictly increase without duplicates")
    return values


def _limit(number: object) -> int:
    if type(number) is not int or not 1 <= number <= MAX_LIGHTS:
        raise ValueError("BSP source Light anchor sample limit must be 1..1000")
    return number


def _terminal_key(row: dict) -> str:
    """Only a *hypothetical* missing-child slot, never a true native leaf."""
    node, branch = row["parent_node"], row["missing_branch"]
    if type(node) is not int or node < 0 or branch not in ("negative", "positive"):
        raise ValueError("Untrusted candidate BSP endpoint")
    return f"node:{node}:missing-{branch}"


def _sweep(model: dict, point: tuple[float, float, float],
           tolerances: tuple[float, ...]) -> dict:
    snapshots = []
    for epsilon in tolerances:
        raw = _trace(model, point, epsilon)
        terminals = raw["candidate_missing_branch_terminals"]
        keys = sorted({_terminal_key(x) for x in terminals})
        if len(keys) != len(terminals):
            raise ValueError("Duplicate candidate BSP terminals in one source trace")
        snapshots.append({
            "epsilon_unreal_units": epsilon,
            "terminal_keys": keys,
            "candidate_terminal_count": len(keys),
            "near_plane_forks": raw["near_plane_forks"],
        })
    singleton_keys = [entry["terminal_keys"][0]
                      for entry in snapshots if entry["candidate_terminal_count"] == 1]
    stable = len(singleton_keys) == len(snapshots) and len(set(singleton_keys)) == 1
    ambiguous = any(entry["candidate_terminal_count"] != 1 for entry in snapshots)
    classification = ("single-terminal-stable-across-epsilons" if stable
                      else "ambiguous-plane-fork" if ambiguous
                      else "epsilon-sensitive-terminal")
    return {
        "classification": classification,
        "single_terminal_key_if_stable": singleton_keys[0] if stable else None,
        "candidate_sweeps": snapshots,
        "no_engine_leaf_or_zone_assignment": True,
    }


def _groups(samples: list[dict]) -> list[dict]:
    """Pure grouping of source-authored Region evidence by candidate endpoint.

    Conflicting Region pairs from the SAME hypothetical terminal are
    counter-evidence against simplistic point->Region extrapolation.
    """
    if not isinstance(samples, list):
        raise ValueError("Original Light samples must be a list")
    groups: dict[str, list[dict]] = {}
    seen_exports: set[int] = set()
    for item in samples:
        if not isinstance(item, dict):
            raise ValueError("Invalid original Light sample row")
        export = item.get("source_actor_export")
        if type(export) is not int or export < 1 or export in seen_exports:
            raise ValueError("Duplicate or invalid original authored Light export")
        seen_exports.add(export)
        key = item.get("single_terminal_key_if_stable")
        if key is None:
            continue
        if (type(key) is not str or not key.startswith("node:") or
                ":missing-" not in key):
            raise ValueError("Invalid hypothesis endpoint key on source Light")
        if item.get("classification") != "single-terminal-stable-across-epsilons":
            raise ValueError("Unstable native Light cannot be counted as stable anchor")
        leaf, zone = item.get("original_Region_iLeaf"), item.get("original_Region_ZoneNumberLow")
        if (type(leaf) is not int or leaf < 0
                or type(zone) is not int or not 0 <= zone <= 255):
            raise ValueError("Native Light original Region value must be valid")
        groups.setdefault(key, []).append(item)
    out = []
    for key in sorted(groups):
        rows = sorted(groups[key], key=lambda x: x["source_actor_export"])
        distinct = sorted({(r["original_Region_iLeaf"], r["original_Region_ZoneNumberLow"])
                           for r in rows})
        distinct_leaf = len({p[0] for p in distinct})
        distinct_zone = len({p[1] for p in distinct})
        out.append({
            "hypothetical_terminal_key": key,
            "source_light_count": len(rows),
            "original_native_light_exports": [r["source_actor_export"] for r in rows],
            "observed_original_Region_pairs_on_existing_Lights": [
                {"iLeaf": leaf, "ZoneNumberLow": zone}
                for leaf, zone in distinct],
            "conflicting_original_iLeaf": distinct_leaf > 1,
            "conflicting_original_zone_number_low": distinct_zone > 1,
            "multiple_authored_Region_pairs_at_same_hypothetical_terminal":
                len(distinct) > 1,
            "native_leaf_or_zone_inference_supported": False,
        })
    return out


def _build(world: DX2Map, *, limit: int,
           epsilons: tuple[float, ...]) -> tuple[dict, dict]:
    limit = _limit(limit)
    tolerances = _epsilons(epsilons)
    world._check_original_unchanged()
    model = _load_model(world)
    original_lights = world.audit_original_lights()
    if (original_lights.get("source_sha256") != world.source_sha256
            or original_lights.get("native_light_spawn_enabled") is not False
            or len(original_lights["lights"]) != original_lights["source_light_count"]):
        raise ValueError("Native original Light audit cannot pin complete source evidence")
    raw_sources = original_lights["lights"][:limit]
    rows = []
    for light in raw_sources:
        source_point = _point(light["location_unreal"])
        sweep = _sweep(model, source_point, tolerances)
        rows.append({
            "source_actor_export": light["export"],
            "original_actor": light["actor"],
            "original_location_unreal_xyz": list(source_point),
            "original_Region_iLeaf": light["region_leaf"],
            "original_Region_ZoneNumberLow": light["region_zone_number_low"],
            **sweep,
            "existing_original_native_Light_only": True,
            "new_point_Region_assignment_supported": False,
        })
    groups = _groups(rows)
    stable_count = sum(r["classification"] == "single-terminal-stable-across-epsilons"
                       for r in rows)
    ambiguous_count = sum(r["classification"] == "ambiguous-plane-fork"
                          for r in rows)
    fragile_count = len(rows) - stable_count - ambiguous_count
    conflict_count = sum(r["multiple_authored_Region_pairs_at_same_hypothetical_terminal"]
                         for r in groups)
    world._check_original_unchanged()
    doc = {
        "schema": SCHEMA,
        "status": "read-only-source-Light-BSP-terminal-concordance",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "world_model_export": model["world_model_export"],
        "world_model_sha256": model["world_model_sha256"],
        "source_bsp_nodes": model["node_count"],
        "source_zone_records": model["zone_count"],
        "epsilon_sweep_unreal_units": list(tolerances),
        "sample_limit": limit,
        "source_original_native_light_count": original_lights["source_light_count"],
        "sampled_existing_native_lights": len(rows),
        "stable_single_terminal_source_lights": stable_count,
        "ambiguous_source_light_candidate_paths": ambiguous_count,
        "epsilon_sensitive_source_lights": fragile_count,
        "hypothetical_terminal_group_count": len(groups),
        "hypothetical_terminal_groups_with_original_Region_conflicts": conflict_count,
        "source_lights": rows,
        "source_terminal_groups": groups,
        "native_new_Light_actor_creation_enabled": False,
        "native_Region_iLeaf_solver_verified": False,
        "native_Region_ZoneNumberLow_solver_verified": False,
        "native_BSP_collision_writer_enabled": False,
        "source_original_modified": False,
        "gameplay_runtime_verified": False,
        "limitations": [
            "Source-authored Light Region values are observations, not inferred Model node fields.",
            "A stable hypothetical missing-branch terminal is NOT an engine leaf ID.",
            "Concordant samples are correlation only; conflicting samples are counter-evidence.",
            "The epsilon sensitivity sweep does not validate native BSP planes or renderer semantics.",
            "Missing Light samples and ambiguous paths cannot justify extrapolating new Region values.",
            "No original game files or native actors are modified or generated.",
        ],
    }
    return doc, model


def original_light_bsp_anchor_atlas(
    world: DX2Map, *, limit: int = 100,
    epsilons: tuple[float, ...] = DEFAULT_EPSILONS,
) -> dict:
    """Read-only source native Light-to-hypothetical BSP endpoint atlas."""
    report, _ = _build(world, limit=limit, epsilons=epsilons)
    return report


def compare_point_with_original_light_anchors(
    world: DX2Map, point_unreal_xyz: tuple[float, float, float],
    *, limit: int = 100, epsilons: tuple[float, ...] = DEFAULT_EPSILONS,
) -> dict:
    """Only source observational overlap, NEVER a point->Region lookup."""
    point = _point(point_unreal_xyz)
    atlas, model = _build(world, limit=limit, epsilons=epsilons)
    candidate = _sweep(model, point, tuple(atlas["epsilon_sweep_unreal_units"]))
    query_keys = {key for snapshot in candidate["candidate_sweeps"]
                  for key in snapshot["terminal_keys"]}
    groups = [g for g in atlas["source_terminal_groups"]
              if g["hypothetical_terminal_key"] in query_keys]
    exact_original_source_matches = [
        {"existing_light_export": row["source_actor_export"],
         "existing_original_Region_iLeaf": row["original_Region_iLeaf"],
         "existing_original_Region_ZoneNumberLow": row["original_Region_ZoneNumberLow"]}
        for row in atlas["source_lights"]
        if row["original_location_unreal_xyz"] == list(point)]
    world._check_original_unchanged()
    return {
        "schema": SCHEMA,
        "status": "read-only-point-vs-original-Light-terminal-observations",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "world_model_export": model["world_model_export"],
        "world_model_sha256": model["world_model_sha256"],
        "point_unreal_xyz": list(point),
        "epsilon_sweep_unreal_units": list(atlas["epsilon_sweep_unreal_units"]),
        "sample_limit": atlas["sample_limit"],
        "source_lights_sampled": atlas["sampled_existing_native_lights"],
        "candidate_point_sweep": candidate,
        "overlapping_existing_Light_terminal_groups": groups,
        "identical_coordinates_of_existing_original_Lights": exact_original_source_matches,
        "point_native_Region_iLeaf_assignment": None,
        "point_native_Region_ZoneNumberLow_assignment": None,
        "native_new_Light_actor_creation_enabled": False,
        "native_Region_iLeaf_solver_verified": False,
        "native_Region_ZoneNumberLow_solver_verified": False,
        "native_BSP_collision_writer_enabled": False,
        "source_original_modified": False,
        "gameplay_runtime_verified": False,
        "limitations": [
            "Observed original-Light Region pairs are never predictions for this point.",
            "Shared hypothetical BSP endpoint is not proof of shared engine Region.iLeaf or zone.",
            "A point matching an authored Light location identifies ONLY that existing Light.",
            "Conflicts, unstable endpoints and near-plane forks remain reported, never resolved by guess.",
            "No GMP, light, BSP leaf, zone or collision data was modified.",
        ],
    }


def save_light_bsp_anchor_report(
    world: DX2Map, report: dict, output: str | Path,
) -> dict:
    """Only fresh private JSON after exact original source report regeneration."""
    world._check_original_unchanged()
    target = Path(output).expanduser().resolve()
    parts = tuple(p.casefold() for p in target.parent.parts)
    if (target.suffix.casefold() != ".json" or target.exists()
            or target.parent == world.source.parent
            or world.source.parent in target.parents
            or any(parts[i:i + 3] == ("content", "dx2", "maps")
                   for i in range(max(0, len(parts) - 2)))):
        raise ValueError("Source Light BSP atlas requires fresh JSON outside game Maps")
    if (not isinstance(report, dict) or report.get("schema") != SCHEMA
            or report.get("source_sha256") != world.source_sha256):
        raise ValueError("Source Light BSP atlas report identity mismatch")
    if report.get("status") == "read-only-source-Light-BSP-terminal-concordance":
        rerun = original_light_bsp_anchor_atlas(
            world, limit=report.get("sample_limit"),
            epsilons=report.get("epsilon_sweep_unreal_units"))
    elif report.get("status") == "read-only-point-vs-original-Light-terminal-observations":
        rerun = compare_point_with_original_light_anchors(
            world, report.get("point_unreal_xyz"), limit=report.get("sample_limit"),
            epsilons=report.get("epsilon_sweep_unreal_units"))
    else:
        raise ValueError("Unsupported native Light BSP atlas report kind")
    if rerun != report:
        raise ValueError("Source-Light BSP atlas was modified or forged after original read")
    raw = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) +
           "\n").encode("utf8")
    if not 0 < len(raw) <= MAX_PRIVATE_REPORT_BYTES:
        raise ValueError("Native Light BSP atlas JSON exceeds private report size limit")
    world._check_original_unchanged()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as file:
        file.write(raw)
    return {
        "schema": SCHEMA, "status": "private-source-replayed-BSP-atlas-JSON-written",
        "output": str(target), "output_sha256": _sha(raw),
        "native_new_Light_actor_creation_enabled": False,
        "native_Region_iLeaf_solver_verified": False,
        "source_original_modified": False,
    }
