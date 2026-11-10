"""Asset-free regression tests: one native DX2 StaticMeshActor Level-list unplace.

No retail data is used. Existing exports must remain byte-identical.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
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
from dx2_actor_unplace_probe import (
    SCHEMA, check_actor, unplace_in_memory, verify_saved_unplace,
    write_isolated,
)
from upkg import Package, RF_HasStack
from upkgwrite import PackageWriter


class NativeStaticUnplaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "Original" / "M1_Synthetic.gmp"
        self.source.parent.mkdir(parents=True)
        self.original = level_fixture(self.source)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.options = dict(
            source_sha256=self.sha, actor_export=1,
            actor_name="StaticMeshActor__1")
        self.output = self.root / "ResearchOnly" / self.source.name

    def test_eligible_original_has_one_removable_level_reference(self):
        result = check_actor(self.source, **self.options)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["status"], "unplace-source-eligible")
        self.assertEqual(result["source_location"], [100, 200, 300])
        self.assertEqual(result["level_actor_count_before"], 3)
        self.assertEqual(result["level_actor_count_after"], 2)
        self.assertFalse(result["native_actor_deleted"])
        self.assertFalse(result["incoming_references_verified"])
        self.assertFalse(result["output_written"])
        self.assertFalse(self.output.exists())

    def test_unplace_changes_only_level_actor_list_preserving_original_export(self):
        result, data = unplace_in_memory(self.source, **self.options)
        self.assertEqual(result["status"], "binary-reparsed-runtime-unverified")
        self.assertEqual(result["original_export_count"], 2)
        self.assertTrue(result["all_original_actor_payloads_preserved"])
        self.assertTrue(result["level_ref_removed"])
        self.assertFalse(result["runtime_game_verified"])
        path = self.root / "scratch.gmp"
        path.write_bytes(data)
        original = Package(self.source)
        updated = Package(path)
        self.assertEqual(original.level_actors(), [2, 0, 1])
        self.assertEqual(updated.level_actors(), [2, 0])
        self.assertEqual(len(original.exports), len(updated.exports))
        self.assertEqual(len(original.names), len(updated.names))
        self.assertEqual(len(original.imports), len(updated.imports))
        self.assertEqual(original.export_bytes(original.exports[0]),
                         updated.export_bytes(updated.exports[0]))
        self.assertEqual(
            original.read_actor(original.exports[0]).state,
            updated.read_actor(updated.exports[0]).state)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_save_as_verify_against_independently_regenerated_entire_package(self):
        result = write_isolated(self.source, self.output, **self.options)
        self.assertEqual(result["status"], "isolated-GMP-created-runtime-unverified")
        manifest = self.output.with_suffix(".dx2ed-prop-unplace.json")
        self.assertTrue(self.output.is_file())
        self.assertTrue(manifest.is_file())
        report = json.loads(manifest.read_text())
        self.assertFalse(report["runtime_game_verified"])
        self.assertFalse(report["native_actor_deleted"])
        verification = verify_saved_unplace(
            self.source, self.output, source_sha256=self.sha)
        self.assertEqual(verification["status"], "binary-verified-runtime-unverified")
        self.assertTrue(verification["original_export_preserved"])
        self.assertEqual(self.source.read_bytes(), self.original)
        with self.assertRaises(FileExistsError):
            write_isolated(self.source, self.output, **self.options)

    def test_reject_corrupted_candidate_even_when_manifest_hash_is_rewritten(self):
        write_isolated(self.source, self.output, **self.options)
        damaged = bytearray(self.output.read_bytes())
        original = Package(self.source)
        from t3common import Reader
        # Deliberately damage original actor payload, rather than changing Level refs.
        needle = original.export_bytes(original.exports[0])
        offset = damaged.find(needle)
        self.assertGreaterEqual(offset, 0)
        damaged[offset + len(needle) - 1] ^= 0x1
        self.output.write_bytes(damaged)
        manifest = self.output.with_suffix(".dx2ed-prop-unplace.json")
        report = json.loads(manifest.read_text())
        report["output_sha256"] = hashlib.sha256(damaged).hexdigest()
        manifest.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "independently replayed"):
            verify_saved_unplace(
                self.source, self.output, source_sha256=self.sha)

    def test_reject_wrong_original_sha_class_and_export_name(self):
        cases = (
            {"source_sha256": "f" * 64},
            {"actor_export": 2},
            {"actor_name": "StaticMeshActor__9"},
            {"actor_name": ""},
            {"actor_export": True},
        )
        for patch in cases:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                unplace_in_memory(self.source, **(self.options | patch))

    def test_reject_non_neutral_state(self):
        pkg = Package(self.source)
        writer = PackageWriter(pkg)
        raw = bytearray(pkg.export_bytes(pkg.exports[0]))
        raw[1] = 1
        writer.set_object(0, bytes(raw))
        self.source.write_bytes(writer.write())
        sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "unsupported native/script frame"):
            unplace_in_memory(
                self.source, **(self.options | {"source_sha256": sha}))

    def test_refuse_source_folder_game_folder_and_nested_destination(self):
        for dest in (
            self.source,
            self.source.parent / self.source.name,
            self.source.parent / "Nested" / self.source.name,
            self.root / "Content" / "DX2" / "Maps" / self.source.name,
            self.root / "Research" / "wrong-name.gmp",
        ):
            with self.subTest(dest=dest), self.assertRaises((ValueError, FileExistsError)):
                write_isolated(self.source, dest, **self.options)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_cli_read_only_preflight_and_refusal(self):
        script = ROOT / "native_editor/package_writer/dx2_actor_unplace_probe.py"
        params = [sys.executable, str(script), str(self.source),
                  "--source-sha256", self.sha,
                  "--actor-export", "1",
                  "--actor-name", "StaticMeshActor__1"]
        check = subprocess.run(
            [*params, "--check-actor"], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertEqual(json.loads(check.stdout)["status"], "unplace-source-eligible")
        trial = subprocess.run(params, capture_output=True, text=True)
        self.assertEqual(trial.returncode, 0, trial.stdout + trial.stderr)
        self.assertEqual(json.loads(trial.stdout)["status"], "binary-reparsed-runtime-unverified")
        bad = subprocess.run(
            [*params[:-1], "WrongActor"], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(json.loads(bad.stdout)["status"], "refused")
        self.assertNotIn("Traceback", bad.stdout + bad.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
