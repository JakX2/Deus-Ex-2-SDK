"""End-to-end source-only DX2SDK v0.1 API and portable CLI tests.

Use a synthetic structurally valid DX2 v95 GMP, one rendered source actor,
original-style private source hash cache, TSD ZIP and 21-kind IBD. All checks
are file-local, require no retail assets, and never modify the original.
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
from dx2sdk import DX2Map, SDK_SCHEMA
from dx2inspect import Package
from test_native_save_as import fixture_gmp
from test_dx2_script_ibd_provenance import ibd_resource, tsd


class SDKPublicSurfaceTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2sdk_fixture_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.maps = self.root / "RetailFixture" / "Content" / "DX2" / "Maps"
        self.maps.mkdir(parents=True)
        self.source = self.maps / "M1_Test.gmp"
        self.source.write_bytes(fixture_gmp())
        self.original_sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.cache = self.root / "PrivateCache" / "actors.json"
        self.cache.parent.mkdir()
        self.actor = {
            "name": "StaticMeshActor__1",
            "class": "StaticMeshActor",
            "export": 1,
            "mesh": "SyntheticCube",
            "location": [100.0, 200.0, 300.0],
            "rotation": [0, 0, 0],
            "game_properties": [],
            "trigger_script_serialized": None,
        }
        self.cache.write_text(json.dumps({
            "meta": {"source_map": self.source.name,
                     "source_sha256": self.original_sha},
            "actors": [self.actor],
        }), encoding="utf8")
        self.zip = self.root / "PrivateOriginalSource" / "TriggerScript.zip"
        self.zip.parent.mkdir()
        with ZipFile(self.zip, "w") as z:
            z.writestr("Defs/TS_TEST.tsd", tsd())
        self.ibd = self.maps / "M1_Test.ibd"
        self.ibd.write_bytes(ibd_resource(tsd()[12:]))
        self.output = self.root / "SDKIsolatedOutput" / self.source.name

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", *args],
            cwd=ROOT, text=True, capture_output=True, timeout=25)

    def test_import_and_original_gmp_identification(self):
        project = DX2Map.open(self.source)
        info = project.info()
        self.assertEqual(info["schema"], SDK_SCHEMA)
        self.assertEqual(info["source_sha256"], self.original_sha)
        self.assertEqual(info["package_version"], 95)
        self.assertEqual(info["licensee_version"], 69)
        self.assertFalse(info["source_actor_cache_verified"])
        self.assertFalse(info["gameplay_runtime_verified"])
        self.assertFalse(info["script_writer_available"])
        self.assertFalse(info["bsp_or_collision_rebuild_available"])
        self.assertEqual(info["exports"], 1)
        self.assertEqual(self.source.read_bytes(), fixture_gmp())

    def test_original_actor_hierarchy_and_cache_optional(self):
        without = DX2Map.open(self.source)
        native = without.actors()
        self.assertEqual(native["count"], 1)
        self.assertEqual(native["shown"][0]["name"], "StaticMeshActor__1")
        self.assertEqual(native["shown"][0]["location_native_xyz"],
                         [100.0, 200.0, 300.0])
        self.assertNotIn("mesh", native["shown"][0])
        project = DX2Map.open(self.source, self.cache)
        original = project.actors(actor_class="StaticMeshActor")
        self.assertEqual(original["count"], 1)
        self.assertEqual(original["shown"][0]["mesh"], "SyntheticCube")
        self.assertFalse(original["shown"][0]["runtime_actor_script_link_verified"])
        self.assertEqual(project.actors(actor_class="Light")["count"], 0)
        self.assertEqual(project.actors(limit=0)["shown"], [])
        with self.assertRaises(ValueError):
            project.actors(limit=-1)

    def test_script_definitions_and_original_ibd_are_read_only(self):
        project = DX2Map.open(self.source, self.cache)
        document = project.script_definitions(self.zip)
        self.assertEqual(document["schema"], SDK_SCHEMA)
        self.assertEqual(len(document["script_definitions"]), 1)
        self.assertEqual(document["script_definitions"][0]["id"], "TS_TEST")
        self.assertFalse(document["runtime_actor_script_link_verified"])
        original_ibd = self.ibd.read_bytes()
        evidence = project.script_resources(self.zip, self.ibd)
        self.assertEqual(evidence["counts"]["exact_payload"], 1)
        self.assertEqual(evidence["counts"]["different_payload"], 0)
        self.assertEqual(evidence["entries"][0]["status"], "exact_payload")
        self.assertFalse(evidence["native_script_writer_enabled"])
        self.assertEqual(self.ibd.read_bytes(), original_ibd)

    def test_standalone_script_calls_refuse_without_source_cache(self):
        project = DX2Map.open(self.source)
        with self.assertRaisesRegex(ValueError, "actors.json"):
            project.script_definitions(self.zip)
        with self.assertRaisesRegex(ValueError, "actors.json"):
            project.script_resources(self.zip, self.ibd)
        with self.assertRaisesRegex(ValueError, "actors.json"):
            project.save_as_translations(
                {"StaticMeshActor__1": [110, 220, 330]}, self.output)

    def test_native_translation_dry_run_then_write_independently_verified(self):
        project = DX2Map.open(self.source, self.cache)
        original_data = self.source.read_bytes()
        target = [125.0, 275.0, 350.0]
        dry = project.save_as_translations(
            {"StaticMeshActor__1": target}, self.output)
        self.assertEqual(dry["status"], "dry-run")
        self.assertFalse(self.output.exists())
        self.assertEqual(dry["sdk_schema"], SDK_SCHEMA)
        self.assertEqual(self.source.read_bytes(), original_data)
        actual = project.save_as_translations(
            {"StaticMeshActor__1": target}, self.output, write=True)
        self.assertEqual(actual["status"], "written-unverified")
        verify = actual["independent_binary_verification"]
        self.assertTrue(verify["verified_binary_structure"])
        self.assertFalse(verify["game_verified"])
        self.assertGreater(verify["changed_bytes"], 0)
        self.assertEqual(self.source.read_bytes(), original_data)
        edited = Package(self.output)
        location = edited.decode_object(edited.exports[0])["Location"]
        self.assertAlmostEqual(location["X"], target[0])
        self.assertAlmostEqual(location["Y"], target[1])
        self.assertAlmostEqual(location["Z"], target[2])
        independent = project.verify_saved_translation(self.output)
        self.assertTrue(independent["verified_binary_structure"])
        self.assertFalse(independent["game_verified"])

    def test_existing_copy_never_overwritten(self):
        project = DX2Map.open(self.source, self.cache)
        self.output.parent.mkdir()
        self.output.write_bytes(b"keep_me")
        with self.assertRaisesRegex(ValueError, "fresh copy"):
            project.save_as_translations(
                {"StaticMeshActor__1": [125, 275, 350]}, self.output,
                write=True)
        self.assertEqual(self.output.read_bytes(), b"keep_me")

    def test_writer_rejects_retail_install_folder_even_if_different_copy(self):
        project = DX2Map.open(self.source, self.cache)
        other_game = self.root / "AnotherInstallation" / "Content" / "DX2" / "Maps"
        with self.assertRaisesRegex(ValueError, "Never write"):
            project.save_as_translations(
                {"StaticMeshActor__1": [125, 275, 350]},
                other_game / self.source.name,
                write=True)
        self.assertFalse((other_game / self.source.name).exists())

    def test_writer_rejects_unknown_or_invalid_actor_positions(self):
        project = DX2Map.open(self.source, self.cache)
        for moved in (
            {"ImaginaryActor": [125, 275, 350]},
            {"StaticMeshActor__1": [100, 200, 300]},
            {"StaticMeshActor__1": [float("nan"), 275, 350]},
            {"StaticMeshActor__1": [True, 275, 350]},
            {"StaticMeshActor__1": [125, float("inf"), 350]},
            {"StaticMeshActor__1": [125, 275]},
        ):
            with self.subTest(moved=moved), self.assertRaises(ValueError):
                project.save_as_translations(moved, self.output, write=True)
        self.assertFalse(self.output.exists())

    def test_actor_cache_must_match_native_identity_not_just_sha(self):
        document = json.loads(self.cache.read_text("utf8"))
        document["actors"][0]["name"] = "ForgedActor"
        self.cache.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "identity"):
            DX2Map.open(self.source, self.cache)

    def test_open_map_rejects_wrong_licensee_and_source_file_tampering(self):
        project = DX2Map.open(self.source)
        modified = bytearray(self.source.read_bytes())
        modified[6] = 133
        self.source.write_bytes(modified)
        with self.assertRaisesRegex(ValueError, "supports DX2"):
            DX2Map.open(self.source)
        with self.assertRaisesRegex(ValueError, "changed"):
            project.info()

    def test_cli_package_help_info_and_actor_list(self):
        for sub in (["--help"], ["info", "--map", str(self.source)],
                    ["actors", "--map", str(self.source), "--limit", "1"]):
            with self.subTest(sub=sub):
                result = self.cli(*sub)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Traceback", result.stdout)
        parsed = json.loads(self.cli("actors", "--map", str(self.source)).stdout)
        self.assertEqual(parsed["count"], 1)

    def test_cli_dry_run_write_verify_and_source_cache_mismatch(self):
        args = ("--map", str(self.source), "--actors", str(self.cache),
                "--actor", "StaticMeshActor__1",
                "--x", "125", "--y", "275", "--z", "350",
                "--output", str(self.output))
        dry = self.cli("move", *args)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["status"], "dry-run")
        self.assertFalse(self.output.exists())
        saved = self.cli("move", *args, "--write")
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertTrue(json.loads(saved.stdout)["independent_binary_verification"][
            "verified_binary_structure"])
        verified = self.cli("verify-move", "--map", str(self.source),
                            "--output", str(self.output))
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertTrue(json.loads(verified.stdout)["verified_binary_structure"])
        again = self.cli("move", *args, "--write")
        self.assertEqual(again.returncode, 2)
        self.assertEqual(json.loads(again.stderr)["status"], "refused")
        self.assertNotIn(str(self.source), again.stderr)

    def test_cli_script_source_inspection_and_ibd_summary(self):
        for command in (
            ["scripts", "--map", str(self.source), "--actors", str(self.cache),
             "--zip", str(self.zip)],
            ["ibd", "--map", str(self.source), "--actors", str(self.cache),
             "--zip", str(self.zip), "--ibd", str(self.ibd)],
        ):
            with self.subTest(command=command):
                result = self.cli(*command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(str(self.source), result.stdout)
        source = json.loads(self.cli(
            "scripts", "--map", str(self.source), "--actors", str(self.cache),
            "--zip", str(self.zip)).stdout)
        self.assertEqual(source["shown"][0]["id"], "TS_TEST")


if __name__ == "__main__":
    unittest.main()
