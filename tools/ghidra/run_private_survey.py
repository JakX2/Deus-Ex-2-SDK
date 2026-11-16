#!/usr/bin/env python3
"""Run original DX2 PE analysis on a PRIVATE machine with local Ghidra.

Does not copy game assets to GitHub. All subprocess output is captured;
only allowlisted keyword counts / code addresses reach the final JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SCHEMA = "DX2-GhidraSurvey-v1"
SUMMARY_SCHEMA = "DX2-GhidraPrivateSummary-v1"
TERMS = (
    ".gmp", ".ibd", "staticmeshactor", "gamesys", "triggerscript",
    "serialize", "deserialize", "loadpackage", "bsp", "collision",
    "door", "vending", "havok",
)
SCRIPT = Path(__file__).resolve().parent / "scripts" / "Dx2SymbolSurvey.java"
REPO = Path(__file__).resolve().parents[2]
MAX_INPUTS = 8
MAX_MANIFEST_SIZE = 16 * 1024
MAX_PE_SIZE = 192 * 1024 * 1024
MAX_REPORT_SIZE = 2 * 1024 * 1024
FUNCTION_ADDRESS = re.compile(r"[0-9a-fA-F:]{1,32}\Z")
MAX_FUNCTIONS_PER_TOPIC = 24


class PrivateSurveyError(ValueError):
    """Deliberately does not embed original binary paths in messages."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path: Path) -> list[Path]:
    path = Path(path)
    if (not path.is_file() or path.is_symlink()
            or not 0 < path.stat().st_size <= MAX_MANIFEST_SIZE):
        raise PrivateSurveyError("Invalid private target manifest")
    paths = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        target = Path(item)
        if not target.is_absolute():
            raise PrivateSurveyError("Manifest targets must be absolute paths")
        try:
            source = target.resolve(strict=True)
        except OSError as exc:
            raise PrivateSurveyError("A private binary does not exist") from exc
        if (not source.is_file() or target.is_symlink()
                or source.suffix.lower() not in (".exe", ".dll")
                or not 128 <= source.stat().st_size <= MAX_PE_SIZE):
            raise PrivateSurveyError("Target must be a private PE .exe/.dll within size limits")
        with source.open("rb") as stream:
            if stream.read(2) != b"MZ":
                raise PrivateSurveyError("Target is not a Windows PE image")
        if source in paths:
            raise PrivateSurveyError("Duplicate private PE target")
        paths.append(source)
        if len(paths) > MAX_INPUTS:
            raise PrivateSurveyError("At most eight private PE targets per run")
    if not paths:
        raise PrivateSurveyError("No private PE targets in manifest")
    return paths


def headless_binary(ghidra_home: Path) -> Path:
    try:
        root = Path(ghidra_home).resolve(strict=True)
    except OSError as exc:
        raise PrivateSurveyError("Ghidra installation root unavailable") from exc
    filename = "analyzeHeadless.bat" if os.name == "nt" else "analyzeHeadless"
    launcher = root / "support" / filename
    if not launcher.is_file():
        raise PrivateSurveyError("Ghidra headless launcher not found")
    if os.name != "nt" and not os.access(launcher, os.X_OK):
        raise PrivateSurveyError("Ghidra headless launcher is not executable")
    if not SCRIPT.is_file():
        raise PrivateSurveyError("DX2 script missing from source checkout")
    return launcher


def sanitize_report(raw: dict, *, digest: str, role: str) -> dict:
    if (type(raw) is not dict or raw.get("schema") != SCHEMA
            or type(raw.get("function_count")) is not int
            or not 0 <= raw["function_count"] <= 50_000_000
            or type(raw.get("defined_data_scanned")) is not int
            or not 0 <= raw["defined_data_scanned"] <= 500_000
            or type(raw.get("scan_limit_reached")) is not bool
            or raw.get("raw_strings_exported") is not False
            or raw.get("decompiled_code_exported") is not False
            or raw.get("engine_runtime_verified") is not False
            or type(raw.get("processor")) is not str
            or not re.fullmatch(r"[A-Za-z0-9:._-]{1,80}", raw["processor"])
            or type(raw.get("keywords")) is not list
            or len(raw["keywords"]) != len(TERMS)):
        raise PrivateSurveyError("Ghidra report schema or bounded scan invalid")
    indexed = {}
    for row in raw["keywords"]:
        if (type(row) is not dict or set(row) != {
                "term", "defined_literal_hits", "candidate_functions"}
                or row["term"] not in TERMS or row["term"] in indexed
                or type(row["defined_literal_hits"]) is not int
                or not 0 <= row["defined_literal_hits"] <= 500_000
                or type(row["candidate_functions"]) is not list
                or len(row["candidate_functions"]) > MAX_FUNCTIONS_PER_TOPIC
                or len(set(map(str, row["candidate_functions"]))) != len(row["candidate_functions"])):
            raise PrivateSurveyError("Ghidra keyword evidence malformed")
        for address in row["candidate_functions"]:
            if type(address) is not str or not FUNCTION_ADDRESS.fullmatch(address):
                raise PrivateSurveyError("Ghidra function address malformed")
        indexed[row["term"]] = row
    if set(indexed) != set(TERMS):
        raise PrivateSurveyError("Ghidra keyword allowlist mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or role not in ("EXE", "DLL"):
        raise PrivateSurveyError("Target fingerprint/role invalid")
    # Reconstruct the report from exactly allowed primitive fields. No binary
    # paths, disassembly, Ghidra logs or raw string text can pass this gate.
    return {
        "schema": SUMMARY_SCHEMA,
        "pe_sha256": digest,
        "pe_role": role,
        "processor": raw["processor"],
        "function_count": raw["function_count"],
        "defined_data_scanned": raw["defined_data_scanned"],
        "scan_limit_reached": raw["scan_limit_reached"],
        "keyword_evidence": [
            {
                "term": term,
                "defined_literal_hits": indexed[term]["defined_literal_hits"],
                "candidate_function_addresses": list(indexed[term]["candidate_functions"]),
            }
            for term in TERMS
        ],
        "native_writer_ready": False,
        "retail_runtime_verified": False,
        "game_assets_included": False,
    }


def run_survey(sources: list[Path], ghidra_home: Path, report_dir: Path,
               *, runner=subprocess.run) -> dict:
    if not sources or len(sources) > MAX_INPUTS:
        raise PrivateSurveyError("Invalid private target count")
    if len(set(sources)) != len(sources):
        raise PrivateSurveyError("Duplicate original binary")
    destination = Path(report_dir).resolve()
    if destination == REPO or REPO in destination.parents:
        raise PrivateSurveyError("Private Ghidra output must stay outside the repository")
    for source in sources:
        if destination == source.parent or source.parent in destination.parents:
            raise PrivateSurveyError("Private Ghidra output cannot be written into the game folder")
    executable = headless_binary(ghidra_home)
    destination.mkdir(parents=True, exist_ok=True)
    final_report = destination / "dx2_research_summary.json"
    if final_report.exists():
        raise PrivateSurveyError("Refusing to overwrite existing private summary")
    summaries = []
    for source in sources:
        digest = _sha256(source)
        with tempfile.TemporaryDirectory(prefix="dx2-ghidra-") as temporary:
            work = Path(temporary)
            report = work / "survey.json"
            project = work / "projects"
            project.mkdir()
            command = [
                str(executable), str(project), "DX2PrivateSurvey",
                "-import", str(source),
                "-scriptPath", str(SCRIPT.parent),
                "-postScript", SCRIPT.name, str(report),
                "-analysisTimeoutPerFile", "900",
                "-max-cpu", "2", "-deleteProject",
            ]
            try:
                execution = runner(command, capture_output=True, text=True,
                                   timeout=1100, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise PrivateSurveyError(
                    "Headless Ghidra did not complete; inspect the private runner") from exc
            if execution.returncode != 0 or not report.is_file():
                # Never print stdout, stderr, command lines or full local paths:
                # Ghidra logs may include private install paths or raw strings.
                raise PrivateSurveyError(
                    "Headless survey failed; review logs on the private runner")
            if not 0 < report.stat().st_size <= MAX_REPORT_SIZE:
                raise PrivateSurveyError("Ghidra summary is empty or oversized")
            try:
                parsed = json.loads(report.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise PrivateSurveyError("Ghidra report is not valid JSON") from exc
            summaries.append(sanitize_report(
                parsed, digest=digest,
                role="EXE" if source.suffix.lower() == ".exe" else "DLL"))
    result = {
        "schema": SUMMARY_SCHEMA,
        "target_count": len(summaries),
        "reports": summaries,
        "game_assets_included": False,
        "retail_runtime_verified": False,
        "source_assets_modified": False,
    }
    with final_report.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2, sort_keys=True, allow_nan=False)
        out.write("\n")
    try:
        final_report.chmod(0o600)
    except OSError:
        pass  # Windows permissions come from the private runner ACL.
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True,
                        help="Private local text file: one absolute EXE/DLL path per line")
    parser.add_argument("--ghidra-home", type=Path,
                        default=os.environ.get("GHIDRA_INSTALL_DIR", ""))
    parser.add_argument("--report-dir", type=Path,
                        help="Private output outside repository and game installation")
    parser.add_argument("--check-inputs-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        sources = load_manifest(args.manifest)
        if args.check_inputs_only:
            print(json.dumps({"status": "private-inputs-valid",
                              "target_count": len(sources),
                              "analysis_performed": False}))
            return 0
        if args.report_dir is None or not str(args.ghidra_home):
            raise PrivateSurveyError("--report-dir and --ghidra-home required")
        report = run_survey(sources, args.ghidra_home, args.report_dir)
        print(json.dumps({"status": "private-survey-finished",
                          "targets": report["target_count"],
                          "game_assets_included": False,
                          "retail_runtime_verified": False}))
        return 0
    except (OSError, ValueError) as exc:
        # No file system paths or raw Ghidra diagnostics in hosted CI logs.
        reason = (str(exc) if isinstance(exc, PrivateSurveyError)
                  else "Private local file or report error; inspect runner")
        print(json.dumps({"status": "refused", "reason": reason,
                          "game_assets_included": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
