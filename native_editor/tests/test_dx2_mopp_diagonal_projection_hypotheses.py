"""Asset-free tests for DX2 diagonal MOPP projection hypotheses.

Everything here is SYNTHETIC. Existing PR #38 conservative behavior remains
the default; this explicitly opt-in research mode is NOT a Havok runtime.
"""
from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_mopp_axis_point_candidates as spatial
import emit_synthetic_mopp_fixture as emitter

ROOT_CODE = b"\x28\x00\xff"
SPLIT_OPERANDS = b"\x80\x7f\x01\x30\x31"


def single_split(opcode: int):
    return spatial.ConservativeMoppPointCandidates(
        ROOT_CODE + bytes([opcode]) + SPLIT_OPERANDS, 2,
        (0.0, 0.0, 0.0, 65536.0))


class DiagonalProjectionHypothesisTests(unittest.TestCase):
    def test_published_op14_sign_is_falsified_by_selected_source_hypothesis(self):
        point = (80., 220., 20.)
        # Published nYpZ reference: 127 - Y/2 + Z/2, returns 27.
        published = 127. - point[1]/2 + point[2]/2
        derived = spatial._diagonal_projection(0x14, point)
        self.assertLess(published, 128)
        self.assertGreaterEqual(derived, 128)
        self.assertEqual(derived, 227.)
        walker = single_split(0x14)
        self.assertEqual(walker.point(point)["candidate_triangle_ids"], [0, 1])
        guessed = walker.point(point, diagonal_mode="derived_diagonals",
                               tolerance_units=1)
        self.assertEqual(guessed["candidate_triangle_ids"], [1])
        self.assertEqual(guessed["hypothesized_diagonal_branch_decisions"], 1)
        self.assertFalse(guessed["diagonal_projection_hypotheses_are_runtime_verified"])

    def test_published_op1c_formula_is_falsified_by_source_hypothesis(self):
        point = (220., 20., 20.)
        published = 254/3 + (-point[0] + point[1] + point[2])/3
        derived = spatial._diagonal_projection(0x1c, point)
        self.assertLess(published, 128)
        self.assertGreaterEqual(derived, 128)
        self.assertAlmostEqual(derived, (508 + 220 - 20 - 20)/3)
        self.assertEqual(single_split(0x1c).point(
            point, diagonal_mode="derived_diagonals",
            tolerance_units=1)["candidate_triangle_ids"], [1])

    def test_0x1b_remains_both_branches_even_in_research_mode(self):
        walker = single_split(0x1b)
        point = (200., 20., 20.)
        answer = walker.point(point, diagonal_mode="derived_diagonals")
        self.assertEqual(answer["candidate_triangle_ids"], [0, 1])
        self.assertEqual(answer["hypothesized_diagonal_branch_decisions"], 0)
        self.assertEqual(answer["opaque_diagonal_decisions_explored_both"], 1)
        self.assertIsNone(spatial._diagonal_projection(0x1b, point))

    def test_supported_hypothesized_axes_select_high_branch(self):
        high = {
            0x13: (10., 200., 200.), 0x14: (10., 220., 20.),
            0x15: (200., 10., 200.), 0x16: (220., 10., 20.),
            0x17: (200., 200., 10.), 0x18: (220., 20., 10.),
            0x19: (200., 200., 200.), 0x1a: (220., 220., 20.),
            0x1c: (220., 20., 20.),
        }
        for op, p in high.items():
            with self.subTest(opcode=hex(op)):
                v = spatial._diagonal_projection(op, p)
                self.assertGreaterEqual(v, 129)
                q = single_split(op).point(p, diagonal_mode="derived_diagonals")
                self.assertEqual(q["candidate_triangle_ids"], [1])

    def test_supported_hypothesized_axes_select_low_branch(self):
        low = {
            0x13: (200., 20., 20.), 0x14: (10., 20., 220.),
            0x15: (20., 220., 20.), 0x16: (20., 10., 220.),
            0x17: (20., 20., 220.), 0x18: (20., 220., 10.),
            0x19: (20., 20., 20.), 0x1a: (20., 20., 220.),
            0x1c: (20., 220., 220.),
        }
        for op, p in low.items():
            with self.subTest(opcode=hex(op)):
                self.assertLess(spatial._diagonal_projection(op, p), 127)
                q = single_split(op).point(p, diagonal_mode="derived_diagonals")
                self.assertEqual(q["candidate_triangle_ids"], [0])

    def test_all_default_diagonals_unpruned_and_unknowns_explicit(self):
        for op in range(0x13, 0x1d):
            with self.subTest(op=hex(op)):
                result = single_split(op).point((220., 220., 220.))
                self.assertEqual(result["candidate_triangle_ids"], [0, 1])
                self.assertEqual(result["diagonal_projection_mode"], "conservative")
                self.assertEqual(result["opaque_diagonal_decisions_explored_both"], 1)
                self.assertFalse(result["diagonal_filter_arithmetic_resolved"])

    def test_overlap_tolerance_never_switches_off_intended_child(self):
        point = (0., 128., 128.)
        q = single_split(0x13)
        r = q.point(point, diagonal_mode="derived_diagonals",
                    tolerance_units=1)
        self.assertEqual(r["candidate_triangle_ids"], [0, 1])
        self.assertEqual(r["tolerance_quantization_units"], 1.)

    def test_query_result_remains_candidate_only_not_contact(self):
        result = single_split(0x1c).point(
            (220., 20., 20.), diagonal_mode="derived_diagonals")
        self.assertFalse(result["query_is_a_havok_runtime_result"])
        self.assertFalse(result["narrowphase_triangle_intersections_computed"])
        self.assertFalse(result["diagonal_projection_hypotheses_are_runtime_verified"])
        self.assertEqual(result["unobserved_opcode_0x1b_explored_both"], True)

    def test_unknown_diagonal_mode_refused(self):
        q = single_split(0x13)
        for mode in ("runtime_havok", "", "prune_all", None, 0, [], {}):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                q.point((0., 0., 20.), diagonal_mode=mode)

    def test_source_derived_formulas_do_not_change_old_default(self):
        q = single_split(0x14)
        point = (10., 220., 20.)
        default = q.point(point)
        explicit = q.point(point, diagonal_mode="conservative")
        self.assertEqual(default, explicit)
        self.assertEqual(default["candidate_triangle_ids"], [0, 1])
        self.assertEqual(q.point(point, diagonal_mode="derived_diagonals")[
            "candidate_triangle_ids"], [1])

    def test_existing_synthetic_level_fixture_is_unmodified(self):
        xyz, triangles = emitter._make_disconnected_triangles(2)
        level, blocks, _ = emitter.make_synthetic_level_fixture(xyz, triangles)
        conservative = spatial.inspect_source_level(level, blocks)
        experimental = spatial.inspect_source_level(
            level, blocks, diagonal_mode="derived_diagonals")
        self.assertEqual(conservative["centroid_false_negatives"], 0)
        self.assertEqual(experimental["centroid_false_negatives"], 0)
        self.assertEqual(conservative["diagonal_projection_mode"], "conservative")
        self.assertEqual(experimental["diagonal_projection_mode"], "derived_diagonals")
        self.assertFalse(experimental["spatial_semantics_runtime_verified"])

    def test_unknown_mode_in_source_level_audit_refused(self):
        xyz, faces = emitter._make_disconnected_triangles(1)
        level, blocks, _ = emitter.make_synthetic_level_fixture(xyz, faces)
        with self.assertRaisesRegex(ValueError, "projection mode"):
            spatial.inspect_source_level(level, blocks, diagonal_mode="force")

    def test_0x14_formula_independent_of_unused_x(self):
        p = (0., 200., 60.)
        q = (254., 200., 60.)
        self.assertEqual(spatial._diagonal_projection(0x14, p),
                         spatial._diagonal_projection(0x14, q))

    def test_diagonal_hypothesis_components_not_quantized_too_early(self):
        p = (127.25, 86.5, 31.75)
        self.assertAlmostEqual(spatial._diagonal_projection(0x14, p),
                               127 + (86.5-31.75)/2)
        self.assertAlmostEqual(spatial._diagonal_projection(0x1c, p),
                               (508+127.25-86.5-31.75)/3)


if __name__ == "__main__":
    unittest.main()
