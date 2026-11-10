"""DX2Ed v0.66 owner-only trial recorder regression; all maps are synthetic."""
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
for parent in (ROOT / "native_editor" / "tests",
               ROOT / "native_editor" / "package_writer",
               ROOT / "third_party" / "t3sdk_assets"):
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))

from test_dx2_actor_clone_probe import level_fixture
from dx2_actor_clone_probe import clone_in_memory
from dx2_native_prop_plan import SCHEMA as PLAN_SCHEMA, save_isolated
from dx2_disposable_retail_trial import ACK as STAGE_ACK, prepare as trial_prepare, stage, restore
from dx2_retail_trial_dossier import prepare as dossier_prepare
from dx2_retail_observation_recorder import (
    ACK, SCHEMA, inspect, record,
)


class OwnerObservationRecorderTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="dx2ed_v066_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "Originals" / "M1_Synthetic.gmp"
        self.source.parent.mkdir()
        initial = level_fixture(self.source)
        _, original = clone_in_memory(
            self.source, source_sha256=hashlib.sha256(initial).hexdigest(),
            actor_export=1, actor_name="StaticMeshActor__1",
            delta=(100.0, 0.0, 0.0))
        self.source.write_bytes(original)
        self.original = original
        self.source_sha = hashlib.sha256(original).hexdigest()
        self.candidate = self.root / "Candidate" / self.source.name
        save_isolated(self.source, self.candidate,
                      source_sha256=self.source_sha,
                      plan={"schema": PLAN_SCHEMA,
                            "moves": [{"actor": "StaticMeshActor__1",
                                       "export": 1, "delta": [20.0, 0.0, 0.0]}],
                            "copies": [{"actor": "StaticMeshActor__1",
                                        "export": 1, "delta": [45.0, 10.0, 0.0]}],
                            "unplaces": [{"actor": "StaticMeshActor__2",
                                          "export": 3}]})
        self.candidate_bytes = self.candidate.read_bytes()
        self.dossier = self.root / "Private" / "Test.dx2trial.json"
        self.observations = self.root / "Private" / "Test.dx2observations.json"
        dossier_prepare(self.source, self.candidate, self.dossier,
                        source_sha256=self.source_sha)
        self.test_root = self.root / "DX2Ed_Disposable_Test"
        self.map_file = self.test_root / "Content" / "DX2" / "Maps" / self.source.name
        self.map_file.parent.mkdir(parents=True)
        (self.test_root / "System").mkdir()
        self.map_file.write_bytes(self.original)
        trial_prepare(self.source, self.candidate, self.test_root,
                      source_sha256=self.source_sha)
        self.evidence = self.root / "TestNote.txt"
        self.evidence.write_text("synthetic human observation fixture")

    def _inspect(self):
        return inspect(self.source, self.candidate, self.dossier,
                       self.observations, self.test_root,
                       source_sha256=self.source_sha)

    def _record(self, key, result="pass", note="Owner manually checked", **overrides):
        kw = {"source_sha256": self.source_sha, "check_id": key,
              "result": result, "note": note, "acknowledgement": ACK}
        kw.update(overrides)
        return record(self.source, self.candidate, self.dossier,
                      self.observations, self.test_root, **kw)

    def _stage(self):
        stage(self.source, self.candidate, self.test_root,
              source_sha256=self.source_sha, acknowledgement=STAGE_ACK)

    def _read_results(self):
        return {r["id"]: r for r in json.loads(
            self.observations.read_text())["results"]}

    def _assert_original_untouched(self):
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.candidate.read_bytes(), self.candidate_bytes)

    def test_prepared_then_staged_then_restored_phase_gates(self):
        initial = self._inspect()
        self.assertEqual(initial["schema"], SCHEMA)
        self.assertEqual(initial["recordable_check_ids_at_current_phase"], ["baseline"])
        self.assertFalse(initial["gameplay_runtime_verified"])
        self.assertEqual(self._record("baseline")["owner_result"], "pass")
        with self.assertRaisesRegex(ValueError, "phase"):
            self._record("collision")
        self._stage()
        current = self._inspect()
        self.assertIn("collision", current["recordable_check_ids_at_current_phase"])
        self.assertNotIn("restore", current["recordable_check_ids_at_current_phase"])
        self._record("collision", result="fail", note="Observed residual collider",
                     evidence=self.evidence)
        row = self._read_results()["collision"]
        self.assertEqual(row["result"], "fail")
        self.assertEqual(row["evidence_sha256"],
                         hashlib.sha256(self.evidence.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, "phase"):
            self._record("restore")
        restore(self.test_root)
        self.assertEqual(self._inspect()["recordable_check_ids_at_current_phase"],
                         ["restore"])
        self._record("restore", note="Original map restored and inspected")
        self.assertEqual(self._inspect()["check_counts"]["pass"], 2)
        self.assertEqual(self._inspect()["check_counts"]["fail"], 1)
        self.assertEqual(self.map_file.read_bytes(), self.original)
        self._assert_original_untouched()

    def test_requires_ack_notes_exact_check_and_matching_receipts(self):
        before = self.observations.read_bytes()
        for key, extras in (
            ("baseline", {"acknowledgement": "YES"}),
            ("baseline", {"note": " "}),
            ("invented", {}),
            ("baseline", {"result": "maybe"}),
            ("baseline", {"note": "x" * 1001}),
        ):
            with self.subTest(key=key, extras=extras), self.assertRaises(ValueError):
                self._record(key, **extras)
        self.assertEqual(self.observations.read_bytes(), before)
        state_path = self.test_root / ".dx2ed-retail-trial-v1" / "state.json"
        state = json.loads(state_path.read_text())
        state["candidate_sha256"] = "f" * 64
        state_path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, "DIFFERENT"):
            self._record("baseline")
        self.assertEqual(self.observations.read_bytes(), before)
        self._assert_original_untouched()

    def test_reject_unknown_target_and_wrong_phase_and_evidence_symlink(self):
        self._stage()
        self.map_file.write_bytes(self.candidate_bytes + b"tamper")
        old = self.observations.read_bytes()
        with self.assertRaisesRegex(ValueError, "phase"):
            self._record("collision")
        self.assertEqual(self.observations.read_bytes(), old)
        self.map_file.write_bytes(self.candidate_bytes)
        link = self.root / "linked-evidence.txt"
        try:
            link.symlink_to(self.evidence)
        except (OSError, NotImplementedError):
            pass
        else:
            with self.assertRaisesRegex(ValueError, "symlink"):
                self._record("collision", evidence=link)
        self.assertEqual(self.observations.read_bytes(), old)
        self._assert_original_untouched()

    def test_clear_only_with_blank_note_and_no_evidence(self):
        self._record("baseline")
        with self.assertRaises(ValueError):
            self._record("baseline", result="not-tested", note="unverified")
        self._record("baseline", result="not-tested", note="")
        self.assertEqual(self._read_results()["baseline"]["result"], "not-tested")
        self._assert_original_untouched()

    def test_cli_inspection_record_and_refused_write(self):
        script = ROOT / "native_editor/package_writer/dx2_retail_observation_recorder.py"
        common = [sys.executable, str(script), "--source", str(self.source),
                  "--candidate", str(self.candidate),
                  "--source-sha256", self.source_sha,
                  "--dossier", str(self.dossier),
                  "--observations", str(self.observations),
                  "--test-root", str(self.test_root)]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)

        def run(*args):
            return subprocess.run([*common, *args], cwd=self.root,
                                  env=env, capture_output=True, text=True)

        found = run("--inspect")
        self.assertEqual(found.returncode, 0, found.stdout + found.stderr)
        self.assertIn("baseline", json.loads(found.stdout)[
            "recordable_check_ids_at_current_phase"])
        bad = run("--record", "--check-id", "baseline", "--result", "pass",
                  "--note", "I checked")
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(json.loads(bad.stdout)["status"], "refused")
        good = run("--record", "--check-id", "baseline", "--result", "pass",
                   "--note", "I checked", "--acknowledge", ACK)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertEqual(json.loads(good.stdout)["owner_result"], "pass")
        self.assertFalse(json.loads(good.stdout)["gameplay_runtime_verified"])
        self._assert_original_untouched()


if __name__ == "__main__":
    unittest.main()
