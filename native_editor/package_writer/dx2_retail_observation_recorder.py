#!/usr/bin/env python3
"""DX2Ed v0.66: guarded *human* observation recording for a disposable GMP trial.

This does not run, monitor or verify Invisible War. It cross-checks the v0.64
original-derived dossier, the manually editable observations and the v0.65
single-map test-copy journal before recording what a human says they observed.
Only the private observations JSON can be changed, never game files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_disposable_retail_trial import (
    _read_state, _test_root, status as trial_status,
)
from dx2_retail_trial_dossier import (
    _read_json, assess, MAX_JSON, OBSERVATIONS_SCHEMA,
)

SCHEMA = "DX2Ed-retail-human-observation-recorder-v1"
ACK = "OWNER_REPORTED_NOT_GAME_VERIFIED"
RESULTS = ("pass", "fail", "inconclusive", "not-tested")
CORE_CANDIDATE_CHECKS = ("candidate-load", "collision", "reentry", "save-reload")
MAX_EVIDENCE_BYTES = 512 * 1024 * 1024


def _paths(source: Path, candidate: Path, dossier: Path,
           observations: Path, test_root: Path) -> tuple[Path, Path, Path, Path, Path]:
    root, _ = _test_root(test_root, source, candidate)
    source = Path(source).expanduser().resolve(strict=True)
    candidate = Path(candidate).expanduser().resolve(strict=True)
    originals = (source.parent, candidate.parent)
    checked = []
    for path, suffix in ((dossier, ".dx2trial.json"),
                         (observations, ".dx2observations.json")):
        raw = Path(path).expanduser()
        if raw.is_symlink():
            raise ValueError("Trial JSON must be a real file, not a symlink")
        path = raw.resolve(strict=True)
        if (not path.is_file() or path.stat().st_nlink != 1
                or not path.name.endswith(suffix)
                or root == path or root in path.parents
                or any(path.parent == p or p in path.parents or
                       path.parent in p.parents for p in originals)):
            raise ValueError("Trial JSON must be private, outside game and GMP source/candidate directories")
        parts = {s.casefold() for s in path.parts}
        if {"content", "dx2", "maps"} <= parts:
            raise ValueError("Trial JSON may not live in Content/DX2/Maps")
        checked.append(path)
    dossier, observations = checked
    if (dossier.parent != observations.parent
            or observations.name !=
            dossier.name.removesuffix(".dx2trial.json") + ".dx2observations.json"):
        raise ValueError("Dossier and observation files must be a matched private pair")
    return source, candidate, dossier, observations, root


def _context(source: Path, candidate: Path, dossier: Path,
             observations: Path, root: Path, source_sha256: str) -> dict:
    # assess() regenerates the ENTIRE candidate GMP byte-for-byte, checks the
    # expected dossier and validates every observation result and fixed flag.
    assessment = assess(source, candidate, dossier, observations,
                        source_sha256=source_sha256)
    original_dossier = _read_json(dossier, suffix=".dx2trial.json")
    journal, _, _ = _read_state(root)
    if (journal["source_file"] != original_dossier["source_file"]
            or journal["source_sha256"] != assessment["source_sha256"]
            or journal["candidate_sha256"] != assessment["candidate_sha256"]
            or journal["candidate_size"] != original_dossier["candidate_size"]):
        raise ValueError("Disposable test-copy journal belongs to a DIFFERENT original/candidate")
    state = trial_status(root)
    return {"assessment": assessment, "state": state,
            "check_ids": [c["id"] for c in original_dossier["checks"]]}


def _phase_for(check_id: str) -> str:
    if check_id == "baseline":
        return "prepared"
    if check_id == "restore":
        return "restored"
    if check_id in CORE_CANDIDATE_CHECKS or check_id.startswith(
            ("move-", "clone-", "unplace-")):
        return "staged"
    raise ValueError("Unknown original-derived check ID")


def inspect(source: Path, candidate: Path, dossier: Path,
            observations: Path, test_root: Path, *,
            source_sha256: str) -> dict:
    source, candidate, dossier, observations, root = _paths(
        source, candidate, dossier, observations, test_root)
    context = _context(source, candidate, dossier, observations, root,
                       source_sha256)
    state, assessment = context["state"], context["assessment"]
    phase = state["status"]
    expected_content = {
        "prepared": "matches-original",
        "staged": "matches-candidate",
        "restored": "matches-original",
    }
    ready = (phase in expected_content
             and state["target_content"] == expected_content.get(phase)
             and state["trial_phase_consistent"])
    available = [key for key in context["check_ids"]
                 if ready and _phase_for(key) == phase]
    return {
        "schema": SCHEMA,
        "status": ("owner-reported-results-read-only" if ready
                   else "unsafe-or-incomplete-test-copy-state-read-only"),
        "trial_id": state["trial_id"],
        "trial_phase": phase,
        "test_map_content": state["target_content"],
        "rollback_backup_verified": state["rollback_backup_verified"],
        "source_sha256": assessment["source_sha256"],
        "candidate_sha256": assessment["candidate_sha256"],
        "owner_assessment": assessment["status"],
        "check_counts": assessment["check_counts"],
        "recordable_check_ids_at_current_phase": available,
        "game_installation_modified": False,
        "gameplay_runtime_verified": False,
        "observations_independently_verified": False,
        "manual_game_testing_required": True,
    }


def _evidence_digest(path: Path | None) -> str | None:
    if path is None:
        return None
    path = Path(path).expanduser()
    if path.is_symlink():
        raise ValueError("Evidence file cannot be a symlink")
    path = path.resolve(strict=True)
    if (not path.is_file() or path.stat().st_size <= 0
            or path.stat().st_size > MAX_EVIDENCE_BYTES):
        raise ValueError("Evidence must be a real nonempty file under 512 MiB")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def record(source: Path, candidate: Path, dossier: Path,
           observations: Path, test_root: Path, *, source_sha256: str,
           check_id: str, result: str, note: str,
           acknowledgement: str, evidence: Path | None = None) -> dict:
    if acknowledgement != ACK:
        raise ValueError("Recording needs --acknowledge OWNER_REPORTED_NOT_GAME_VERIFIED")
    if result not in RESULTS or not isinstance(note, str) or len(note) > 1000:
        raise ValueError("Invalid owner result or note (maximum 1000 characters)")
    if result == "not-tested":
        if note or evidence is not None:
            raise ValueError("Clearing a result requires empty note and no evidence")
    elif not note.strip():
        raise ValueError("Each human observation must include an explanatory note")
    source, candidate, dossier, observations, root = _paths(
        source, candidate, dossier, observations, test_root)
    context = _context(source, candidate, dossier, observations, root,
                       source_sha256)
    if check_id not in context["check_ids"]:
        raise ValueError("Check ID is not present in original-derived dossier")
    state = context["state"]
    if result != "not-tested":
        required_phase = _phase_for(check_id)
        required_content = ("matches-candidate" if required_phase == "staged"
                            else "matches-original")
        if (state["status"] != required_phase
                or state["target_content"] != required_content
                or not state["trial_phase_consistent"]):
            raise ValueError("Observation phase mismatch or unsafe disposable map state")
    digest = _evidence_digest(evidence) if result != "not-tested" else None
    # The existing observations file is a private data record, NEVER a game
    # resource. Source and candidate GMPs and the trial journal are read-only.
    old_bytes = observations.read_bytes()
    old_sha = hashlib.sha256(old_bytes).digest()
    old_mode = stat.S_IMODE(observations.stat().st_mode)
    document = _read_json(observations, suffix=".dx2observations.json")
    if document["schema"] != OBSERVATIONS_SCHEMA:
        raise ValueError("Wrong observation schema")
    matches = [row for row in document["results"] if row["id"] == check_id]
    if len(matches) != 1:
        raise ValueError("Cannot unambiguously identify observation")
    matches[0].update(result=result, note=note, evidence_sha256=digest)
    encoded = (json.dumps(document, indent=2, sort_keys=True,
                          ensure_ascii=True, allow_nan=False) + "\n").encode()
    if len(encoded) > MAX_JSON:
        raise ValueError("Recorded observations exceed private JSON limit")
    # Verify no other writer changed the observation file before replacement.
    if hashlib.sha256(observations.read_bytes()).digest() != old_sha:
        raise ValueError("Observations changed during record; refusing overwrite")
    temp = observations.with_name(
        observations.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        with temp.open("xb") as writer:
            writer.write(encoded)
            writer.flush()
            os.fsync(writer.fileno())
        os.chmod(temp, old_mode)
        os.replace(temp, observations)
    finally:
        temp.unlink(missing_ok=True)
    report = _context(source, candidate, dossier, observations, root,
                      source_sha256)["assessment"]
    return {
        "schema": SCHEMA,
        "status": "owner-observation-recorded-not-independently-verified",
        "check_id": check_id,
        "owner_result": result,
        "trial_phase_at_recording": state["status"],
        "evidence_sha256": digest,
        "check_counts": report["check_counts"],
        "game_installation_modified": False,
        "gameplay_runtime_verified": False,
        "observations_independently_verified": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--dossier", required=True, type=Path)
    p.add_argument("--observations", required=True, type=Path)
    p.add_argument("--test-root", required=True, type=Path)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--record", action="store_true")
    p.add_argument("--check-id")
    p.add_argument("--result", choices=RESULTS)
    p.add_argument("--note")
    p.add_argument("--evidence", type=Path)
    p.add_argument("--acknowledge")
    args = p.parse_args(argv)
    try:
        kw = dict(source_sha256=args.source_sha256)
        if args.inspect:
            if any(x is not None for x in (
                    args.check_id, args.result, args.note,
                    args.evidence, args.acknowledge)):
                raise ValueError("Inspect is read-only; omit all record options")
            report = inspect(args.source, args.candidate, args.dossier,
                             args.observations, args.test_root, **kw)
        else:
            if args.check_id is None or args.result is None or args.note is None:
                raise ValueError("Record requires --check-id --result --note")
            report = record(
                args.source, args.candidate, args.dossier, args.observations,
                args.test_root, check_id=args.check_id, result=args.result,
                note=args.note, evidence=args.evidence,
                acknowledgement=args.acknowledge, **kw)
    except Exception as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "refused",
            "reason": str(exc) or type(exc).__name__,
            "game_installation_modified": False,
            "gameplay_runtime_verified": False,
        }))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
