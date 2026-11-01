"""Fixture-only checks for T3Ed capability tracker and DX2 IBD asset catalog."""
import json
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "native_editor" / "godot_editor" / "backend"
sys.path.insert(0, str(BACKEND))
from dx2_asset_catalog import SCHEMA, catalog_from_bundles, catalog_from_paths
from dx2_asset_preview import preview_path, load_selected_asset, source_bundle_paths, export_asset_preview
from dx2_archetype_catalog import archetype_catalog, ACTOR_CLASS_SCHEMA, catalog_for_map


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
        writer = next(c for c in capabilities if c["id"] == "packaging_build")
        self.assertEqual(writer["status"], "partial")
        self.assertIn("translation-only", writer["evidence"])
        self.assertIn("BSP", writer["next_step"])

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

    def test_generate_unplaced_mesh_preview_glb_uses_original_bundle_identity(self):
        with TemporaryDirectory() as root:
            folder = Path(root)
            source = folder / "mission.ibd"
            source.write_bytes(b"owned test fixture data")
            catalog_path = folder / "assets.json"
            catalog_path.write_text(json.dumps({
                "schema": SCHEMA, "asset_payloads_included": False,
                "source_paths": [str(source)],
                "assets": [{"name": "UnusedDoor", "kind": "staticmesh", "type_id": 4,
                            "bundle": "mission.ibd", "resource_index": 9, "bytes": 16}]
            }))
            bundle = SimpleNamespace(name="mission.ibd")
            record = SimpleNamespace(index=9)
            mesh = SimpleNamespace(
                name="UnusedDoor",
                positions=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)],
                normals=[(0.,0.,1.)]*3,
                uv=[(0.,0.),(1.,0.),(0.,1.)],
                indices=[0,1,2],
                sections=[{"name":"FictionalMaterial", "first_index":0, "index_count":3}],
                skins=[{"name":"Default","materials":["FictionalMaterial"]}])
            mapping = {4: {"unuseddoor": (bundle, record)}, 8: {}, 10: {}}
            with patch("dx2_asset_preview.load_resource_index",
                       return_value=([bundle], mapping, {})), \
                 patch("dx2_asset_preview.parse_mesh", return_value=mesh):
                result = export_asset_preview(catalog_path, "UnusedDoor")
            self.assertFalse(result["cached"])
            binary = Path(result["glb"]).read_bytes()
            self.assertEqual(binary[:4], b"glTF")
            self.assertEqual(struct.unpack_from("<I", binary, 4)[0], 2)
            json_length = struct.unpack_from("<I", binary, 12)[0]
            doc = json.loads(binary[20:20+json_length])
            self.assertEqual(doc["meshes"][0]["name"], "UnusedDoor")
            self.assertTrue(doc["nodes"][0]["extras"]["DX2PreviewOnly"])
            cached = export_asset_preview(catalog_path, "UnusedDoor")
            self.assertTrue(cached["cached"])
            self.assertEqual(source.read_bytes(), b"owned test fixture data")

    def test_reject_asset_preview_when_index_changes(self):
        with TemporaryDirectory() as root:
            folder = Path(root)
            source = folder / "mission.ibd"
            source.write_bytes(b"fixture")
            catalog_path = folder / "assets.json"
            catalog_path.write_text(json.dumps({
                "schema": SCHEMA, "asset_payloads_included": False,
                "source_paths": [str(source)],
                "assets": [{"name": "Door", "kind": "staticmesh", "type_id": 4,
                            "bundle": "mission.ibd", "resource_index": 9, "bytes": 16}]
            }))
            mapping = {4: {"door": (SimpleNamespace(name="mission.ibd"),
                                    SimpleNamespace(index=10))}, 8: {}, 10: {}}
            with patch("dx2_asset_preview.load_resource_index",
                       return_value=([], mapping, {})):
                with self.assertRaisesRegex(ValueError, "identity differs"):
                    export_asset_preview(catalog_path, "Door")

    def test_archetype_palette_preserves_declared_parent_and_observed_template(self):
        catalog = archetype_catalog([
            {"name": "Door_1", "class": "DX2Door", "export": 71,
             "mesh": "M1Door", "game_properties": [
                 {"id":12, "name":"Locked", "type":"bool", "value":True}]},
            {"name": "Door_2", "class": "DX2Door", "export": 72,
             "mesh": None, "game_properties": [
                 {"id":12, "name":"Locked", "type":"bool", "value":False}]},
            {"name": "Zone", "class": "Trigger", "export": 73,
             "mesh": None, "game_properties":[]},
        ], system_classes={
            "DX2Game.DX2Door":{"base":"Actor","package":"DX2Game.d2u"},
            "DX2Game.UnusedNPC":{"base":"Pawn","package":"DX2Game.d2u"},
        }, system_properties={"12":{"name":"Locked"}})
        self.assertEqual(catalog["schema"], ACTOR_CLASS_SCHEMA)
        self.assertFalse(catalog["native_spawn_supported"])
        door = next(c for c in catalog["classes"] if c["qualified"]=="DX2Game.DX2Door")
        self.assertEqual(door["base"], "Actor")
        self.assertEqual(door["observed_actors"], 2)
        self.assertEqual(door["template_actor"], "Door_1")
        self.assertEqual(door["template_export"], 71)
        self.assertEqual(door["property_signatures"][0]["id"], 12)
        npc = next(c for c in catalog["classes"] if c["class"]=="UnusedNPC")
        self.assertEqual(npc["observed_actors"], 0)
        self.assertIsNone(npc["template_actor"])
        trigger = next(c for c in catalog["classes"] if c["class"]=="Trigger")
        self.assertEqual(trigger["source"],"map_observation")

    def test_ambiguous_gamesys_short_class_names_are_not_guessed(self):
        catalog = archetype_catalog(
            [{"name":"Unknown_1","class":"Shared","mesh":"Block","export":5}],
            system_classes={"DX2AI.Shared":{"base":"Pawn"},
                            "DX2Game.Shared":{"base":"Actor"}})
        self.assertEqual(catalog["ambiguous_names"], ["shared"])
        observed = next(c for c in catalog["classes"] if c["source"]=="map_observation")
        self.assertEqual(observed["qualified"],"observed.Shared")
        self.assertEqual(observed["template_actor"],"Unknown_1")
        self.assertEqual(sum(c["observed_actors"] for c in catalog["classes"]),1)

    def test_archetypes_can_load_verified_system_catalog_json(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/"classes.json"
            p.write_text(json.dumps({"schema":"dx2-catalog-0.1",
                "classes":{"DX2Game.Camera":{"base":"Actor","package":"DX2Game.d2u"}},
                "properties":{}}))
            result = catalog_for_map([],p)
            self.assertEqual(len(result["classes"]),1)
            self.assertEqual(result["classes"][0]["base"],"Actor")
            p.write_text(json.dumps({"schema":"unexpected","classes":{}}))
            with self.assertRaisesRegex(ValueError,"Unsupported"):
                catalog_for_map([],p)

    def test_tracker_calls_out_source_format_boundary(self):
        text = (ROOT / "native_editor" / "T3ED_PARITY_PLAN.md").read_text(encoding="utf8")
        self.assertIn("retail .gmp", text)
        self.assertIn("DX2", text)
        self.assertIn("BSP", text)
        self.assertIn("Asset Browser", text)


if __name__ == "__main__":
    unittest.main()
