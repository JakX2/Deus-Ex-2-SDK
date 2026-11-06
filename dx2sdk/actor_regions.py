"""DX2SDK v0.11: source-authored native Actor Region and BSP concordance.

Extends the v0.10 original-Light evidence to other *original Level member*
actors with explicitly authored Location, Region and Level references.
The source-authored Region and LevelInfo refs are independently read from
T3SDK; their identities must agree with the separate DX2 package reader.
These are provenance records, NOT new native point-to-leaf/zone assignments.

Only read source-original UE95 GMP; optionally create an entirely private
JSON, replaying all evidence from the unchanged source first. No game map,
BSP, script, collision, light state or actor property writer.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from .api import DX2Map
from .bsp_trace import _load_model, _point
from .bsp_anchors import _epsilons, _sweep, _terminal_key, DEFAULT_EPSILONS
from dx2_package_roundtrip import inspect_noop
from dx2_light_dependency_audit import _reference, inspect_light
from upkg import Package as T3Package, prop_value, struct_fields

SCHEMA = "DX2SDK-source-original-all-Actor-Region-BSP-atlas-v1"
MAX_LEVEL_MEMBERS = 30000
MAX_SAMPLES = 1000
MAX_PRIVATE_JSON = 12 * 1024 * 1024


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_options(limit: object, actor_class: object,
                      epsilons: object) -> tuple[int, str | None, tuple[float,...]]:
    if type(limit) is not int or not 1 <= limit <= MAX_SAMPLES:
        raise ValueError("Original Region atlas limit must be 1..1000")
    if actor_class is not None and (type(actor_class) is not str
                                    or not actor_class or len(actor_class) > 128):
        raise ValueError("Class filter must be a nonempty exact original class string")
    return limit, actor_class, _epsilons(epsilons)


def _native_region_row(pkg: T3Package, export: int, members: list[int]) -> dict:
    """Original tagged property proof, without guessing inherited/default Region."""
    exp = pkg.exports[export-1]
    if members.count(export) != 1 or exp.index + 1 != export:
        raise ValueError("Native actor must have unique original Level membership")
    if not exp.serial_size:
        raise ValueError("No original native actor bytes")
    native = pkg.read_actor(exp)
    if native.parse_error:
        raise ValueError("Original actor tagged property parse failed")
    props = native.properties
    for name in ("Location", "Region", "Level"):
        if sum(p.name == name and p.array_index == 0 for p in props) != 1:
            raise ValueError("Missing or duplicate explicitly authored " + name + " tag")
    location = struct_fields(prop_value(props, "Location"))
    if set(location) != {"X", "Y", "Z"}:
        raise ValueError("Source Location is not an exact XYZ tagged struct")
    point = _point(tuple(location[k] for k in ("X", "Y", "Z")))
    region = struct_fields(prop_value(props, "Region"))
    if not {"iLeaf", "ZoneNumberLow", "Zone"}.issubset(region):
        raise ValueError("Explicit Region lacks iLeaf/ZoneNumberLow/Zone")
    leaf = region["iLeaf"]
    zone = region["ZoneNumberLow"]
    if (type(leaf) is not int or leaf < 0
            or type(zone) is not int or not 0 <= zone <= 255):
        raise ValueError("Source native Region leaf or zone is unassigned/unsupported")
    level = _reference(pkg, prop_value(props, "Level"), cls="LevelInfo")
    region_zone = _reference(pkg, region["Zone"], cls="LevelInfo")
    if level["export"] != region_zone["export"]:
        raise ValueError("Source native Region.Zone and LevelInfo links disagree")
    if pkg.export_class(exp) == "Light":
        # A native Light is only an anchor if the full v0.6 Light-specific
        # native frame and PhysicsVolume provenance also validates.
        audited = inspect_light(pkg, exp, members)
        if (audited["region_leaf"] != leaf or
                audited["region_zone_number_low"] != zone or
                audited["location_unreal"] != list(point)):
            raise ValueError("Independent native Light dependency audit disagrees")
    return {
        "source_actor_export": export,
        "original_actor": exp.name,
        "original_actor_class": pkg.export_class(exp),
        "original_location_unreal_xyz": list(point),
        "original_Region_iLeaf": leaf,
        "original_Region_ZoneNumberLow": zone,
        "original_LevelInfo_export": level["export"],
        "original_Region_Zone_LevelInfo_export": region_zone["export"],
        "explicit_authored_native_Region_and_Location": True,
        "original_authority": "T3SDK_Level_member_native_tagged_properties",
    }


def _original_actor_rows(
    world: DX2Map, *, actor_class: str | None,
) -> tuple[list[dict], dict]:
    world._check_original_unchanged()
    no_op, original = inspect_noop(world.source)
    if (original != world._package.data
            or no_op.get("byte_identical") is not True
            or no_op.get("source_sha256") != world.source_sha256):
        raise ValueError("Original GMP failed byte-identical independent no-op proof")
    pkg = T3Package(world.source)
    members = pkg.level_actors()
    if (members is None or len(members) > MAX_LEVEL_MEMBERS
            or len(members) != len(set(members))
            or any(type(i) is not int or not 1 <= i <= len(pkg.exports)
                   for i in members)):
        raise ValueError("Original Level actor membership is absent, malformed or excessive")
    if (len(pkg.exports) != len(world._package.exports)
            or len(pkg.names) != len(world._package.names)
            or len(pkg.imports) != len(world._package.imports)):
        raise ValueError("Independent source original package readers disagree on tables")
    valid = []
    reasons = Counter()
    selected_count = 0
    source_classes = Counter()
    for export in members:
        exp = pkg.exports[export-1]
        other = world._package.exports[export-1]
        cls = pkg.export_class(exp)
        if (other["name"] != exp.name or world._package.class_name(other) != cls
                or other["offset"] != exp.serial_offset
                or other["size"] != exp.serial_size):
            raise ValueError("Original actor name/class/source-bounds differ between readers")
        if actor_class is not None and actor_class != cls:
            continue
        selected_count += 1
        source_classes[cls] += 1
        try:
            row = _native_region_row(pkg, export, members)
        except (ValueError, IndexError, EOFError, KeyError, TypeError):
            reasons["missing_or_unusable_explicit_Region_or_source_links"] += 1
            continue
        valid.append(row)
    world._check_original_unchanged()
    if sum(reasons.values()) + len(valid) != selected_count:
        raise ValueError("Original authored Region coverage accounting mismatch")
    return valid, {
        "original_level_actor_members": len(members),
        "class_filtered_level_members": selected_count,
        "actor_classes_in_filtered_level_members": dict(sorted(source_classes.items())),
        "eligible_explicit_original_region_actors": len(valid),
        "excluded_authored_region_actors": dict(reasons),
        "source_light_specific_provenance_enforced": True,
        "original_independent_noop_bytes_equal": True,
    }


def _group_regions(rows: list[dict]) -> list[dict]:
    """Hypothetical BSP slot grouping, preserving authored cross-class conflicts."""
    slots: dict[str, list[dict]] = {}
    exports = set()
    for item in rows:
        e = item["source_actor_export"]
        if type(e) is not int or e < 1 or e in exports:
            raise ValueError("Duplicate source actor in Region group")
        exports.add(e)
        endpoint = item["single_terminal_key_if_stable"]
        if endpoint is None:
            continue
        if item["classification"] != "single-terminal-stable-across-epsilons":
            raise ValueError("Ambiguous actor cannot enter stable hypothetical BSP slot")
        slots.setdefault(endpoint, []).append(item)
    groups = []
    for key, bucket in sorted(slots.items()):
        ordered = sorted(bucket, key=lambda x: x["source_actor_export"])
        pairs = sorted({(x["original_Region_iLeaf"], x["original_Region_ZoneNumberLow"])
                        for x in ordered})
        classes = dict(sorted(Counter(x["original_actor_class"] for x in ordered).items()))
        groups.append({
            "hypothetical_terminal_key": key,
            "original_actor_count": len(ordered),
            "original_actor_exports": [x["source_actor_export"] for x in ordered],
            "authored_classes": classes,
            "original_region_pairs": [
                {"iLeaf": leaf, "ZoneNumberLow": zone} for leaf,zone in pairs],
            "original_iLeaf_conflict": len({a for a,b in pairs}) > 1,
            "original_zone_number_low_conflict": len({b for a,b in pairs}) > 1,
            "any_original_Region_conflict": len(pairs) > 1,
            "multi_class_observations": len(classes) > 1,
            "native_point_to_Region_equivalence_verified": False,
        })
    return groups


def _build(
    world: DX2Map, *, limit: int = 250,
    actor_class: str | None = None,
    epsilons: tuple[float, ...] = DEFAULT_EPSILONS,
) -> tuple[dict, dict]:
    limit, actor_class, tolerances = _validate_options(limit, actor_class, epsilons)
    model = _load_model(world)
    valid, coverage = _original_actor_rows(world, actor_class=actor_class)
    rows = []
    ambiguous = 0
    for source in valid[:limit]:
        try:
            sample = _sweep(
                model, _point(source["original_location_unreal_xyz"]), tolerances)
        except ValueError:
            ambiguous += 1
            continue
        rows.append({
            **source,
            **sample,
            "source_actor_was_not_relocated": True,
            "new_point_Region_assignment_supported": False,
        })
    groups = _group_regions(rows)
    stable = sum(x["classification"] == "single-terminal-stable-across-epsilons"
                 for x in rows)
    forks = sum(x["classification"] == "ambiguous-plane-fork" for x in rows)
    sensitive = len(rows) - stable - forks
    world._check_original_unchanged()
    return {
        "schema": SCHEMA,
        "status": "read-only-source-original-Actor-Region-BSP-atlas",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "world_model_export": model["world_model_export"],
        "world_model_sha256": model["world_model_sha256"],
        "candidate_bsp_nodes": model["node_count"],
        "original_zone_records": model["zone_count"],
        "epsilon_sweep_unreal_units": list(tolerances),
        "source_actor_class_filter": actor_class,
        "sample_limit": limit,
        **coverage,
        "sampled_explicit_region_actors": len(rows),
        "source_Region_actors_skipped_due_to_trace_bounds": ambiguous,
        "stable_single_hypothetical_terminal_actors": stable,
        "near_plane_fork_actors": forks,
        "epsilon_sensitive_actors": sensitive,
        "hypothetical_terminal_groups": groups,
        "group_count": len(groups),
        "group_count_with_conflicting_source_Region": sum(
            x["any_original_Region_conflict"] for x in groups),
        "group_count_with_multiple_native_actor_classes": sum(
            x["multi_class_observations"] for x in groups),
        "source_original_actor_observations": rows,
        "no_new_Region_inference": True,
        "point_to_leaf_verified": False,
        "point_to_zone_verified": False,
        "native_Light_actor_spawn_enabled": False,
        "native_bsp_or_collision_rebuild_enabled": False,
        "source_gmp_modified": False,
        "gameplay_runtime_verified": False,
        "limitations": [
            "Only explicitly authored source tagged Region+Location+Level links qualify.",
            "Missing, inherited, malformed or unassigned Region values are excluded and counted.",
            "Original Light actors additionally require their full existing frame/physics audit.",
            "Terminal key is a hypothesized Model missing child branch, NOT an engine BSP leaf.",
            "A shared terminal may contain multiple contradictory source leaf/zone pairs.",
            "Source-only parsing and synthetic tests do not verify native point placement.",
            "No map, actor, native BSP, baked lighting, collision or script data was changed.",
        ],
    }, model


def original_actor_region_bsp_atlas(
    world: DX2Map, *, limit: int = 250,
    actor_class: str | None = None,
    epsilons: tuple[float, ...] = DEFAULT_EPSILONS,
) -> dict:
    """Source-only original Level actor Region provenance and BSP slot groups."""
    report, _ = _build(world, limit=limit, actor_class=actor_class, epsilons=epsilons)
    return report


def compare_point_to_original_actor_regions(
    world: DX2Map, point_unreal_xyz: tuple[float, float, float],
    *, limit: int = 250, actor_class: str | None = None,
    epsilons: tuple[float, ...] = DEFAULT_EPSILONS,
) -> dict:
    """Compare evidence; do not return a guessed native Region assignment."""
    xyz = _point(point_unreal_xyz)
    atlas, model = _build(world, limit=limit, actor_class=actor_class, epsilons=epsilons)
    target = _sweep(model, xyz, tuple(atlas["epsilon_sweep_unreal_units"]))
    candidates = {key for sweep in target["candidate_sweeps"]
                  for key in sweep["terminal_keys"]}
    groups = [g for g in atlas["hypothetical_terminal_groups"]
              if g["hypothetical_terminal_key"] in candidates]
    exact = [
        {"source_actor_export": row["source_actor_export"],
         "source_actor_class": row["original_actor_class"],
         "authored_original_Region_iLeaf": row["original_Region_iLeaf"],
         "authored_original_Region_ZoneNumberLow": row["original_Region_ZoneNumberLow"]}
        for row in atlas["source_original_actor_observations"]
        if row["original_location_unreal_xyz"] == list(xyz)]
    world._check_original_unchanged()
    return {
        "schema": SCHEMA,
        "status": "read-only-point-vs-source-Actor-Region-BSP-evidence",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "world_model_export": model["world_model_export"],
        "world_model_sha256": model["world_model_sha256"],
        "point_unreal_xyz": list(xyz),
        "source_actor_class_filter": actor_class,
        "sample_limit": limit,
        "epsilon_sweep_unreal_units": list(atlas["epsilon_sweep_unreal_units"]),
        "sampled_explicit_region_actors": atlas["sampled_explicit_region_actors"],
        "candidate_point_sweep": target,
        "overlapping_existing_actor_terminal_groups": groups,
        "exact_coordinate_matches_to_original_actors": exact,
        "new_point_Region_iLeaf": None,
        "new_point_Region_ZoneNumberLow": None,
        "point_to_leaf_verified": False,
        "point_to_zone_verified": False,
        "native_Light_actor_spawn_enabled": False,
        "native_bsp_or_collision_rebuild_enabled": False,
        "source_gmp_modified": False,
        "gameplay_runtime_verified": False,
    }


def save_original_actor_region_atlas(
    world: DX2Map, report: dict, output: str | Path,
) -> dict:
    """Only private new JSON after regeneration from the original source."""
    world._check_original_unchanged()
    dest = Path(output).expanduser().resolve()
    parts = tuple(p.casefold() for p in dest.parent.parts)
    if (dest.suffix.casefold() != ".json" or dest.exists()
            or dest.parent == world.source.parent
            or world.source.parent in dest.parents
            or any(parts[i:i+3] == ("content", "dx2", "maps")
                   for i in range(max(0, len(parts)-2)))):
        raise ValueError("Native Actor Region atlas must be fresh private JSON outside retail Maps")
    if (not isinstance(report, dict) or report.get("schema") != SCHEMA
            or report.get("source_sha256") != world.source_sha256):
        raise ValueError("Native Actor Region atlas source identity mismatch")
    kw = {
        "limit": report.get("sample_limit"),
        "actor_class": report.get("source_actor_class_filter"),
        "epsilons": report.get("epsilon_sweep_unreal_units"),
    }
    if report.get("status") == "read-only-source-original-Actor-Region-BSP-atlas":
        regenerated = original_actor_region_bsp_atlas(world, **kw)
    elif report.get("status") == "read-only-point-vs-source-Actor-Region-BSP-evidence":
        regenerated = compare_point_to_original_actor_regions(
            world, report.get("point_unreal_xyz"), **kw)
    else:
        raise ValueError("Unsupported source Actor Region atlas report kind")
    if regenerated != report:
        raise ValueError("Original actor Region atlas report differs from source replay")
    encoded = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False)
               + "\n").encode("utf8")
    if len(encoded) > MAX_PRIVATE_JSON:
        raise ValueError("Original Actor Region atlas JSON exceeds private report limit")
    world._check_original_unchanged()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("xb") as f:
        f.write(encoded)
    return {
        "schema": SCHEMA,
        "status": "private-replayed-original-Actor-Region-JSON-written",
        "output": str(dest),
        "output_sha256": _sha(encoded),
        "source_gmp_modified": False,
        "native_Light_actor_spawn_enabled": False,
    }
