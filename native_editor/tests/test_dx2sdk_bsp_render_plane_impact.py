import unittest
from copy import deepcopy

from dx2sdk.bsp_render_plane_impact import compare_plane_render_triangles


class RenderPlaneImpactTests(unittest.TestCase):
    def setUp(self):
        self.nodes = [((0., 0., 1., 0.), (0., 0., 0., 10.))]
        self.triangles = [
            ([0, 0, 0], ((0., 0., 0.), (1., 0., 0.), (0., 1., 0.))),
            ([0, 0, 1], ((0., 0., 2.), (1., 0., 2.), (0., 1., 2.))),
            ([0, 0, 2], ((0., 0., 4.), (1., 0., 4.), (0., 1., 4.))),
        ]

    def test_plane_shift_changes_real_geometry_candidates_without_mutation(self):
        original_nodes = deepcopy(self.nodes)
        original_triangles = deepcopy(self.triangles)
        result = compare_plane_render_triangles(
            self.nodes, self.triangles, node=0, replacement=(0, 0, 1, 2))
        self.assertEqual(result["original_candidate_render_triangles"], 1)
        self.assertEqual(result["hypothetical_candidate_render_triangles"], 1)
        self.assertEqual(result["lost_triangle_locator_examples"], [[0, 0, 0]])
        self.assertEqual(result["gained_triangle_locator_examples"], [[0, 0, 1]])
        self.assertFalse(result["collision_rebuilt"])
        self.assertFalse(result["candidate_matching_is_engine_ownership"])
        self.assertEqual(self.nodes, original_nodes)
        self.assertEqual(self.triangles, original_triangles)

    def test_rejects_bad_edits(self):
        for replacement in ((0, 0, 1, 0), (0, 0, 2, 0),
                            (float("nan"), 0, 1, 0)):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                compare_plane_render_triangles(
                    self.nodes, self.triangles, node=0, replacement=replacement)
        with self.assertRaises(ValueError):
            compare_plane_render_triangles(
                self.nodes, self.triangles, node=True, replacement=(0, 0, 1, 2))
        with self.assertRaises(ValueError):
            compare_plane_render_triangles(
                self.nodes, [([0, 0, 0], ((0, 0, 0),))],
                node=0, replacement=(0, 0, 1, 2))


if __name__ == "__main__":
    unittest.main()
