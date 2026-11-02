"""Synthetic geometric regression tests for the Seattle Club stair preview.

Coordinates are small derived bounds and placements, not retail geometry,
textures or game packages. They make the correction measurable and reversible.
"""
import itertools
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "map_exporter"))

from dx2level import actor_matrix, preview_roll_sign
from dx2scene import SCALE


def rendered_aabb_unreal(actor, bounds, roll_sign):
    """Reconstruct UE-coordinate AABB from the exported glTF node matrix."""
    matrix = actor_matrix(actor, roll_sign=roll_sign)
    low, high = bounds
    corners = itertools.product(*zip(low, high))
    ue_points = []
    for x, y, z in corners:
        world = [x * SCALE, z * SCALE, y * SCALE]
        placed = [
            sum(matrix[column * 4 + row] * world[column] for column in range(3))
            + matrix[12 + row]
            for row in range(3)
        ]
        ue_points.append([placed[0] / SCALE, placed[2] / SCALE, placed[1] / SCALE])
    return ([min(p[i] for p in ue_points) for i in range(3)],
            [max(p[i] for p in ue_points) for i in range(3)])


class SeattleClubStairPreviewTests(unittest.TestCase):
    # A 12-foot-wide tread: 192 Unreal units across and 48 units deep.
    TREAD_BOUNDS = ([-48.0015, 0.0, -192.0], [0.0, 32.014, 0.0])

    def test_correction_is_only_for_two_club_stair_meshes(self):
        self.assertEqual(preview_roll_sign("M1_Seattle_Club.gmp", "1Hub_club-stair-12ft", enabled=True), -1)
        self.assertEqual(preview_roll_sign("M1_Seattle_Club.gmp", "1Hub_penthouseB1_stair1", enabled=True), -1)
        self.assertEqual(preview_roll_sign("M1_Seattle_Club.gmp", "M1PENT_stair-rail", enabled=True), 1)
        self.assertEqual(preview_roll_sign("M3_Germany_Trier.gmp", "1Hub_club-stair-12ft", enabled=True), 1)
        self.assertEqual(preview_roll_sign("M1_Seattle_Club.gmp", "GO_coffeecup", enabled=True), 1)

    def test_default_preview_preserves_raw_actor_rotation(self):
        self.assertEqual(preview_roll_sign("M1_Seattle_Club.gmp", "1Hub_club-stair-12ft"), 1)

    def test_west_stair_moves_inside_bsp_side(self):
        a = dict(x=-935.998, y=-835.999, z=-448, rotation=[0, 16384, 16384])
        corrected = rendered_aabb_unreal(a, self.TREAD_BOUNDS, -1)
        uncorrected = rendered_aabb_unreal(a, self.TREAD_BOUNDS, 1)
        # Nearby BSP footprint has x = -936 .. -744.
        self.assertAlmostEqual(corrected[0][0], -936, delta=0.02)
        self.assertAlmostEqual(corrected[1][0], -744, delta=0.02)
        self.assertLess(uncorrected[0][0], -1127)

    def test_east_stair_moves_inside_bsp_side(self):
        a = dict(x=952, y=16, z=-64, rotation=[0, -16384, 16384])
        corrected = rendered_aabb_unreal(a, self.TREAD_BOUNDS, -1)
        uncorrected = rendered_aabb_unreal(a, self.TREAD_BOUNDS, 1)
        # Nearby BSP footprint has x = 760 .. 952.
        self.assertAlmostEqual(corrected[0][0], 760, delta=0.02)
        self.assertAlmostEqual(corrected[1][0], 952, delta=0.02)
        self.assertGreater(uncorrected[1][0], 1143)

    def test_penthouse_stair_footprint_and_elevation(self):
        a = dict(x=680, y=-496, z=-320, rotation=[0, 16384, 16384])
        bounds = ([-239.994, -160, -128], [0.01, 0, 0])
        corrected = rendered_aabb_unreal(a, bounds, -1)
        uncorrected = rendered_aabb_unreal(a, bounds, 1)
        # Stair is adjacent to BSP x = 680 .. 808 and z = -320 .. -160.
        self.assertAlmostEqual(corrected[0][0], 680, delta=0.02)
        self.assertAlmostEqual(corrected[1][0], 808, delta=0.02)
        self.assertAlmostEqual(corrected[0][2], -320, delta=0.02)
        self.assertAlmostEqual(corrected[1][2], -160, delta=0.02)
        self.assertLess(uncorrected[0][0], 553)
        self.assertLess(uncorrected[0][2], -479)

    def test_original_euler_rotation_unchanged_by_default(self):
        actor = dict(x=0, y=0, z=0, rotation=[0, 16384, 16384])
        self.assertEqual(actor_matrix(actor), actor_matrix(actor, roll_sign=1))
        self.assertNotEqual(actor_matrix(actor), actor_matrix(actor, roll_sign=-1))

    def test_editor_backend_cache_version_changed(self):
        backend = (ROOT / "native_editor" / "godot_editor"
                   / "backend" / "dx2_native_backend.py").read_text()
        self.assertIn("v0.2.7-wto-glass-alpha-v1", backend)

    def test_export_report_names_precisely_applied_preview_corrections(self):
        source = (ROOT / "map_exporter" / "dx2level.py").read_text()
        self.assertIn("'club_stair_preview_roll_corrections':club_stair_preview_fixes", source)
        self.assertIn("'DX2PreviewRollSign':roll_sign", source)


if __name__ == "__main__":
    unittest.main()
