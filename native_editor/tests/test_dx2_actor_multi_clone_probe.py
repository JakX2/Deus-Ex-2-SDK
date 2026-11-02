"""Synthetic source-only tests for experimental 2..8 native DX2 prop clones."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "native_editor" / "tests",
          ROOT / "native_editor" / "package_writer",
          ROOT / "third_party" / "t3sdk_assets"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from test_dx2_actor_clone_probe import level_fixture
from dx2_actor_multi_clone_probe import (
    SCHEMA, clone_many_in_memory, save_isolated,
)
from upkg import Package


class MultiCloneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "Original" / "M1_Test.gmp"
        self.source.parent.mkdir()
        self.original = level_fixture(self.source)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.copies = [
            {"actor": "StaticMeshActor__1", "export": 1,
             "delta": [100, 0, 0]},
            {"actor": "StaticMeshActor__1", "export": 1,
             "delta": [0, 100, 50]},
            {"actor": "StaticMeshActor__1", "export": 1,
             "delta": [-50, 0, 75]},
        ]

    def test_three_copies_append_unique_exports_and_level_references(self):
        report, data = clone_many_in_memory(
            self.source, source_sha256=self.sha, copies=self.copies)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["original_export_count"], 2)
        self.assertEqual(report["new_export_count"], 5)
        self.assertEqual(report["level_actor_count_after"], 6)
        self.assertTrue(report["original_bytes_unchanged"])
        self.assertFalse(report["runtime_game_verified"])
        self.assertEqual([r["new_export"] for r in report["copies"]], [3, 4, 5])
        self.assertEqual(len({r["new_actor"] for r in report["copies"]}), 3)
        self.assertEqual([r["after"] for r in report["copies"]],
                         [[200, 200, 300], [100, 300, 350], [50, 200, 375]])
        self.assertTrue(all(r["payload_provenance_verified"] for r in report["copies"]))
        candidate = self.root / "candidate.gmp"
        candidate.write_bytes(data)
        after = Package(candidate)
        self.assertEqual(after.level_actors(), [2, 0, 1, 3, 4, 5])
        before = Package(self.source)
        self.assertEqual(before.export_bytes(before.exports[0]),
                         after.export_bytes(after.exports[0]))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_isolated_save_as_and_overwrite_rejection(self):
        output = self.root / "Output" / self.source.name
        report = save_isolated(self.source, output, source_sha256=self.sha,
                               copies=self.copies)
        self.assertEqual(report["status"], "isolated-GMP-created-runtime-unverified")
        manifest = output.with_suffix(".dx2ed-multi-prop-clone.json")
        self.assertTrue(manifest.exists())
        self.assertEqual(json.loads(manifest.read_text())["output_sha256"],
                         hashlib.sha256(output.read_bytes()).hexdigest())
        with self.assertRaises(FileExistsError):
            save_isolated(self.source, output, source_sha256=self.sha,
                          copies=self.copies)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_refuse_unknown_source_bad_delta_or_too_many(self):
        bad_cases = [
            [],
            [self.copies[0]],
            self.copies * 3,
            [{**self.copies[0], "actor": "D_Foreign"}] + self.copies[1:],
            [{**self.copies[0], "export": 2}] + self.copies[1:],
            [{**self.copies[0], "delta": [0, 0, 0]}] + self.copies[1:],
            [{**self.copies[0], "delta": [float("nan"), 0, 0]}] + self.copies[1:],
            [{**self.copies[0], "delta": [5000, 0, 0]}] + self.copies[1:],
            [{**self.copies[0], "extra": "unsupported"}] + self.copies[1:],
        ]
        for rows in bad_cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                clone_many_in_memory(self.source, source_sha256=self.sha,
                                     copies=rows)
        with self.assertRaises(ValueError):
            save_isolated(
                self.source,
                self.root / "Content" / "DX2" / "Maps" / self.source.name,
                source_sha256=self.sha, copies=self.copies)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_cli_json_plan_refusal_and_memory_only_success(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"schema": SCHEMA, "copies": self.copies}))
        script = ROOT / "native_editor/package_writer/dx2_actor_multi_clone_probe.py"
        args = [sys.executable, str(script), str(self.source),
                "--source-sha256", self.sha, "--copies-json", str(plan)]
        good = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        result = json.loads(good.stdout)
        self.assertEqual(result["status"], "binary-reparsed-runtime-unverified")
        self.assertEqual(self.source.read_bytes(), self.original)
        plan.write_text(json.dumps({"schema": "invalid", "copies": self.copies}))
        bad = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("Invalid exact multi-prop plan", json.loads(bad.stdout)["reason"])
        self.assertNotIn("Traceback", bad.stdout + bad.stderr)


if __name__ == "__main__":
    unittest.main()
