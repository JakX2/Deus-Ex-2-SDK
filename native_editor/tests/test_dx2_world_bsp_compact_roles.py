"""Asset-free diagnostic tests; no proprietary maps or field names assumed."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_world_bsp_compact_roles as roles
from test_dx2_world_bsp_zone_relations import synthetic_world


def row(start, surface, *, vcount=4, coplanar=-1, collision=-1, render=-1):
    return {"fields": [0, start, surface, -1, -1, coplanar, collision, render],
            "vertex_count": vcount}


class CompactRoleHypothesisTests(unittest.TestCase):
    def test_dense_candidate_vertex_intervals_and_same_coplanar_surface(self):
        records = [row(0, 9, coplanar=1), row(4, 9), row(8, 10, render=45)]
        report = roles.analyze_rows(records, include_nodes=True)
        self.assertEqual(report["candidate_slot_count"], 12)
        self.assertTrue(report["candidate_vertex_spans"]["dense_zero_based_no_overlaps"])
        self.assertEqual(report["candidate_vertex_spans"]["adjacent_exact_contiguous"], 2)
        self.assertEqual(report["candidate_vertex_spans"]["overlap_slot_count"], 0)
        self.assertEqual(report["coplanar_candidate_surface"]["same_field2"], 1)
        self.assertEqual(report["fields"]["7"]["at_least_node_count"], 1)
        self.assertEqual(len(report["node_compact_rows"]), 3)

    def test_overlap_and_gaps_are_reported_not_hidden(self):
        report = roles.analyze_rows([row(0, 3), row(2, 3), row(12, 8)])
        ranges = report["candidate_vertex_spans"]
        self.assertEqual(ranges["union_slots"], 10)
        self.assertEqual(ranges["overlap_slot_count"], 2)
        self.assertEqual(ranges["adjacent_exact_contiguous"], 0)
        self.assertFalse(ranges["dense_zero_based_no_overlaps"])
        self.assertEqual(len(report["exception_examples"]["noncontiguous_candidate_vertex_starts"]), 2)

    def test_same_plane_does_not_force_same_surface(self):
        report = roles.analyze_rows([row(0, 4, coplanar=1), row(4, 5)])
        self.assertEqual(report["coplanar_candidate_surface"]["different_field2"], 1)
        self.assertEqual(len(report["exception_examples"]["coplanar_differing_candidate_surfaces"]), 1)

    def test_collision_and_render_values_are_not_node_refs(self):
        report = roles.analyze_rows([row(0, 1, collision=5000, render=9000),
                                     row(4, 2, collision=-1, render=-1)])
        self.assertEqual(report["fields"]["6"]["at_least_node_count"], 1)
        self.assertEqual(report["fields"]["7"]["max"], 9000)
        self.assertEqual(report["fields"]["6"]["negative_one_count"], 1)

    def test_negative_vertex_start_not_mistaken_for_proof(self):
        report = roles.analyze_rows([row(-1, 0), row(1, 0)])
        self.assertEqual(report["candidate_vertex_spans"]["negative_starts"], 1)
        self.assertFalse(report["candidate_vertex_spans"]["dense_zero_based_no_overlaps"])

    def test_rejects_invalid_inputs_without_silent_coercion(self):
        for invalid in ([], [row(0, 0, vcount=2)],
                        [{"fields":[0,1,2],"vertex_count":4}],
                        [row(0, 0, coplanar=0)],
                        [row(0, 0, coplanar=3)]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                roles.analyze_rows(invalid)

    def test_integration_reuses_existing_tree_and_zone_validators(self):
        payload,frame = synthetic_world()
        report = roles.inspect_model(payload,frame,include_nodes=True)
        self.assertTrue(report["rooted_node_graph_and_zone_masks_prevalidated"])
        self.assertEqual(report["nodes"],3)
        self.assertEqual(report["candidate_slot_count"],12)
        self.assertEqual(report["coplanar_candidate_surface"]["field5_links"],0)
        self.assertEqual(len(report["node_compact_rows"]),3)
        wrong=bytearray(payload)
        wrong[frame["node_records"][0]["start"]+16]=0
        with self.assertRaises(ValueError):
            roles.inspect_model(bytes(wrong),frame)


if __name__ == "__main__":
    unittest.main()
