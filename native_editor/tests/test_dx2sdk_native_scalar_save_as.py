"""Synthetic DX2SDK native top-level IntProperty/FloatProperty Save As tests.

Never uses actual Deus Ex retail data. This tests real UE95 tagged-property
serialization and independently validates changes against an original GMP.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dx2sdk import DX2Map
from dx2sdk.scalars import (
    SCHEMA, _encode, original_scalar_fields,
    save_as_scalar_copy, verify_scalar_copy)
from dx2inspect import Package
from test_native_save_as import fixture_gmp


class NativeTaggedScalarWriterTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2sdk_native_scalar_test_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.maps = self.root / "OriginalGameFixture" / "Content" / "DX2" / "Maps"
        self.maps.mkdir(parents=True)
        self.source = self.maps / "M1_Test.gmp"
        self.source.write_bytes(fixture_gmp())
        self.original_bytes = self.source.read_bytes()
        self.cache = self.root / "PrivateCache" / "actors.json"
        self.cache.parent.mkdir()
        self.cache.write_text(json.dumps({
            "meta": {
                "source_map": self.source.name,
                "source_sha256": hashlib.sha256(self.original_bytes).hexdigest(),
            },
            "actors": [{
                "name": "StaticMeshActor__1",
                "class": "StaticMeshActor",
                "mesh": "SyntheticCube",
                "export": 1,
                "location": [100.0, 200.0, 300.0],
                "rotation": [0, 0, 0],
                "game_properties": [],
            }],
        }), encoding="utf8")
        self.output = self.root / "IsolatedOutput" / self.source.name
        self.world = DX2Map.open(self.source, self.cache)
        self.edits = {"StaticMeshActor__1": {"FixtureFlag": 123456}}
        self.private_manifest = self.output.with_suffix(".dx2sdk-scalar.json")

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", "-m", "dx2sdk", *args],
                              cwd=ROOT, capture_output=True,
                              text=True, timeout=30)

    def test_source_native_int32_field_inventory_is_typed_and_restrictive(self):
        report = self.world.native_scalar_fields("StaticMeshActor__1")
        self.assertEqual(report["schema"], SCHEMA)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["runtime_game_verified"])
        self.assertFalse(report["native_gamesys_or_script_writer_enabled"])
        self.assertEqual(report["fields"], [
            {"property": "FixtureFlag", "type": "int32",
             "source_value": 98765},
        ])
        self.assertEqual(self.original_bytes, self.source.read_bytes())

    def test_dry_run_never_writes_output_or_manifest(self):
        result = self.world.save_as_scalar_changes(self.edits, self.output)
        self.assertEqual(result["status"], "dry-run")
        self.assertEqual(result["edited_field_count"], 1)
        self.assertGreater(result["changed_byte_count"], 0)
        self.assertFalse(result["runtime_game_verified"])
        self.assertFalse(result["native_script_writer_enabled"])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.private_manifest.exists())
        self.assertEqual(self.original_bytes, self.source.read_bytes())

    def test_int32_native_patch_in_isolated_copy_and_full_file_verifier(self):
        report = self.world.save_as_scalar_changes(
            self.edits, self.output, write=True)
        self.assertEqual(report["status"], "written-unverified-gameplay")
        self.assertEqual(report["edited_field_count"], 1)
        self.assertTrue(report["independent_byte_validation"])
        self.assertFalse(report["runtime_game_verified"])
        self.assertTrue(self.output.exists())
        self.assertTrue(self.private_manifest.exists())
        out = Package(self.output)
        self.assertEqual(out.decode_object(out.exports[0])["FixtureFlag"], 123456)
        self.assertEqual(out.decode_object(out.exports[0])["Location"],
                         {"X": 100.0, "Y": 200.0, "Z": 300.0})
        self.assertEqual(self.original_bytes, self.source.read_bytes())
        verified = self.world.verify_saved_scalar_changes(self.output)
        self.assertTrue(verified["verified_binary_structure"])
        self.assertEqual(verified["unapproved_bytes"], 0)
        self.assertEqual(verified["changed_fields"], 1)
        self.assertFalse(verified["runtime_game_verified"])

    def test_different_scalar_patches_never_silently_overwrite(self):
        self.world.save_as_scalar_changes(self.edits, self.output, write=True)
        before = self.output.read_bytes()
        manifest = self.private_manifest.read_bytes()
        with self.assertRaises(ValueError):
            self.world.save_as_scalar_changes(
                {"StaticMeshActor__1": {"FixtureFlag": 1}},
                self.output, write=True)
        self.assertEqual(before, self.output.read_bytes())
        self.assertEqual(manifest, self.private_manifest.read_bytes())

    def test_reject_missing_original_cache_and_unknown_actor(self):
        no_cache = DX2Map.open(self.source)
        with self.assertRaisesRegex(ValueError, "actors.json"):
            original_scalar_fields(no_cache, "StaticMeshActor__1")
        with self.assertRaises(ValueError):
            self.world.native_scalar_fields("UnknownSourceActor")
        with self.assertRaises(ValueError):
            save_as_scalar_copy(self.world, {"Unknown": {"FixtureFlag": 2}},
                                self.output)

    def test_reject_gamesys_nonnumeric_location_and_unknown_native_tags(self):
        for changes in (
            {"StaticMeshActor__1": {"Location": 14}},
            {"StaticMeshActor__1": {"Rotation": 1}},
            {"StaticMeshActor__1": {"bHidden": True}},
            {"StaticMeshActor__1": {"UnrealUnknownTag": 25}},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                save_as_scalar_copy(self.world, changes, self.output, write=True)
        self.assertFalse(self.output.exists())

    def test_reject_invalid_int32_and_noop_changes(self):
        for val in (True, False, 98765, 2147483648, -2147483649, 1.5,
                    "1", float("nan"), float("inf")):
            with self.subTest(value=val), self.assertRaises(ValueError):
                self.world.save_as_scalar_changes(
                    {"StaticMeshActor__1": {"FixtureFlag": val}},
                    self.output, write=True)
        self.assertFalse(self.output.exists())

    def test_numeric_float32_encoder_rejects_unsafe_values(self):
        self.assertEqual(_encode(25.5, 4), (25.5, struct.pack("<f", 25.5)))
        self.assertEqual(_encode(-4, 2)[1], struct.pack("<i", -4))
        for n in (True, False, float("nan"), float("inf"), -float("inf"),
                  1e100, "not a float"):
            with self.subTest(n=n), self.assertRaises(ValueError):
                _encode(n, 4)
        with self.assertRaises(ValueError):
            _encode(2, 255)

    def test_scalar_copy_never_targets_any_game_maps_or_original_map(self):
        for where in (self.maps / self.source.name,
                      self.root / "Other" / "Content" / "DX2" / "Maps"
                      / self.source.name):
            with self.subTest(where=where), self.assertRaises(ValueError):
                self.world.save_as_scalar_changes(self.edits, where, write=True)
        self.assertEqual(self.original_bytes, self.source.read_bytes())

    def test_invalid_existing_manifest_blocks_new_output(self):
        self.output.parent.mkdir()
        self.private_manifest.write_text("private previous manifest")
        with self.assertRaises(ValueError):
            self.world.save_as_scalar_changes(self.edits, self.output, write=True)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.private_manifest.read_text(), "private previous manifest")

    def test_injected_unapproved_byte_rejected_even_if_hash_updated(self):
        self.world.save_as_scalar_changes(self.edits, self.output, write=True)
        original = bytearray(self.output.read_bytes())
        original[-1] ^= 1  # outside the existing numeric FixtureFlag payload
        self.output.write_bytes(original)
        manifest = json.loads(self.private_manifest.read_text())
        manifest["output_sha256"] = hashlib.sha256(self.output.read_bytes()).hexdigest()
        manifest["changed_byte_count"] += 1
        self.private_manifest.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Unapproved native byte"):
            self.world.verify_saved_scalar_changes(self.output)

    def test_manifest_forged_runtime_support_refused(self):
        self.world.save_as_scalar_changes(self.edits, self.output, write=True)
        doc = json.loads(self.private_manifest.read_text())
        doc["runtime_game_verified"] = True
        self.private_manifest.write_text(json.dumps(doc))
        with self.assertRaises(ValueError):
            self.world.verify_saved_scalar_changes(self.output)

    def test_original_sha_and_actor_cache_drift_refused_before_writer(self):
        changed = json.loads(self.cache.read_text())
        changed["actors"][0]["mesh"] = "ChangedSourceData"
        self.cache.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "cache changed"):
            self.world.save_as_scalar_changes(
                self.edits, self.output, write=True)
        self.assertFalse(self.output.exists())

    def test_cli_exposes_original_field_and_dry_run_explicit_binary_patch(self):
        source = ("--map", str(self.source), "--actors", str(self.cache))
        inv = self.cli("scalar-fields", *source,
                       "--actor", "StaticMeshActor__1")
        self.assertEqual(inv.returncode, 0, inv.stderr)
        shown = json.loads(inv.stdout)
        self.assertEqual(shown["fields"][0]["source_value"], 98765)
        cmd = ("set-scalar", *source,
               "--actor", "StaticMeshActor__1",
               "--property", "FixtureFlag", "--value", "123456",
               "--output", str(self.output))
        dry = self.cli(*cmd)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["status"], "dry-run")
        self.assertFalse(self.output.exists())
        written = self.cli(*cmd, "--write")
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertTrue(json.loads(written.stdout)["independent_binary_verification"])
        verify = self.cli("verify-scalar", *source,
                          "--output", str(self.output))
        self.assertEqual(verify.returncode, 0, verify.stderr)
        self.assertTrue(json.loads(verify.stdout)["verified_binary_structure"])
        self.assertEqual(self.original_bytes, self.source.read_bytes())

    def test_unsupported_native_float_string_does_not_write(self):
        source = ("--map", str(self.source), "--actors", str(self.cache))
        cmd = ("set-scalar", *source, "--actor", "StaticMeshActor__1",
               "--property", "FixtureFlag", "--value", "nan",
               "--output", str(self.output), "--write")
        rejected = self.cli(*cmd)
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(json.loads(rejected.stderr)["status"], "refused")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
