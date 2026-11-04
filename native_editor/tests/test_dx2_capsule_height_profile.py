"""Asset-free multi-height edge capsule contact profile regression tests.

The same source triangles and MOPP-conservative query are independently checked
at every height. Contact is NOT equated to a blocking or Havok traversability
verdict. No original GMP data or in-game collision writer are involved.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import export_capsule_first_contact_preview as preview
import inspect_mopp_axis_point_candidates as mopp
import inspect_mopp_point_triangle_oracle as geometry

SHA = "c" * 64


def source():
    vertices = [(0., 0., 0.), (2., 0., 0.), (0., 2., 0.)]
    triangles = [(0, 1, 2, True)]
    original = list(vertices), list(triangles)
    oracle = geometry.LevelPointTriangleOracle(vertices, triangles)
    walker = mopp.ConservativeMoppPointCandidates(
        b"\x28\x00\xff\x30", 1, (0., 0., -10., 65536.))
    return oracle, walker, original, vertices, triangles


def profile(offsets=(0., .5, 1.), **overrides):
    oracle, walker, *_ = source()
    args = dict(map_name="Fixture.gmp", source_hash=SHA,
                start=(.5, .5, .2), end=(.6, .5, .2),
                radius=.15, axis=(0., 0., 1.), axis_half_length=.1,
                height_offsets=offsets)
    args.update(overrides)
    return preview.build_profile_document(oracle, walker, **args)


class OriginalEdgeCapsuleHeightProfileTests(unittest.TestCase):
    def test_floor_contact_at_low_height_and_no_contact_above(self):
        result = profile((0., .5, 1.))
        self.assertEqual(result["schema"], preview.PROFILE_SCHEMA)
        self.assertEqual([s["geometric_source_triangle_hits"]
                          for s in result["profile_samples"]], [1, 0, 0])
        self.assertEqual(result["profile_samples"][0]["first_hit_original_triangle_id"], 0)
        self.assertTrue(result["profile_samples"][0]["first_contact_initial_overlap"])
        for high in result["profile_samples"][1:]:
            self.assertIsNone(high["first_hit_original_triangle_id"])
            self.assertIsNone(high["first_contact_path_t"])
        self.assertTrue(result["contact_is_not_a_blocking_classifier"])
        self.assertTrue(result["no_contact_is_not_proof_of_walkability"])

    def test_offsets_are_relative_upward_original_level_z_not_godot_y(self):
        result = profile((0., .25, 2.))
        self.assertEqual(result["height_direction_original_Level"], "positive Z")
        self.assertEqual(result["baseline_capsule_start_godot_xyz"], [.05, .02, .05])
        self.assertEqual(result["baseline_capsule_end_godot_xyz"], [.06, .02, .05])
        self.assertEqual([s["relative_height_level_units"]
                          for s in result["profile_samples"]], [0., .25, 2.])

    def test_invalid_profile_shapes_order_and_nonfinite_values_refused(self):
        cases = [[], [0.], [0.] * 10, [.1, .5],
                 [0., 0.], [0., .009], [0., -.5],
                 [0., float("nan")], [0., float("inf")],
                 [0., 100.1], [0., 1., .5], "0,1", [0., True]]
        for candidate in cases:
            with self.subTest(offsets=candidate), self.assertRaises(ValueError):
                profile(candidate)
        with self.assertRaisesRegex(ValueError, "fixed original Level"):
            profile((0., 1.), axis=(0., 1., 0.))

    def test_original_triangle_data_and_identity_remain_unchanged(self):
        oracle, walker, original, vertices, triangles = source()
        result = preview.build_profile_document(
            oracle, walker, map_name="Fixture.gmp", source_hash=SHA,
            start=(.5, .5, .2), end=(.6, .5, .2),
            radius=.15, axis=(0., 0., 1.), axis_half_length=.1,
            height_offsets=[0., .2, .5])
        self.assertEqual((vertices, triangles), original)
        self.assertEqual(result["source_sha256"], SHA)
        self.assertEqual(result["source_map"], "Fixture.gmp")
        self.assertFalse(result["original_game_assets_modified"])
        self.assertFalse(result["havok_runtime_contact_verified"])
        self.assertTrue(result["not_a_native_collision_writer"])
        self.assertNotIn("source_level_vertices", json.dumps(result))

    def test_profile_inherits_authenticated_source_identity_refusals(self):
        for invalid in (dict(map_name="../Fixture.gmp"),
                        dict(source_hash="g" * 64),
                        dict(start=(float("nan"), 0., 0.)),
                        dict(radius=-1.)):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                profile((0., 1.), **invalid)

    def test_no_private_sidecar_created_when_original_hash_is_wrong(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Maps" / "Fixture.gmp"
            path.parent.mkdir()
            path.write_bytes(b"fake GMP")
            output = Path(d) / "Private" / "profile.json"
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                preview.build(
                    path, output, expected_sha256=SHA,
                    start=(.5, .5, .2), end=(.6, .5, .2),
                    radius=.15, axis=(0., 0., 1.), axis_half_length=.1,
                    height_offsets=[0., .5, 1.])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
