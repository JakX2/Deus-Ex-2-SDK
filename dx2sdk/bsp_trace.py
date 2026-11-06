"""Source-verified DX2 BSP *plane-side hypotheses*, never native leaf assignment.

Original DX2 World Model boundaries, eight-compact reference graph and zone
mask recurrence are validated by independent read-only research parsers.

Fields 3/4 strongly correlate with negative/positive plane child sides
but their Unreal/Flesh semantics are not engine-verified. Field 5 is a
coplanar-reference candidate, NOT a new spatial leaf. The output is a
diagnostic, not a working BSP point-to-leaf implementation. No GMP writing,
new Light spawning, zone assignment, collision or BSP compilation.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct

from .api import DX2Map
from dx2inspect import Cursor
from inspect_level_world_model import _parse_world_model
from inspect_world_bsp_node_boundaries import parse_world_model
from inspect_world_bsp_zone_relations import inspect_zone_relations

SCHEMA = "DX2SDK-source-BSP-plane-side-candidate-trace-v1"
MAX_TERMINALS = 64
MAX_PATH_DEPTH = 512
MAX_LIGHT_ROWS = 1000


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _point(values: object) -> tuple[float, float, float]:
    if (not isinstance(values, (list, tuple)) or len(values) != 3
            or any(type(x) not in (int, float) for x in values)):
        raise ValueError("BSP point must contain exactly three numeric coordinates")
    xyz = tuple(float(v) for v in values)
    if any(not math.isfinite(x) or abs(x) > 1_000_000 for x in xyz):
        raise ValueError("BSP point outside finite original source-unit range")
    return xyz


def _epsilon(value: object) -> float:
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not .00001 <= value <= 1.0):
        raise ValueError("BSP diagnostic plane epsilon must be 0.00001..1.0 source units")
    return float(value)


def _load_model(world: DX2Map) -> dict:
    world._check_original_unchanged()
    pkg = world._package
    direct = _parse_world_model(pkg)
    export = direct["world_model_export_ref"]
    if (type(export) is not int or not 1 <= export <= len(pkg.exports)
            or pkg.class_name(pkg.exports[export-1]) != "Model"):
        raise ValueError("Original Level does not reference exactly one valid World Model")
    payload = pkg.payload(pkg.exports[export-1])
    if _sha(payload) != direct["world_model_payload_sha256"]:
        raise ValueError("Direct Level/Model source payload SHA is inconsistent")
    frame = parse_world_model(payload, include_nodes=True)
    verified = inspect_zone_relations(
        payload, frame, include_zones=False, include_nodes=False)
    n = frame["candidate_node_count"]
    if (verified["nodes"] != n or verified["zones"] != frame["candidate_zone_count"]
            or verified["exact_zone_mask_subtree_recurrence"] != n
            or verified["verified_parent_child_zone_mask_subsets"] != n-1
            or verified["rooted_node_graph_validated"] is not True):
        raise ValueError("Original candidate BSP zone/link evidence did not validate")
    parsed = []
    for ordinal, row in enumerate(frame["node_records"]):
        start, length = row["start"], row["length"]
        if type(start) is not int or type(length) is not int:
            raise ValueError("Original BSP node record has malformed bounds")
        r = Cursor(payload, start+48, start+length-53)
        compact = [r.ci() for _ in range(8)]
        if r.at != start+length-53:
            raise ValueError("Candidate eight-compact node fields shifted")
        negative, positive, coplanar = compact[3:6]
        zone_a, zone_b, _vcount = struct.unpack_from("<HHB", payload, start+length-21)
        plane = struct.unpack_from("<4f", payload, start)
        parsed.append({
            "node": ordinal, "plane": plane,
            "negative": negative, "positive": positive, "coplanar": coplanar,
            "zone_a": zone_a, "zone_b": zone_b,
            "subtree_zone_mask": int.from_bytes(
                payload[start+16:start+48], "little"),
        })
    world._check_original_unchanged()
    return {
        "source_sha256": world.source_sha256,
        "world_model_sha256": _sha(payload),
        "world_model_export": export,
        "node_count": n, "zone_count": frame["candidate_zone_count"],
        "nodes": parsed,
        "graph_and_zone_relations_validated": True,
    }


def _trace(model: dict, xyz: tuple[float, float, float], epsilon: float) -> dict:
    nodes = model["nodes"]
    stack = [(0, ())]
    terminals = []
    encountered_coplanar = 0
    total_node_visits = 0
    maximum_depth = 0
    near_plane_decisions = 0
    while stack:
        index, history = stack.pop()
        if len(history) >= MAX_PATH_DEPTH:
            raise ValueError("BSP candidate plane trace exceeds safety depth")
        if not 0 <= index < len(nodes):
            raise ValueError("Candidate BSP plane link outside original node bounds")
        node = nodes[index]
        a, b, c, w = node["plane"]
        signed = a * xyz[0] + b * xyz[1] + c * xyz[2] - w
        if not math.isfinite(signed):
            raise ValueError("Candidate BSP plane evaluation became nonfinite")
        total_node_visits += 1
        if total_node_visits > len(nodes):
            raise ValueError("BSP candidate walk revisited or exceeded validated rooted graph")
        maximum_depth = max(maximum_depth, len(history)+1)
        encountered_coplanar += int(node["coplanar"] >= 0)
        side = "near_plane" if abs(signed) <= epsilon else (
            "negative" if signed < 0 else "positive")
        sides = ("negative", "positive") if side == "near_plane" else (side,)
        if side == "near_plane":
            near_plane_decisions += 1
        for direction in sides:
            child = node[direction]
            step = {
                "node": index, "side": direction,
                "signed_plane_distance_source_units": signed,
                "field": 3 if direction == "negative" else 4,
                "child": child if child >= 0 else None,
                "coplanar_reference_field5": (
                    node["coplanar"] if node["coplanar"] >= 0 else None),
            }
            route = history + (step,)
            if child >= 0:
                stack.append((child, route))
            else:
                terminals.append({
                    "parent_node": index, "missing_branch": direction,
                    "node_zone_a_u16": node["zone_a"],
                    "node_zone_b_u16": node["zone_b"],
                    "node_subtree_zone_mask_bits": [
                        z for z in range(model["zone_count"])
                        if node["subtree_zone_mask"] & (1 << z)],
                    "plane_path": list(route),
                    "source_region_leaf": None,
                    "source_region_zone_number_low": None,
                    "native_leaf_or_zone_assignment_verified": False,
                })
                if len(terminals) > MAX_TERMINALS:
                    raise ValueError("Ambiguous BSP plane trace exceeds 64 diagnostic endpoints")
    if not terminals:
        raise ValueError("Candidate BSP plane walk reached no missing branch")
    terminals.sort(key=lambda t: [
        (s["node"], s["field"]) for s in t["plane_path"]])
    return {
        "point_unreal_xyz": list(xyz),
        "epsilon_unreal_units": epsilon,
        "candidate_terminal_count": len(terminals),
        "candidate_missing_branch_terminals": terminals,
        "visited_nodes": total_node_visits,
        "max_path_depth": maximum_depth,
        "near_plane_forks": near_plane_decisions,
        "visited_nodes_with_field5_coplanar_reference": encountered_coplanar,
        "diagnostic_only": True,
        "point_to_leaf_verified": False,
        "point_to_zone_verified": False,
        "native_light_placement_enabled": False,
    }


def trace_bsp_point(
    world: DX2Map, point_unreal_xyz: tuple[float, float, float],
    *, epsilon: float = .01,
) -> dict:
    """Read-only original BSP source plane-side candidate paths at one point."""
    xyz, eps = _point(point_unreal_xyz), _epsilon(epsilon)
    model = _load_model(world)
    trace = _trace(model, xyz, eps)
    world._check_original_unchanged()
    return {
        "schema": SCHEMA,
        "status": "read-only-candidate-BSP-plane-paths",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "world_model_export": model["world_model_export"],
        "world_model_sha256": model["world_model_sha256"],
        "source_node_count": model["node_count"],
        "source_zone_record_count": model["zone_count"],
        "graph_and_zone_relations_validated":
            model["graph_and_zone_relations_validated"],
        **trace,
        "source_original_modified": False,
        "native_bsp_rebuild_supported": False,
        "runtime_game_verified": False,
        "limitations": [
            "Compact child columns 3/4 are correlated plane-side hypotheses, not named engine fields.",
            "A missing candidate child branch is NOT proven to be an Unreal/Flesh BSP leaf index.",
            "Compact field 5 coplanar references are noted, not treated as spatial child links.",
            "Node zone A/B and subtree masks cannot assign Region.ZoneNumberLow at arbitrary new points.",
            "No original GMP or runtime asset is written or modified.",
        ],
    }


def trace_original_light_regions(
    world: DX2Map, *, limit: int = 50, epsilon: float = .01,
) -> dict:
    """Compare candidate plane walks with proven ORIGINAL Light Region fields.

    This is a calibration dataset, not a derived point-to-leaf resolver:
    native Level/Region and Model node indexes may not share numbering.
    """
    if type(limit) is not int or not 0 <= limit <= MAX_LIGHT_ROWS:
        raise ValueError("Original Light BSP trace limit must be 0..1000")
    eps = _epsilon(epsilon)
    model = _load_model(world)
    audit = world.audit_original_lights()
    source_rows = audit["lights"]
    if len(source_rows) != audit["source_light_count"]:
        raise ValueError("Original native Light inventory is incomplete")
    samples = []
    count_zone_pair_matches = 0
    for row in source_rows[:limit]:
        xyz = _point(row["location_unreal"])
        trace = _trace(model, xyz, eps)
        original_zone = row["region_zone_number_low"]
        potential_match = any(original_zone in (
            item["node_zone_a_u16"], item["node_zone_b_u16"])
            for item in trace["candidate_missing_branch_terminals"])
        count_zone_pair_matches += int(potential_match)
        samples.append({
            "original_export": row["export"], "original_actor": row["actor"],
            "original_location_unreal_xyz": list(xyz),
            "original_Region_iLeaf": row["region_leaf"],
            "original_Region_ZoneNumberLow": original_zone,
            "candidate_terminal_count": trace["candidate_terminal_count"],
            "candidate_missing_branch_terminals": trace[
                "candidate_missing_branch_terminals"],
            "observed_source_zone_in_terminal_node_zone_pair": potential_match,
            "equivalence_with_engine_Region_proven": False,
            "native_light_relocation_or_spawn_enabled": False,
        })
    world._check_original_unchanged()
    return {
        "schema": SCHEMA,
        "status": "read-only-original-Light-vs-BSP-plane-correlation",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "world_model_export": model["world_model_export"],
        "world_model_sha256": model["world_model_sha256"],
        "source_node_count": model["node_count"],
        "source_zone_record_count": model["zone_count"],
        "original_lights_checked_by_native_reference_audit": audit["source_light_count"],
        "original_lights_sampled": len(samples),
        "source_zone_matches_terminal_node_fields": count_zone_pair_matches,
        "epsilon_unreal_units": eps,
        "samples": samples,
        "original_source_modified": False,
        "native_light_creation_enabled": False,
        "native_region_leaf_assignment_verified": False,
        "native_region_zone_assignment_verified": False,
        "gameplay_runtime_verified": False,
        "limitations": [
            "The correlation is an observation, not a source-verified engine Region resolver.",
            "Model node indexes, terminal missing branches, and Region.iLeaf may use different spaces.",
            "Original Light state-frame initialization and compiled collision remain blocked.",
            "No GMP modifications, generated Lights or package output.",
        ],
    }


def save_bsp_diagnostic_report(
    world: DX2Map, report: dict, output: str | Path,
) -> dict:
    """New private JSON only; never original game content or overwritten file."""
    world._check_original_unchanged()
    path = Path(output).expanduser().resolve()
    parts = tuple(p.casefold() for p in path.parent.parts)
    if (path.suffix.casefold() != ".json" or path.exists()
            or path == world.source or path.parent == world.source.parent
            or world.source.parent in path.parents
            or any(parts[i:i+3] == ("content", "dx2", "maps")
                   for i in range(max(0, len(parts)-2)))):
        raise ValueError("BSP report must be a fresh private JSON outside any retail Maps")
    if (not isinstance(report, dict)
            or report.get("schema") != SCHEMA
            or report.get("source_sha256") != world.source_sha256
            or report.get("native_bsp_rebuild_supported", False) is not False
            or report.get("native_light_creation_enabled", False) is not False
            or report.get("point_to_leaf_verified", False) is not False
            or report.get("native_region_leaf_assignment_verified", False) is not False):
        raise ValueError("BSP diagnostic report source or enabled native capability is invalid")
    # A caller may pass an arbitrary dictionary. A source SHA and disabled
    # flags alone cannot authenticate its node paths or original Light values.
    # Reconstruct from the unchanged native source and require full identity,
    # including every negative capability, original actor field and branch.
    if report.get("status") == "read-only-candidate-BSP-plane-paths":
        regenerated = trace_bsp_point(
            world, report.get("point_unreal_xyz"),
            epsilon=report.get("epsilon_unreal_units"))
    elif report.get("status") == "read-only-original-Light-vs-BSP-plane-correlation":
        regenerated = trace_original_light_regions(
            world, limit=report.get("original_lights_sampled"),
            epsilon=report.get("epsilon_unreal_units"))
    else:
        raise ValueError("Unknown BSP report kind, unable to replay source evidence")
    if report != regenerated:
        raise ValueError("BSP report differs from independent original-source replay")
    raw = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
           + "\n").encode("utf8")
    if len(raw) > 12 * 1024 * 1024:
        raise ValueError("BSP diagnostic exceeds private JSON size limit")
    world._check_original_unchanged()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(raw)
    return {"schema": SCHEMA, "status": "private-read-only-diagnostic-saved",
            "output": str(path), "report_sha256": _sha(raw),
            "original_source_modified": False,
            "native_light_creation_enabled": False}
