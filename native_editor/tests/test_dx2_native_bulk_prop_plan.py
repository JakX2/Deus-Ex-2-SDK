"""P109 bulk native static prop plans, synthetic fixtures only."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
for directory in (
    ROOT / "native_editor/tests",
    ROOT / "native_editor/package_writer",
    ROOT / "third_party/t3sdk_assets",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from test_dx2_actor_clone_probe import level_fixture
from dx2_native_prop_plan import (
    BULK_SCHEMA, BULK_MANIFEST_SUFFIX, SCHEMA, _plan, compile_in_memory,
    save_isolated, verify_saved_plan,
)
from upkg import Package


class NativeBulkTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "Original" / "M1_Bulk.gmp"
        self.source.parent.mkdir(parents=True)
        self.original = level_fixture(self.source)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.output = self.root / "Isolated" / self.source.name
        self.single = {
            "schema": BULK_SCHEMA,
            "moves": [{"actor": "StaticMeshActor__1", "export": 1,
                       "delta": [100, 0, 0]}],
            "copies": [], "unplaces": [],
        }

    def test_single_operation_allowed_only_for_opt_in_bulk(self):
        report, candidate = compile_in_memory(
            self.source, source_sha256=self.sha, plan=self.single, bulk=True)
        self.assertEqual(report["schema"], BULK_SCHEMA)
        self.assertEqual(len(report["moved"]), 1)
        self.assertNotEqual(candidate, self.original)
        self.assertFalse(report["runtime_game_verified"])
        old = {**self.single, "schema": SCHEMA}
        with self.assertRaises(ValueError):
            compile_in_memory(self.source, source_sha256=self.sha, plan=old)
        with self.assertRaises(ValueError):
            compile_in_memory(self.source, source_sha256=self.sha, plan=self.single)

    def test_20_copies_in_one_native_gmp_exceeds_legacy_limit(self):
        plan = {
            "schema": BULK_SCHEMA, "moves": [], "unplaces": [],
            "copies": [
                {"actor": "StaticMeshActor__1", "export": 1,
                 "delta": [float(10 + 20 * i), 0.0, 0.0]}
                for i in range(20)
            ],
        }
        report, candidate = compile_in_memory(
            self.source, source_sha256=self.sha, plan=plan, bulk=True)
        self.assertEqual(len(report["copied"]), 20)
        self.assertEqual(report["new_export_count"],
                         report["original_export_count"] + 20)
        candidate_path = self.root / "scratch.gmp"
        candidate_path.write_bytes(candidate)
        before = Package(self.source)
        after = Package(candidate_path)
        self.assertEqual(len(after.level_actors()), len(before.level_actors()) + 20)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_save_full_replay_and_no_retail_write(self):
        result = save_isolated(self.source, self.output, source_sha256=self.sha,
                               plan=self.single, bulk=True)
        self.assertEqual(result["schema"], BULK_SCHEMA)
        manifest = self.output.with_suffix(BULK_MANIFEST_SUFFIX)
        self.assertTrue(manifest.exists())
        verify = verify_saved_plan(self.source, self.output, source_sha256=self.sha,
                                   bulk=True)
        self.assertTrue(verify["all_candidate_bytes_replayed"])
        with self.assertRaises(ValueError):
            verify_saved_plan(self.source, self.output, source_sha256=self.sha)
        self.assertEqual(self.source.read_bytes(), self.original)
        modified = bytearray(self.output.read_bytes())
        modified[-1] ^= 0x01
        self.output.write_bytes(modified)
        with self.assertRaises(ValueError):
            verify_saved_plan(self.source, self.output,
                              source_sha256=self.sha, bulk=True)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_bulk_limits_and_source_identity_still_fail_closed(self):
        copies = [{"actor": "StaticMeshActor__1", "export": 1,
                   "delta": [20.0 + n, 0.0, 0.0]} for n in range(257)]
        plan = {**self.single, "moves": [], "copies": copies}
        with self.assertRaisesRegex(ValueError, "256"):
            _plan(plan, bulk=True)
        with self.assertRaises(ValueError):
            _plan({**self.single, "schema": SCHEMA}, bulk=True)
        # Reusing one original actor as a copy template is intentional;
        # individual cloned exports receive distinct native identities.
        twice = _plan({**self.single, "moves": [],
                       "copies": [copies[0], copies[0]]}, bulk=True)
        self.assertEqual(len(twice["copies"]), 2)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            compile_in_memory(self.source, source_sha256="f" * 64,
                              plan=self.single, bulk=True)
        with self.assertRaises((ValueError, FileExistsError)):
            save_isolated(self.source, self.source, source_sha256=self.sha,
                          plan=self.single, bulk=True)

    def test_cross_mode_manifest_cannot_be_accepted(self):
        save_isolated(self.source, self.output, source_sha256=self.sha,
                      plan=self.single, bulk=True)
        record = json.loads(self.output.with_suffix(BULK_MANIFEST_SUFFIX).read_text())
        self.assertEqual(record["schema"], BULK_SCHEMA)
        self.assertTrue(record["all_changes_scope_verified"])
        self.assertFalse(record["incoming_references_verified"])
        record["schema"] = SCHEMA
        self.output.with_suffix(BULK_MANIFEST_SUFFIX).write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "manifest source identity"):
            verify_saved_plan(self.source, self.output,
                              source_sha256=self.sha, bulk=True)


if __name__ == "__main__":
    unittest.main()
