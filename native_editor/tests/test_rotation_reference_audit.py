"""Synthetic tests for the read-only UE2 rotation reference audit."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor" / "godot_editor" / "backend"))
from dx2_rotation_audit import (
    SCHEMA, analyze_actors, dx2_preview_basis, max_difference,
    ue2_reference_basis, main,
)


def actor(number, mesh, rot):
    return {"name": "Actor" + str(number), "class": "StaticMeshActor",
            "export": number, "mesh": mesh, "rotation": rot,
            "location": [1, 2, 3]}


class RotationReferenceTests(unittest.TestCase):
    def test_seattle_ue2_reference(self):
        expected = ((-1, 0, 0), (0, 0, -1), (0, -1, 0))
        actual = ue2_reference_basis((0, 32768, 16384))
        self.assertLess(max_difference(actual, expected), 1e-10)

    def test_nonsymmetric_source_sdk_matrix_guard(self):
        # Independent reference values calculated directly with the user's
        # T3SDK 0.3.1 t3common.godot_basis(100, 900, 8192).
        # t3common returns Godot Basis COLUMNS; rows below are transposed.
        original_sdk_rows = (
            (0.996233848471, -0.067692005457, -0.054184052616),
            (0.009587233050, 0.707074283567, -0.707074283567),
            (0.086175426446, 0.703891859532, 0.705060313704),
        )
        self.assertLess(
            max_difference(ue2_reference_basis((100, 900, 8192)),
                           original_sdk_rows), 2e-12)
        self.assertLess(
            max_difference(dx2_preview_basis((100, 900, 8192), True),
                           original_sdk_rows), 2e-12)

    def test_inverted_roll_matches_ue2_reference(self):
        for rot in ((0,0,0), (0,32768,16384), (256,16384,32768),
                    (100,900,8192), (8192,8192,8192),
                    (-1000,24555,-32124), (50000,-65536,131072)):
            with self.subTest(rot=rot):
                self.assertLess(max_difference(dx2_preview_basis(rot, True),
                                               ue2_reference_basis(rot)), 1e-10)

    def test_zero_and_half_turn_unchanged(self):
        for roll in (0, 32768, -32768, 65536, 98304):
            rot = (256,16384,roll)
            with self.subTest(roll=roll):
                self.assertLess(max_difference(dx2_preview_basis(rot),
                                               dx2_preview_basis(rot,True)), 1e-10)

    def test_report_tracks_eligible_and_invalid_rotations(self):
        payload = {"meta": {"source_map": "Seattle.gmp", "source_sha256":"test"},
                   "actors": [actor(1, "Trim", [0,32768,16384]),
                              actor(2, "Pipe", [256,16384,32768]),
                              actor(3, "Table", [0,0,0]),
                              actor(4, "Broken", [0,0,float("nan")]),
                              actor(5, None, [0,0,1000])]}
        result = analyze_actors(payload)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertFalse(result["game_verified"])
        self.assertEqual(result["counts"], {
            "mesh_linked":4, "nontrivial_roll":1, "half_turn_roll":1,
            "zero_or_full_turn_roll":1, "invalid_rotator":1})
        self.assertTrue(result["actors"][0]["auto_roll_changes_basis"])
        self.assertFalse(result["actors"][1]["auto_roll_changes_basis"])
        self.assertLess(result["actors"][0]["inverted_vs_ue2_max_abs"],1e-7)

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_actors({"actors":{}})

    def test_cli_never_overwrites_source(self):
        with TemporaryDirectory() as td:
            original = Path(td) / "actors.json"
            audit = Path(td) / "audit.json"
            original.write_text(json.dumps({"actors":[actor(1,"Trim",[0,0,16384])]}))
            before = original.read_bytes()
            self.assertEqual(main([str(original), "--output",str(audit)]),0)
            self.assertEqual(original.read_bytes(),before)
            self.assertEqual(json.loads(audit.read_text())["schema"],SCHEMA)
            with self.assertRaises(SystemExit):
                main([str(original),"--output",str(original)])
            self.assertEqual(original.read_bytes(),before)


if __name__ == "__main__":
    unittest.main()
