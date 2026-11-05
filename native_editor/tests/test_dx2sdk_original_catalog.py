"""DX2SDK independent source-backed original GMP actor cache and inspector.

Uses a deliberately invented DX2 UE95 GMP with tagged FVector Location and
unrelated tagged properties; verifies cache reproducibility and original
native scene identity without involving Godot, IBDs or real game files.
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
from dx2sdk.catalog import (
    SCHEMA, scan_original_actor_catalog, write_original_actor_catalog)
from test_native_save_as import fixture_gmp


class OriginalCatalogScannerTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2sdk_synthetic_scan_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.maps = self.root / "InstalledFixture" / "Content" / "DX2" / "Maps"
        self.maps.mkdir(parents=True)
        self.source = self.maps / "M1_Test.gmp"
        self.source.write_bytes(fixture_gmp())
        self.private = self.root / "DX2SDKPrivate" / "M1_Test" / "actors.json"
        self.source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", *args],
            cwd=ROOT, text=True, capture_output=True, timeout=30)

    def test_direct_catalog_scan_creates_valid_source_bound_actor_cache(self):
        world = DX2Map.open(self.source)
        original = self.source.read_bytes()
        generated = world.build_actor_catalog()
        self.assertEqual(generated["meta"]["schema"], SCHEMA)
        self.assertEqual(generated["meta"]["source_sha256"], self.source_hash)
        self.assertEqual(generated["meta"]["source_map"], self.source.name)
        self.assertTrue(generated["meta"]["source_only_catalog"])
        self.assertFalse(generated["meta"]["runtime_actor_script_links_verified"])
        self.assertEqual(len(generated["actors"]), 1)
        actor = generated["actors"][0]
        self.assertEqual(actor["name"], "StaticMeshActor__1")
        self.assertEqual(actor["class"], "StaticMeshActor")
        self.assertEqual(actor["export"], 1)
        self.assertEqual(actor["location"], [100.0, 200.0, 300.0])
        self.assertEqual(actor["rotation"], [0, 0, 0])
        self.assertEqual(actor["tagged"]["FixtureFlag"], 98765)
        self.assertIsNone(actor["trigger_script_serialized"])
        self.assertIsNone(actor["mesh"])
        self.assertFalse(actor["native_location_writer_candidate"])
        self.assertEqual(actor["native_location_writer_reason"],
                         "source_mesh_reference_unresolved")
        self.assertFalse(self.private.exists())
        self.assertEqual(self.source.read_bytes(), original)

    def test_scan_cache_write_can_be_reloaded_and_used_by_read_only_sdk(self):
        world = DX2Map.open(self.source)
        original = self.source.read_bytes()
        summary = write_original_actor_catalog(world, self.private)
        self.assertEqual(summary["status"], "private_original_actor_cache_written")
        self.assertEqual(summary["actor_count"], 1)
        self.assertFalse(summary["gameplay_runtime_verified"])
        self.assertFalse(summary["original_source_modified"])
        self.assertEqual(summary["writer_candidate_count"], 0)
        self.assertEqual(summary["unresolved_static_mesh_count"], 1)
        self.assertTrue(self.private.is_file())
        loaded = DX2Map.open(self.source, self.private)
        self.assertTrue(loaded.info()["source_actor_cache_verified"])
        self.assertEqual(loaded.actors()["shown"][0]["name"], "StaticMeshActor__1")
        with self.assertRaisesRegex(ValueError, "existing rendered"):
            loaded.save_as_translations(
                {"StaticMeshActor__1": [125, 275, 350]},
                self.root / "Copies" / self.source.name, write=True)
        self.assertEqual(original, self.source.read_bytes())

    def test_scan_refuses_game_maps_tree_existing_catalog_and_wrong_filename(self):
        world = DX2Map.open(self.source)
        for output in (
            self.maps / "actors.json",
            self.root / "OtherInstall" / "Content" / "DX2" / "Maps" / "actors.json",
            self.root / "Private" / "not_actors.json",
        ):
            with self.subTest(output=output), self.assertRaises(ValueError):
                world.export_actor_catalog(output)
            self.assertFalse(output.exists())
        world.export_actor_catalog(self.private)
        before = self.private.read_bytes()
        with self.assertRaises(ValueError):
            world.export_actor_catalog(self.private)
        self.assertEqual(self.private.read_bytes(), before)

    def test_system_property_declarations_are_optional_but_source_validated(self):
        catalog = self.root / "PrivateOwnerCatalog.json"
        catalog.write_text(json.dumps({
            "schema": "dx2-catalog-0.1",
            "properties": {"43": {"name": "StaticMesh", "type": "object"}},
        }), encoding="utf8")
        result = DX2Map.open(self.source).build_actor_catalog(system=catalog)
        self.assertTrue(result["meta"]["optional_owner_system_catalog"])
        self.assertEqual(result["actors"][0]["export"], 1)
        bad = self.root / "Unrelated.txt"
        bad.write_text("not an original catalog")
        with self.assertRaises(ValueError):
            DX2Map.open(self.source).build_actor_catalog(system=bad)

    def test_actor_inspector_exposes_original_tagged_fields_but_no_writer(self):
        world = DX2Map.open(self.source)
        result = world.inspect_actor(export=1)
        self.assertEqual(result["actor_name"], "StaticMeshActor__1")
        self.assertEqual(result["actor_class"], "StaticMeshActor")
        self.assertEqual(result["actor_export"], 1)
        self.assertEqual(result["tagged_properties"]["FixtureFlag"], 98765)
        self.assertEqual(result["tagged_properties"]["Location"],
                         {"X": 100.0, "Y": 200.0, "Z": 300.0})
        self.assertEqual(result["gamesys_blocks"], [])
        self.assertTrue(result["native_location_field_layout_detected"])
        self.assertTrue(result["original_values_read_only"])
        self.assertFalse(result["native_property_writer_enabled"])
        self.assertFalse(result["actor_runtime_script_binding_verified"])
        by_name = world.inspect_actor(name="StaticMeshActor__1")
        self.assertEqual(by_name, result)

    def test_actor_inspector_rejects_ambiguous_or_invalid_original_selection(self):
        world = DX2Map.open(self.source)
        for selector in ({}, {"export": 1, "name": "StaticMeshActor__1"},
                         {"name": "Missing"}, {"export": 0},
                         {"export": True}, {"export": 99}):
            with self.subTest(selector=selector), self.assertRaises(ValueError):
                world.inspect_actor(**selector)

    def test_source_sha_drift_refuses_scan_and_property_inspection(self):
        world = DX2Map.open(self.source)
        self.source.write_bytes(self.source.read_bytes() + b"CHANGED")
        with self.assertRaisesRegex(ValueError, "changed"):
            world.build_actor_catalog()
        with self.assertRaisesRegex(ValueError, "changed"):
            world.inspect_actor(export=1)
        self.assertFalse(self.private.exists())

    def test_cli_scan_map_and_inspect_actor_without_godot(self):
        res = self.cli("scan-map", "--map", str(self.source),
                       "--output", str(self.private))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)["actor_count"], 1)
        self.assertTrue(self.private.exists())
        self.assertNotIn(str(self.source), res.stdout)
        details = self.cli("inspect-actor", "--map", str(self.source),
                           "--actor", "StaticMeshActor__1")
        self.assertEqual(details.returncode, 0, details.stderr)
        doc = json.loads(details.stdout)
        self.assertEqual(doc["tagged_properties"]["FixtureFlag"], 98765)
        self.assertFalse(doc["native_property_writer_enabled"])
        again = self.cli("scan-map", "--map", str(self.source),
                         "--output", str(self.private))
        self.assertEqual(again.returncode, 2)
        self.assertEqual(json.loads(again.stderr)["status"], "refused")

    def test_original_actor_scanner_output_is_deterministic(self):
        world = DX2Map.open(self.source)
        a = json.dumps(world.build_actor_catalog(), sort_keys=True)
        b = json.dumps(world.build_actor_catalog(), sort_keys=True)
        self.assertEqual(a, b)
        self.assertEqual(self.source_hash,
                         hashlib.sha256(self.source.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
