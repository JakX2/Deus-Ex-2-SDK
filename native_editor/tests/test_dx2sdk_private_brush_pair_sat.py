"""Synthetic regression of source-private convex pair SAT, not DX2 physics."""
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

from dx2sdk.private_brush_pair_sat import (
    SCHEMA, inspect_private_box_pair,
)


def box(*cuts):
    return {
        "kind": "Box", "size": [2., 2., 2.], "steps": 1,
        "clip_plane": cuts[0],
    } if len(cuts) == 1 else {
        "kind": "Box", "size": [2., 2., 2.], "steps": 1,
        "clip_planes": list(cuts),
    }


def cut(n, d=0.0):
    return {"normal": list(n), "distance": d, "keep_positive": False}


def translated(x=0, y=0, z=0):
    return {
        "basis": [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]],
        "origin": [x, y, z],
    }


class PrivatePairSATTests(unittest.TestCase):
    def setUp(self):
        self.spec = box(cut((1., 0., 0.)))

    def test_same_brush_overlap_and_stable_readonly_identity(self):
        original = deepcopy(self.spec)
        result = inspect_private_box_pair(self.spec, self.spec)
        self.assertEqual(result, inspect_private_box_pair(self.spec, self.spec))
        self.assertEqual(self.spec, original)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["classification"], "interior-overlap")
        self.assertTrue(result["intersects_or_touches_within_tolerance"])
        self.assertTrue(result["has_strict_volume_overlap"])
        self.assertGreaterEqual(result["tested_unique_sat_axis_count"], 3)
        self.assertEqual(result["boundary_topology_sha256_a"],
                         result["boundary_topology_sha256_b"])
        self.assertFalse(result["native_bsp_compilation_enabled"])
        self.assertFalse(result["native_havok_mopp_collision_enabled"])
        self.assertFalse(result["source_original_gmp_or_ibd_modified"])
        self.assertFalse(result["retail_game_runtime_verified"])

    def test_disjoint_touching_face_edge_corner_and_interior_overlap(self):
        samples = [
            ((3, 0, 0), "disjoint", False, False),
            ((1, 0, 0), "boundary-contact", True, False),
            ((1, 2, 0), "boundary-contact", True, False),
            ((1, 2, 2), "boundary-contact", True, False),
            ((0.5, 0, 0), "interior-overlap", True, True),
            ((0, 0, 0), "interior-overlap", True, True),
        ]
        for origin, kind, contact, interior in samples:
            with self.subTest(origin=origin):
                result = inspect_private_box_pair(
                    self.spec, self.spec, transform_b=translated(*origin))
                self.assertEqual(result["classification"], kind)
                self.assertEqual(result[
                    "intersects_or_touches_within_tolerance"], contact)
                self.assertEqual(result["has_strict_volume_overlap"], interior)
                self.assertTrue(math.isclose(
                    sum(v*v for v in result["witness_axis"]), 1.0,
                    rel_tol=0.0, abs_tol=1e-9))
                self.assertTrue(result["tested_unique_sat_axis_count"] <= 1324)
        far = inspect_private_box_pair(
            self.spec, self.spec, transform_b=translated(3, 0, 0))
        self.assertAlmostEqual(far["witness_axis_gap_m"], 2.0)
        self.assertIsNone(far["minimum_tested_interval_overlap_m"])

    def test_rotated_brush_and_edge_cross_only_separating_axis(self):
        quarter = {
            "basis": [[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]],
            "origin": [0., 0., 0.],
        }
        overlap = inspect_private_box_pair(
            self.spec, self.spec, transform_b=quarter)
        self.assertEqual(overlap["classification"], "interior-overlap")
        # This fixture's three original and three rotated face-normal axes
        # all overlap, but an EDGE x EDGE axis proves the pair disjoint.
        # R = Rz(0.04597668) Ry(0.92382237) Rx(0.91500877).
        tilted = {
            "basis": [
                [0.6021376776965159, 0.6037048141609223,
                 0.5224659935892222],
                [0.027703814691560497, 0.6382046071279579,
                 -0.769368168104312],
                [-0.7979114711230704, 0.47773986310499084,
                 0.3675621137313287],
            ],
            "origin": [-0.99167546, 2.40033669, -0.46588614],
        }
        result = inspect_private_box_pair(
            self.spec, self.spec, transform_b=tilted)
        self.assertEqual(result["classification"], "disjoint")
        self.assertEqual(result["witness_kind"], "edge-cross")
        self.assertGreater(result["witness_axis_gap_m"], 0.04)
        self.assertGreater(result["tested_sat_axis_types"].get("edge-cross", 0), 0)
        self.assertEqual(tilted["origin"],
                         [-0.99167546, 2.40033669, -0.46588614])

    def test_reject_invalid_geometry_transforms_and_native_source_types(self):
        for bad in (
            {"basis": [[1, 0, 0], [0, 1, 0], [0, 0, -1]],
             "origin": [0, 0, 0]},  # reflection
            {"basis": [[2, 0, 0], [0, 1, 0], [0, 0, 1]],
             "origin": [0, 0, 0]},  # scale
            {"basis": [[1, 0, 0], [0.2, 1, 0], [0, 0, 1]],
             "origin": [0, 0, 0]},  # shear
            {"basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
             "origin": [float("nan"), 0, 0]},
            {"basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
             "origin": [1_000_001, 0, 0]},
            {"basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
             "origin": [True, 0, 0]},
            {"basis": [1, 0, 0], "origin": [0, 0, 0]},
            {"origin": [0, 0, 0]},
        ):
            with self.subTest(transform=bad), self.assertRaises(ValueError):
                inspect_private_box_pair(
                    self.spec, self.spec, transform_b=bad)
        for bad in (
            {}, {"kind": "StaticMeshActor", "source": "game.gmp"},
            box(cut((0, 0, 0))),
        ):
            with self.subTest(spec=bad), self.assertRaises(ValueError):
                inspect_private_box_pair(self.spec, bad)

    def test_readonly_private_draft_and_cli_no_original_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = root/"first.json", root/"second.json"
            first.write_text(json.dumps(self.spec), encoding="utf-8")
            second.write_text(json.dumps(self.spec), encoding="utf-8")
            original = root/"M1_original.gmp"
            original.write_bytes(b"PROPRIETARY_SOURCE_SENTINEL_UNTOUCHED")
            original_sha = hashlib.sha256(original.read_bytes()).hexdigest()
            move = root/"move.json"
            move.write_text(json.dumps(translated(3, 0, 0)),
                            encoding="utf-8")
            command = [sys.executable, "-m",
                       "dx2sdk.private_brush_pair_sat"]
            run = subprocess.run(command + [
                str(first), str(second), "--transform-b", str(move)],
                capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)["classification"],
                             "disjoint")
            draft = root/"private_draft.json"
            draft.write_text(json.dumps({
                "schema": "DX2Ed-prop-draft-v1", "read_only_source": True,
                "copies": [{"name": "DraftProp_99", "from_actor": "Brush::Box",
                            "brush": self.spec}],
            }), encoding="utf-8")
            selection = subprocess.run(command+[
                str(first), str(draft), "--copy-b", "DraftProp_99"],
                capture_output=True, text=True)
            self.assertEqual(selection.returncode, 0, selection.stderr)
            self.assertEqual(json.loads(selection.stdout)["classification"],
                             "interior-overlap")
            refusal_cases = (
                [str(original), str(second)],
                [str(first), str(original)],
                [str(first), str(draft)],
                [str(draft), str(second)],
                [str(first), str(draft), "--copy-b", "DraftProp_000"],
                [str(first), str(second), "--transform-b", str(original)],
            )
            for args in refusal_cases:
                with self.subTest(args=args):
                    refused = subprocess.run(command+args, capture_output=True,
                                             text=True)
                    self.assertEqual(refused.returncode, 2, refused.stderr)
                    self.assertFalse(refused.stdout.strip())
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),
                             original_sha)
            self.assertEqual(
                sorted(x.name for x in root.iterdir()),
                sorted(["first.json", "second.json", "private_draft.json",
                        "move.json", "M1_original.gmp"]))


if __name__ == "__main__":
    unittest.main()
