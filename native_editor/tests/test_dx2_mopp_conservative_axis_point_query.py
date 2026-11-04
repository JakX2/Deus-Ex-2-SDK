"""Synthetic-only tests for the conservative, NOT-runtime DX2 MOPP point walker."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import emit_synthetic_mopp_fixture as emitter
import inspect_level_mopp_triangle_tree as mopp
import inspect_mopp_axis_point_candidates as spatial

ROOT_CODE = b"\x28\x00\xff"


def walker(code: bytes, triangles: int = 2,
           *, origin=(0., 0., 0.), scale=65536.):
    return spatial.ConservativeMoppPointCandidates(
        code, triangles, (*origin, scale))


class ConservativePointQueryTests(unittest.TestCase):
    def test_two_leaf_axis_split_selects_expected_candidate_ids(self):
        code = ROOT_CODE + b"\x20\x80\x01\x30\x31"
        q = walker(code)
        left = q.point((30., 0., 100.), tolerance_units=0)
        right = q.point((190., 0., 100.), tolerance_units=0)
        self.assertEqual(left["candidate_triangle_ids"], [0])
        self.assertEqual(right["candidate_triangle_ids"], [1])
        self.assertFalse(left["query_is_a_havok_runtime_result"])

    def test_one_unit_margin_keeps_both_near_quantized_boundary(self):
        q = walker(ROOT_CODE + b"\x20\x80\x01\x30\x31")
        self.assertEqual(q.point((128.5, 0., 100.),
                                 tolerance_units=0)["candidate_triangle_ids"], [1])
        self.assertEqual(q.point((128.5, 0., 100.),
                                 tolerance_units=1)["candidate_triangle_ids"], [0, 1])
        self.assertEqual(q.point((127.5, 0., 100.),
                                 tolerance_units=1)["candidate_triangle_ids"], [0, 1])

    def test_root_filter_excludes_outside_points(self):
        q = walker(ROOT_CODE + b"\x30", triangles=1)
        self.assertEqual(q.point((0., 0., 10.))["candidate_triangle_ids"], [0])
        self.assertEqual(q.point((0., 0., -10.))["candidate_triangle_ids"], [])
        self.assertEqual(q.point((0., 0., 290.))["candidate_triangle_ids"], [])
        self.assertEqual(q.point((0., 0., 260.), tolerance_units=1)["candidate_triangle_ids"], [])

    def test_rescale_is_necessary_for_a_descended_axis_split(self):
        # MOPP 0x01 transforms X=65 into (65-1)*2=128.
        code = ROOT_CODE + b"\x01\x01\x00\x00\x20\x80\x01\x30\x31"
        q = walker(code)
        p = q.point((65., 0., 100.), tolerance_units=0)
        self.assertEqual(p["candidate_triangle_ids"], [1])
        self.assertEqual(p["rescale_instructions_applied"], 1)

    def test_split_with_overlapping_thresholds_checks_both(self):
        # 0x10 BB=140 AA=120 -> overlap zone including coordinate 130.
        code = ROOT_CODE + b"\x10\x8c\x78\x01\x30\x31"
        q = walker(code)
        self.assertEqual(q.point((130., 0., 100.),
                                 tolerance_units=0)["candidate_triangle_ids"], [0, 1])

    def test_split16_two_offsets_and_output_base(self):
        # 0x23, first displacement=0, second=1. Two leaf IDs.
        code = ROOT_CODE + b"\x23\x8c\x78\x00\x00\x00\x01\x30\x31"
        q = walker(code)
        self.assertEqual(q.point((130., 0., 100.),
                                 tolerance_units=0)["candidate_triangle_ids"], [0, 1])
        base_code = ROOT_CODE + b"\x0b\x00\x00\x01\x00\x30"
        self.assertEqual(walker(base_code, triangles=300).point(
            (0., 0., 100.))["candidate_triangle_ids"], [256])

    def test_diagonal_axis_is_never_guessed(self):
        # 0x13 must take both branches even when the point seems far away.
        code = ROOT_CODE + b"\x13\x01\xfe\x01\x30\x31"
        q = walker(code)
        result = q.point((0., 0., 100.))
        self.assertEqual(result["candidate_triangle_ids"], [0, 1])
        self.assertEqual(result["opaque_diagonal_decisions_explored_both"], 1)
        self.assertFalse(result["diagonal_filter_arithmetic_resolved"])

    def test_filter24_axis_hypothesis_is_explicit(self):
        # x24=512, lower 256, upper 768; high-resolution coordinate path.
        code = ROOT_CODE + b"\x29\x00\x01\x00\x00\x03\x00\x30"
        q = walker(code, triangles=1)
        self.assertEqual(q.point((512/65536., 0., 100.),
                                 tolerance_units=0)["candidate_triangle_ids"], [0])
        self.assertEqual(q.point((1., 0., 100.),
                                 tolerance_units=0)["candidate_triangle_ids"], [])

    def test_leaf_id_byte_order_and_no_narrowphase_claim(self):
        code = ROOT_CODE + b"\x52\x00\x01\x00"
        q = walker(code, triangles=300)
        result = q.point((0., 0., 100.))
        self.assertEqual(result["candidate_triangle_ids"], [256])
        self.assertFalse(result["narrowphase_triangle_intersections_computed"])

    def test_realistic_two_triangle_synthetic_level_probe(self):
        xyz, tri = emitter._make_disconnected_triangles(2)
        level, blocks, _ = emitter.make_synthetic_level_fixture(xyz, tri)
        result = spatial.inspect_source_level(level, blocks)
        self.assertEqual(result["nondegenerate_centroid_probes"], 2)
        self.assertEqual(result["centroid_false_negatives"], 0)
        self.assertTrue(result["all_centroids_checked"])
        self.assertFalse(result["spatial_semantics_runtime_verified"])

    def test_synthetic_compiler_is_not_a_spatial_builder(self):
        # Both triangle centroids have low X, but generated root uses 0x20
        # split X at 128, so the second triangle is incorrectly pruned.
        xyz = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.),
               (0., 0., 100.), (1., 0., 100.), (0., 1., 100.)]
        tri = [(0, 1, 2), (3, 4, 5)]
        level, blocks, _ = emitter.make_synthetic_level_fixture(xyz, tri)
        result = spatial.inspect_source_level(level, blocks)
        self.assertEqual(result["nondegenerate_centroid_probes"], 2)
        self.assertGreater(result["centroid_false_negatives"], 0)
        self.assertEqual(result["status"], "centroid_counterexample_observed")
        # The old symbolic graph still passes; this is why geometry matters.
        self.assertEqual(mopp.inspect_mopp_link(level, blocks)[
            "unique_valid_mopp_triangle_leaves"], 2)

    def test_omitted_degenerate_triangle_not_in_candidates(self):
        xyz = [(0.,0.,0.),(1.,0.,0.),(2.,0.,0.),(0.,1.,0.)]
        tri = [(0,1,2),(0,1,3)]
        level, blocks, _ = emitter.make_synthetic_level_fixture(xyz, tri)
        result = spatial.inspect_source_level(level, blocks)
        self.assertEqual(result["nondegenerate_centroid_probes"], 1)
        self.assertEqual(result["centroid_false_negatives"], 0)
        self.assertEqual(result["original_mopp_reachable_triangle_count"], 1)

    def test_sample_limit_is_deterministic(self):
        xyz, tri = emitter._make_disconnected_triangles(2)
        level, blocks, _ = emitter.make_synthetic_level_fixture(xyz, tri)
        result = spatial.inspect_source_level(level, blocks, max_centroids=1)
        self.assertEqual(result["nondegenerate_centroid_probes"], 1)
        self.assertFalse(result["all_centroids_checked"])

    def test_hash_and_original_bytes_remain_unchanged(self):
        xyz, tri = emitter._make_disconnected_triangles(2)
        level, blocks, _ = emitter.make_synthetic_level_fixture(xyz, tri)
        digest = hashlib.sha256(level).digest()
        spatial.inspect_source_level(level, blocks)
        self.assertEqual(hashlib.sha256(level).digest(), digest)

    def test_invalid_input_values_fail_closed(self):
        q = walker(ROOT_CODE + b"\x30", triangles=1)
        for val in ((0, float("nan"), 0), (0, float("inf"), 0),
                    (0, True, 0), (0, 0), "123", (1e8,0,0)):
            with self.subTest(pos=val), self.assertRaises(ValueError):
                q.point(val)
        for tol in (-1, float("nan"), float("inf"), True, 5):
            with self.subTest(tol=tol), self.assertRaises(ValueError):
                q.point((0, 0, 10), tolerance_units=tol)

    def test_broken_source_grammar_rejected_before_query(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            walker(ROOT_CODE+b"\xff", triangles=1)
        with self.assertRaisesRegex(ValueError, "jump"):
            walker(ROOT_CODE+b"\x05\xff\x30", triangles=1)
        with self.assertRaises(ValueError):
            spatial.ConservativeMoppPointCandidates(ROOT_CODE+b"\x30",
                                                     1, (0.,0.,0.,0.))

    def test_no_assumed_runtime_spatial_correctness(self):
        code = ROOT_CODE + b"\x20\x80\x01\x30\x31"
        q = walker(code)
        self.assertEqual(q.complete_leaf_set, {0,1})
        self.assertEqual(q.point((0.,0.,100.))["candidate_triangle_ids"], [0])
        self.assertEqual(q.point((0.,0.,100.))["tolerance_quantization_units"], 1.0)
        self.assertFalse(q.point((0.,0.,100.))["query_is_a_havok_runtime_result"])


if __name__ == "__main__":
    unittest.main()
