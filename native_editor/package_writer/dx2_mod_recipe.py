#!/usr/bin/env python3
"""Asset-free DX2Ed v0.61 native static-prop mod recipe.

A tiny, source-SHA-pinned JSON *instruction recipe*, not a modified retail GMP.
The original DX2 game and original map must be supplied locally by each user.
The only generated GMP is a new, isolated and byte-verified test candidate.
No game installation, automatic map replacement or runtime success claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_actor_clone_probe import _destination, _pin
from dx2_package_roundtrip import _validate_input, sha256
from dx2_native_prop_plan import (
    _plan, _read_plan, compile_in_memory, save_isolated, verify_saved_plan,
)

SCHEMA = "DX2Ed-portable-native-static-prop-recipe-v1"
SUFFIX = ".dx2edmod.json"
MAX_RECIPE_BYTES = 128 * 1024
FIELDS = {
    "schema", "source_file", "source_sha256", "source_size",
    "candidate_sha256", "candidate_size", "native_plan",
    "operation_counts", "includes_retail_assets", "runtime_game_verified",
    "automatic_game_installation",
}


def _recipe_path(value: Path, original: Path):
    target = Path(value).expanduser().resolve()
    if not target.name.endswith(SUFFIX):
        raise ValueError("Portable recipe filename must end with .dx2edmod.json")
    if (target == original or target.parent == original.parent
            or original.parent in target.parents):
        raise ValueError("Recipe cannot be created in original map folder or descendants")
    parts = [segment.casefold() for segment in target.parent.parts]
    if all(name in parts for name in ("content", "dx2", "maps")):
        raise ValueError("Recipe cannot be written inside a game Content/DX2/Maps directory")
    return target


def _counts(plan):
    return {
        "moves": len(plan["moves"]),
        "copies": len(plan["copies"]),
        "unplaces": len(plan["unplaces"]),
    }


def _draft(source: Path, *, source_sha256: str, plan: dict):
    source = _validate_input(Path(source))
    source_sha256 = _pin(source_sha256)
    summary, candidate = compile_in_memory(
        source, source_sha256=source_sha256, plan=plan)
    normalized = summary["plan"]
    doc = {
        "schema": SCHEMA,
        "source_file": source.name,
        "source_sha256": source_sha256,
        "source_size": source.stat().st_size,
        "candidate_sha256": summary["output_sha256"],
        "candidate_size": len(candidate),
        "native_plan": normalized,
        "operation_counts": _counts(normalized),
        "includes_retail_assets": False,
        "runtime_game_verified": False,
        "automatic_game_installation": False,
    }
    if sha256(candidate) != doc["candidate_sha256"]:
        raise ValueError("Candidate digest disagrees with native writer")
    if len(json.dumps(doc, sort_keys=True).encode("utf-8")) > MAX_RECIPE_BYTES:
        raise ValueError("Portable recipe exceeds size cap")
    return doc, candidate


def export_recipe(source: Path, recipe_file: Path, *, source_sha256: str, plan: dict):
    source = _validate_input(Path(source))
    target = _recipe_path(recipe_file, source)
    doc, candidate = _draft(source, source_sha256=source_sha256, plan=plan)
    if target.exists():
        raise FileExistsError("Refusing to overwrite an existing mod recipe")
    serialized = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if len(serialized.encode("utf-8")) > MAX_RECIPE_BYTES:
        raise ValueError("Serialized recipe exceeds size cap")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    try:
        loaded = read_recipe(target)
        if loaded != doc or sha256(candidate) != loaded["candidate_sha256"]:
            raise ValueError("On-disk portable recipe failed immediate verification")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {
        "schema": SCHEMA, "status": "source-verified-mod-recipe-created",
        "recipe_file": str(target), "source_file": source.name,
        "source_sha256": doc["source_sha256"],
        "candidate_sha256": doc["candidate_sha256"],
        "operation_counts": doc["operation_counts"],
        "includes_retail_assets": False,
        "runtime_game_verified": False,
        "game_installation_modified": False,
        "gmp_output_written": False,
    }


def read_recipe(path: Path) -> dict:
    path = Path(path).expanduser().resolve(strict=True)
    if not path.name.endswith(SUFFIX):
        raise ValueError("Unrecognized portable mod recipe suffix")
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_RECIPE_BYTES:
        raise ValueError("Recipe missing, empty or oversized")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or set(doc) != FIELDS or doc["schema"] != SCHEMA:
        raise ValueError("Invalid native mod recipe schema or unexpected metadata")
    if (not isinstance(doc["source_file"], str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}\.gmp", doc["source_file"], flags=re.I)
            or doc["source_file"] in (".gmp", "..gmp")
            or "/" in doc["source_file"] or "\\" in doc["source_file"]):
        raise ValueError("Recipe must contain only the original GMP basename")
    if (type(doc["source_size"]) is not int or doc["source_size"] <= 0
            or type(doc["candidate_size"]) is not int or doc["candidate_size"] <= 0):
        raise ValueError("Recipe source/candidate lengths invalid")
    _pin(doc["source_sha256"])
    _pin(doc["candidate_sha256"])
    normalized = _plan(doc["native_plan"])
    if normalized != doc["native_plan"] or doc["operation_counts"] != _counts(normalized):
        raise ValueError("Recipe plan or operation counts are not canonical")
    if (doc["includes_retail_assets"] is not False
            or doc["runtime_game_verified"] is not False
            or doc["automatic_game_installation"] is not False):
        raise ValueError("Portable mod recipes cannot include or install retail game assets")
    return doc


def reconstruct(source: Path, recipe_file: Path, *, output: Path | None = None):
    """Check source and recipe; output optional, NEVER in-place."""
    source = _validate_input(Path(source))
    doc = read_recipe(recipe_file)
    if source.name.casefold() != doc["source_file"].casefold():
        raise ValueError("Original GMP basename does not match recipe")
    if (source.stat().st_size != doc["source_size"]
            or sha256(source.read_bytes()) != doc["source_sha256"]):
        raise ValueError("User-owned original GMP does not match recipe SHA/size")
    expected, candidate = _draft(
        source, source_sha256=doc["source_sha256"],
        plan=doc["native_plan"])
    if any(expected[key] != doc[key] for key in (
        "source_file", "source_sha256", "source_size",
        "candidate_sha256", "candidate_size", "native_plan", "operation_counts"
    )):
        raise ValueError("Recompiled native candidate does not match recipe expectation")
    if output is None:
        return {
            "schema": SCHEMA, "status": "recipe-recompiled-runtime-unverified",
            "source_sha256": doc["source_sha256"],
            "candidate_sha256": doc["candidate_sha256"],
            "operation_counts": doc["operation_counts"],
            "gmp_output_written": False, "includes_retail_assets": False,
            "runtime_game_verified": False, "game_installation_modified": False,
        }
    output = Path(output).expanduser().resolve()
    _destination(source, output)
    result = save_isolated(
        source, output, source_sha256=doc["source_sha256"],
        plan=doc["native_plan"])
    try:
        if (sha256(output.read_bytes()) != doc["candidate_sha256"]
                or len(output.read_bytes()) != doc["candidate_size"]):
            raise ValueError("Saved candidate does not match portable recipe")
        proof = verify_saved_plan(
            source, output, source_sha256=doc["source_sha256"])
        if proof["output_sha256"] != doc["candidate_sha256"]:
            raise ValueError("Saved candidate replay verifier disagrees")
    except Exception:
        # The new GMP has already been allocated by save_isolated. Do not
        # delete an unrelated file if it was externally changed afterward.
        # A mismatch is surfaced as a refusal for explicit user inspection.
        raise
    return {
        "schema": SCHEMA,
        "status": "isolated-GMP-rebuilt-from-portable-recipe-runtime-unverified",
        "output_file": str(output),
        "source_sha256": doc["source_sha256"],
        "candidate_sha256": doc["candidate_sha256"],
        "operation_counts": doc["operation_counts"],
        "all_candidate_bytes_replayed": proof["all_candidate_bytes_replayed"],
        "gmp_output_written": True, "includes_retail_assets": False,
        "runtime_game_verified": False, "game_installation_modified": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="User-owned original DX2 GMP")
    parser.add_argument("--source-sha256", help="Required for export, exact 64-char lowercase hex")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export-recipe", type=Path, help="New .dx2edmod.json, contains NO GMP data")
    group.add_argument("--recipe", type=Path, help="Load a portable recipe and reconstruct/verify")
    parser.add_argument("--plan-json", type=Path, help="v0.60 native static-prop plan for export")
    parser.add_argument("--output", type=Path, help="Optional NEW isolated .gmp for recipe apply")
    args = parser.parse_args(argv)
    try:
        if args.export_recipe:
            if args.plan_json is None or args.output is not None or not args.source_sha256:
                raise ValueError("Export requires --plan-json, --source-sha256, and no --output")
            result = export_recipe(
                args.source, args.export_recipe,
                source_sha256=args.source_sha256, plan=_read_plan(args.plan_json))
        else:
            if args.plan_json is not None or args.source_sha256 is not None:
                raise ValueError("Recipe reconstruction takes only --recipe and optional --output")
            result = reconstruct(args.source, args.recipe, output=args.output)
    except Exception as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "refused", "reason": str(exc) or type(exc).__name__,
            "gmp_output_written": False, "runtime_game_verified": False,
        }))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
