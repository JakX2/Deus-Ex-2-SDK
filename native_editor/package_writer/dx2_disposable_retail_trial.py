#!/usr/bin/env python3
"""DX2Ed v0.65: reversible GMP A/B trial in an EXPLICITLY named test copy.

NEVER touch an original retail game folder. The selected directory must be
named exactly "DX2Ed_Disposable_Test", be separate from the original source,
already contain a copy of the original GMP, and have a System directory.
The user must acknowledge the disposable copy before stage. No game launch
or game process management. Only ONE existing GMP is touched, with an
independent intact rollback backup and a durable journal.

This is a human-controlled research tool, not a mod installer or game test
certification. All native candidate bytes are reconstructed from the exact
original GMP before any staging.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dx2_retail_trial_dossier import expected_dossier
from dx2_package_roundtrip import _validate_input, sha256

SCHEMA = "DX2Ed-disposable-retail-static-prop-trial-v1"
ROOT_NAME = "DX2Ed_Disposable_Test"
STATE_FOLDER = ".dx2ed-retail-trial-v1"
JOURNAL_NAME = "state.json"
BACKUP_NAME = "original-map.gmp"
ACK = "YES_DISPOSABLE_TEST_COPY"
MAX_JOURNAL_SIZE = 16 * 1024

STATE_FIELDS = {
    "schema", "status", "source_file", "source_sha256",
    "candidate_sha256", "candidate_size", "trial_id",
    "backed_up_original_sha256", "game_runtime_verified",
    "source_original_modified", "manual_test_required",
}


def _canonical(value: Path, *, must_exist: bool = True) -> Path:
    path = Path(value).expanduser()
    path = path.resolve(strict=must_exist)
    if not must_exist and path.exists():
        raise FileExistsError("Refusing to overwrite pre-existing trial file")
    return path


def _test_root(root: Path, source: Path | None = None,
               candidate: Path | None = None) -> tuple[Path, Path]:
    root = _canonical(root)
    if not root.is_dir() or root.name != ROOT_NAME:
        raise ValueError("Only a separate game copy named DX2Ed_Disposable_Test is allowed")
    if not (root / "System").is_dir():
        raise ValueError("Disposable game copy must have a real System directory")
    maps = root / "Content" / "DX2" / "Maps"
    if not maps.is_dir() or maps.resolve(strict=True) != maps:
        raise ValueError("Disposable map folder missing or redirected through symlink")
    if (root / "System").resolve(strict=True) != root / "System":
        raise ValueError("Disposable game System directory is symlinked")
    for other in (source, candidate):
        if other is None:
            continue
        other = _canonical(other)
        # A source/candidate *inside* the test folder, a test folder
        # *inside* the original maps directory, or common path alias
        # is always invalid. This guards accidental original installs.
        if (other == root or root in other.parents
                or root == other.parent or other.parent in root.parents):
            raise ValueError("Original source and candidate must be outside the disposable game copy")
    return root, maps


def _target(root: Path, source_name: str) -> Path:
    if (not isinstance(source_name, str) or not source_name.lower().endswith(".gmp")
            or source_name in ("", ".", "..") or Path(source_name).name != source_name):
        raise ValueError("Invalid original GMP basename in trial receipt")
    path = root / "Content" / "DX2" / "Maps" / source_name
    if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
        raise ValueError("Disposable game MUST already contain a real original GMP, not a symlink")
    return path


def _private_paths(root: Path) -> tuple[Path, Path, Path]:
    folder = root / STATE_FOLDER
    return folder, folder / JOURNAL_NAME, folder / BACKUP_NAME


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_state(root: Path) -> tuple[dict, Path, Path]:
    folder, journal, backup = _private_paths(root)
    if (not folder.is_dir() or folder.is_symlink()
            or folder.resolve(strict=True) != folder
            or not journal.is_file() or journal.is_symlink()
            or not backup.is_file() or backup.is_symlink()):
        raise ValueError("Disposable trial receipt/rollback backup is missing or redirected")
    if not 0 < journal.stat().st_size <= MAX_JOURNAL_SIZE:
        raise ValueError("Disposable trial receipt is missing or oversized")
    doc = json.loads(journal.read_text(encoding="utf-8"))
    if (type(doc) is not dict or set(doc) != STATE_FIELDS
            or doc["schema"] != SCHEMA
            or doc["status"] not in ("prepared", "staging", "staged",
                                    "restoring", "restored")
            or doc["game_runtime_verified"] is not False
            or doc["source_original_modified"] is not False
            or doc["manual_test_required"] is not True
            or not isinstance(doc["trial_id"], str)
            or len(doc["trial_id"]) != 24
            or any(c not in "0123456789abcdef" for c in doc["trial_id"])
            or type(doc["candidate_size"]) is not int
            or doc["candidate_size"] <= 0):
        raise ValueError("Disposable trial receipt schema/status/safety flags invalid")
    for key in ("source_sha256", "candidate_sha256",
                "backed_up_original_sha256"):
        val = doc.get(key)
        if (not isinstance(val, str) or len(val) != 64
                or any(c not in "0123456789abcdef" for c in val)):
            raise ValueError("Invalid disposable trial SHA-256")
    if doc["backed_up_original_sha256"] != doc["source_sha256"]:
        raise ValueError("Backup source digest conflicts with original source")
    target = _target(root, doc["source_file"])
    if _hash_file(backup) != doc["source_sha256"]:
        raise ValueError("Trial backup digest mismatch: DO NOT continue or overwrite")
    return doc, target, journal


def _write_state(journal: Path, doc: dict) -> None:
    blob = json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if len(blob.encode("utf-8")) > MAX_JOURNAL_SIZE:
        raise ValueError("Disposable trial receipt exceeds size cap")
    # Write to new same-directory temporary and atomically rename. No
    # overwriting arbitrary owner files: only our protected, validated
    # journal path is ever replaced.
    temp = journal.with_name(JOURNAL_NAME + "." + secrets.token_hex(8) + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as f:
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, journal)
    finally:
        temp.unlink(missing_ok=True)


def _swap_target(target: Path, new_bytes: bytes) -> None:
    if not target.is_file() or target.is_symlink():
        raise ValueError("Disposable original map target disappeared/redirected")
    temp = target.with_name(target.name + "." + secrets.token_hex(8) + ".dx2tmp")
    try:
        with temp.open("xb") as f:
            f.write(new_bytes)
            f.flush()
            os.fsync(f.fileno())
        if temp.stat().st_size != len(new_bytes) or temp.read_bytes() != new_bytes:
            raise ValueError("Candidate staging temporary bytes changed")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def _receipt(doc: dict, *, phase: str, target_sha256: str) -> dict:
    return {
        "schema": SCHEMA,
        "status": phase,
        "trial_id": doc["trial_id"],
        "source_sha256": doc["source_sha256"],
        "candidate_sha256": doc["candidate_sha256"],
        "disposable_target_sha256": target_sha256,
        "game_runtime_verified": False,
        "source_original_modified": False,
        "manual_game_testing_required": True,
    }


def prepare(source: Path, candidate: Path, test_root: Path, *,
            source_sha256: str) -> dict:
    source = _validate_input(Path(source))
    candidate = _canonical(candidate)
    root, _ = _test_root(test_root, source, candidate)
    target = _target(root, source.name)
    folder, journal, backup = _private_paths(root)
    if folder.exists() or journal.exists() or backup.exists():
        raise FileExistsError("A trial already exists: inspect/restore; never overwrite its backup")
    dossier = expected_dossier(source, candidate, source_sha256=source_sha256)
    original = source.read_bytes()
    if (target.read_bytes() != original
            or _hash_file(target) != source_sha256):
        raise ValueError("Disposable map is NOT byte-identical to the verified original GMP")
    state = {
        "schema": SCHEMA, "status": "prepared",
        "source_file": source.name, "source_sha256": dossier["source_sha256"],
        "candidate_sha256": dossier["candidate_sha256"],
        "candidate_size": dossier["candidate_size"],
        "trial_id": secrets.token_hex(12),
        "backed_up_original_sha256": dossier["source_sha256"],
        "game_runtime_verified": False,
        "source_original_modified": False,
        "manual_test_required": True,
    }
    folder.mkdir()  # exclusive; no existing journal/backup is touched
    try:
        with backup.open("xb") as f:
            f.write(original)
            f.flush()
            os.fsync(f.fileno())
        if backup.read_bytes() != original or _hash_file(target) != source_sha256:
            raise ValueError("Backup or disposable map changed before trial receipt")
        with journal.open("x", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        # Keep any successfully written backup, even after an error.
        # Never automatically delete rollback evidence.
        raise
    return _receipt(state, phase="prepared-original-map-untouched",
                    target_sha256=_hash_file(target))


def stage(source: Path, candidate: Path, test_root: Path, *,
          source_sha256: str, acknowledgement: str) -> dict:
    if acknowledgement != ACK:
        raise ValueError("Staging requires --acknowledge YES_DISPOSABLE_TEST_COPY")
    source = _validate_input(Path(source))
    candidate = _canonical(candidate)
    root, _ = _test_root(test_root, source, candidate)
    doc, target, journal = _read_state(root)
    if (doc["status"] not in ("prepared", "staging")
            or doc["source_file"] != source.name
            or doc["source_sha256"] != source_sha256):
        raise ValueError("Cannot stage: receipt not prepared or source does not match")
    dossier = expected_dossier(source, candidate, source_sha256=source_sha256)
    if (dossier["candidate_sha256"] != doc["candidate_sha256"]
            or dossier["candidate_size"] != doc["candidate_size"]):
        raise ValueError("Isolated GMP candidate no longer matches frozen trial receipt")
    present = _hash_file(target)
    if present == doc["candidate_sha256"] and doc["status"] == "staging":
        doc["status"] = "staged"  # recovery from interruption after atomic copy
        _write_state(journal, doc)
        return _receipt(doc, phase="staged-disposable-game-copy-only",
                        target_sha256=present)
    if present != doc["source_sha256"]:
        raise ValueError("Test map changed unexpectedly; refuse to overwrite")
    doc["status"] = "staging"
    _write_state(journal, doc)
    # Check immediately before replacement; race with the running game is
    # not avoidable using a portable Python file operation, so the user
    # must explicitly close the game before staging or restoring.
    if _hash_file(target) != doc["source_sha256"]:
        raise ValueError("Test map changed after staging receipt; manual review required")
    _swap_target(target, candidate.read_bytes())
    if _hash_file(target) != doc["candidate_sha256"]:
        raise ValueError("Staged test map bytes do not match native recipe")
    doc["status"] = "staged"
    _write_state(journal, doc)
    return _receipt(doc, phase="staged-disposable-game-copy-only",
                    target_sha256=_hash_file(target))


def restore(test_root: Path) -> dict:
    root, _ = _test_root(test_root)
    doc, target, journal = _read_state(root)
    if doc["status"] not in ("staged", "staging", "restoring", "restored"):
        raise ValueError("No staged GMP to restore; original disposable map is untouched")
    observed = _hash_file(target)
    if observed not in (doc["candidate_sha256"], doc["source_sha256"]):
        raise ValueError("Disposable map changed since stage: refuse to overwrite unknown data")
    if observed == doc["source_sha256"]:
        doc["status"] = "restored"
        _write_state(journal, doc)
        return _receipt(doc, phase="restored-original-gmp-in-disposable-copy",
                        target_sha256=observed)
    doc["status"] = "restoring"
    _write_state(journal, doc)
    _, _, backup = _private_paths(root)
    data = backup.read_bytes()
    if sha256(data) != doc["source_sha256"]:
        raise ValueError("Rollback original changed; refuse to restore unverified data")
    if _hash_file(target) != doc["candidate_sha256"]:
        raise ValueError("Test map changed after restore receipt; manual review required")
    _swap_target(target, data)
    if _hash_file(target) != doc["source_sha256"]:
        raise ValueError("Rollback failed digest verification; manual review required")
    doc["status"] = "restored"
    _write_state(journal, doc)
    return _receipt(doc, phase="restored-original-gmp-in-disposable-copy",
                    target_sha256=_hash_file(target))


def status(test_root: Path) -> dict:
    root, _ = _test_root(test_root)
    doc, target, _ = _read_state(root)
    present = _hash_file(target)
    phase = (
        "matches-original" if present == doc["source_sha256"] else
        "matches-candidate" if present == doc["candidate_sha256"] else
        "unexpected-content-do-not-overwrite"
    )
    result = _receipt(doc, phase=doc["status"], target_sha256=present)
    result["target_content"] = phase
    result["rollback_backup_verified"] = True
    result["trial_phase_consistent"] = (
        (doc["status"] in ("prepared", "restored") and phase == "matches-original")
        or (doc["status"] == "staged" and phase == "matches-candidate")
        or (doc["status"] in ("staging", "restoring") and
            phase in ("matches-original", "matches-candidate"))
    )
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--test-root", type=Path, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare", action="store_true")
    g.add_argument("--stage", action="store_true")
    g.add_argument("--restore", action="store_true")
    g.add_argument("--status", action="store_true")
    p.add_argument("--source", type=Path)
    p.add_argument("--candidate", type=Path)
    p.add_argument("--source-sha256")
    p.add_argument("--acknowledge")
    args = p.parse_args(argv)
    try:
        if args.prepare or args.stage:
            if (args.source is None or args.candidate is None
                    or args.source_sha256 is None):
                raise ValueError("Prepare/stage need --source --candidate --source-sha256")
            kw = {"source_sha256": args.source_sha256}
            if args.stage:
                result = stage(args.source, args.candidate, args.test_root,
                               acknowledgement=args.acknowledge, **kw)
            else:
                if args.acknowledge is not None:
                    raise ValueError("Prepare doesn't install GMP; omit acknowledgement")
                result = prepare(args.source, args.candidate, args.test_root, **kw)
        else:
            if (args.source is not None or args.candidate is not None
                    or args.source_sha256 is not None or args.acknowledge is not None):
                raise ValueError("Status/restore need only --test-root")
            result = restore(args.test_root) if args.restore else status(args.test_root)
    except Exception as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "refused",
            "reason": str(exc) or type(exc).__name__,
            "game_runtime_verified": False,
            "source_original_modified": False,
        }))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
