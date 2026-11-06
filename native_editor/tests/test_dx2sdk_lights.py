"""Standalone SDK Light audit and source-only authored bLightOn tests.

All GMPs below are generated from invented v95 package fixtures.
No original retail map, executable or game art is bundled.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dx2sdk import DX2Map
from test_dx2_light_dependency_audit import _synthetic_light_map
from test_dx2_gamesys_audit import fixture_with_gamesys
from tools.build_dx2sdk_source_release import build, ARCHIVE
from upkg import Package
from upkgwrite import ActorEdit, PackageWriter


def synthetic_switch_map(path: Path) -> bytes:
    fixture_with_gamesys(path)
    pkg = Package(path)
    writer = PackageWriter(pkg)
    actor = ActorEdit(writer, pkg.exports[0])
    block = actor.block(237)
    block.id = (0x80 << 16) | 1487
    block.data = b"\x01"
    actor.changes.append("invented authored bLightOn GameSys fixture")
    assert actor.commit()
    data = writer.write()
    path.write_bytes(data)
    return data


class DX2SDKLightTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="dx2sdk_lights_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.light_source = self.root / "Original" / "M1_Lights.gmp"
        self.light_source.parent.mkdir()
        self.light_bytes = _synthetic_light_map(self.light_source)
        self.switch_source = self.root / "Fixtures" / "M1_Switch.gmp"
        self.switch_source.parent.mkdir()
        self.switch_bytes = synthetic_switch_map(self.switch_source)
        self.output = self.root / "Private" / self.switch_source.name

    def cli(self, *args, cwd=ROOT):
        return subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", *args],
            cwd=cwd, capture_output=True, text=True, timeout=60)

    def test_light_region_audit_and_private_export(self):
        world = DX2Map.open(self.light_source)
        audit = world.audit_original_lights(export=1)
        self.assertEqual(audit["source_light_count"], 1)
        self.assertEqual(audit["lights"][0]["region_leaf"], 20)
        self.assertEqual(audit["lights"][0]["region_zone_number_low"], 8)
        self.assertFalse(audit["native_light_spawn_enabled"])
        self.assertFalse(audit["lights"][0]["state_frame_clone_verified"])
        target = self.root / "Private" / "lights.json"
        self.assertEqual(
            world.export_original_lights(target)["source_sha256"],
            hashlib.sha256(self.light_bytes).hexdigest())
        self.assertTrue(target.exists())
        with self.assertRaisesRegex(ValueError, "fresh private"):
            world.export_original_lights(target)
        with self.assertRaisesRegex(ValueError, "fresh private"):
            world.export_original_lights(
                self.root / "Other" / "Content" / "DX2" / "Maps" / "lights.json")
        self.assertEqual(self.light_source.read_bytes(), self.light_bytes)
        result = self.cli("audit-lights", "--map", str(self.light_source), "--export", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["lights"][0]["export"], 1)
        invalid = self.cli("audit-lights", "--map", str(self.light_source), "--export", "2")
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(self.light_source.read_bytes(), self.light_bytes)

    def test_switch_list_dry_write_and_independent_verification(self):
        world = DX2Map.open(self.switch_source)
        candidates = world.original_light_switches(limit=10)
        self.assertEqual(candidates["candidate_count"], 1)
        item = candidates["shown"][0]
        self.assertEqual(item["actor"], "StaticMeshActor__1")
        self.assertEqual(item["export"], 1)
        self.assertIs(item["original_value"], True)
        self.assertFalse(item["runtime_lighting_effect_verified"])
        params = dict(export=1, actor="StaticMeshActor__1",
                      expected=True, output=self.output)
        dry = world.set_existing_light_switch(**params)
        self.assertEqual(dry["status"], "dry-run")
        self.assertTrue(dry["independent_full_package_byte_match"])
        self.assertFalse(self.output.exists())
        saved = world.set_existing_light_switch(**params, write=True)
        self.assertTrue(saved["verified_binary_structure"])
        self.assertEqual(saved["changed_bytes"], 1)
        verified = world.verify_saved_light_switch(self.output)
        self.assertEqual(verified["unapproved_bytes"], 0)
        diff = [i for i,(a,b) in enumerate(zip(self.switch_bytes,self.output.read_bytes()))
                if a!=b]
        self.assertEqual(len(diff), 1)
        self.assertEqual(self.switch_source.read_bytes(), self.switch_bytes)
        with self.assertRaises(ValueError):
            world.set_existing_light_switch(**params, write=True)
        with self.assertRaises(ValueError):
            world.set_existing_light_switch(**{**params, "expected": False})

    def test_reject_wrong_paths_mutated_source_and_tampered_outputs(self):
        world = DX2Map.open(self.switch_source)
        opts = dict(export=1, actor="StaticMeshActor__1", expected=True)
        for path in (self.switch_source,
                     self.switch_source.parent / "nested" / self.switch_source.name,
                     self.root / "NewRetail" / "Content" / "DX2" / "Maps" /
                     self.switch_source.name):
            with self.subTest(path=path), self.assertRaises(ValueError):
                world.set_existing_light_switch(**opts, output=path)
        with self.assertRaises(ValueError):
            world.set_existing_light_switch(
                **{**opts, "actor": "Light__9"}, output=self.output)
        with self.assertRaises(ValueError):
            world.set_existing_light_switch(
                **{**opts, "export": True}, output=self.output)
        with self.assertRaises(ValueError):
            world.original_light_switches(limit=1001)
        world.set_existing_light_switch(**opts, output=self.output, write=True)
        report_path = self.output.with_suffix(".dx2ed-gamesys-bool.json")
        manifest = json.loads(report_path.read_text())
        manifest["gameplay_effect_verified"] = True
        report_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "unsafe claims"):
            world.verify_saved_light_switch(self.output)
        manifest["gameplay_effect_verified"] = False
        report_path.write_text(json.dumps(manifest))
        wrong = bytearray(self.output.read_bytes())
        wrong[-1] ^= 1
        self.output.write_bytes(wrong)
        with self.assertRaisesRegex(ValueError, "replay"):
            world.verify_saved_light_switch(self.output)
        self.output.write_bytes(self.switch_bytes)
        with self.assertRaises(ValueError):
            world.verify_saved_light_switch(self.output)
        self.switch_source.write_bytes(self.switch_bytes + b"tampered")
        with self.assertRaises(ValueError):
            world.original_light_switches()

    def test_portable_zip_exposes_same_native_light_workflow(self):
        zip_path = self.root / "dx2sdk.zip"
        build(ROOT, zip_path)
        with ZipFile(zip_path) as archive:
            self.assertIn(f"{ARCHIVE}/dx2sdk/lights.py", archive.namelist())
            archive.extractall(self.root / "extracted")
        sdk = self.root / "extracted" / ARCHIVE
        report = self.cli("audit-lights", "--map", str(self.light_source),
                          "--export", "1", cwd=sdk)
        self.assertEqual(report.returncode, 0, report.stderr)
        switch = self.cli("light-switches", "--map", str(self.switch_source), cwd=sdk)
        self.assertEqual(switch.returncode, 0, switch.stderr)
        self.assertEqual(json.loads(switch.stdout)["candidate_count"], 1)
        args = ("set-light-switch", "--map", str(self.switch_source),
                "--actor", "StaticMeshActor__1", "--export", "1",
                "--expect", "true", "--output", str(self.output))
        dry = self.cli(*args, cwd=sdk)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertFalse(self.output.exists())
        written = self.cli(*args, "--write", cwd=sdk)
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertTrue(json.loads(written.stdout)["verified_binary_structure"])
        verified = self.cli("verify-light-switch", "--map", str(self.switch_source),
                            "--output", str(self.output), cwd=sdk)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertTrue(json.loads(verified.stdout)["verified_binary_structure"])
        self.assertEqual(self.switch_source.read_bytes(), self.switch_bytes)


if __name__ == "__main__":
    unittest.main()
