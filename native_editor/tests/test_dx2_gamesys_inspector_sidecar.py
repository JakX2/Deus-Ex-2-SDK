"""Fixture-only tests for the Godot source-backed GameSys Inspector sidecar.

No original-game data is bundled. Only source SHA, export, property order,
read-only flags and class/actor provenance are allowed to drive the UI.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
for module in (ROOT / "native_editor" / "godot_editor" / "backend",
               ROOT / "native_editor" / "package_writer"):
    sys.path.insert(0, str(module))

from dx2_gamesys_inspector_sidecar import SCHEMA, assemble_inspector, build_inspector_sidecar


class GameSysGodotInspectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.map = self.folder / "M1_Test.gmp"
        self.map.write_bytes(b"synthetic original package fixture")
        self.sha = hashlib.sha256(self.map.read_bytes()).hexdigest()
        self.actors_doc = {
            "meta": {"source_sha256": self.sha, "source_map": self.map.name},
            "actors": [{"name": "D_1179__0", "class": "DX2Pawn",
                        "export": 35, "game_properties": [
                {"id": 92, "version": 1, "encoding": "array", "value": {
                    "items": [71, 72], "interpretation": "index",
                }},
                {"id": 79, "version": 1, "encoding": "name", "value": "Security"},
            ]}],
        }
        self.audit = {
            "schema": "DX2Ed-native-gamesys-block-audit-v1",
            "read_only": True, "source_map": self.map.name,
            "source_sha256": self.sha, "actor_verification_errors": 0,
            "verified_game_properties": 2,
            "fields": [
                {"actor": "D_1179__0", "export": 35,
                 "property_id": 92, "source_block_index": 0,
                 "source_declared_name": "TriggerScripts",
                 "source_declared_type": "array<name>",
                 "source_declared_in": "Engine.Actor",
                 "encoding": "array", "version": 1, "encoded_id": 720988,
                 "payload_offset": 256, "payload_bytes": 3,
                 "payload_sha256": "ab" * 32},
                {"actor": "D_1179__0", "export": 35,
                 "property_id": 79, "source_block_index": 1,
                 "source_declared_name": "Tag",
                 "source_declared_type": "name",
                 "source_declared_in": "Engine.Actor",
                 "encoding": "name", "version": 1, "encoded_id": 393295,
                 "payload_offset": 271, "payload_bytes": 2,
                 "payload_sha256": "bc" * 32},
            ],
        }
        self.archetype = {
            "schema": "DX2Ed-gamesys-archetype-research-v1", "read_only": True,
            "original_package_sha256": "ef" * 32,
            "counts": {"classes_unparsed": 0, "classes_found": 1},
            "archetypes": [{
                "class": "D_1179", "display_name": "BotBasicVuln",
                "parent": "D_1198",
                "source_ancestry": ["D_1179", "D_1198"],
                "inheritance_complete": True,
                "original_t3sdk_grouped_layout_recovered": True,
                "local_property_count": 1,
                "local_defaults": [{
                    "property_id": 959, "source_declared_name": "VulnerabilityInfo",
                    "encoding": "struct", "element_count": 29,
                    "elements": [{"element_index": 0, "typed_fields": [
                        {"name": "Vulnerability", "type": "Float", "value": 1.0}
                    ]}],
                }],
            }],
        }

    def test_source_bound_join_preserves_unresolved_script_array(self):
        output = assemble_inspector(self.map, self.actors_doc, self.audit, self.archetype)
        self.assertEqual(output["schema"], SCHEMA)
        self.assertTrue(output["read_only"])
        self.assertFalse(output["native_game_editing_enabled"])
        self.assertFalse(output["native_archetype_spawning_enabled"])
        self.assertFalse(output["actor_to_archetype_binding_verified"])
        self.assertEqual(output["source_sha256"], self.sha)
        self.assertEqual(output["matched_scene_actors"], 1)
        actor = output["actors"]["35"]
        self.assertEqual(actor["name"], "D_1179__0")
        self.assertEqual(actor["properties"][0]["name"], "TriggerScripts")
        self.assertEqual(actor["properties"][0]["declared_type"], "array<name>")
        self.assertEqual(actor["properties"][0]["source_value"]["items"], [71, 72])
        self.assertFalse(actor["properties"][0]["native_edit_supported"])
        self.assertEqual(output["archetypes"][0]["display_name"], "BotBasicVuln")
        self.assertTrue(output["archetypes"][0]["recovered_dx2_layout"])
        self.assertFalse(output["archetypes"][0]["spawnable_verified"])

    def test_rejects_wrong_package_identity_and_reordered_original_block(self):
        audit = json.loads(json.dumps(self.audit))
        audit["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "audit does not match"):
            assemble_inspector(self.map, self.actors_doc, audit, self.archetype)
        audit = json.loads(json.dumps(self.audit))
        audit["fields"][0]["property_id"] = 999
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            assemble_inspector(self.map, self.actors_doc, audit, self.archetype)
        actor_doc = json.loads(json.dumps(self.actors_doc))
        actor_doc["actors"][0]["export"] = 12
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            assemble_inspector(self.map, actor_doc, self.audit, self.archetype)
        actor_doc = json.loads(json.dumps(self.actors_doc))
        actor_doc["meta"]["source_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "Actor cache"):
            assemble_inspector(self.map, actor_doc, self.audit, self.archetype)

    def test_source_archetype_list_is_not_a_map_actor_assignment(self):
        data = assemble_inspector(self.map, self.actors_doc, self.audit, self.archetype)
        self.assertNotIn("archetype", data["actors"]["35"])
        self.assertEqual(data["archetypes"][0]["parent"], "D_1198")
        self.assertEqual(data["archetypes"][0]["local_defaults"][0]["element_count"], 29)
        broken = json.loads(json.dumps(self.archetype))
        broken["counts"]["classes_unparsed"] = 57
        with self.assertRaisesRegex(ValueError, "incomplete"):
            assemble_inspector(self.map, self.actors_doc, self.audit, broken)

    def test_private_cache_json_requires_new_output_and_never_writes_gmp(self):
        cache = self.folder / "actors.json"
        cache.write_text(json.dumps(self.actors_doc))
        system = self.folder / "System"
        system.mkdir()
        output = self.folder / "gamesys_inspector.json"
        before = self.map.read_bytes()
        # Exercise joining and serialization independently from licensed data.
        with patch("dx2_gamesys_audit.audit_gamesys", return_value=self.audit), \
                patch("dx2_gamesys_archetype_audit.analyze_archetypes",
                      return_value=self.archetype):
            result = build_inspector_sidecar(self.map, cache, system, output)
            self.assertEqual(result["matched_scene_actors"], 1)
            self.assertEqual(json.loads(output.read_text())["schema"], SCHEMA)
            with self.assertRaisesRegex(FileExistsError, "overwrite"):
                build_inspector_sidecar(self.map, cache, system, output)
            with self.assertRaisesRegex(ValueError, "Output must"):
                build_inspector_sidecar(self.map, cache, system, self.map)
        self.assertEqual(self.map.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
