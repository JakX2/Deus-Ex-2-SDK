"""Synthetic original StaticMeshActor clone through public DX2SDK v0.4.

The source GMP is invented and contains one source-eligible neutral state
frame and synthetic Level actor refs. No proprietary game data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dx2sdk import DX2Map
from dx2sdk.clones import SCHEMA
from test_dx2_actor_clone_probe import level_fixture
from dx2inspect import Package


class PublicStaticPropCloneTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2sdk_public_original_prop_clone_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "OriginalFixture" / "M1_Test.gmp"
        self.source.parent.mkdir()
        self.original = level_fixture(self.source)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.world = DX2Map.open(self.source)
        self.output = self.root / "SafePrivateOutput" / self.source.name
        self.manifest = self.output.with_suffix(".dx2ed-prop-clone.json")

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", *args],
            cwd=ROOT, capture_output=True, text=True, timeout=45)

    def test_read_only_native_clone_candidates_are_source_verified(self):
        report = self.world.static_prop_clone_candidates(limit=10)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["status"],
                         "source-verified-static-prop-candidates")
        self.assertTrue(report["read_only"])
        self.assertFalse(report["gameplay_runtime_verified"])
        self.assertFalse(report["native_arbitrary_actor_spawning_enabled"])
        self.assertTrue(any(x["actor"] == "StaticMeshActor__1"
                            and x["export"] == 1
                            for x in report["candidates"]))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_original_state_idle_clone_dry_run_does_not_write(self):
        result = self.world.clone_existing_static_prop(
            original_export=1, original_actor="StaticMeshActor__1",
            delta_native_xyz=(100, 0, 0), output=self.output)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["status"], "binary-reparsed-runtime-unverified")
        self.assertFalse(result["runtime_game_verified"])
        self.assertTrue(result["original_bytes_unchanged"])
        self.assertTrue(result["clone_frame_normalized"])
        self.assertTrue(result["clone_payload_provenance_verified"])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_isolated_clone_native_save_and_entire_binary_replay(self):
        result = self.world.clone_existing_static_prop(
            original_export=1, original_actor="StaticMeshActor__1",
            delta_native_xyz=(100, 0, 0), output=self.output, write=True)
        self.assertEqual(result["status"],
                         "isolated-GMP-created-runtime-unverified")
        self.assertTrue(result["independent_verified_binary_structure"])
        self.assertTrue(self.output.is_file())
        self.assertTrue(self.manifest.is_file())
        saved = Package(self.output)
        source = Package(self.source)
        self.assertEqual(len(saved.exports), len(source.exports) + 1)
        self.assertEqual(saved.guid, source.guid)
        self.assertEqual(saved.scene_actors()[0][0]["name"],
                         "StaticMeshActor__1")
        independent = self.world.verify_saved_clone(self.output)
        self.assertTrue(independent["verified_binary_structure"])
        self.assertTrue(independent["new_clone_state_normalized"])
        self.assertTrue(independent["original_export_untouched"])
        self.assertFalse(independent["gameplay_runtime_verified"])
        self.assertEqual(self.source.read_bytes(), self.original)
        original_exports = source.exports
        new_exports = saved.exports
        self.assertEqual(source.payload(original_exports[0]),
                         saved.payload(new_exports[0]))

    def test_refuse_existing_native_output_never_overwrites(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"original user file")
        with self.assertRaises(ValueError):
            self.world.clone_existing_static_prop(
                original_export=1, original_actor="StaticMeshActor__1",
                delta_native_xyz=(100, 0, 0),
                output=self.output, write=True)
        self.assertEqual(self.output.read_bytes(), b"original user file")

    def test_refuse_game_install_source_folder_and_other_game_maps(self):
        for output in (
            self.source,
            self.source.parent / self.source.name,
            self.root / "AnotherInstall" / "Content" / "DX2" / "Maps"
            / self.source.name,
        ):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.world.clone_existing_static_prop(
                    original_export=1, original_actor="StaticMeshActor__1",
                    delta_native_xyz=(100, 0, 0),
                    output=output, write=True)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_refuse_unknown_actor_export_and_invalid_delta(self):
        bad_args = [
            (2, "StaticMeshActor__1", (100, 0, 0)),
            (1, "BogusActor", (100, 0, 0)),
            (1, "StaticMeshActor__1", (0, 0, 0)),
            (1, "StaticMeshActor__1", (5000, 0, 0)),
            (1, "StaticMeshActor__1", (float("nan"), 0, 0)),
            (1, "StaticMeshActor__1", (True, 0, 0)),
            (1, "StaticMeshActor__1", (100,)),
        ]
        for index, name, delta in bad_args:
            with self.subTest(index=index, name=name, delta=delta):
                with self.assertRaises(ValueError):
                    self.world.clone_existing_static_prop(
                        original_export=index, original_actor=name,
                        delta_native_xyz=delta, output=self.output, write=True)
        self.assertFalse(self.output.exists())

    def test_rejected_source_drift_never_writes_clone(self):
        self.source.write_bytes(self.original + b"DRIFT")
        with self.assertRaisesRegex(ValueError, "changed"):
            self.world.clone_existing_static_prop(
                original_export=1, original_actor="StaticMeshActor__1",
                delta_native_xyz=(100, 0, 0),
                output=self.output, write=True)
        self.assertFalse(self.output.exists())

    def test_saved_clone_manifest_runtime_claim_refused(self):
        self.world.clone_existing_static_prop(
            original_export=1, original_actor="StaticMeshActor__1",
            delta_native_xyz=(100, 0, 0), output=self.output, write=True)
        report = json.loads(self.manifest.read_text("utf8"))
        report["runtime_game_verified"] = True
        self.manifest.write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            self.world.verify_saved_clone(self.output)

    def test_saved_clone_forged_output_sha_cannot_bypass_rebuild(self):
        self.world.clone_existing_static_prop(
            original_export=1, original_actor="StaticMeshActor__1",
            delta_native_xyz=(100, 0, 0), output=self.output, write=True)
        data = bytearray(self.output.read_bytes())
        data[-1] ^= 1
        self.output.write_bytes(data)
        doc = json.loads(self.manifest.read_text("utf8"))
        doc["output_sha256"] = hashlib.sha256(data).hexdigest()
        self.manifest.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "deviates"):
            self.world.verify_saved_clone(self.output)

    def test_native_clone_cli_dry_run_explicit_write_and_reverify(self):
        source = ("--map", str(self.source))
        listed = self.cli("clone-candidates", *source, "--limit", "10")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(json.loads(listed.stdout)["candidate_count"], 1)
        args = ("clone-prop", *source,
                "--actor", "StaticMeshActor__1", "--export", "1",
                "--dx", "100", "--dy", "0", "--dz", "0",
                "--output", str(self.output))
        dry = self.cli(*args)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["status"],
                         "binary-reparsed-runtime-unverified")
        self.assertFalse(self.output.exists())
        written = self.cli(*args, "--write")
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertTrue(json.loads(written.stdout)[
            "independent_full_binary_verification"])
        verify = self.cli("verify-clone", *source, "--output", str(self.output))
        self.assertEqual(verify.returncode, 0, verify.stderr)
        self.assertTrue(json.loads(verify.stdout)["verified_binary_structure"])
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
