"""Synthetic closed-piece tests for source-private A minus B CSG preview.

Every input is invented. No retail GMP/IBD, World BSP or native collision
data is read or modified; no subtract result is claimed to be game-native.
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

from dx2sdk.private_brush_subtraction import SCHEMA, subtract_private_boxes


def cut(n, distance=0.0):
    return {"normal": list(n), "distance": distance, "keep_positive": False}


def box(size=(2., 2., 2.), distance=0.0):
    return {"kind": "Box", "size": list(size), "steps": 1,
            "clip_plane": cut((1., 0., 0.), distance)}


def move(x=0., y=0., z=0.):
    return {"basis": [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]],
            "origin": [x, y, z]}


def point_in_piece(piece, at, anchor):
    local = [at[i]-anchor[i] for i in range(3)]
    return all(
        sum(f["outward_normal"][i]*local[i] for i in range(3))
        <= f["distance_from_anchor_m"]+1e-7
        for f in piece["faces"]
    )


class PrivateCSGDifferenceTests(unittest.TestCase):
    def setUp(self):
        self.half = box()

    def assert_valid_pieces(self, result):
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["operation"], "a-minus-b")
        self.assertTrue(result["volume_partition_verified"])
        self.assertTrue(result["all_pieces_individually_closed"])
        self.assertEqual(result["piece_count"], len(result["pieces"]))
        self.assertEqual(result["original_gmp_or_ibd_modified"], False)
        self.assertEqual(result["native_bsp_or_csg_writer_enabled"], False)
        self.assertEqual(result["native_havok_or_mopp_cooker_enabled"], False)
        self.assertEqual(result["retail_game_runtime_verified"], False)
        self.assertAlmostEqual(
            math.fsum(p["volume_m3"] for p in result["pieces"]),
            result["remaining_volume_m3"], places=7)
        self.assertAlmostEqual(
            result["source_a_volume_m3"],
            result["remaining_volume_m3"]+
            result["removed_intersection_volume_m3"], places=6)
        for ordinal, piece in enumerate(result["pieces"]):
            self.assertEqual(piece["piece_index"], ordinal)
            self.assertEqual(piece["euler_characteristic"], 2)
            self.assertTrue(piece["all_edges_two_opposite_face_uses"])
            self.assertEqual(piece["vertex_count"]-piece["edge_count"]
                             +piece["face_count"], 2)
            self.assertGreater(piece["volume_m3"], 0)
            self.assertGreater(piece["surface_area_m2"], 0)
            self.assertEqual(len(piece["private_shell_sha256"]), 64)
            self.assertEqual(piece["triangle_count"], sum(
                len(face["vertex_ids"])-2 for face in piece["faces"]))
            for face in piece["faces"]:
                self.assertGreater(face["area_m2"], 0)
                self.assertTrue(face["private_face_sources"])
                self.assertEqual(
                    len(face["vertex_ids"]),
                    len(face["adjacent_face_indices_per_edge"]))
                for neighbor in face["adjacent_face_indices_per_edge"]:
                    self.assertNotEqual(face["face_index"], neighbor)
                    self.assertIn(face["face_index"],
                                  piece["faces"][neighbor][
                                      "adjacent_face_indices_per_edge"])

    def test_half_box_minus_shifted_half_box_one_closed_cut_piece(self):
        source = deepcopy(self.half)
        result = subtract_private_boxes(
            self.half, self.half, transform_b=move(0.5))
        self.assertEqual(self.half, source)
        self.assertEqual(result, subtract_private_boxes(
            self.half, self.half, transform_b=move(0.5)))
        self.assert_valid_pieces(result)
        self.assertEqual(result["sat_contact_classification"],
                         "interior-overlap")
        self.assertEqual(result["piece_count"], 1)
        self.assertAlmostEqual(result["source_a_volume_m3"], 4.)
        self.assertAlmostEqual(result["removed_intersection_volume_m3"], 2.)
        self.assertAlmostEqual(result["remaining_volume_m3"], 2.)
        piece = result["pieces"][0]
        self.assertEqual(piece["emission"], "split-outside")
        self.assertEqual((piece["vertex_count"], piece["edge_count"],
                          piece["face_count"]), (8, 12, 6))
        self.assertAlmostEqual(min(p[0] for p in piece["vertices"]), -1.)
        self.assertAlmostEqual(max(p[0] for p in piece["vertices"]), -0.5)
        self.assertTrue(any(
            p.get("private_boolean_side") == "outside-b-halfspace-cap"
            for face in piece["faces"]
            for p in face["private_face_sources"]))
        self.assertTrue(point_in_piece(
            piece, (-0.75, 0, 0), result["local_calculation_anchor_m"]))
        self.assertFalse(point_in_piece(
            piece, (-0.25, 0, 0), result["local_calculation_anchor_m"]))

    def test_disjoint_tangent_identical_and_containing_brush(self):
        for displacement, classification in (
            (3., "disjoint"), (1., "boundary-contact")):
            result = subtract_private_boxes(
                self.half, self.half, transform_b=move(displacement))
            self.assert_valid_pieces(result)
            self.assertEqual(result["sat_contact_classification"],
                             classification)
            self.assertEqual(result["piece_count"], 1)
            self.assertEqual(result["pieces"][0]["emission"],
                             "unchanged-source-a")
            self.assertAlmostEqual(result["remaining_volume_m3"], 4.)
            self.assertEqual(result["removed_intersection_volume_m3"], 0.)
        same = subtract_private_boxes(self.half, self.half)
        self.assert_valid_pieces(same)
        self.assertEqual(same["piece_count"], 0)
        self.assertEqual(same["pieces"], [])
        self.assertAlmostEqual(same["removed_intersection_volume_m3"], 4.)
        self.assertAlmostEqual(same["remaining_volume_m3"], 0.)
        # Larger B completely engulfs A including A's authored x=0 cap.
        engulf = subtract_private_boxes(
            self.half, box(size=(6., 6., 6.), distance=1.))
        self.assert_valid_pieces(engulf)
        self.assertEqual(engulf["piece_count"], 0)
        self.assertAlmostEqual(engulf["remaining_volume_m3"], 0.)

    def test_six_piece_internal_cavity_volume_and_disjoint_interiors(self):
        a = box(size=(4., 4., 4.), distance=1.)
        b = box()
        result = subtract_private_boxes(a, b, transform_b=move(-0.5))
        self.assert_valid_pieces(result)
        self.assertEqual(result["piece_count"], 6)
        self.assertAlmostEqual(result["source_a_volume_m3"], 48.)
        self.assertAlmostEqual(result["removed_intersection_volume_m3"], 4.)
        self.assertAlmostEqual(result["remaining_volume_m3"], 44.)
        anchor = result["local_calculation_anchor_m"]
        # Sample a strict interior grid. Every retained sample must be
        # in exactly one convex piece, never two. The removed B interior
        # must be absent even though it lies strictly inside A.
        for xi in range(-7, 4):
            x = xi/4.
            for yi in range(-7, 8, 2):
                y = yi/4.
                for zi in range(-7, 8, 2):
                    z = zi/4.
                    if abs(x+1.5) < 1e-7 or abs(x+0.5) < 1e-7:
                        continue  # samples landing on coplanar piece seams
                    count = sum(point_in_piece(
                        piece, (x, y, z), anchor)
                        for piece in result["pieces"])
                    inside_a = -2 < x < 1 and abs(y) < 2 and abs(z) < 2
                    inside_b = -1.5 < x < -0.5 and abs(y) < 1 and abs(z) < 1
                    # Skip tests exactly on B's y/z planar boundaries:
                    # interface ownership is not unique there.
                    if abs(abs(y)-1.) < 1e-7 or abs(abs(z)-1.) < 1e-7:
                        continue
                    self.assertEqual(count, int(inside_a and not inside_b),
                                     (x, y, z, count))

    def test_rigid_rotation_and_large_preview_origin(self):
        quarter = {
            "basis": [[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]],
            "origin": [0., 0., 0.],
        }
        result = subtract_private_boxes(
            self.half, self.half, transform_b=quarter)
        self.assert_valid_pieces(result)
        self.assertAlmostEqual(result["removed_intersection_volume_m3"], 2.)
        self.assertAlmostEqual(result["remaining_volume_m3"], 2.)
        angle = math.pi/4
        turn = {
            "basis": [[math.cos(angle), -math.sin(angle), 0.],
                      [math.sin(angle), math.cos(angle), 0.],
                      [0., 0., 1.]],
            "origin": [0.1, 0.2, 0.],
        }
        tilted = subtract_private_boxes(
            self.half, self.half, transform_b=turn)
        self.assert_valid_pieces(tilted)
        self.assertGreater(tilted["removed_intersection_volume_m3"], 0.)
        self.assertLess(tilted["removed_intersection_volume_m3"], 4.)
        far = subtract_private_boxes(
            self.half, self.half,
            transform_a=move(100000., 20000., -1000.),
            transform_b=move(100000.5, 20000., -1000.))
        self.assert_valid_pieces(far)
        self.assertAlmostEqual(far["remaining_volume_m3"], 2., places=6)
        self.assertAlmostEqual(
            min(v[0] for p in far["pieces"] for v in p["vertices"]),
            99999.)

    def test_reject_bad_brush_transform_and_native_map_paths(self):
        for bad in ({}, None, {"kind": "StaticMeshActor"},
                    box(distance=1.0)):
            with self.subTest(spec=bad), self.assertRaises(ValueError):
                subtract_private_boxes(self.half, bad)
        for basis in (
            [[2.,0.,0.],[0.,1.,0.],[0.,0.,1.]],
            [[1.,0.,0.],[0.,1.,0.],[0.,0.,-1.]],
        ):
            with self.subTest(basis=basis), self.assertRaises(ValueError):
                subtract_private_boxes(
                    self.half, self.half,
                    transform_b={"basis": basis, "origin": [0,0,0]})

    def test_cli_is_read_only_and_requires_private_draft_selection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left, draft, transform, sentinel = (
                root/"left.json", root/"draft.json",
                root/"transform.json", root/"original.gmp")
            left.write_text(json.dumps(self.half), encoding="utf-8")
            draft.write_text(json.dumps({
                "schema": "DX2Ed-prop-draft-v1",
                "read_only_source": True,
                "copies": [{"name": "DraftProp_101",
                            "from_actor": "Brush::Box",
                            "brush": self.half}],
            }), encoding="utf-8")
            transform.write_text(json.dumps(move(0.5)), encoding="utf-8")
            sentinel.write_bytes(b"IMMUTABLE_ORIGINAL_DX2_GMP_TEST")
            before = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            command = [sys.executable, "-m", "dx2sdk.private_brush_subtraction"]
            good = subprocess.run(
                command+[str(left), str(draft), "--copy-b", "DraftProp_101",
                         "--transform-b", str(transform)],
                capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            output = json.loads(good.stdout)
            self.assertEqual(output["piece_count"], 1)
            self.assertAlmostEqual(output["remaining_volume_m3"], 2.)
            for denied in (
                [str(left),str(draft)],
                [str(sentinel),str(left)],
                [str(left),str(sentinel)],
                [str(left),str(draft),"--copy-b","DraftProp_999"],
                [str(left),str(left),"--transform-a",str(sentinel)]):
                with self.subTest(args=denied):
                    run = subprocess.run(
                        command+denied, capture_output=True, text=True)
                    self.assertEqual(run.returncode, 2, run.stderr)
                    self.assertFalse(run.stdout.strip())
            self.assertEqual(
                sorted(p.name for p in root.iterdir()),
                ["draft.json", "left.json", "original.gmp", "transform.json"])
            self.assertEqual(before, hashlib.sha256(sentinel.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
