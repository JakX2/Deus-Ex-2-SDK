"""Pure, fixture-only tests for checking original BSP against cached reports."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "map_exporter"))
from dx2_bsp_source_audit import box_distance_ue, compare_bsp_data


def block(offset, name, verts, num_tris):
    return {
        "offset": offset, "id": offset // 10,
        "vertices": [(point, (0, 0, 1), (0, 0)) for point in verts],
        "sections": [{"material": name, "indices": list(range(num_tris * 3))}],
    }


class SourceBspAuditTests(unittest.TestCase):
    def test_source_parity_and_nearby_render_blocks(self):
        b = [
            block(100, "M1WTO_intwall1", [(0, -480, 240), (600, 160, 400)], 7),
            block(200, "BF", [(3952, 1680, -160), (4784, 2512, 400)], 12),
        ]
        report = {"source_map_sha256": "testhash", "visible_bsp_triangles": 7}
        r = compare_bsp_data(b, 2, "WTO.gmp", "testhash", report, (0, -272, 396))
        self.assertTrue(r["report_source_hash_matches"])
        self.assertTrue(r["visible_triangles_match_matching_cache_report"])
        self.assertEqual(r["bf_only_hidden_blocks"], 1)
        self.assertEqual(r["bf_hidden_triangles"], 12)
        self.assertEqual(r["render_block_section_count"], 2)
        self.assertEqual(len(r["nearest_source_render_blocks"]), 1)
        self.assertEqual(r["nearest_source_render_blocks"][0]["target_to_vertex_aabb_ue"], 0)

    def test_mismatched_map_hash_cannot_claim_parity(self):
        r = compare_bsp_data(
            [block(100, "wall", [(0, 0, 0), (10, 10, 10)], 1)],
            1, "WTO.gmp", "actual",
            {"source_map_sha256": "wrong", "visible_bsp_triangles": 1})
        self.assertFalse(r["visible_triangles_match_matching_cache_report"])

    def test_reject_nonfinite_target(self):
        with self.assertRaises(ValueError):
            compare_bsp_data([],0,"a.gmp","x",{},(0,float("nan"),0))

    def test_distance_outside_and_inside_bounds(self):
        self.assertAlmostEqual(box_distance_ue((0, 0, 0), (2, 2, 2), (4, 2, 2)), 2)
        self.assertEqual(box_distance_ue((0, 0, 0), (2, 2, 2), (1, 1, 1)),0)


if __name__ == "__main__":
    unittest.main()
