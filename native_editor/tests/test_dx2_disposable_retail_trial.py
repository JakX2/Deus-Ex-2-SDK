"""v0.65 synthetic disposable-game A/B trial regression.

Every written GMP is a non-proprietary minimal DX2 v95 fixture. Tests
never modify a real game, install, run or automate game processes.
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
for parent in (
    ROOT / "native_editor" / "tests",
    ROOT / "native_editor" / "package_writer",
    ROOT / "third_party" / "t3sdk_assets",
):
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))

from test_dx2_actor_clone_probe import level_fixture
from dx2_actor_clone_probe import clone_in_memory
from dx2_native_prop_plan import SCHEMA as PLAN_SCHEMA, save_isolated
from dx2_disposable_retail_trial import (
    SCHEMA, ACK, prepare, stage, restore, status,
)


class DisposableRetailTrialTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2ed_v065_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "OwnerOriginals" / "M1_Synthetic.gmp"
        self.source.parent.mkdir(parents=True)
        initial = level_fixture(self.source)
        _, updated = clone_in_memory(
            self.source, source_sha256=hashlib.sha256(initial).hexdigest(),
            actor_export=1, actor_name="StaticMeshActor__1",
            delta=(100.0, 0.0, 0.0))
        self.source.write_bytes(updated)
        self.original = self.source.read_bytes()
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.candidate = self.root / "IsolatedCandidate" / self.source.name
        plan = {
            "schema": PLAN_SCHEMA,
            "moves": [{"actor": "StaticMeshActor__1", "export": 1,
                       "delta": [30.0, 0.0, 0.0]}],
            "copies": [{"actor": "StaticMeshActor__1", "export": 1,
                        "delta": [90.0, 20.0, 0.0]}],
            "unplaces": [{"actor": "StaticMeshActor__2", "export": 3}],
        }
        save_isolated(self.source, self.candidate,
                      source_sha256=self.sha, plan=plan)
        self.edited = self.candidate.read_bytes()
        self.edit_sha = hashlib.sha256(self.edited).hexdigest()
        self.test_root = self.root / "DX2Ed_Disposable_Test"
        self.map_file = (
            self.test_root / "Content" / "DX2" / "Maps" / self.source.name)
        self.map_file.parent.mkdir(parents=True)
        (self.test_root / "System").mkdir()
        self.map_file.write_bytes(self.original)
        self.state_file = self.test_root / ".dx2ed-retail-trial-v1" / "state.json"
        self.backup = self.state_file.parent / "original-map.gmp"

    def _prepare(self):
        return prepare(self.source, self.candidate, self.test_root,
                       source_sha256=self.sha)

    def _stage(self, acknowledgement=ACK):
        return stage(self.source, self.candidate, self.test_root,
                     source_sha256=self.sha, acknowledgement=acknowledgement)

    def _assert_original_untouched(self):
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.candidate.read_bytes(), self.edited)

    def test_prep_only_saves_separate_intact_backup_then_stage_and_restore(self):
        initial = self._prepare()
        self.assertEqual(initial["schema"], SCHEMA)
        self.assertEqual(initial["status"], "prepared-original-map-untouched")
        self.assertFalse(initial["game_runtime_verified"])
        self.assertFalse(initial["source_original_modified"])
        self.assertEqual(self.map_file.read_bytes(), self.original)
        self.assertEqual(self.backup.read_bytes(), self.original)
        self.assertEqual(status(self.test_root)["target_content"], "matches-original")
        staged = self._stage()
        self.assertEqual(staged["status"], "staged-disposable-game-copy-only")
        self.assertEqual(self.map_file.read_bytes(), self.edited)
        self.assertEqual(self.backup.read_bytes(), self.original)
        current = status(self.test_root)
        self.assertEqual(current["target_content"], "matches-candidate")
        self.assertTrue(current["trial_phase_consistent"])
        self.assertTrue(current["rollback_backup_verified"])
        restored = restore(self.test_root)
        self.assertEqual(restored["status"],
                         "restored-original-gmp-in-disposable-copy")
        self.assertEqual(self.map_file.read_bytes(), self.original)
        self.assertEqual(self.backup.read_bytes(), self.original)
        self.assertTrue(self.state_file.exists())
        self.assertTrue(status(self.test_root)["trial_phase_consistent"])
        self._assert_original_untouched()
        with self.assertRaises(ValueError):
            self._stage()
        with self.assertRaises(FileExistsError):
            self._prepare()

    def test_refuses_stage_without_explicit_disposable_ack(self):
        self._prepare()
        for ack in (None, "", "yes", "YES_DISPOSABLE"):
            with self.subTest(ack=ack), self.assertRaises(ValueError):
                self._stage(ack)
            self.assertEqual(self.map_file.read_bytes(), self.original)
        with self.assertRaises(ValueError):
            restore(self.test_root)
        self._assert_original_untouched()

    def test_refuses_other_root_game_install_and_source_inside_test_copy(self):
        wrong = self.root / "OriginalRetailGame"
        maps = wrong / "Content" / "DX2" / "Maps"
        maps.mkdir(parents=True)
        (wrong / "System").mkdir()
        (maps / self.source.name).write_bytes(self.original)
        with self.assertRaisesRegex(ValueError, "DX2Ed_Disposable_Test"):
            prepare(self.source, self.candidate, wrong, source_sha256=self.sha)
        self.assertFalse((wrong / ".dx2ed-retail-trial-v1").exists())
        with self.assertRaises(ValueError):
            prepare(self.map_file, self.candidate, self.test_root,
                    source_sha256=self.sha)
        self.assertEqual(self.map_file.read_bytes(), self.original)
        self._assert_original_untouched()

    def test_refuse_symlinked_target_and_mismatched_baseline(self):
        self.map_file.write_bytes(self.original + b"not original map")
        with self.assertRaisesRegex(ValueError, "NOT byte-identical"):
            self._prepare()
        self.assertFalse(self.backup.exists())
        self.map_file.unlink()
        try:
            self.map_file.symlink_to(self.source)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on test filesystem")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self._prepare()
        self.assertFalse(self.backup.exists())
        self._assert_original_untouched()

    def test_refuse_changed_test_target_before_stage_or_restore(self):
        self._prepare()
        self.map_file.write_bytes(self.original + b"unexpected")
        with self.assertRaisesRegex(ValueError, "unexpectedly"):
            self._stage()
        self.assertEqual(self.backup.read_bytes(), self.original)
        self.map_file.write_bytes(self.original)
        self._stage()
        self.map_file.write_bytes(self.edited + b"modified by game")
        with self.assertRaisesRegex(ValueError, "changed since stage"):
            restore(self.test_root)
        self.assertEqual(self.map_file.read_bytes(), self.edited + b"modified by game")
        self.assertEqual(self.backup.read_bytes(), self.original)
        self._assert_original_untouched()

    def test_refuse_tampered_backup_receipt_and_candidate(self):
        self._prepare()
        state = json.loads(self.state_file.read_text())
        for change in (
            {"game_runtime_verified": True},
            {"source_sha256": "f" * 64},
            {"status": "playable-success"},
            {"new_unknown_field": 1},
        ):
            self.state_file.write_text(json.dumps({**state, **change}))
            with self.subTest(change=change), self.assertRaises(ValueError):
                status(self.test_root)
        self.state_file.write_text(json.dumps(state))
        self.backup.write_bytes(self.original + b"tampered")
        with self.assertRaisesRegex(ValueError, "backup digest mismatch"):
            self._stage()
        self.backup.write_bytes(self.original)
        self.candidate.write_bytes(self.edited + b"tampered candidate")
        with self.assertRaises(ValueError):
            self._stage()
        self.candidate.write_bytes(self.edited)
        self.assertEqual(self.map_file.read_bytes(), self.original)
        self._assert_original_untouched()

    def test_recover_interrupted_staging_and_restoration(self):
        self._prepare()
        state = json.loads(self.state_file.read_text())
        state["status"] = "staging"
        self.state_file.write_text(json.dumps(state))
        staged = self._stage()
        self.assertEqual(staged["status"], "staged-disposable-game-copy-only")
        self.assertEqual(self.map_file.read_bytes(), self.edited)
        state = json.loads(self.state_file.read_text())
        state["status"] = "staging"
        self.state_file.write_text(json.dumps(state))
        staged = self._stage()
        self.assertEqual(staged["status"], "staged-disposable-game-copy-only")
        self.assertEqual(self.map_file.read_bytes(), self.edited)
        state = json.loads(self.state_file.read_text())
        state["status"] = "restoring"
        self.state_file.write_text(json.dumps(state))
        self.assertEqual(restore(self.test_root)["status"],
                         "restored-original-gmp-in-disposable-copy")
        self.assertEqual(self.map_file.read_bytes(), self.original)
        self._assert_original_untouched()

    def test_cli_all_phases_from_arbitrary_cwd_without_pythonpath(self):
        tool = ROOT / "native_editor/package_writer/dx2_disposable_retail_trial.py"
        common = [
            sys.executable, str(tool), "--test-root", str(self.test_root),
        ]
        original_args = [
            "--source", str(self.source), "--candidate", str(self.candidate),
            "--source-sha256", self.sha,
        ]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)

        def run(*extra):
            return subprocess.run([*common, *extra], cwd=self.root,
                                  env=env, text=True, capture_output=True)

        prep = run("--prepare", *original_args)
        self.assertEqual(prep.returncode, 0, prep.stdout + prep.stderr)
        self.assertEqual(json.loads(prep.stdout)["status"],
                         "prepared-original-map-untouched")
        miss = run("--stage", *original_args)
        self.assertEqual(miss.returncode, 2)
        self.assertEqual(json.loads(miss.stdout)["status"], "refused")
        staged = run("--stage", *original_args, "--acknowledge", ACK)
        self.assertEqual(staged.returncode, 0, staged.stdout + staged.stderr)
        self.assertEqual(self.map_file.read_bytes(), self.edited)
        check = run("--status")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertEqual(json.loads(check.stdout)["target_content"], "matches-candidate")
        rollback = run("--restore")
        self.assertEqual(rollback.returncode, 0, rollback.stdout + rollback.stderr)
        self.assertEqual(self.map_file.read_bytes(), self.original)
        self.assertEqual(self.backup.read_bytes(), self.original)
        self.assertNotIn("Traceback", "".join(
            x.stdout + x.stderr for x in (prep, miss, staged, check, rollback)))
        self._assert_original_untouched()


if __name__ == "__main__":
    unittest.main()
