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
