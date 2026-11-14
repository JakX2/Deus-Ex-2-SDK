"""Asset-free tests for conservative door/vending source discovery."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest import TestCase, main
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / "godot_editor" / "backend"
sys.path.insert(0, str(BACKEND))
import dx2_interactive_actor_candidates as discovery


def fake_actor(name, export, mesh=None, position=None, props=None, script=None):
    return {
        "name": name, "export": export, "class": "D_100",
        "mesh": mesh, "location": position if position is not None else [0, 0, 0],
        "game_properties": props if props is not None else [],
        "trigger_script_serialized": script,
    }


class InteractiveCandidateTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.maps = self.root / "game" / "Content" / "DX2" / "Maps"
        self.maps.mkdir(parents=True)
        self.source = self.maps / "M1_Synthetic.gmp"
        self.source.write_bytes(b"made-up non-game test bytes")
        self.private = self.root / "private"
        self.private.mkdir()
        self.actors = [
            fake_actor("D_1__0", 4, mesh="door_slide_A", position=[0, 0, 0],
                       props=[{"id": 92, "name": "TriggerScripts", "value": {
                           "interpretation": "index", "items": [12]}},
                              {"id": 43, "name": "ObjectMesh", "value": {"ref": 2}}],
                       script={"interpretation": "index", "items": [12]}),
            fake_actor("D_2__0", 8, mesh="snack_machine_A", position=[20, 0, 0]),
            fake_actor("D_3__0", 9, mesh="metal_table", position=[100, 0, 0]),
            fake_actor("D_4__0", 10, mesh=None, position=[1024, 0, 0]),
        ]

    def meta(self, sha=None):
        return {"map": self.source.name,
                "map_sha256": sha or hashlib.sha256(self.source.read_bytes()).hexdigest(),
                "scene_parse_failures": [],
                "game_property_decode_errors": []}

    def test_original_name_mesh_evidence_not_functional_claim(self):
        found, total = discovery.find_candidates(self.actors, kind="both")
        self.assertEqual(total, 2)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["source_export"], 4)
        self.assertEqual(found[0]["matching_source_fields"][0]["category"], "door")
        self.assertEqual(found[0]["original_gamesys_property_ids"], [43, 92])
        self.assertTrue(found[0]["raw_trigger_script_field_present"])
        self.assertFalse(found[0]["functional_interaction_verified"])
        self.assertFalse(found[0]["actor_script_binding_verified"])
        self.assertFalse(found[0]["native_clone_eligible"])
        self.assertEqual(found[1]["matching_source_fields"][0]["category"], "vending")
        self.assertEqual(found[0]["nearby_source_actors_spatial_only"][0]["export"], 8)
        self.assertNotIn(10, [x["export"] for x in found[0]["nearby_source_actors_spatial_only"]])

    def test_category_filter_and_no_generic_machine_guess(self):
        door, door_count = discovery.find_candidates(self.actors, kind="door")
        vend, vend_count = discovery.find_candidates(self.actors, kind="vending")
        self.assertEqual((door_count, vend_count), (1, 1))
        self.assertEqual(door[0]["source_export"], 4)
        self.assertEqual(vend[0]["source_export"], 8)
        generic = [fake_actor("D_1000", 1, "machinery")]
        self.assertEqual(discovery.find_candidates(generic)[1], 0)

    def test_result_limit_is_explicit(self):
        records = [fake_actor("Door_%d" % i, i + 1) for i in range(3)]
        candidates, total = discovery.find_candidates(records, limit=1)
        self.assertEqual((len(candidates), total), (1, 3))
        with self.assertRaises(ValueError):
            discovery.find_candidates(records, limit=0)

    def test_duplicate_source_export_fails(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            discovery.find_candidates(self.actors + [fake_actor("door_other", 4)])

    def test_invalid_coordinate_never_creates_spatial_link(self):
        records = [
            fake_actor("door", 1, position=[float("nan"), 0, 0]),
            fake_actor("vending", 2, position=[1, 0, 0]),
        ]
        found, _ = discovery.find_candidates(records)
        self.assertIsNone(found[0]["location_unreal_xyz"])
        self.assertEqual(found[0]["nearby_source_actors_spatial_only"], [])

    def test_original_gmp_identity_and_no_mutation(self):
        old = self.source.read_bytes()
        with patch.object(discovery, "actor_records", return_value=(self.meta(), self.actors)):
            report = discovery.audit(self.source)
        self.assertEqual(report["candidate_count"], 2)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["functional_interactions_verified"])
        self.assertFalse(report["native_interactive_clone_supported"])
        self.assertEqual(old, self.source.read_bytes())

    def test_forged_actor_catalog_source_refused(self):
        wrong = self.meta("f" * 64)
        with patch.object(discovery, "actor_records", return_value=(wrong, self.actors)):
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                discovery.audit(self.source)

    def test_mutating_source_during_catalog_read_refused(self):
        old_meta = self.meta()
        def mutate(_map, _system):
            self.source.write_bytes(b"modified synthetic bytes")
            return old_meta, self.actors
        with patch.object(discovery, "actor_records", side_effect=mutate):
            with self.assertRaisesRegex(ValueError, "changed"):
                discovery.audit(self.source)

    def test_private_new_json_only_and_refusal_in_maps_folder(self):
        report = {"schema": discovery.SCHEMA, "read_only": True}
        with self.assertRaisesRegex(ValueError, "outside"):
            discovery._output(report, self.maps / "bad.json", self.source)
        destination = self.private / "actors.json"
        discovery._output(report, destination, self.source)
        self.assertEqual(json.loads(destination.read_text()), report)
        with self.assertRaises(FileExistsError):
            discovery._output(report, destination, self.source)

    def test_cli_can_emit_report_without_writing_game(self):
        original = self.source.read_bytes()
        with patch.object(discovery, "actor_records", return_value=(self.meta(), self.actors)):
            output = io.StringIO()
            with redirect_stdout(output):
                code = discovery.main(["--map", str(self.source), "--kind", "vending"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["candidate_count"], 1)
        self.assertEqual(payload["candidates"][0]["source_export"], 8)
        self.assertEqual(self.source.read_bytes(), original)


if __name__ == "__main__":
    main()
