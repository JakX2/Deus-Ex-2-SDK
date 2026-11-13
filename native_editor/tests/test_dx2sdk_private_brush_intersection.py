"""Asset-free regression for CLOSED source-private convex CSG intersection.

Only invented editor authored Box geometry is used. Original game World BSP,
Havok/MOPP and native GMP/IBD are never read or modified.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dx2sdk.private_brush_intersection import (
    SCHEMA, intersect_private_boxes,
)


def clip(normal, distance=0.0, positive=False):
    return {"normal": list(normal), "distance": distance,
            "keep_positive": positive}


def box(*clips, size=(2., 2., 2.)):
    record = {"kind": "Box", "size": list(size), "steps": 1}
    if len(clips) == 1:
        record["clip_plane"] = clips[0]
    else:
        record["clip_planes"] = list(clips)
    return record


def translated(x, y=0.0, z=0.0):
    return {"basis": [[1.,0.,0.], [0.,1.,0.], [0.,0.,1.]],
            "origin": [x,y,z]}


class PrivateCSGIntersectionTests(unittest.TestCase):
    def setUp(self):
        self.half = box(clip((1., 0., 0.)))

    def _assert_shell(self, result):
        self.assertTrue(result["has_volume"])
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["status"],
                         "closed-source-private-convex-intersection-preview")
        self.assertEqual(result["euler_characteristic"], 2)
        self.assertEqual(result["vertex_count"]-result["edge_count"]
                         +result["face_count"], 2)
        self.assertTrue(result["all_edges_two_opposite_face_uses"])
        self.assertGreater(result["surface_area_m2"], 0)
        self.assertGreater(result["volume_m3"], 0)
        self.assertEqual(result["triangle_count"],
                         sum(len(f["vertex_ids"])-2 for f in result["faces"]))
        self.assertEqual(len(result["intersection_geometry_sha256"]), 64)
        for face in result["faces"]:
            self.assertGreater(face["area_m2"], 0)
            self.assertEqual(len(face["vertex_ids"]),
                             len(face["adjacent_face_indices_per_edge"]))
            self.assertTrue(face["private_face_sources"])
            for adjacent in face["adjacent_face_indices_per_edge"]:
                self.assertNotEqual(face["face_index"], adjacent)
                self.assertIn(face["face_index"], result["faces"][adjacent][
                    "adjacent_face_indices_per_edge"])
        for edge in result["edges"]:
            self.assertEqual(len(edge["adjacent_face_indices"]), 2)
        self.assertFalse(result["native_BSP_or_CSG_writer_enabled"])
        self.assertFalse(result["native_collision_generated"])
        self.assertFalse(result["original_gmp_or_ibd_modified"])
        self.assertFalse(result["retail_game_runtime_verified"])

    def test_identical_half_boxes_exact_shell_and_multi_source_faces(self):
        spec = deepcopy(self.half)
        result = intersect_private_boxes(self.half, self.half)
        self.assertEqual(self.half, spec)
        self.assertEqual(result, intersect_private_boxes(self.half, self.half))
        self._assert_shell(result)
        self.assertEqual((result["vertex_count"], result["edge_count"],
                          result["face_count"], result["triangle_count"]),
                         (8, 12, 6, 12))
        self.assertAlmostEqual(result["volume_m3"], 4.)
        self.assertAlmostEqual(result["surface_area_m2"], 16.)
        self.assertTrue(all(
            {p["source_private_brush"] for p in f["private_face_sources"]}
            == {"a", "b"} for f in result["faces"]))

    def test_overlapping_half_boxes_shifted_and_analytic_volume(self):
        result = intersect_private_boxes(
            self.half, self.half, transform_b=translated(0.5))
        self._assert_shell(result)
        self.assertAlmostEqual(result["volume_m3"], 2.)
        self.assertAlmostEqual(result["surface_area_m2"], 12.)
        self.assertEqual(min(v[0] for v in result["vertices"]), -0.5)
        self.assertEqual(max(v[0] for v in result["vertices"]), 0.)
        self.assertTrue(any(
            p["source_private_brush"] == "b"
            for face in result["faces"]
            for p in face["private_face_sources"]))
        self.assertTrue(any(
            p["source_private_brush"] == "a"
            for face in result["faces"]
            for p in face["private_face_sources"]))

    def test_rotated_boxes_intersect_and_keep_closed_manifold(self):
        quarter = {
            "basis": [[0.,-1.,0.], [1.,0.,0.], [0.,0.,1.]],
            "origin": [0.,0.,0.],
        }
        result = intersect_private_boxes(
            self.half, self.half, transform_b=quarter)
        self._assert_shell(result)
        self.assertAlmostEqual(result["volume_m3"], 2., places=7)
        self.assertEqual((result["vertex_count"], result["edge_count"],
                          result["face_count"]), (8,12,6))
        angle = math.pi/4
        rotated = {
            "basis": [[math.cos(angle), -math.sin(angle), 0.],
                      [math.sin(angle), math.cos(angle), 0.],
                      [0., 0., 1.]],
            "origin": [0.1, 0.2, 0.],
        }
        multi = intersect_private_boxes(
            self.half, self.half, transform_b=rotated)
        self._assert_shell(multi)
        self.assertLess(multi["volume_m3"], 4.)
        self.assertGreater(multi["volume_m3"], 0.)

    def test_contained_private_solid_and_far_from_origin(self):
        large = box(clip((1.,0.,0.)), size=(4.,4.,4.))
        small = intersect_private_boxes(
            large, self.half, transform_b=translated(-0.25))
        self._assert_shell(small)
        self.assertAlmostEqual(small["volume_m3"], 4.)
        shifted = intersect_private_boxes(
            self.half, self.half,
            transform_a=translated(100000., 32000., -1024.),
            transform_b=translated(100000.5, 32000., -1024.))
        self._assert_shell(shifted)
        self.assertAlmostEqual(shifted["volume_m3"], 2.)
        self.assertAlmostEqual(min(v[0] for v in shifted["vertices"]),
                               99999.5)

    def test_disjoint_and_boundary_contact_emit_no_fake_solid(self):
        for move, classification in (
            ((3.,0.,0.), "disjoint"),
            ((1.,0.,0.), "boundary-contact"),
            ((1.,2.,0.), "boundary-contact"),
            ((1.,2.,2.), "boundary-contact"),
        ):
            with self.subTest(move=move):
                result = intersect_private_boxes(
                    self.half, self.half, transform_b=translated(*move))
                self.assertFalse(result["has_volume"])
                self.assertEqual(result["sat_contact_classification"],
                                 classification)
                self.assertEqual(result["volume_m3"], 0.)
                self.assertEqual(result["vertices"], [])
                self.assertEqual(result["faces"], [])
                self.assertEqual(result["edges"], [])
                self.assertFalse(result["native_BSP_or_CSG_writer_enabled"])

    def test_eight_corner_brush_self_intersection(self):
        unit = 1./math.sqrt(3.)
        cuts = [clip((x*unit,y*unit,z*unit), 1.4)
                for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        original = box(*cuts)
        result = intersect_private_boxes(original, original)
        self._assert_shell(result)
        self.assertEqual((result["face_count"],result["vertex_count"],
                          result["edge_count"]), (14,24,36))
        self.assertAlmostEqual(result["volume_m3"],
                               8-8*(3-math.sqrt(3)*1.4)**3/6, places=6)

    def test_invalid_source_or_transform_refusal(self):
        for bad in (None, {}, {"kind": "StaticMeshActor"},
                    box(clip((0,0,0)))):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                intersect_private_boxes(self.half, bad)
        for bad in (
            {"basis": [[2,0,0],[0,1,0],[0,0,1]],"origin":[0,0,0]},
            {"basis": [[1,0,0],[0,1,0],[0,0,-1]],"origin":[0,0,0]},
            {"basis": [[1,0,0],[0,1,0],[0,0,1]],"origin":[float('nan'),0,0]},
        ):
            with self.subTest(frame=bad), self.assertRaises(ValueError):
                intersect_private_boxes(self.half, self.half, transform_b=bad)

    def test_cli_draft_selection_and_unchanged_mock_gmp(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root/"first.json"
            draft = root/"private_draft.json"
            move = root/"move.json"
            original = root/"original.gmp"
            first.write_text(json.dumps(self.half), encoding="utf-8")
            draft.write_text(json.dumps({
                "schema":"DX2Ed-prop-draft-v1",
                "read_only_source":True,
                "copies":[{"name":"DraftProp_100","from_actor":"Brush::Box",
                           "brush":self.half}],
            }), encoding="utf-8")
            move.write_text(json.dumps(translated(0.5)), encoding="utf-8")
            original.write_bytes(b"ORIGINAL_GMP_SOURCE_SENTINEL")
            pinned_sha = hashlib.sha256(original.read_bytes()).hexdigest()
            command = [sys.executable, "-m",
                       "dx2sdk.private_brush_intersection"]
            worked = subprocess.run(
                command+[str(first), str(draft), "--copy-b", "DraftProp_100",
                         "--transform-b", str(move)],
                capture_output=True, text=True)
            self.assertEqual(worked.returncode, 0, worked.stderr)
            self.assertAlmostEqual(json.loads(worked.stdout)["volume_m3"], 2.)
            for args in (
                [str(first),str(draft)],
                [str(first),str(original)],
                [str(original),str(first)],
                [str(first),str(draft),"--copy-b","DraftProp_999"],
                [str(first),str(first),"--transform-b",str(original)],
            ):
                with self.subTest(args=args):
                    denied = subprocess.run(command+args,
                                            capture_output=True, text=True)
                    self.assertEqual(denied.returncode, 2, denied.stderr)
                    self.assertFalse(denied.stdout.strip())
            self.assertEqual(pinned_sha,
                             hashlib.sha256(original.read_bytes()).hexdigest())
            self.assertEqual(
                sorted(p.name for p in root.iterdir()),
                sorted(["first.json","private_draft.json","move.json",
                        "original.gmp"]))


if __name__ == "__main__":
    unittest.main()
