"""Asset-free cross-language preflight of editor-private 3D convex Box brushes.

No retail Deus Ex files are read or emitted.
"""
from __future__ import annotations

from copy import deepcopy
import math
import unittest

from dx2sdk.private_brush_preflight import (
    SCHEMA, inspect_private_box_convex,
)


def box(*planes):
    return {
        "kind": "Box", "size": [2.0, 2.0, 2.0], "steps": 1,
        "clip_plane": planes[0] if len(planes) == 1 else None,
    } if len(planes) == 1 else {
        "kind": "Box", "size": [2.0, 2.0, 2.0], "steps": 1,
        "clip_planes": list(planes),
    }


def clip(normal, distance=0.0, keep_positive=False):
    return {
        "normal": list(normal), "distance": distance,
        "keep_positive": keep_positive,
    }


class PrivateConvexBrushPreflightTests(unittest.TestCase):
    def test_half_cube_has_independent_closed_manifold_and_volume(self):
        spec = box(clip((1.0, 0.0, 0.0)))
        before = deepcopy(spec)
        result = inspect_private_box_convex(spec)
        self.assertEqual(spec, before)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["coordinate_system"], "Godot-local-metres-Y-up")
        self.assertEqual(result["input_clip_plane_count"], 1)
        self.assertEqual(result["active_cut_cap_count"], 1)
        self.assertEqual(result["vertex_count"], 8)
        self.assertEqual(result["edge_count"], 12)
        self.assertEqual(result["face_count"], 6)
        self.assertEqual(result["triangle_count"], 12)
        self.assertEqual(result["euler_characteristic"], 2)
        self.assertAlmostEqual(result["enclosed_private_volume_m3"], 4.0)
        self.assertEqual(len(result["private_brush_spec_sha256"]), 64)
        self.assertEqual(result, inspect_private_box_convex(spec))
        self.assertFalse(result["native_world_model_writer_enabled"])
        self.assertFalse(result["native_bsp_surface_indices_known"])
        self.assertFalse(result["original_gmp_or_ibd_modified"])
        self.assertFalse(result["collision_rebuild_verified"])
        self.assertFalse(result["runtime_verified"])
        caps = [f for f in result["local_faces_not_native_bsp"]
                if f["kind"] == "private_cut_cap"]
        self.assertEqual(len(caps), 1)
        self.assertEqual(caps[0]["slot"], 0)
        self.assertEqual(len(caps[0]["vertices"]), 4)
        self.assertTrue(all(abs(x) < 1e-6
                            for x, _, _ in caps[0]["vertices"]))

    def test_kept_side_mirrors_the_private_x_halfspace(self):
        left = inspect_private_box_convex(box(clip((1., 0., 0.))))
        right = inspect_private_box_convex(box(
            clip((1., 0., 0.), keep_positive=True)))
        self.assertAlmostEqual(left["enclosed_private_volume_m3"], 4)
        self.assertAlmostEqual(right["enclosed_private_volume_m3"], 4)
        self.assertNotEqual(left["private_geometry_sha256_quantized_1e-6m"],
                            right["private_geometry_sha256_quantized_1e-6m"])
        for f in right["local_faces_not_native_bsp"]:
            if f["kind"] == "private_cut_cap":
                self.assertEqual(f["normal"], [-1., 0., 0.])

    def test_two_private_cuts_form_closed_quarter_box(self):
        spec = box(clip((1., 0., 0.)), clip((0., 1., 0.)))
        r = inspect_private_box_convex(spec)
        self.assertAlmostEqual(r["enclosed_private_volume_m3"], 2.0)
        self.assertEqual(r["active_cut_cap_count"], 2)
        self.assertEqual(r["triangle_count"], 12)
        self.assertEqual(r["euler_characteristic"], 2)

    def test_eight_independent_corner_cuts_reach_14_faces_and_44_triangles(self):
        u = 1.0/math.sqrt(3.0)
        cuts = [
            clip((sx*u, sy*u, sz*u), 1.4)
            for sx in (-1, 1)
            for sy in (-1, 1)
            for sz in (-1, 1)
        ]
        input_a = box(*cuts)
        original = deepcopy(input_a)
        a = inspect_private_box_convex(input_a)
        self.assertEqual(input_a, original)
        self.assertEqual(a["input_clip_plane_count"], 8)
        self.assertEqual(a["active_cut_cap_count"], 8)
        self.assertEqual(a["face_count"], 14)
        self.assertEqual(a["vertex_count"], 24)
        self.assertEqual(a["edge_count"], 36)
        self.assertEqual(a["triangle_count"], 44)
        self.assertEqual(a["euler_characteristic"], 2)
        expected = 8. - 8.*(3.-math.sqrt(3.)*1.4)**3/6.
        self.assertAlmostEqual(a["enclosed_private_volume_m3"], expected, places=5)
        b = inspect_private_box_convex(box(*reversed(cuts)))
        self.assertAlmostEqual(b["enclosed_private_volume_m3"], expected, places=5)
        self.assertEqual(a["private_geometry_sha256_quantized_1e-6m"],
                         b["private_geometry_sha256_quantized_1e-6m"])
        self.assertNotEqual(a["private_brush_spec_sha256"],
                            b["private_brush_spec_sha256"])

    def test_refuse_redundant_near_tangent_and_empty_sequential_cuts(self):
        a = clip((1., 0., 0.))
        for other in (
            clip((1., 0., 0.), 0.5),  # redundant after x <= 0
            clip((-1., 0., 0.), -0.8),  # x >= .8, empty
        ):
            with self.subTest(other=other), self.assertRaises(ValueError):
                inspect_private_box_convex(box(a, other))
        for impossible in (
            clip((1., 0., 0.), 0.99),  # near tangent to original x=1
            clip((1., 0., 0.), 1.0),
            clip((1., 0., 0.), -1.0),
        ):
            with self.subTest(plane=impossible), self.assertRaises(ValueError):
                inspect_private_box_convex(box(impossible))

    def test_refuse_invalid_record_fields_and_nonfinite_numbers(self):
        valid = box(clip((1., 0., 0.)))
        inputs = []
        for field, value in (
            ("kind", "StaticMeshActor"), ("size", [2., 2.]),
            ("size", [257., 2., 2.]), ("size", [2., 0., 2.]),
            ("steps", 2), ("steps", True),
        ):
            mutated = deepcopy(valid)
            mutated[field] = value
            inputs.append(mutated)
        for field, value in (
            ("normal", [2., 0., 0.]),
            ("normal", [math.nan, 0., 0.]),
            ("normal", [0., 0., 0.]),
            ("distance", math.inf), ("distance", 257.),
            ("keep_positive", 0),
        ):
            mutated = deepcopy(valid)
            mutated["clip_plane"][field] = value
            inputs.append(mutated)
        for field in ("size", "kind", "clip_plane"):
            mutated = deepcopy(valid)
            del mutated[field]
            inputs.append(mutated)
        extra = deepcopy(valid)
        extra["native_writer_enabled"] = True
        inputs.append(extra)
        confused = deepcopy(valid)
        confused["clip_planes"] = [confused["clip_plane"]]
        inputs.append(confused)
        nine = box(*[clip((1., 0., 0.)) for _ in range(9)])
        inputs.append(nine)
        for invalid in inputs:
            with self.subTest(spec=str(invalid)[:100]), self.assertRaises(ValueError):
                inspect_private_box_convex(invalid)

    def test_refuse_file_path_or_unstructured_input(self):
        for invalid in (None, "C:/DX2/Maps/example.gmp", [],
                        {"kind": "Box"}, {"source_gmp": "retail.gmp"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                inspect_private_box_convex(invalid)


if __name__ == "__main__":
    unittest.main()
