"""P112: bulk native GMP candidates can be staged only into a disposable game copy.

All assets and maps here are synthetic. No retail installation is accessed.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
for directory in (
    ROOT / "native_editor" / "tests",
    ROOT / "native_editor" / "package_writer",
    ROOT / "third_party" / "t3sdk_assets",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from test_dx2_actor_clone_probe import level_fixture
from dx2_native_prop_plan import (
    BULK_SCHEMA, BULK_MANIFEST_SUFFIX, MANIFEST_SUFFIX, save_isolated,
)
from dx2_retail_trial_dossier import expected_dossier, prepare as create_dossier
from dx2_disposable_retail_trial import (
    ACK, prepare as create_trial, stage, status, restore,
)


class BulkDisposableGameTrialTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2ed_p112_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "OwnedOriginals" / "M1_Synthetic.gmp"
        self.source.parent.mkdir()
        self.original = level_fixture(self.source)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.candidate = self.root / "IsolatedCandidate" / self.source.name
        self.plan = {
            "schema": BULK_SCHEMA, "moves": [], "unplaces": [],
            "copies": [
                {"actor": "StaticMeshActor__1", "export": 1,
                 "delta": [float(40 + 20 * i), 0., 0.]}
                for i in range(20)
            ],
        }
        save_isolated(self.source, self.candidate, source_sha256=self.sha,
                      plan=self.plan, bulk=True)
        self.edited = self.candidate.read_bytes()
        self.root_copy = self.root / "DX2Ed_Disposable_Test"
        self.test_map = self.root_copy / "Content" / "DX2" / "Maps" / self.source.name
        self.test_map.parent.mkdir(parents=True)
        (self.root_copy / "System").mkdir()
        self.test_map.write_bytes(self.original)

    def test_bulk_candidate_dossier_has_one_check_per_operation(self):
        report = expected_dossier(self.source, self.candidate, source_sha256=self.sha)
        self.assertEqual(report["native_plan"], self.plan)
        self.assertEqual(report["operation_counts"],
                         {"moves": 0, "copies": 20, "unplaces": 0})
        self.assertEqual(len(report["checks"]), 26)
        self.assertEqual(report["checks"][-1]["id"], "clone-20")
        self.assertTrue(report["automated_whole_gmp_byte_replay_verified"])
        self.assertFalse(report["gameplay_runtime_verified"])
        self.assertFalse(report["game_installation_modified"])
        dossier_path = self.root / "PrivateReports" / "Trial.dx2trial.json"
        result = create_dossier(self.source, self.candidate, dossier_path,
                                source_sha256=self.sha)
        self.assertEqual(result["checks_count"], 26)
        self.assertFalse(result["gameplay_runtime_verified"])
        self.assertFalse((self.root_copy / ".dx2ed-retail-trial-v1").exists())

    def test_bulk_candidate_is_staged_and_restored_in_disposable_copy_only(self):
        a = create_trial(self.source, self.candidate, self.root_copy,
                         source_sha256=self.sha)
        self.assertEqual(a["status"], "prepared-original-map-untouched")
        self.assertEqual(self.test_map.read_bytes(), self.original)
        self.assertEqual(status(self.root_copy)["target_content"], "matches-original")
        with self.assertRaises(ValueError):
            stage(self.source, self.candidate, self.root_copy,
                  source_sha256=self.sha, acknowledgement="incorrect")
        receipt = stage(self.source, self.candidate, self.root_copy,
                        source_sha256=self.sha, acknowledgement=ACK)
        self.assertEqual(receipt["status"], "staged-disposable-game-copy-only")
        self.assertEqual(self.test_map.read_bytes(), self.edited)
        self.assertEqual(status(self.root_copy)["target_content"], "matches-candidate")
        self.assertEqual(self.source.read_bytes(), self.original)
        rollback = restore(self.root_copy)
        self.assertEqual(rollback["status"], "restored-original-gmp-in-disposable-copy")
        self.assertEqual(self.test_map.read_bytes(), self.original)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.candidate.read_bytes(), self.edited)

    def test_bulk_candidate_refuses_dual_manifests_and_tampered_bytes(self):
        manifest = self.candidate.with_suffix(BULK_MANIFEST_SUFFIX)
        legacy = self.candidate.with_suffix(MANIFEST_SUFFIX)
        legacy.write_text(manifest.read_text())
        with self.assertRaisesRegex(ValueError, "exactly one"):
            expected_dossier(self.source, self.candidate, source_sha256=self.sha)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            create_trial(self.source, self.candidate, self.root_copy,
                         source_sha256=self.sha)
        legacy.unlink()
        changed = bytearray(self.edited)
        changed[-1] ^= 1
        self.candidate.write_bytes(changed)
        with self.assertRaises(ValueError):
            create_trial(self.source, self.candidate, self.root_copy,
                         source_sha256=self.sha)
        self.assertEqual(self.test_map.read_bytes(), self.original)
        self.assertFalse((self.root_copy / ".dx2ed-retail-trial-v1").exists())


if __name__ == "__main__":
    unittest.main()
