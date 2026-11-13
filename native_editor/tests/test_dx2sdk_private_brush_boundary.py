"""Asset-free regression for a source-private convex closed boundary contract.

The topology and segment tests use only invented editor-authored Box planes.
No original DX2 retail geometry or native writer is invoked.
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

from dx2sdk.private_brush_boundary import (
    SCHEMA, SEGMENT_SCHEMA, build_private_box_boundary,
    query_private_box_segment,
)


def cut(normal, distance=0.0, keep_positive=False):
    return {
        "normal": list(normal), "distance": distance,
        "keep_positive": keep_positive,
    }


def box(*cuts):
    result = {"kind": "Box", "size": [2.0, 2.0, 2.0], "steps": 1}
    if len(cuts) == 1:
        result["clip_plane"] = cuts[0]
    else:
        result["clip_planes"] = list(cuts)
    return result


class PrivateBoundaryTests(unittest.TestCase):
    def test_half_cube_exact_face_edge_graph_and_source_isolation(self):
        spec = box(cut((1.0, 0.0, 0.0)))
        original = deepcopy(spec)
        result = build_private_box_boundary(spec)
        same = build_private_box_boundary(spec)
        self.assertEqual(spec, original)
        self.assertEqual(result, same)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual((result["vertex_count"], result["edge_count"],
                          result["face_count"]), (8, 12, 6))
        self.assertEqual(result["euler_characteristic"], 2)
        self.assertAlmostEqual(result["enclosed_volume_m3"], 4.0)
        self.assertAlmostEqual(result["surface_area_m2"], 16.0)
        self.assertTrue(result["all_edges_two_opposite_face_uses"])
        self.assertFalse(result["native_BSP_or_CSG_writer_enabled"])
        self.assertFalse(result["native_collision_generated"])
        self.assertFalse(result["source_gmp_or_ibd_modified"])
        self.assertFalse(result["retail_game_runtime_verified"])
        for face in result["faces"]:
            self.assertEqual(len(face["vertex_ids"]),
                             len(face["adjacent_face_indices_per_edge"]))
            self.assertGreater(face["area_m2"], 0)
        for edge in result["edges"]:
            first, second = edge["oriented_face_uses"]
            self.assertEqual(first["oriented_vertex_ids"],
                             second["oriented_vertex_ids"][::-1])
            self.assertNotEqual(first["face_index"], second["face_index"])
        self.assertEqual(sorted(face["slot"] for face in result["faces"]
                                if face["kind"] == "private_cut_cap"), [0])

    def test_eight_corner_brush_closed_boundary_and_interior_probe(self):
        u = 1.0/math.sqrt(3.0)
        corners = [cut((x*u, y*u, z*u), 1.4)
                   for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        shape = box(*corners)
        report = build_private_box_boundary(shape)
        self.assertEqual((report["face_count"], report["vertex_count"],
                          report["edge_count"]), (14, 24, 36))
        self.assertEqual(report["euler_characteristic"], 2)
        self.assertEqual(sum(f["kind"] == "private_cut_cap"
                             for f in report["faces"]), 8)
        expected_volume = 8 - 8*(3-math.sqrt(3)*1.4)**3/6
        self.assertAlmostEqual(report["enclosed_volume_m3"], expected_volume,
                               places=6)
        self.assertEqual(
            query_private_box_segment(shape, (0,0,0), (0,0,0))["contact_kind"],
            "stationary-inside")
        reordered = build_private_box_boundary(box(*reversed(corners)))
        self.assertEqual(report["private_geometry_sha256"],
                         reordered["private_geometry_sha256"])
        self.assertNotEqual(report["source_private_spec_sha256"],
                            reordered["source_private_spec_sha256"])

    def test_segment_entry_exit_and_cut_face_identity(self):
        spec = box(cut((1,0,0)))
        hit = query_private_box_segment(spec, (-2,0,0), (2,0,0))
        self.assertEqual(hit["schema"], SEGMENT_SCHEMA)
        self.assertTrue(hit["intersects"])
        self.assertTrue(hit["crosses_strict_interior"])
        self.assertEqual(hit["contact_kind"], "interior-interval")
        self.assertAlmostEqual(hit["entry_t"], 0.25)
        self.assertAlmostEqual(hit["exit_t"], 0.50)
        self.assertEqual(hit["entry_point"], [-1.0,0.0,0.0])
        self.assertEqual(hit["exit_point"], [0.0,0.0,0.0])
        faces = build_private_box_boundary(spec)["faces"]
        self.assertEqual([faces[i]["kind"] for i in hit["exit_face_indices"]],
                         ["private_cut_cap"])
        self.assertEqual([faces[i]["slot"] for i in hit["entry_face_indices"]],
                         [1])
        self.assertEqual(hit["start_classification"], "outside")
        self.assertEqual(hit["end_classification"], "outside")
        from_inside = query_private_box_segment(spec, (-0.5,0,0), (0.5,0,0))
        self.assertTrue(from_inside["intersects"])
        self.assertAlmostEqual(from_inside["entry_t"], 0.0)
        self.assertAlmostEqual(from_inside["exit_t"], 0.5)
        self.assertEqual(from_inside["start_classification"], "inside")
        self.assertGreaterEqual(len(
            query_private_box_segment(spec, (-2,-2,0), (0,0,0))[
                "entry_face_indices"]), 2)

    def test_disjoint_parallel_grazing_and_boundary_only_cases(self):
        spec = box(cut((1,0,0)))
        miss = query_private_box_segment(spec, (-2,2,0), (2,2,0))
        self.assertFalse(miss["intersects"])
        self.assertEqual(miss["contact_kind"], "miss")
        self.assertIsNone(miss["entry_t"])
        boundary = query_private_box_segment(spec, (0,-2,0), (0,2,0))
        self.assertTrue(boundary["intersects"])
        self.assertEqual(boundary["contact_kind"], "boundary-only-interval")
        self.assertFalse(boundary["crosses_strict_interior"])
        self.assertAlmostEqual(boundary["entry_t"], 0.25)
        self.assertAlmostEqual(boundary["exit_t"], 0.75)
        tangent = query_private_box_segment(spec, (0,2,0), (0,0,2))
        self.assertTrue(tangent["intersects"])
        self.assertEqual(tangent["contact_kind"], "tangent-point")
        self.assertAlmostEqual(tangent["entry_t"], 0.5)
        self.assertAlmostEqual(tangent["exit_t"], 0.5)
        stationary = query_private_box_segment(spec, (0,0,0), (0,0,0))
        self.assertEqual(stationary["contact_kind"], "stationary-boundary")
        self.assertFalse(stationary["crosses_strict_interior"])
        self.assertFalse(
            query_private_box_segment(spec, (2,2,2), (2,2,2))["intersects"])

    def test_refuse_nonfinite_broken_private_and_overbounded_geometry(self):
        spec = box(cut((1,0,0)))
        for invalid in (
                None, {"kind": "StaticMeshActor"},
                box(cut((0,0,0))),
                box(*[cut((1,0,0)) for _ in range(9)]),
                box(cut((1,0,0), 1.0)),
                box(cut((1,0,0)), cut((1,0,0)))):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                build_private_box_boundary(invalid)
        for start, end in (
            ((0,0,float("nan")), (1,1,1)),
            ((0,0,0), (float("inf"),1,1)),
            ((0,0,0), (2_000_000,0,0)),
            ((True,0,0), (0,0,0)),
            ((0,0), (0,0,0)),
        ):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                query_private_box_segment(spec, start, end)

    def test_cli_draft_restrictions_and_unchanged_original_gmp_sentinel(self):
        spec = box(cut((1,0,0)))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            private = root/"private.json"
            private.write_text(json.dumps(spec), encoding="utf-8")
            source = root/"original.gmp"
            source.write_bytes(b"NEVER_MUTATE_ORIGINAL_GMP")
            source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            script = [sys.executable, "-m", "dx2sdk.private_brush_boundary"]
            command = script+[str(private), "--start", "-2", "0", "0",
                              "--end", "2", "0", "0"]
            hit = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(hit.returncode, 0, hit.stderr)
            self.assertEqual(json.loads(hit.stdout)["contact_kind"],
                             "interior-interval")
            draft = root/"draft.json"
            draft.write_text(json.dumps({
                "schema": "DX2Ed-prop-draft-v1", "read_only_source": True,
                "copies": [{
                    "name": "DraftProp_98", "from_actor": "Brush::Box",
                    "brush": spec,
                }],
            }), encoding="utf-8")
            without_copy = subprocess.run(
                script+[str(draft)], capture_output=True, text=True)
            self.assertEqual(without_copy.returncode, 2)
            with_copy = subprocess.run(
                script+[str(draft), "--copy", "DraftProp_98"],
                capture_output=True, text=True)
            self.assertEqual(with_copy.returncode, 0, with_copy.stderr)
            self.assertEqual(json.loads(with_copy.stdout)["face_count"], 6)
            for path in (source,):
                denied = subprocess.run(
                    script+[str(path)], capture_output=True, text=True)
                self.assertEqual(denied.returncode, 2)
            self.assertEqual(source_sha,
                             hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(sorted(p.name for p in root.iterdir()),
                             ["draft.json", "original.gmp", "private.json"])


if __name__ == "__main__":
    unittest.main()
