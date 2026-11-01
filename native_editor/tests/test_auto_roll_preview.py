"""Synthetic tests: global roll preview is a hypothesis, not a native fix."""
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "map_exporter"))

from dx2level import actor_matrix, meaningful_roll_flip, preview_auto_roll_sign, preview_roll_sign


class AutoRollPreviewTests(unittest.TestCase):
    def test_only_rolls_with_a_real_orientation_difference_are_inverted(self):
        self.assertFalse(meaningful_roll_flip([0, 0, 0]))
        self.assertFalse(meaningful_roll_flip([256, 16384, 32768]))  # Trier screenshot: 180-degree roll
        self.assertFalse(meaningful_roll_flip([0, 0, -32768]))
        self.assertFalse(meaningful_roll_flip([0, 0, 65536]))
        self.assertTrue(meaningful_roll_flip([0, 32768, 16384]))  # Seattle trim: +90 degrees
        self.assertTrue(meaningful_roll_flip([0, 0, -16384]))
        self.assertTrue(meaningful_roll_flip([100, 0, 8192]))

    def test_no_unrecognized_rotator_values_are_auto_corrected(self):
        self.assertFalse(meaningful_roll_flip(None))
        self.assertFalse(meaningful_roll_flip([0, 0]))
        self.assertFalse(meaningful_roll_flip([0, 0, float("nan")]))
        self.assertFalse(meaningful_roll_flip([0, 0, float("inf")]))
        self.assertEqual(preview_auto_roll_sign({"rotation":[0, 0, 16384]}, False), 1)

    def test_seattle_trim_280_matches_manual_invert_roll_hypothesis(self):
        actor = {"x": -1200.01672363281, "y": 735.847595214844,
                 "z": 400.016448974609, "rotation":[0, 32768, 16384]}
        self.assertEqual(preview_auto_roll_sign(actor, True), -1)
        original = actor_matrix(actor)
        automatic = actor_matrix(actor, roll_sign=preview_auto_roll_sign(actor, True))
        manual = actor_matrix(actor, roll_sign=-1)
        self.assertEqual(automatic, manual)
        self.assertTrue(any(abs(a-b) > 0.1 for a,b in zip(original[:12], automatic[:12])))
        self.assertEqual(original[12:15], automatic[12:15])  # no movement or pivot translation

    def test_trier_180_roll_inversion_is_mathematical_noop(self):
        actor = {"x": -400, "y": 1000, "z": 180, "rotation":[256, 16384, 32768]}
        self.assertEqual(preview_auto_roll_sign(actor, True), 1)
        original = actor_matrix(actor)
        reversed_roll = actor_matrix(actor, roll_sign=-1)
        for a,b in zip(original, reversed_roll):
            self.assertAlmostEqual(a,b,places=10)

    def test_confirmed_club_opt_in_is_not_lost_when_auto_mode_off(self):
        self.assertEqual(preview_roll_sign("m1_seattle_club.gmp","1hub_club-stair-12ft",True),-1)
        self.assertEqual(preview_roll_sign("m1_seattle_club.gmp","1hub_club-stair-12ft",False),1)


if __name__=="__main__":
    unittest.main()
