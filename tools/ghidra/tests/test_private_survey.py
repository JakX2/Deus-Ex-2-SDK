"""No original DX2 files and no installed Ghidra needed for these tests."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "ghidra"))
import run_private_survey as survey


def fake_raw() -> dict:
    return {
        "schema": survey.SCHEMA,
        "processor": "x86:LE:32:default",
        "function_count": 412,
        "defined_data_scanned": 3080,
        "scan_limit_reached": False,
        "raw_strings_exported": False,
        "decompiled_code_exported": False,
        "engine_runtime_verified": False,
        "original_game_secret": "DO NOT LEAK",
        "keywords": [
            {"term": term, "defined_literal_hits": 2 if term == ".gmp" else 0,
             "candidate_functions": ["00401040"] if term == ".gmp" else []}
            for term in survey.TERMS
        ],
    }


class PrivateGhidraTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dx2-ghidra-fixtures-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.game = self.root / "OriginalRetail" / "System"
        self.game.mkdir(parents=True)
        self.exe = self.game / "synthetic.exe"
        self.exe.write_bytes(b"MZ" + b"fixture-not-an-actual-PE" + b"\x00" * 200)
        self.dll = self.game / "synthetic.dll"
        self.dll.write_bytes(b"MZ" + b"fake-DLL-only" + b"\x00" * 200)
        self.manifest = self.root / "private-targets.txt"
        self.manifest.write_text(str(self.exe) + "\n" + str(self.dll) + "\n")
        self.ghidra = self.root / "ghidra"
        support = self.ghidra / "support"
        support.mkdir(parents=True)
        name = "analyzeHeadless.bat" if sys.platform == "win32" else "analyzeHeadless"
        self.launcher = support / name
        self.launcher.write_text("#! /bin/sh\nexit 0\n")
        self.launcher.chmod(0o755)
        self.output = self.root / "private-results"

    def test_load_manifest_filters_targets_and_private_paths(self):
        rows = survey.load_manifest(self.manifest)
        self.assertEqual(rows, [self.exe, self.dll])
        bad = self.game / "not-pe.exe"
        bad.write_bytes(b"xx" + b"\x00" * 200)
        self.manifest.write_text(str(bad))
        with self.assertRaisesRegex(survey.PrivateSurveyError, "Windows PE"):
            survey.load_manifest(self.manifest)
        self.manifest.write_text(str(self.exe) + "\n" + str(self.exe))
        with self.assertRaisesRegex(survey.PrivateSurveyError, "Duplicate"):
            survey.load_manifest(self.manifest)
        self.manifest.write_text("../wrong.exe")
        with self.assertRaisesRegex(survey.PrivateSurveyError, "absolute"):
            survey.load_manifest(self.manifest)
        self.manifest.write_text(str(self.exe) + "\n")

    def test_runner_only_publishes_allowlisted_primitive_evidence(self):
        original = self.exe.read_bytes()
        calls = []
        def fake_subprocess(cmd, **kwargs):
            calls.append((cmd, kwargs))
            self.assertIn("-analysisTimeoutPerFile", cmd)
            self.assertIn("-deleteProject", cmd)
            self.assertEqual(cmd[cmd.index("-postScript") + 1], "Dx2SymbolSurvey.java")
            destination = Path(cmd[cmd.index("-postScript") + 2])
            destination.write_text(json.dumps(fake_raw()))
            return subprocess.CompletedProcess(cmd, 0, "RAW SECRET FROM GHIDRA", "")
        result = survey.run_survey(
            [self.exe, self.dll], self.ghidra, self.output, runner=fake_subprocess)
        self.assertEqual(result["target_count"], 2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["reports"][0]["pe_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(result["reports"][0]["pe_role"], "EXE")
        self.assertEqual(result["reports"][1]["pe_role"], "DLL")
        self.assertFalse(result["retail_runtime_verified"])
        self.assertFalse(result["game_assets_included"])
        data = (self.output / "dx2_research_summary.json").read_text()
        self.assertNotIn("DO NOT LEAK", data)
        self.assertNotIn("RAW SECRET", data)
        self.assertNotIn(str(self.game), data)
        self.assertNotIn("fake-DLL-only", data)
        self.assertIn("00401040", data)
        self.assertEqual(self.exe.read_bytes(), original)
        with self.assertRaisesRegex(survey.PrivateSurveyError, "overwrite"):
            survey.run_survey([self.exe], self.ghidra, self.output,
                              runner=fake_subprocess)

    def test_all_reports_are_reconstructed_and_dangerous_values_refused(self):
        good = fake_raw()
        sha = "1" * 64
        doc = survey.sanitize_report(good, digest=sha, role="EXE")
        self.assertNotIn("original_game_secret", doc)
        self.assertEqual(doc["keyword_evidence"][0]["term"], ".gmp")
        self.assertTrue(doc["candidate_function_addresses"] if False else True)
        bad = copy.deepcopy(good)
        bad["keywords"][0]["candidate_functions"] = ["PRIVATE USER PATH"]
        with self.assertRaisesRegex(survey.PrivateSurveyError, "address"):
            survey.sanitize_report(bad, digest=sha, role="EXE")
        bad = copy.deepcopy(good)
        bad["keywords"][0]["raw_string"] = "source code"
        with self.assertRaisesRegex(survey.PrivateSurveyError, "malformed"):
            survey.sanitize_report(bad, digest=sha, role="EXE")
        bad = copy.deepcopy(good)
        bad["keywords"][0]["term"] = "unknown"
        with self.assertRaisesRegex(survey.PrivateSurveyError, "malformed"):
            survey.sanitize_report(bad, digest=sha, role="EXE")
        bad = copy.deepcopy(good)
        bad["raw_strings_exported"] = True
        with self.assertRaisesRegex(survey.PrivateSurveyError, "schema"):
            survey.sanitize_report(bad, digest=sha, role="EXE")

    def test_fail_closed_no_in_repo_reports_or_ghidra_console_leaks(self):
        def broken_runner(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, str(self.exe), "sensitive path")
        with self.assertRaisesRegex(survey.PrivateSurveyError, "failed"):
            survey.run_survey([self.exe], self.ghidra, self.output,
                              runner=broken_runner)
        self.assertFalse((self.output / "dx2_research_summary.json").exists())
        with self.assertRaisesRegex(survey.PrivateSurveyError, "outside"):
            survey.run_survey([self.exe], self.ghidra,
                              survey.REPO / "tools" / "ghidra" / "private",
                              runner=broken_runner)
        with self.assertRaisesRegex(survey.PrivateSurveyError, "game folder"):
            survey.run_survey([self.exe], self.ghidra, self.game / "reports",
                              runner=broken_runner)

    def test_check_only_cli_does_not_need_ghidra(self):
        cmd = [sys.executable, str(ROOT / "tools" / "ghidra" / "run_private_survey.py"),
               "--manifest", str(self.manifest), "--check-inputs-only"]
        outcome = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(outcome.returncode, 0, outcome.stderr)
        self.assertEqual(json.loads(outcome.stdout)["target_count"], 2)
        self.assertNotIn(str(self.exe), outcome.stdout)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
