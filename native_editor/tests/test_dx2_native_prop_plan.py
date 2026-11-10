"""Synthetic DX2 v95 tests for one atomic native StaticMeshActor change plan."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
for folder in (
    ROOT / "native_editor/tests",
    ROOT / "native_editor/package_writer",
    ROOT / "third_party/t3sdk_assets",
):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from test_dx2_actor_clone_probe import level_fixture
from dx2_actor_clone_probe import clone_in_memory
from dx2_native_prop_plan import (
    SCHEMA, compile_in_memory, save_isolated, verify_saved_plan,
)
from upkg import Package
from upkgwrite import ActorEdit, PackageWriter


class NativeCombinedPropPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "Original" / "M1_Synthetic.gmp"
        self.source.parent.mkdir(parents=True)
        initial = level_fixture(self.source)
        original_sha = hashlib.sha256(initial).hexdigest()
        _, with_second = clone_in_memory(
            self.source, source_sha256=original_sha,
            actor_export=1, actor_name="StaticMeshActor__1",
            delta=(100.0, 0.0, 0.0))
        self.source.write_bytes(with_second)
        self.original = self.source.read_bytes()
        self.sha = hashlib.sha256(self.original).hexdigest()
        reader = Package(self.source)
        self.other_name = reader.exports[2].name
        self.assertEqual(reader.level_actors(), [2, 0, 1, 3])
        self.plan = {
            "schema": SCHEMA,
            "moves": [
                {"actor": "StaticMeshActor__1", "export": 1,
                 "delta": [20, 0, 0]},
            ],
            "copies": [
                {"actor": "StaticMeshActor__1", "export": 1,
                 "delta": [40, 10, 0]},
            ],
            "unplaces": [
                {"actor": self.other_name, "export": 3},
            ],
        }
        self.output = self.root / "Isolated" / self.source.name

    def test_move_copy_and_unplace_in_one_original_source_transaction(self):
        report, candidate = compile_in_memory(
            self.source, source_sha256=self.sha, plan=self.plan)
        self.assertEqual(report["status"], "binary-reparsed-runtime-unverified")
        self.assertFalse(report["runtime_game_verified"])
        self.assertTrue(report["all_changes_scope_verified"])
        self.assertFalse(report["native_actor_exports_deleted"])
        self.assertEqual(report["original_export_count"], 3)
        self.assertEqual(report["new_export_count"], 4)
        self.assertEqual(report["moved"][0]["after"], [120, 200, 300])
        self.assertEqual(report["copied"][0]["after"], [140, 210, 300])
        self.assertEqual(report["copied"][0]["new_export"], 4)
        self.assertEqual(report["unplaced"], [
            {"actor": self.other_name, "export": 3}])
        staged = self.root / "candidate.gmp"
        staged.write_bytes(candidate)
        before = Package(self.source)
        after = Package(staged)
        self.assertEqual(after.level_actors(), [2, 0, 1, 4])
        self.assertEqual(
            after.export_bytes(after.exports[2]),
            before.export_bytes(before.exports[2]),
        )
        original_editor = ActorEdit(PackageWriter(before), before.exports[0])
        candidate_editor = ActorEdit(PackageWriter(after), after.exports[0])
        self.assertEqual(original_editor.struct_values("Location", "Vector"),
                         [100, 200, 300])
        self.assertEqual(candidate_editor.struct_values("Location", "Vector"),
                         [120, 200, 300])
        self.assertEqual(self.original, self.source.read_bytes())

    def test_save_and_replay_verifier_rejects_rehashed_output_tampering(self):
        result = save_isolated(self.source, self.output,
                               source_sha256=self.sha, plan=self.plan)
        self.assertEqual(result["status"], "isolated-GMP-created-runtime-unverified")
        manifest = self.output.with_suffix(".dx2ed-native-prop-plan.json")
        self.assertTrue(manifest.exists())
        check = verify_saved_plan(self.source, self.output, source_sha256=self.sha)
        self.assertTrue(check["all_candidate_bytes_replayed"])
        with self.assertRaises(FileExistsError):
            save_isolated(self.source, self.output, source_sha256=self.sha,
                          plan=self.plan)
        damaged = bytearray(self.output.read_bytes())
        damaged[-1] ^= 1
        self.output.write_bytes(damaged)
        record = json.loads(manifest.read_text())
        record["output_sha256"] = hashlib.sha256(damaged).hexdigest()
        manifest.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "whole-file proof"):
            verify_saved_plan(self.source, self.output, source_sha256=self.sha)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_two_operation_kinds_only_allowed(self):
        plan = {**self.plan, "moves": []}
        report, candidate = compile_in_memory(
            self.source, source_sha256=self.sha, plan=plan)
        self.assertEqual(len(report["copied"]), 1)
        self.assertEqual(len(report["unplaced"]), 1)
        self.assertEqual(len(report["moved"]), 0)
        self.assertNotEqual(candidate, self.original)

    def test_reject_conflicting_operations_duplicate_ids_and_bad_positions(self):
        bad = [
            {**self.plan, "unplaces": [
                {"actor": "StaticMeshActor__1", "export": 1}]},
            {**self.plan, "moves": self.plan["moves"] * 2},
            {**self.plan, "unplaces": self.plan["unplaces"] * 2},
            {**self.plan, "moves": [] , "unplaces": []},
            {**self.plan, "copies": self.plan["copies"] * 9},
            {**self.plan, "copies": [
                {**self.plan["copies"][0], "delta": [0, 0, 0]}]},
            {**self.plan, "copies": [
                {**self.plan["copies"][0], "delta": [float("nan"), 0, 0]}]},
            {**self.plan, "copies": [
                {**self.plan["copies"][0], "delta": [10_000, 0, 0]}]},
            {**self.plan, "moves": [
                {**self.plan["moves"][0], "actor": self.other_name}]},
            {**self.plan, "unplaces": [
                {"actor": "OtherActor", "export": 3}]},
            {**self.plan, "moves": [
                {**self.plan["moves"][0], "export": True}]},
            {**self.plan, "copies": [
                {**self.plan["copies"][0], "extra": True}]},
            {**self.plan, "schema": "unknown"},
        ]
        for row in bad:
            with self.subTest(row=row), self.assertRaises(ValueError):
                compile_in_memory(self.source, source_sha256=self.sha, plan=row)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_refuse_wrong_source_and_unsafe_destination(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            compile_in_memory(self.source, source_sha256="f" * 64, plan=self.plan)
        destinations = [
            self.source,
            self.source.parent / "Research" / self.source.name,
            self.root / "Content/DX2/Maps" / self.source.name,
            self.root / "Elsewhere" / "wrongname.gmp",
        ]
        for dest in destinations:
            with self.subTest(dest=dest), self.assertRaises((ValueError, FileExistsError)):
                save_isolated(self.source, dest, source_sha256=self.sha,
                              plan=self.plan)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_cli_in_memory_and_isolated_verify(self):
        script = ROOT / "native_editor/package_writer/dx2_native_prop_plan.py"
        plan_json = self.root / "combined.json"
        plan_json.write_text(json.dumps(self.plan))
        args = [sys.executable, str(script), str(self.source),
                "--source-sha256", self.sha]
        check = subprocess.run([*args, "--plan-json", str(plan_json)],
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertEqual(json.loads(check.stdout)["status"],
                         "binary-reparsed-runtime-unverified")
        saved = subprocess.run(
            [*args, "--plan-json", str(plan_json), "--output", str(self.output)],
            capture_output=True, text=True)
        self.assertEqual(saved.returncode, 0, saved.stdout + saved.stderr)
        self.assertTrue(self.output.exists())
        verify = subprocess.run(
            [*args, "--verify", "--output", str(self.output)],
            capture_output=True, text=True)
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        self.assertTrue(json.loads(verify.stdout)["all_candidate_bytes_replayed"])
        bogus = subprocess.run([*args, "--verify"], capture_output=True, text=True)
        self.assertEqual(bogus.returncode, 2)
        self.assertEqual(json.loads(bogus.stdout)["status"], "refused")
        self.assertNotIn("Traceback", bogus.stdout + bogus.stderr)


if __name__ == "__main__":
    unittest.main()
