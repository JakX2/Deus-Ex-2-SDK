"""DX2SDK CLI: private original GMP inspection and isolated safe map-copy tools.

Run from repo/source ZIP:
    python -B -m dx2sdk --help
In the Windows prototype, use SDK_CONSOLE.cmd.
"""
from __future__ import annotations

import argparse
import json
import sys

from .api import DX2Map, __version__
from .projects import write_position_plan, apply_position_plan


def _json(document):
    print(json.dumps(document, ensure_ascii=True, indent=2, allow_nan=False))


def _add_source(command, cache=False):
    command.add_argument("--map", required=True,
                         help="Your original DX2 Ion Storm v95 .gmp")
    if cache:
        command.add_argument("--actors", required=True,
                             help="SHA-bound original DX2Ed actors.json")


def make_parser():
    parser = argparse.ArgumentParser(
        prog="DX2SDK", description=(
            "Deus Ex: Invisible War native source-only SDK v%s. "
            "Read original maps/scripts and write isolated copies of "
            "existing StaticMeshActor Location data only." % __version__))
    parser.add_argument("--version", action="version",
                        version="DX2SDK %s" % __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help="Inspect original GMP package identity")
    _add_source(info)
    info.add_argument("--actors", help="Optional SHA-bound original actors.json")

    actors = sub.add_parser("actors", help="List positioned original actors")
    _add_source(actors)
    actors.add_argument("--actors", help="Optional SHA-bound actor cache")
    actors.add_argument("--class", dest="actor_class",
                        help="Exact original actor class, e.g. StaticMeshActor")
    actors.add_argument("--limit", type=int, default=50)

    scanner = sub.add_parser(
        "scan-map", help="Create source-verified private actors.json directly from original GMP")
    _add_source(scanner)
    scanner.add_argument("--output", required=True,
                         help="NEW private actors.json, outside all game Maps folders")
    scanner.add_argument("--system",
                         help="Optional owner-original System directory or DX2 property catalog JSON")

    inspect = sub.add_parser(
        "inspect-actor", help="Inspect native authored tagged and GameSys properties")
    _add_source(inspect)
    selector = inspect.add_mutually_exclusive_group(required=True)
    selector.add_argument("--actor", help="Exact native actor name")
    selector.add_argument("--export", type=int, help="Original one-based export ID")

    lights = sub.add_parser(
        "audit-lights", help="Audit original Light BSP/zone/frame dependencies (read-only)")
    _add_source(lights)
    lights.add_argument("--export", type=int, help="Optional original Light export")
    lights.add_argument("--output", help="Fresh private JSON report outside game Maps")

    switches = sub.add_parser(
        "light-switches", help="List source-authored one-byte GameSys bLightOn fields")
    _add_source(switches)
    switches.add_argument("--limit", type=int, default=50)

    toggle = sub.add_parser(
        "set-light-switch",
        help="Dry-run or isolated Save As of an existing bLightOn Boolean, not a new Light")
    _add_source(toggle)
    toggle.add_argument("--actor", required=True, help="Exact original fixture actor name")
    toggle.add_argument("--export", type=int, required=True,
                        help="Original placed actor one-based export")
    toggle.add_argument("--expect", required=True, choices=("true", "false"),
                        help="Pinned original bLightOn value; replacement is opposite")
    toggle.add_argument("--output", required=True,
                        help="Fresh isolated GMP with original basename")
    toggle.add_argument("--write", action="store_true",
                        help="Explicitly write isolated GMP; default dry-run")

    switch_verify = sub.add_parser(
        "verify-light-switch",
        help="Independently replay and verify saved bLightOn GMP, one byte only")
    _add_source(switch_verify)
    switch_verify.add_argument("--output", required=True)

    colors = sub.add_parser(
        "light-colors",
        help="List original source-verified exact 10-byte GameSys LightColor struct actors")
    _add_source(colors)
    colors.add_argument("--limit", type=int, default=50)

    color_set = sub.add_parser(
        "set-light-color",
        help="Dry-run or isolated exact 1..3 existing LightColor byte replacements")
    _add_source(color_set)
    color_set.add_argument("--actor", required=True)
    color_set.add_argument("--export", type=int, required=True)
    color_set.add_argument("--expect", nargs=3, type=int, metavar=("B", "H", "S"),
                           required=True, help="Pin original brightness/hue/saturation bytes")
    color_set.add_argument("--brightness", type=int, help="New authored brightness byte (0..255)")
    color_set.add_argument("--hue", type=int, help="New authored hue byte (0..255)")
    color_set.add_argument("--saturation", type=int, help="New authored saturation byte (0..255)")
    color_set.add_argument("--output", required=True,
                           help="Fresh isolated GMP with original source basename")
    color_set.add_argument("--write", action="store_true",
                           help="Explicit output creation; dry run otherwise")

    color_verify = sub.add_parser(
        "verify-light-color",
        help="Reconstruct saved source-locked LightColor bytes and compare whole GMP")
    _add_source(color_verify)
    color_verify.add_argument("--output", required=True)

    multi_color = sub.add_parser(
        "make-lightcolor-plan",
        help="Create private source-locked 2..8 original LightColor actor plan")
    _add_source(multi_color)
    multi_color.add_argument(
        "--edit", required=True, action="append", nargs=7,
        metavar=("EXPORT", "OLD_B", "OLD_H", "OLD_S", "NEW_B", "NEW_H", "NEW_S"),
        help="Repeat 2..8 times: one source actor plus pinned original and target bytes")
    multi_color.add_argument("--plan", required=True,
                             help="Fresh private JSON outside all game Maps directories")

    multi_apply = sub.add_parser(
        "apply-lightcolor-plan",
        help="Dry-run or explicitly write source-locked 2..8 LightColor actors into one GMP")
    _add_source(multi_apply)
    multi_apply.add_argument("--plan", required=True)
    multi_apply.add_argument("--output", required=True)
    multi_apply.add_argument("--write", action="store_true",
                             help="Explicit private GMP Save As; dry-run by default")

    multi_color_verify = sub.add_parser(
        "verify-multi-lightcolor",
        help="Independently reconstruct every approved LightColor edit and compare whole GMP")
    _add_source(multi_color_verify)
    multi_color_verify.add_argument("--output", required=True)

    definitions = sub.add_parser(
        "scripts", help="Inspect original source TriggerScript definitions")
    _add_source(definitions, cache=True)
    definitions.add_argument("--zip", required=True,
                             help="Original TriggerScript.zip")
    definitions.add_argument("--filter", default="",
                             help="Optional case-insensitive script ID/title filter")
    definitions.add_argument("--limit", type=int, default=50)

    resources = sub.add_parser(
        "ibd", help="Compare original TSD definitions to one original IBD")
    _add_source(resources, cache=True)
    resources.add_argument("--zip", required=True)
    resources.add_argument("--ibd", required=True)

    compare = sub.add_parser(
        "compare", help="Compare mission IBD + Kernel_TSDALL to standalone TSDs")
    _add_source(compare, cache=True)
    compare.add_argument("--zip", required=True)
    compare.add_argument("--mission-ibd", required=True)
    compare.add_argument("--kernel-ibd", required=True)

    list_clones = sub.add_parser(
        "clone-candidates",
        help="List source-original idle/unlinked StaticMeshActor copies eligible for experimental cloning")
    _add_source(list_clones)
    list_clones.add_argument("--limit", type=int, default=100)

    clone = sub.add_parser(
        "clone-prop",
        help="Dry-run or explicitly create one isolated static-mesh duplicate using audited T3SDK")
    _add_source(clone)
    clone.add_argument("--actor", required=True,
                       help="Exact existing source StaticMeshActor name")
    clone.add_argument("--export", type=int, required=True,
                       help="Original one-based source native export index")
    clone.add_argument("--dx", type=float, required=True,
                       help="Native X delta, -4096..4096")
    clone.add_argument("--dy", type=float, required=True,
                       help="Native Y delta, -4096..4096")
    clone.add_argument("--dz", type=float, required=True,
                       help="Native Z delta, -4096..4096")
    clone.add_argument("--output", required=True,
                       help="Fresh isolated GMP path with original basename")
    clone.add_argument("--write", action="store_true",
                       help="Explicitly write new native GMP copy; dry-run by default")

    clone_verify = sub.add_parser(
        "verify-clone", help="Rebuild original static prop clone and verify saved entire GMP")
    _add_source(clone_verify)
    clone_verify.add_argument("--output", required=True)

    multi_plan = sub.add_parser(
        "make-multi-clone-plan",
        help="Write a source-locked 2..8 original static prop duplicate plan JSON")
    _add_source(multi_plan)
    multi_plan.add_argument(
        "--copy", action="append", nargs=4,
        metavar=("EXPORT", "DX", "DY", "DZ"), required=True,
        help="Repeat 2..8 times. Original export ID and native delta X/Y/Z")
    multi_plan.add_argument(
        "--plan", required=True,
        help="Fresh private .json, never inside game Content/DX2/Maps")

    multi_apply = sub.add_parser(
        "apply-multi-clone-plan",
        help="Dry-run or explicitly save 2..8 source-verified prop duplicates")
    _add_source(multi_apply)
    multi_apply.add_argument("--plan", required=True,
                             help="DX2SDK native source-locked clone plan JSON")
    multi_apply.add_argument("--output", required=True,
                             help="Fresh isolated GMP with original map basename")
    multi_apply.add_argument("--write", action="store_true",
                             help="Explicitly write new GMP; dry-run otherwise")

    multi_verify = sub.add_parser(
        "verify-multi-clone",
        help="Recreate original 2..8 source prop copies and check every GMP byte")
    _add_source(multi_verify)
    multi_verify.add_argument("--output", required=True)

    fields = sub.add_parser(
        "scalar-fields",
        help="List original 4-byte int/float tagged fields eligible for experimental Save As")
    _add_source(fields, cache=True)
    fields.add_argument("--actor", required=True,
                        help="Exact original positioned StaticMeshActor name")

    scalar = sub.add_parser(
        "set-scalar", help="Dry-run first, then isolated existing native scalar GMP copy")
    _add_source(scalar, cache=True)
    scalar.add_argument("--actor", required=True,
                        help="Original existing StaticMeshActor name")
    scalar.add_argument("--property", dest="property_name", required=True,
                        help="Existing authored top-level numeric tag name")
    scalar.add_argument("--value", required=True,
                        help="New int32 or float32 value, source type is verified")
    scalar.add_argument("--output", required=True,
                        help="Fresh isolated GMP with identical source basename")
    scalar.add_argument("--write", action="store_true",
                        help="Explicitly write experimental binary copy, dry-run is default")

    scalar_verify = sub.add_parser(
        "verify-scalar", help="Independently audit every edited byte of scalar GMP copy")
    _add_source(scalar_verify, cache=True)
    scalar_verify.add_argument("--output", required=True)

    audit = sub.add_parser("native-audit",
                           help="Find existing source actors with writable Location")
    _add_source(audit, cache=True)

    noop = sub.add_parser("noop-audit",
                          help="Check MIT T3SDK byte-identical GMP reassembly")
    _add_source(noop)

    move = sub.add_parser(
        "move", help="Dry-run by default; isolate existing StaticMeshActor Location")
    _add_source(move, cache=True)
    move.add_argument("--actor", required=True,
                      help="Exact original StaticMeshActor name")
    move.add_argument("--x", type=float, required=True,
                      help="NEW X in original native DX2 world units")
    move.add_argument("--y", type=float, required=True,
                      help="NEW Y in original native DX2 world units")
    move.add_argument("--z", type=float, required=True,
                      help="NEW Z in original native DX2 world units")
    move.add_argument("--output", required=True,
                      help="Fresh isolated folder/output with same GMP basename")
    move.add_argument("--write", action="store_true",
                      help="Explicitly create new copy (default is dry-run)")

    plan = sub.add_parser(
        "make-plan", help="Create fresh source-locked editable position plan JSON")
    _add_source(plan, cache=True)
    plan.add_argument("--actor", required=True)
    plan.add_argument("--x", type=float, required=True)
    plan.add_argument("--y", type=float, required=True)
    plan.add_argument("--z", type=float, required=True)
    plan.add_argument("--plan", required=True,
                      help="Fresh private .json outside original game folders")

    apply = sub.add_parser(
        "apply-plan", help="Validate editable multi-actor plan and dry-run / write new map")
    _add_source(apply, cache=True)
    apply.add_argument("--plan", required=True,
                       help="Source-locked DX2SDK-position-plan-v1 JSON")
    apply.add_argument("--output", required=True,
                       help="Fresh isolated GMP copy with original basename")
    apply.add_argument("--write", action="store_true",
                       help="Explicitly write new copy; otherwise dry-run")

    verify = sub.add_parser("verify-move",
                            help="Reverify binary integrity of isolated edited GMP")
    _add_source(verify)
    verify.add_argument("--output", required=True)

    return parser


def _compare_summary(doc):
    c = doc["counts"]
    transitions = doc["actor_name_slot_candidates"]
    by_group = {}
    for key in ("mission_vs_standalone", "kernel_vs_standalone",
                "mission_vs_kernel"):
        differing = 0
        only = 0
        both = 0
        other = 0
        too_short = 0
        for script in doc["script_rows"]:
            profile = script.get(key)
            if not isinstance(profile, dict) or profile.get("byte_equal") is not False:
                continue
            differing += 1
            if profile.get("candidate_word4_4byte_slot_comparable") is not True:
                too_short += 1
            elif profile.get("candidate_word4_only_difference") is True:
                only += 1
            elif profile.get("candidate_word4_and_other_changes") is True:
                both += 1
            else:
                other += 1
        by_group[key] = {
            "different_resource_payloads": differing,
            "bytes_4_through_7_only_changed": only,
            "bytes_4_through_7_plus_other_changes": both,
            "other_changes_only": other,
            "too_short": too_short,
        }
    return {
        "read_only": True, "counts": c,
        "payload_difference_groups": by_group,
        "actor_name_slot_candidate_status": transitions["status"],
        "actor_name_slot_candidate_occurrences":
            transitions["raw_name_slot_candidate_occurrences"],
        "runtime_actor_script_binding_verified": False,
        "native_script_writer_enabled": False,
        "original_source_names_bytes_hashes_included": False,
    }


def _parse_native_multi_clone_copies(world, groups):
    if not isinstance(groups, list) or not 2 <= len(groups) <= 8:
        raise ValueError("Provide 2..8 explicit original --copy EXPORT DX DY DZ rows")
    result = []
    for item in groups:
        try:
            export = int(item[0], 10)
            if export < 1 or export > len(world._package.exports):
                raise ValueError()
            delta = [float(n) for n in item[1:4]]
        except (ValueError, OverflowError, TypeError):
            raise ValueError("Original clone source export or relative delta invalid") from None
        source = world._package.exports[export - 1]
        if world._package.class_name(source) != "StaticMeshActor":
            raise ValueError("Only original native StaticMeshActor exports may be cloned")
        result.append({"actor": source["name"], "export": export,
                       "delta": delta})
    return result


def main(argv=None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    try:
        project = DX2Map.open(args.map, getattr(args, "actors", None))
        if args.command == "info":
            _json(project.info())
        elif args.command == "actors":
            _json(project.actors(actor_class=args.actor_class, limit=args.limit))
        elif args.command == "scan-map":
            report = project.export_actor_catalog(
                args.output, system=args.system)
            _json({"schema": report["schema"],
                   "status": report["status"],
                   "source_map": report["source_map"],
                   "actor_count": report["actor_count"],
                   "source_verified_location_candidates":
                       report["writer_candidate_count"],
                   "unresolved_source_static_meshes":
                       report["unresolved_static_mesh_count"],
                   "gameplay_runtime_verified": False,
                   "original_source_modified": False})
        elif args.command == "inspect-actor":
            _json(project.inspect_actor(
                export=args.export, name=args.actor))
        elif args.command == "audit-lights":
            result = (project.export_original_lights(args.output, export=args.export)
                      if args.output else project.audit_original_lights(export=args.export))
            if args.output:
                _json({"schema": result["schema"], "status": result["status"],
                       "source_map": project.source.name,
                       "source_light_count": result["source_light_count"],
                       "selected_light_count": len(result["lights"]),
                       "native_light_spawn_enabled": False,
                       "original_source_modified": False})
            else:
                _json(result)
        elif args.command == "light-switches":
            _json(project.original_light_switches(limit=args.limit))
        elif args.command == "set-light-switch":
            _json(project.set_existing_light_switch(
                export=args.export, actor=args.actor,
                expected=args.expect == "true",
                output=args.output, write=args.write))
        elif args.command == "verify-light-switch":
            _json(project.verify_saved_light_switch(args.output))
        elif args.command == "light-colors":
            _json(project.original_light_colors(limit=args.limit))
        elif args.command == "set-light-color":
            changes = {key: getattr(args, key) for key in
                       ("brightness", "hue", "saturation")
                       if getattr(args, key) is not None}
            _json(project.set_existing_light_color(
                export=args.export, actor=args.actor, expected=tuple(args.expect),
                changes=changes, output=args.output, write=args.write))
        elif args.command == "verify-light-color":
            _json(project.verify_saved_light_color(args.output))
        elif args.command == "make-lightcolor-plan":
            if not 2 <= len(args.edit) <= 8:
                raise ValueError("LightColor batch plan requires exactly 2..8 source actor rows")
            copies = []
            for item in args.edit:
                values = [int(x, 10) for x in item]
                export = values[0]
                if not 1 <= export <= len(project._package.exports):
                    raise ValueError("Source LightColor export ID outside original map")
                source = project._package.exports[export - 1]
                before, after = values[1:4], values[4:7]
                updates = {name: value for name, old, value in
                           zip(("brightness", "hue", "saturation"), before, after)
                           if value != old}
                copies.append({
                    "actor": source["name"], "export": export,
                    "expected": before, "changes": updates})
            plan = project.write_lightcolor_plan(copies, args.plan)
            _json({"schema": plan["schema"], "status": "private_source_plan_created",
                   "planned_actor_edits": len(plan["actors"]),
                   "gameplay_runtime_verified": False,
                   "native_bsp_or_zone_rebuild_enabled": False})
        elif args.command == "apply-lightcolor-plan":
            report = project.apply_lightcolor_plan(
                args.plan, args.output, write=args.write)
            _json({"schema": report["schema"], "status": report["status"],
                   "edited_actor_count": report["edited_actor_count"],
                   "changed_bytes": report["changed_bytes"],
                   "verified_binary_structure":
                       report.get("verified_binary_structure", False),
                   "gameplay_runtime_verified": False})
        elif args.command == "verify-multi-lightcolor":
            _json(project.verify_saved_multi_lightcolor(args.output))
        elif args.command == "scripts":
            if not 0 <= args.limit <= 5000:
                raise ValueError("Script list limit must be 0..5000")
            report = project.script_definitions(args.zip)
            matching = [x for x in report["script_definitions"]
                        if args.filter.casefold() in
                        (x["id"] + " " + x.get("title", "")).casefold()]
            _json({"map": project.source.name, "matching": len(matching),
                   "shown": matching[:args.limit], "read_only": True,
                   "native_script_writer_enabled": False})
        elif args.command == "ibd":
            report = project.script_resources(args.zip, args.ibd)
            _json({"read_only": True, "counts": report["counts"],
                   "actor_name_slot_status":
                       report["original_actor_name_slot_probe"]["status"],
                   "runtime_actor_script_binding_verified": False,
                   "original_source_paths_not_exported": True})
        elif args.command == "compare":
            _json(_compare_summary(project.compare_script_bundles(
                args.zip, args.mission_ibd, args.kernel_ibd)))
        elif args.command == "clone-candidates":
            report = project.static_prop_clone_candidates(limit=args.limit)
            _json({"schema": report["schema"], "status": report["status"],
                   "source_map": project.source.name,
                   "candidate_count": len(report["candidates"]),
                   "candidates": report["candidates"], "read_only": True,
                   "gameplay_runtime_verified": False,
                   "native_arbitrary_actor_spawning_enabled": False})
        elif args.command == "clone-prop":
            report = project.clone_existing_static_prop(
                original_export=args.export, original_actor=args.actor,
                delta_native_xyz=(args.dx, args.dy, args.dz),
                output=args.output, write=args.write)
            _json({"schema": report["schema"], "status": report["status"],
                   "original_export": report["source_actor_export"],
                   "new_export": report["new_actor_export"],
                   "normalized_clone_frame": report["clone_frame_normalized"],
                   "source_bytes_unchanged": report["original_bytes_unchanged"],
                   "independent_full_binary_verification":
                       report.get("independent_verified_binary_structure", False),
                   "runtime_game_verified": False})
        elif args.command == "verify-clone":
            report = project.verify_saved_clone(args.output)
            _json({"schema": report["schema"],
                   "verified_binary_structure": report["verified_binary_structure"],
                   "new_export": report["new_export"],
                   "new_clone_state_normalized": report["new_clone_state_normalized"],
                   "gameplay_runtime_verified": False})
        elif args.command == "make-multi-clone-plan":
            copies = _parse_native_multi_clone_copies(project, args.copy)
            report = project.write_multi_clone_plan(copies, args.plan)
            _json({"schema": report["schema"],
                   "status": "source_locked_private_clone_plan_created",
                   "source_map": project.source.name,
                   "planned_existing_static_prop_copies": len(report["copies"]),
                   "runtime_game_verified": False,
                   "native_arbitrary_actor_spawning_enabled": False})
        elif args.command == "apply-multi-clone-plan":
            report = project.apply_multi_clone_plan(
                args.plan, args.output, write=args.write)
            _json({"schema": report["schema"], "status": report["status"],
                   "existing_static_prop_copies": len(report["copies"]),
                   "new_export_count": report["new_export_count"],
                   "independent_full_binary_verification":
                       report.get("independent_full_binary_verification", False),
                   "runtime_game_verified": False,
                   "native_arbitrary_actor_spawning_enabled": False})
        elif args.command == "verify-multi-clone":
            report = project.verify_saved_multi_clone(args.output)
            _json({"schema": report["schema"],
                   "verified_binary_structure":
                       report["verified_binary_structure"],
                   "new_actor_count": report["new_actor_count"],
                   "new_clones_state_normalized":
                       report["new_clones_state_normalized"],
                   "gameplay_runtime_verified": False})
        elif args.command == "scalar-fields":
            report = project.native_scalar_fields(args.actor)
            _json({"schema": report["schema"], "actor_name": report["actor_name"],
                   "fields": report["fields"], "read_only": True,
                   "runtime_game_verified": False})
        elif args.command == "set-scalar":
            fields = project.native_scalar_fields(args.actor)["fields"]
            selected = [f for f in fields if f["property"] == args.property_name]
            if len(selected) != 1:
                raise ValueError("Field not eligible for existing native numeric scalar editing")
            try:
                numeric = (int(args.value, 10) if selected[0]["type"] == "int32"
                           else float(args.value))
            except (ValueError, OverflowError):
                raise ValueError("Requested numeric value cannot be parsed as original field type") from None
            report = project.save_as_scalar_changes(
                {args.actor: {args.property_name: numeric}},
                args.output, write=args.write)
            _json({"schema": report["schema"],
                   "status": report["status"],
                   "edited_field_count": report["edited_field_count"],
                   "changed_byte_count": report["changed_byte_count"],
                   "independent_binary_verification":
                       report["independent_byte_validation"],
                   "runtime_game_verified": False,
                   "source_original_modified": False})
        elif args.command == "verify-scalar":
            report = project.verify_saved_scalar_changes(args.output)
            _json({"schema": report["schema"],
                   "verified_binary_structure":
                       report["verified_binary_structure"],
                   "changed_fields": report["changed_fields"],
                   "changed_bytes": report["changed_bytes"],
                   "unapproved_bytes": report["unapproved_bytes"],
                   "runtime_game_verified": False})
        elif args.command == "native-audit":
            report = project.native_location_audit()
            _json({"read_only": True, "original_map": project.source.name,
                   "source_actor_count": report.get("total_actor_records"),
                   "rendered_static_mesh_candidates":
                       report.get("rendered_static_mesh_candidates"),
                   "supported_static_mesh_actors":
                       report.get("native_location_candidates"),
                   "unsupported_static_mesh_candidates":
                       report.get("unsupported_candidates"),
                   "schema": report.get("schema"),
                   "native_editing_supported": "translation_only",
                   "gameplay_runtime_verified": False})
        elif args.command == "noop-audit":
            report = project.native_noop_audit()
            _json({"read_only": True, "original_map": project.source.name,
                   "no_op_bytes_identical": report.get("byte_identical", False),
                   "gameplay_runtime_verified": False})
        elif args.command == "move":
            report = project.save_as_translations(
                {args.actor: [args.x, args.y, args.z]},
                args.output, write=args.write)
            _json({"sdk_schema": report["sdk_schema"],
                   "status": report["status"],
                   "source_map": project.source.name,
                   "output_filename": project.source.name,
                   "translated_existing_actors":
                       len(report["translated_existing_actors"]),
                   "independent_binary_verification":
                       report.get("independent_binary_verification", None),
                   "gameplay_runtime_verified": False,
                   "no_original_game_files_modified": True})
        elif args.command == "make-plan":
            plan = write_position_plan(
                project, {args.actor: [args.x, args.y, args.z]},
                args.plan)
            _json({"schema": plan["schema"], "status": "private_plan_created",
                   "source_map": project.source.name,
                   "planned_existing_actor_moves": len(plan["moves"]),
                   "gameplay_runtime_verified": False,
                   "native_script_edits_enabled": False})
        elif args.command == "apply-plan":
            report = apply_position_plan(
                project, args.plan, args.output, write=args.write)
            _json({"sdk_schema": report["sdk_schema"],
                   "status": report["status"],
                   "source_map": project.source.name,
                   "translated_existing_actors":
                       len(report["translated_existing_actors"]),
                   "independent_binary_verification":
                       report.get("independent_binary_verification", None),
                   "gameplay_runtime_verified": False,
                   "no_original_game_files_modified": True})
        elif args.command == "verify-move":
            report = project.verify_saved_translation(args.output)
            _json({"verified_binary_structure": report["verified_binary_structure"],
                   "translated_existing_actors": report["translated_existing_actors"],
                   "changed_bytes": report["changed_bytes"],
                   "gameplay_runtime_verified": False})
        else:
            parser.error("Unknown DX2SDK subcommand")
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError,
            ArithmeticError, RuntimeError) as exc:
        # No private paths, script names or source bytes in CLI errors.
        if isinstance(exc, (OSError, KeyError, IndexError, ArithmeticError)):
            error = "source_parse_or_native_safety_check_failed"
        else:
            error = str(exc)
            if any(sep in error for sep in ("/", "\\", ":\\", " at ", " in ")):
                error = "source_parse_or_native_safety_check_failed"
        print(json.dumps({"status": "refused", "code": error}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
