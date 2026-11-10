"""v0.64: only synthetic DX2 original/candidate GMP test receipts.

No retail game starts, installations, asset embeds or automatic map copying.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
for path in (
    ROOT / "native_editor" / "tests",
    ROOT / "native_editor" / "package_writer",
    ROOT / "third_party" / "t3sdk_assets",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from test_dx2_actor_clone_probe import level_fixture
from dx2_actor_clone_probe import clone_in_memory
from dx2_native_prop_plan import SCHEMA as PLAN_SCHEMA, save_isolated
from dx2_retail_trial_dossier import (
    SCHEMA, OBSERVATIONS_SCHEMA, assess, expected_dossier, prepare,
)


class RetailGmpDossierTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2ed_v064_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "Originals" / "M1_Synthetic.gmp"
        self.source.parent.mkdir()
        initial = level_fixture(self.source)
        _, cloned = clone_in_memory(
            self.source, source_sha256=hashlib.sha256(initial).hexdigest(),
            actor_export=1, actor_name="StaticMeshActor__1",
            delta=(100.0, 0.0, 0.0))
        self.source.write_bytes(cloned)
        self.original = cloned
        self.sha = hashlib.sha256(cloned).hexdigest()
        self.candidate = self.root / "Candidate" / self.source.name
        self.plan = {
            "schema": PLAN_SCHEMA,
            "moves": [{
                "actor": "StaticMeshActor__1", "export": 1,
                "delta": [20.0, 0.0, 0.0],
            }],
            "copies": [{
                "actor": "StaticMeshActor__1", "export": 1,
                "delta": [45.0, 10.0, 0.0],
            }],
            "unplaces": [{
                "actor": "StaticMeshActor__2", "export": 3,
            }],
        }
        save_isolated(self.source, self.candidate, source_sha256=self.sha,
                      plan=self.plan)
        self.candidate_binary = self.candidate.read_bytes()
        self.dossier = self.root / "PrivateTestResults" / "WTOTest.dx2trial.json"
        self.observations = self.dossier.with_name("WTOTest.dx2observations.json")

    def _prepare(self):
        return prepare(self.source, self.candidate, self.dossier,
                       source_sha256=self.sha)

    def _assess(self):
        return assess(self.source, self.candidate, self.dossier,
                      self.observations, source_sha256=self.sha)

    def test_prepare_two_content_free_files_and_operation_specific_matrix(self):
        receipt = self._prepare()
        self.assertEqual(receipt["status"],
                         "private-trial-dossier-created-runtime-not-tested")
        self.assertEqual(receipt["checks_count"], 9)
        self.assertTrue(receipt["automated_whole_gmp_byte_replay_verified"])
        self.assertFalse(receipt["game_installation_modified"])
        self.assertFalse(receipt["gameplay_runtime_verified"])
        doc = json.loads(self.dossier.read_text())
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["native_plan"], self.plan)
        self.assertEqual(doc["source_file"], self.source.name)
        self.assertEqual(doc["candidate_sha256"],
                         hashlib.sha256(self.candidate_binary).hexdigest())
        self.assertEqual(doc["operation_counts"],
                         {"moves": 1, "copies": 1, "unplaces": 1})
        self.assertEqual([x["id"] for x in doc["checks"]], [
            "baseline", "candidate-load", "collision", "reentry",
            "save-reload", "restore", "move-01", "clone-01", "unplace-01"])
        copy = next(x for x in doc["checks"] if x["id"] == "clone-01")
        self.assertEqual(copy["original_actor"], "StaticMeshActor__1")
        self.assertEqual(copy["source_export"], 1)
        self.assertEqual(copy["new_export"], 4)
        self.assertEqual(copy["expected_candidate_location_xyz"], [145, 210, 300])
        self.assertTrue(copy["new_actor"])
        self.assertNotIn(str(self.root), self.dossier.read_text())
        self.assertLess(self.dossier.stat().st_size, 10000)
        blank = json.loads(self.observations.read_text())
        self.assertEqual(blank["schema"], OBSERVATIONS_SCHEMA)
        self.assertEqual(len(blank["results"]), 9)
        self.assertTrue(all(x["result"] == "not-tested" for x in blank["results"]))
        self.assertTrue(blank["reported_by_owner_only"])
        self.assertFalse(blank["gameplay_runtime_verified"])
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.candidate.read_bytes(), self.candidate_binary)

    def test_blank_incomplete_pass_or_fail_assessment_never_verifies_runtime(self):
        self._prepare()
        blank = self._assess()
        self.assertEqual(blank["status"],
                         "owner-trial-incomplete-runtime-unverified")
        self.assertEqual(blank["check_counts"]["not-tested"], 9)
        self.assertFalse(blank["gameplay_runtime_verified"])
        obs = json.loads(self.observations.read_text())
        for row in obs["results"]:
            row["result"] = "pass"
            row["note"] = "Manually observed on a disposable original-game copy"
        self.observations.write_text(json.dumps(obs))
        positive = self._assess()
        self.assertEqual(positive["status"],
                         "owner-reported-all-checks-pass-not-independently-verified")
        self.assertEqual(positive["check_counts"]["pass"], 9)
        self.assertFalse(positive["gameplay_runtime_verified"])
        self.assertFalse(positive["observations_independently_verified"])
        self.assertFalse(positive["safe_native_unplace_certified"])
        obs["results"][2]["result"] = "fail"
        obs["results"][2]["note"] = "Unexpected leftover collision"
        self.observations.write_text(json.dumps(obs))
        issue = self._assess()
        self.assertEqual(issue["status"],
                         "owner-reported-issues-runtime-unverified")
        self.assertEqual(issue["check_counts"]["fail"], 1)
        obs["results"][2]["result"] = "inconclusive"
        self.observations.write_text(json.dumps(obs))
        uncertain = self._assess()
        self.assertEqual(uncertain["status"],
                         "owner-trial-incomplete-runtime-unverified")

    def test_refuse_forged_dossier_observations_and_bad_receipt(self):
        self._prepare()
        doc = json.loads(self.dossier.read_text())
        for change in (
            {"candidate_sha256": "f" * 64},
            {"automated_whole_gmp_byte_replay_verified": False},
            {"gameplay_runtime_verified": True},
            {"native_plan": {**doc["native_plan"], "unplaces": []}},
            {"checks": doc["checks"][:-1]},
        ):
            with self.subTest(change=change):
                self.dossier.write_text(json.dumps({**doc, **change}))
                with self.assertRaises(ValueError):
                    self._assess()
        self.dossier.write_text(json.dumps(doc))
        obs = json.loads(self.observations.read_text())
        for change in (
            {"candidate_sha256": "f" * 64},
            {"gameplay_runtime_verified": True},
            {"results": obs["results"][:-1]},
            {"reported_by_owner_only": False},
        ):
            with self.subTest(change=change):
                self.observations.write_text(json.dumps({**obs, **change}))
                with self.assertRaises(ValueError):
                    self._assess()
        bad_result = {**obs, "results": [dict(x) for x in obs["results"]]}
        bad_result["results"][0]["id"] = "clone-99"
        self.observations.write_text(json.dumps(bad_result))
        with self.assertRaises(ValueError):
            self._assess()
        self.observations.write_text(json.dumps(obs))
        manifest = self.candidate.with_suffix(".dx2ed-native-prop-plan.json")
        text = manifest.read_text()
        data = json.loads(text)
        data["output_sha256"] = "f" * 64
        manifest.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            expected_dossier(self.source, self.candidate, source_sha256=self.sha)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_refuse_bad_sha_candidate_tamper_and_original_changes(self):
        # Either the manifest source pin or the original source check
        # may reject the wrong digest; both correctly fail closed.
        with self.assertRaises(ValueError):
            expected_dossier(self.source, self.candidate,
                             source_sha256="f" * 64)
        bad = bytearray(self.candidate_binary)
        bad[-1] ^= 1
        self.candidate.write_bytes(bad)
        with self.assertRaises(ValueError):
            self._prepare()
        self.assertFalse(self.dossier.exists())
        self.candidate.write_bytes(self.candidate_binary)
        self._prepare()
        self.source.write_bytes(self.original + b"modified original")
        with self.assertRaises(ValueError):
            self._assess()

    def test_refuse_unsafe_placing_and_no_overwrite(self):
        for dest in (
            self.source.parent / "test.dx2trial.json",
            self.candidate.parent / "test.dx2trial.json",
            self.root / "Game" / "Content" / "DX2" / "Maps" / "test.dx2trial.json",
            self.root / "test.json",
        ):
            with self.subTest(dest=dest), self.assertRaises(ValueError):
                prepare(self.source, self.candidate, dest, source_sha256=self.sha)
            self.assertFalse(dest.exists())
        self._prepare()
        with self.assertRaises(FileExistsError):
            self._prepare()
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.candidate.read_bytes(), self.candidate_binary)

    def test_cli_prepare_assess_standalone_without_pythonpath(self):
        script = ROOT / "native_editor/package_writer/dx2_retail_trial_dossier.py"
        args = [
            sys.executable, str(script),
            "--source", str(self.source),
            "--candidate", str(self.candidate),
            "--source-sha256", self.sha,
            "--dossier", str(self.dossier),
        ]
        clean = dict(os.environ)
        clean.pop("PYTHONPATH", None)
        prepared = subprocess.run([*args, "--prepare"], cwd=self.root,
                                  env=clean, capture_output=True, text=True)
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        self.assertFalse(json.loads(prepared.stdout)["gameplay_runtime_verified"])
        assessed = subprocess.run([*args, "--assess",
                                   "--observations", str(self.observations)],
                                  cwd=self.root, env=clean,
                                  capture_output=True, text=True)
        self.assertEqual(assessed.returncode, 0, assessed.stdout + assessed.stderr)
        self.assertEqual(json.loads(assessed.stdout)["check_counts"]["not-tested"], 9)
        refused = subprocess.run([*args, "--prepare"], cwd=self.root,
                                 env=clean, capture_output=True, text=True)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(json.loads(refused.stdout)["status"], "refused")
        self.assertNotIn("Traceback", refused.stdout + refused.stderr)
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
