#!/usr/bin/env python3
"""DX2Ed v0.64: reversible, source-pinned RETAIL TEST PLAN only.

An isolated original-derived GMP is recompiled and every byte verified before
a content-free human test dossier is prepared. Nothing is installed, run, copied
into Content/DX2/Maps, or modified in the original game. Observations are
USER-REPORTED, not an independent assertion of gameplay compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from dx2_actor_clone_probe import _pin
from dx2_native_prop_plan import (
    _manifest_path, MAX_MANIFEST_BYTES, compile_in_memory,
    verify_saved_plan,
)
from dx2_package_roundtrip import _validate_input, sha256

SCHEMA = "DX2Ed-retail-static-prop-trial-dossier-v1"
OBSERVATIONS_SCHEMA = "DX2Ed-retail-static-prop-observations-v1"
MAX_JSON = 512 * 1024
REQUIRED_PHASES = (
    ("baseline", "Enter the original unchanged map in a separate, backed-up retail installation and record baseline props, gameplay and collision."),
    ("candidate-load", "Manually test a COPY of the candidate in a disposable game installation; confirm fresh map entry, no crash and no missing unrelated world assets."),
    ("collision", "Check player contact on moved/copied/unplaced props; confirm collision corresponds to visible objects (and does not remain after removal)."),
    ("reentry", "Travel out of the edited map and back; check every intended change and nearby unaffected objects."),
    ("save-reload", "Create a disposable saved game and reload it; check objects, collision, script/AI behavior and all intended edits."),
    ("restore", "Restore the backed-up original retail map by hand; verify baseline visuals and no persistent game/save corruption."),
)


def _read_json(path: Path, *, suffix: str) -> dict:
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file() or not path.name.endswith(suffix):
        raise ValueError("Expected a source-only JSON with the correct suffix")
    if not 0 < path.stat().st_size <= MAX_JSON:
        raise ValueError("Source-only JSON is empty or oversized")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("Expected a JSON object")
    return doc


def _output_paths(destination: Path, source: Path, candidate: Path) -> tuple[Path, Path]:
    path = Path(destination).expanduser().resolve()
    if not path.name.endswith(".dx2trial.json"):
        raise ValueError("Trial dossier output must end with .dx2trial.json")
    observations = path.with_name(path.name.removesuffix(".dx2trial.json") + ".dx2observations.json")
    protected = (source.parent, candidate.parent)
    if any(
        path == p or path.parent == p or
        p in path.parents or path.parent in p.parents for p in protected
    ):
        raise ValueError("Dossier may not be written near or above the source/candidate GMP")
    parts = [x.casefold() for x in path.parts]
    if {"content", "dx2", "maps"} <= set(parts):
        raise ValueError("Never write trial records inside any game's Content/DX2/Maps")
    if path.exists() or observations.exists():
        raise FileExistsError("Never overwrite existing trial dossier or observations")
    return path, observations


def _checklist(plan: dict, compilation: dict) -> list[dict]:
    checks = [{"id": name, "category": "manual-runtime", "original_actor": None,
               "expectation": desc}
              for name, desc in REQUIRED_PHASES]
    for i, row in enumerate(compilation["moved"], 1):
        checks.append({
            "id": f"move-{i:02d}", "category": "manual-actor-transform",
            "original_actor": row["actor"],
            "original_export": row["export"],
            "expected_original_location_xyz": row["before"],
            "expected_candidate_location_xyz": row["after"],
            "expectation": "Confirm original static prop has moved to the expected new location (not a preview-only move).",
        })
    for i, row in enumerate(compilation["copied"], 1):
        checks.append({
            "id": f"clone-{i:02d}", "category": "manual-new-object",
            "original_actor": row["source_actor"],
            "source_export": row["source_export"],
            "new_actor": row["new_actor"],
            "new_export": row["new_export"],
            "expected_candidate_location_xyz": row["after"],
            "expectation": "Confirm a new in-game static mesh exists where expected, distinct from the original.",
        })
    for i, row in enumerate(compilation["unplaced"], 1):
        checks.append({
            "id": f"unplace-{i:02d}", "category": "manual-level-membership",
            "original_actor": row["actor"], "original_export": row["export"],
            "expectation": "Confirm original prop disappears on fresh map entry and leaves no unwanted collision or script effects.",
        })
    if len(checks) > 32 or len({c["id"] for c in checks}) != len(checks):
        raise ValueError("Invalid or excessive retail test check IDs")
    return checks


def expected_dossier(source: Path, candidate: Path, *, source_sha256: str) -> dict:
    """Regenerate exact trial plan from independently replayed native GMP."""
    source = _validate_input(Path(source))
    candidate = Path(candidate).expanduser().resolve(strict=True)
    pin = _pin(source_sha256)
    receipt = verify_saved_plan(source, candidate, source_sha256=pin)
    if (receipt["all_candidate_bytes_replayed"] is not True
            or receipt["runtime_game_verified"] is not False
            or receipt["native_actor_exports_deleted"] is not False
            or receipt["game_installation_modified"] is not False):
        raise ValueError("Native GMP receipt did not prove isolated binary replay")
    manifest = _read_json(_manifest_path(candidate), suffix=".dx2ed-native-prop-plan.json")
    plan = manifest["plan"]
    compilation, generated = compile_in_memory(
        source, source_sha256=pin, plan=plan)
    if generated != candidate.read_bytes() or receipt["output_sha256"] != sha256(generated):
        raise ValueError("Trial candidate whole-file replay failed")
    if sha256(source.read_bytes()) != pin:
        raise ValueError("Original GMP changed during independent trial compilation")
    dossier = {
        "schema": SCHEMA,
        "source_file": source.name,
        "source_sha256": pin,
        "source_size": source.stat().st_size,
        "candidate_sha256": receipt["output_sha256"],
        "candidate_size": len(generated),
        "native_plan": compilation["plan"],
        "operation_counts": {
            "moves": len(compilation["moved"]),
            "copies": len(compilation["copied"]),
            "unplaces": len(compilation["unplaced"]),
        },
        "checks": _checklist(compilation["plan"], compilation),
        "automated_whole_gmp_byte_replay_verified": True,
        "game_installation_modified": False,
        "gameplay_runtime_verified": False,
        "observations_independently_verified": False,
        "includes_retail_game_assets": False,
        "installation_automated": False,
        "instructions": (
            "Manually test ONLY a disposable backed-up retail game copy. "
            "Never overwrite your original GMP or savegames; restore sources "
            "and record results yourself. This tool NEVER runs or installs the game."
        ),
    }
    if len(json.dumps(dossier, ensure_ascii=True).encode()) > MAX_JSON:
        raise ValueError("Trial dossier exceeds output limit")
    return dossier


def _empty_observations(dossier: dict) -> dict:
    return {
        "schema": OBSERVATIONS_SCHEMA,
        "source_sha256": dossier["source_sha256"],
        "candidate_sha256": dossier["candidate_sha256"],
        "results": [{"id": row["id"], "result": "not-tested",
                     "note": "", "evidence_sha256": None}
                    for row in dossier["checks"]],
        "reported_by_owner_only": True,
        "gameplay_runtime_verified": False,
        "warnings": "Fill each result manually after testing a backed-up disposable copy; this is not independent verification.",
    }


def prepare(source: Path, candidate: Path, dossier_path: Path, *,
            source_sha256: str) -> dict:
    source = _validate_input(Path(source))
    candidate = Path(candidate).expanduser().resolve(strict=True)
    dossier_path, observations_path = _output_paths(dossier_path, source, candidate)
    doc = expected_dossier(source, candidate, source_sha256=source_sha256)
    observations = _empty_observations(doc)
    dossier_path.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        for dest, payload in ((dossier_path, doc), (observations_path, observations)):
            blob = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
            if len(blob.encode("utf-8")) > MAX_JSON:
                raise ValueError("Trial JSON exceeds output limit")
            with dest.open("x", encoding="utf-8") as f:
                created.append(dest)
                f.write(blob)
        if (_read_json(dossier_path, suffix=".dx2trial.json") != doc
                or _read_json(observations_path, suffix=".dx2observations.json") != observations):
            raise ValueError("Trial dossier could not be reread exactly")
    except Exception:
        for dest in created:
            dest.unlink(missing_ok=True)
        raise
    return {
        "schema": SCHEMA,
        "status": "private-trial-dossier-created-runtime-not-tested",
        "dossier_file": str(dossier_path),
        "observations_file": str(observations_path),
        "candidate_sha256": doc["candidate_sha256"],
        "checks_count": len(doc["checks"]),
        "automated_whole_gmp_byte_replay_verified": True,
        "game_installation_modified": False,
        "gameplay_runtime_verified": False,
    }


def assess(source: Path, candidate: Path, dossier_path: Path,
           observations_path: Path, *, source_sha256: str) -> dict:
    doc = _read_json(dossier_path, suffix=".dx2trial.json")
    exact = expected_dossier(source, candidate, source_sha256=source_sha256)
    if doc != exact:
        raise ValueError("Trial dossier differs from original-reconstructed candidate")
    observed = _read_json(observations_path, suffix=".dx2observations.json")
    if (set(observed) != {
            "schema", "source_sha256", "candidate_sha256", "results",
            "reported_by_owner_only", "gameplay_runtime_verified", "warnings"}
            or observed["schema"] != OBSERVATIONS_SCHEMA
            or observed["source_sha256"] != exact["source_sha256"]
            or observed["candidate_sha256"] != exact["candidate_sha256"]
            or observed["reported_by_owner_only"] is not True
            or observed["gameplay_runtime_verified"] is not False
            or not isinstance(observed["warnings"], str)
            or type(observed["results"]) is not list
            or len(observed["results"]) != len(exact["checks"])):
        raise ValueError("Observation log schema/hash or no-runtime-proof flags invalid")
    counts = {"pass": 0, "fail": 0, "inconclusive": 0, "not-tested": 0}
    for original, row in zip(exact["checks"], observed["results"]):
        if (type(row) is not dict
                or set(row) != {"id", "result", "note", "evidence_sha256"}
                or row["id"] != original["id"]
                or row["result"] not in counts
                or type(row["note"]) is not str or len(row["note"]) > 1000
                or not (
                    row["evidence_sha256"] is None
                    or type(row["evidence_sha256"]) is str and
                    bool(re.fullmatch(r"[0-9a-f]{64}", row["evidence_sha256"]))
                )):
            raise ValueError("Observation row fails strict trial ID/status/evidence schema")
        counts[row["result"]] += 1
    if counts["fail"]:
        status = "owner-reported-issues-runtime-unverified"
    elif counts["not-tested"] or counts["inconclusive"]:
        status = "owner-trial-incomplete-runtime-unverified"
    else:
        status = "owner-reported-all-checks-pass-not-independently-verified"
    return {
        "schema": SCHEMA, "status": status,
        "source_sha256": exact["source_sha256"],
        "candidate_sha256": exact["candidate_sha256"],
        "check_counts": counts,
        "automated_whole_gmp_byte_replay_verified": True,
        "game_installation_modified": False,
        "gameplay_runtime_verified": False,
        "observations_independently_verified": False,
        "actor_to_script_binding_verified": False,
        "safe_native_unplace_certified": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--dossier", required=True, type=Path)
    p.add_argument("--observations", type=Path, help="Existing manually edited observations JSON; only with --assess")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true", help="Create new private, no-retail dossier and blank observation log")
    group.add_argument("--assess", action="store_true", help="Read-only assessment, DOES NOT claim runtime verification")
    args = p.parse_args(argv)
    try:
        if args.prepare:
            if args.observations is not None:
                raise ValueError("--prepare does not accept --observations")
            result = prepare(args.source, args.candidate, args.dossier,
                             source_sha256=args.source_sha256)
        else:
            if args.observations is None:
                raise ValueError("--assess requires --observations")
            result = assess(args.source, args.candidate, args.dossier,
                            args.observations, source_sha256=args.source_sha256)
    except Exception as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "refused",
            "reason": str(exc) or type(exc).__name__,
            "game_installation_modified": False,
            "gameplay_runtime_verified": False,
        }))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
