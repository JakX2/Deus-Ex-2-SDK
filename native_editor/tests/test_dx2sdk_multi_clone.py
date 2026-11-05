"""Public DX2SDK original multi-prop clone / source-locked plan regression.

Invented UE95 GMP with one neutral, unlinked StaticMeshActor and valid
synthetic Level actor list. No original DXIW data or proprietary binaries.
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
from dx2sdk.multi_clones import (
    PLAN_SCHEMA, NATIVE_SCHEMA, build_multi_clone_plan,
    write_multi_clone_plan, load_multi_clone_plan,
    duplicate_existing_static_props, apply_multi_clone_plan,
    verify_saved_multi_clone,
)
from dx2inspect import Package
from test_dx2_actor_clone_probe import level_fixture


class DX2SDKMultiPropTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2sdk_public_multi_clone_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "FixtureOriginal" / "M1_Test.gmp"
        self.source.parent.mkdir()
        self.source_bytes = level_fixture(self.source)
        self.sha = hashlib.sha256(self.source_bytes).hexdigest()
        self.world = DX2Map.open(self.source)
        self.plan = self.root / "PrivateProject" / "clone_plan.json"
        self.output = self.root / "IsolatedGMP" / self.source.name
        self.manifest = self.output.with_suffix(".dx2ed-multi-prop-clone.json")
        self.copies = [
            {"actor": "StaticMeshActor__1", "export": 1,
             "delta": [100, 0, 0]},
            {"actor": "StaticMeshActor__1", "export": 1,
             "delta": [0, 100, 50]},
            {"actor": "StaticMeshActor__1", "export": 1,
             "delta": [-50, 0, 75]},
        ]

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", *args],
            cwd=ROOT, capture_output=True, text=True, timeout=60)

    def test_build_plan_only_verifies_original_in_memory(self):
        doc = build_multi_clone_plan(self.world, self.copies)
        self.assertEqual(doc["schema"], PLAN_SCHEMA)
        self.assertEqual(doc["source_map"], self.source.name)
        self.assertEqual(doc["source_map_sha256"], self.sha)
        self.assertEqual(len(doc["copies"]), 3)
        self.assertTrue(doc["original_source_read_only"])
        self.assertFalse(doc["runtime_game_verified"])
        self.assertFalse(doc["native_arbitrary_actor_spawning_enabled"])
        self.assertFalse(doc["native_script_writer_enabled"])
        self.assertFalse(doc["native_collision_bsp_writer_enabled"])
        self.assertFalse(self.plan.exists())
        self.assertFalse(self.output.exists())
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_private_plan_roundtrip_dry_run_three_clones_and_binary_replay(self):
        generated = write_multi_clone_plan(self.world, self.copies, self.plan)
        self.assertEqual(generated["schema"], PLAN_SCHEMA)
        self.assertEqual(load_multi_clone_plan(self.world, self.plan),
                         [{**x, "delta": [float(v) for v in x["delta"]]}
                          for x in self.copies])
        dry = apply_multi_clone_plan(self.world, self.plan, self.output)
        self.assertEqual(dry["status"], "binary-reparsed-runtime-unverified")
        self.assertEqual(len(dry["copies"]), 3)
        self.assertFalse(self.output.exists())
        written = apply_multi_clone_plan(
            self.world, self.plan, self.output, write=True)
        self.assertEqual(written["schema"], NATIVE_SCHEMA)
        self.assertEqual(written["status"],
                         "isolated-GMP-created-runtime-unverified")
        self.assertTrue(written["independent_full_binary_verification"])
        self.assertTrue(self.output.is_file())
        self.assertTrue(self.manifest.is_file())
        result = verify_saved_multi_clone(self.world, self.output)
        self.assertTrue(result["verified_binary_structure"])
        self.assertTrue(result["original_exports_preserved"])
        self.assertTrue(result["new_clones_state_normalized"])
        self.assertEqual(result["new_actor_count"], 3)
        self.assertFalse(result["gameplay_runtime_verified"])
        self.assertFalse(result["native_arbitrary_actor_spawning_enabled"])
        original = Package(self.source)
        output = Package(self.output)
        self.assertEqual(len(original.exports), 2)
        self.assertEqual(len(output.exports), 5)
        self.assertEqual(len(original.names) + 3, len(output.names))
        self.assertEqual(output.guid, original.guid)
        self.assertEqual(original.payload(original.exports[0]),
                         output.payload(output.exports[0]))
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_direct_two_copy_dry_run_and_isolated_save(self):
        copies = self.copies[:2]
        dry = self.world.duplicate_existing_static_props(copies, self.output)
        self.assertEqual(len(dry["copies"]), 2)
        self.assertFalse(self.output.exists())
        report = self.world.duplicate_existing_static_props(
            copies, self.output, write=True)
        self.assertTrue(report["independent_full_binary_verification"])
        self.assertEqual(self.world.verify_saved_multi_clone(
            self.output)["new_actor_count"], 2)

    def test_plan_tampering_of_source_identity_and_disabled_flags_refused(self):
        write_multi_clone_plan(self.world, self.copies, self.plan)
        base = json.loads(self.plan.read_text("utf8"))
        for field, forged in (
            ("source_map_sha256", "f" * 64),
            ("source_map", "OtherMap.gmp"),
            ("runtime_game_verified", True),
            ("native_arbitrary_actor_spawning_enabled", True),
            ("native_script_writer_enabled", True),
            ("native_collision_bsp_writer_enabled", True),
            ("original_source_read_only", False),
            ("schema", "fake"),
        ):
            with self.subTest(field=field):
                self.plan.write_text(json.dumps({**base, field: forged}))
                with self.assertRaises(ValueError):
                    load_multi_clone_plan(self.world, self.plan)
        self.plan.write_text(json.dumps(base))
        with self.assertRaisesRegex(ValueError, "fresh private"):
            write_multi_clone_plan(self.world, self.copies, self.plan)
        self.assertFalse(self.output.exists())

    def test_plan_tampered_actor_export_delta_or_bogus_extra_rejected(self):
        write_multi_clone_plan(self.world, self.copies, self.plan)
        original = json.loads(self.plan.read_text("utf8"))
        for field, forged in (
            ("actor", "NPC"),
            ("export", 2),
            ("delta", [0, 0, 0]),
            ("delta", [float("nan"), 0, 0]),
            ("delta", [True, 0, 0]),
            ("delta", [5000, 0, 0]),
        ):
            with self.subTest(field=field):
                edited = json.loads(json.dumps(original))
                edited["copies"][0][field] = forged
                self.plan.write_text(json.dumps(edited))
                with self.assertRaises(ValueError):
                    load_multi_clone_plan(self.world, self.plan)
        wrong = json.loads(json.dumps(original))
        wrong["copies"][0]["unknown"] = "injected"
        self.plan.write_text(json.dumps(wrong))
        with self.assertRaises(ValueError):
            load_multi_clone_plan(self.world, self.plan)
        self.assertFalse(self.output.exists())

    def test_reject_invalid_clone_count_or_bad_native_delta(self):
        cases = (
            [],
            [self.copies[0]],
            self.copies * 3,
            [{**self.copies[0], "delta": [float("inf"), 0, 0]},
             self.copies[1]],
            [{**self.copies[0], "delta": [0, 0, 0]}, self.copies[1]],
            [{**self.copies[0], "actor": "NPC"}, self.copies[1]],
            [{**self.copies[0], "export": True}, self.copies[1]],
        )
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                build_multi_clone_plan(self.world, rows)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_reject_original_or_another_game_maps_output(self):
        for path in (
            self.source,
            self.source.parent / self.source.name,
            self.root / "NewInstallation" / "Content" / "DX2" / "Maps"
            / self.source.name,
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                duplicate_existing_static_props(
                    self.world, self.copies, path, write=True)
        for target in (
            self.source.parent / "clone_plan.json",
            self.root / "Content" / "DX2" / "Maps" / "plan.json",
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                write_multi_clone_plan(self.world, self.copies, target)
            self.assertFalse(target.exists())
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_existing_gmp_and_manifest_are_never_overwritten(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"preexisting original user content")
        with self.assertRaises(ValueError):
            duplicate_existing_static_props(
                self.world, self.copies, self.output, write=True)
        self.assertEqual(self.output.read_bytes(),
                         b"preexisting original user content")
        self.output.unlink()
        self.manifest.write_text("existing manifest")
        with self.assertRaises(FileExistsError):
            duplicate_existing_static_props(
                self.world, self.copies, self.output, write=True)
        self.assertEqual(self.manifest.read_text(), "existing manifest")

    def test_forged_manifest_runtime_flags_and_tampered_output_refused(self):
        duplicate_existing_static_props(
            self.world, self.copies, self.output, write=True)
        base = json.loads(self.manifest.read_text("utf8"))
        for field, value in (
            ("runtime_game_verified", True),
            ("original_bytes_unchanged", False),
            ("game_installation_modified", True),
            ("source_sha256", "0" * 64),
        ):
            with self.subTest(field=field):
                self.manifest.write_text(json.dumps({**base, field: value}))
                with self.assertRaises(ValueError):
                    verify_saved_multi_clone(self.world, self.output)
        self.manifest.write_text(json.dumps(base))
        contents = bytearray(self.output.read_bytes())
        contents[-1] ^= 1
        self.output.write_bytes(contents)
        base["output_sha256"] = hashlib.sha256(contents).hexdigest()
        self.manifest.write_text(json.dumps(base))
        with self.assertRaisesRegex(ValueError, "deviates"):
            verify_saved_multi_clone(self.world, self.output)

    def test_original_source_sha_drift_refuses_plan_and_write(self):
        self.source.write_bytes(self.source_bytes + b"DIFFERENT")
        with self.assertRaisesRegex(ValueError, "changed"):
            self.world.duplicate_existing_static_props(
                self.copies, self.output, write=True)
        with self.assertRaisesRegex(ValueError, "changed"):
            self.world.build_multi_clone_plan(self.copies)
        self.assertFalse(self.output.exists())

    def test_cli_make_plan_apply_dry_run_explicit_write_and_replay(self):
        make = [
            "make-multi-clone-plan", "--map", str(self.source),
            "--copy", "1", "100", "0", "0",
            "--copy", "1", "0", "100", "50",
            "--copy", "1", "-50", "0", "75",
            "--plan", str(self.plan),
        ]
        formed = self.cli(*make)
        self.assertEqual(formed.returncode, 0, formed.stderr)
        self.assertEqual(json.loads(formed.stdout)[
            "planned_existing_static_prop_copies"], 3)
        self.assertTrue(self.plan.is_file())
        command = [
            "apply-multi-clone-plan", "--map", str(self.source),
            "--plan", str(self.plan), "--output", str(self.output),
        ]
        dry = self.cli(*command)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["status"],
                         "binary-reparsed-runtime-unverified")
        self.assertFalse(self.output.exists())
        written = self.cli(*command, "--write")
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertTrue(json.loads(written.stdout)[
            "independent_full_binary_verification"])
        checked = self.cli("verify-multi-clone", "--map",
                           str(self.source), "--output", str(self.output))
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertTrue(json.loads(checked.stdout)["verified_binary_structure"])
        self.assertEqual(json.loads(checked.stdout)["new_actor_count"], 3)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)


if __name__ == "__main__":
    unittest.main()
