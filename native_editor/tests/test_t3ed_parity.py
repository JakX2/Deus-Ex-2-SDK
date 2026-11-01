"""Fixture-only checks for T3Ed capability tracker and DX2 IBD asset catalog."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "native_editor" / "godot_editor" / "backend"
sys.path.insert(0, str(BACKEND))
from dx2_asset_catalog import SCHEMA, catalog_from_bundles, catalog_from_paths
from dx2_asset_preview import preview_path, load_selected_asset, source_bundle_paths


def fixture_resource(name, kind, type_id, index, size=64):
    return SimpleNamespace(name=name, kind=kind, typ=type_id, index=index, size=size)


def fixture_bundle(name, *resources):
    return SimpleNamespace(name=name, resources=resources)


class T3EdParityAndCatalogTests(unittest.TestCase):
    def test_tracker_has_unique_evidence_backed_capabilities(self):
        manifest = json.loads((ROOT / "native_editor" / "t3ed_parity.json").read_text(encoding="utf8"))
        self.assertEqual(manifest["schema"], "DX2Ed-T3Ed-parity-v1")
        capabilities = manifest["capabilities"]
        self.assertGreaterEqual(len(capabilities), 20)
        ids = [c["id"] for c in capabilities]
        self.assertEqual(len(ids), len(set(ids)))
        for item in capabilities:
            self.assertIn(item["status"], manifest["allowed_statuses"])
            self.assertIn(item["phase"], (1, 2, 3, 4))
            self.assertTrue(item["evidence"])
            self.assertTrue(item["next_step"])
        self.assertEqual(next(c for c in capabilities if c["id"] == "packaging_build")["status"], "missing")

    def test_catalog_lists_all_types_including_unplaced_resources(self):
        result = catalog_from_bundles([fixture_bundle("mission.ibd",
            fixture_resource("Door", "staticmesh", 4, 10),
            fixture_resource("Granite", "texture", 8, 4),
            fixture_resource("DoorMaterial", "matlib", 10, 6),
            fixture_resource("TouchTrigger", "triggerscriptdef", 21, 20),
        )])
        self.assertEqual(result["schema"], SCHEMA)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["asset_payloads_included"])
        self.assertEqual(len(result["assets"]), 4)
        self.assertEqual(result["counts_by_kind"]["texture"], 1)
        self.assertEqual(result["counts_by_kind"]["triggerscriptdef"], 1)

    def test_first_bundle_wins_and_name_collisions_are_reported(self):
        result = catalog_from_bundles([
            fixture_bundle("mission.ibd", fixture_resource("chair", "staticmesh", 4, 1)),
            fixture_bundle("Kernel.ibd", fixture_resource("CHAIR", "staticmesh", 4, 4),
                           fixture_resource("Chair", "texture", 8, 5)),
        ])
        self.assertEqual(len(result["assets"]), 2)
        chair = next(a for a in result["assets"] if a["kind"] == "staticmesh")
        self.assertEqual(chair["bundle"], "mission.ibd")
        self.assertEqual(result["collision_count"], 1)
        self.assertEqual(result["name_collisions"][0]["shadowed_source"], "Kernel.ibd")

    def test_catalog_never_embeds_resource_bytes(self):
        result = catalog_from_bundles([fixture_bundle("mission.ibd",
            fixture_resource("Prop", "staticmesh", 4, 5, size=1234))])
        self.assertEqual(result["assets"][0]["bytes"], 1234)
        self.assertNotIn("payload", result["assets"][0])
        json.dumps(result)

    def test_catalog_requires_explicit_source_files(self):
        with self.assertRaisesRegex(ValueError, "At least one IBD"):
            catalog_from_paths([])

    def test_asset_preview_filename_is_safe_for_unicode_and_slashes(self):
        name = "Ásset/A\\\\\\:Stair"
        path = preview_path(Path("/tmp/dx2ed/asset_catalog.json"), name)
        self.assertEqual(path.parent.name, "asset_previews")
        self.assertTrue(path.name.startswith("mesh_"))
        self.assertTrue(path.name.endswith(".glb"))
        self.assertNotIn("/", path.name)

    def test_asset_preview_requires_exact_static_mesh_identity(self):
        catalog = {"schema":SCHEMA, "asset_payloads_included":False, "assets":[
            {"name":"Stair", "kind":"staticmesh","bundle":"main.ibd","resource_index":1},
            {"name":"Wall", "kind":"texture","bundle":"main.ibd","resource_index":2}]}
        self.assertEqual(load_selected_asset(catalog,"Stair")["bundle"],"main.ibd")
        with self.assertRaisesRegex(ValueError, "Expected one staticmesh"):
            load_selected_asset(catalog,"Wall")
        with self.assertRaisesRegex(ValueError, "Expected one staticmesh"):
            load_selected_asset(catalog,"stair")
        catalog["asset_payloads_included"] = True
        with self.assertRaisesRegex(ValueError, "unsafe"):
            load_selected_asset(catalog,"Stair")

    def test_asset_preview_rejects_unlisted_sources(self):
        with self.assertRaisesRegex(ValueError,"missing source paths"):
            source_bundle_paths(Path("/tmp/catalog.json"), {"source_paths":[]})

    def test_tracker_calls_out_source_format_boundary(self):
        text = (ROOT / "native_editor" / "T3ED_PARITY_PLAN.md").read_text(encoding="utf8")
        self.assertIn("retail .gmp", text)
        self.assertIn("DX2", text)
        self.assertIn("BSP", text)
        self.assertIn("Asset Browser", text)


if __name__ == "__main__":
    unittest.main()
