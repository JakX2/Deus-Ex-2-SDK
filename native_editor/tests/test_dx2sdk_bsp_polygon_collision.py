"""Synthetic regression gates for ambiguous BSP covers and collision provenance."""
import math
import unittest
from unittest.mock import patch

from test_dx2_bsp_polygon_candidates import A,B,C,D,SQUARE,PLANE,SPHERE,node,labelled
from inspect_bsp_polygon_candidates import (
    analyze_polygons, recover_ambiguous_polygons, join_polygon_collision, RADIUS_FACTOR,
)
from dx2sdk.bsp_mopp_plane_impact import _source_triangle_rows
from test_dx2_level_mopp_triangle_provenance import fixture
from test_dx2sdk_bsp_mopp_plane_impact import triangles


class PolygonCollisionTests(unittest.TestCase):
    def test_identical_nodes_remain_ambiguous(self):
        result=analyze_polygons([node(),node()],labelled(SQUARE),
                                include_polygons=True,recover_ambiguous=True)
        self.assertEqual(result["counts"]["ambiguity_multiple_cover_components"],1)
        self.assertEqual(result["preview_polygons"],[])

    def test_unique_cover_recovered_without_ownership_claim(self):
        # Two coplanar nodes: the square has two triangles, the competing
        # triangle node cannot satisfy its source bounding center/radius.
        bad=node(3,(1.5,.5,0.,1.6))
        result=analyze_polygons([node(),bad],labelled(SQUARE),
                                include_polygons=True,recover_ambiguous=True)
        self.assertEqual(result["counts"]["ambiguity_unique_cover_components"],1)
        self.assertEqual(result["counts"]["ambiguity_recovered_preview_polygons"],1)
        row=result["preview_polygons"][0]
        self.assertEqual(row["source_node"],0)
        self.assertEqual(row["assignment_method"],"unique_complete_cover_hypothesis")
        self.assertFalse(row["native_write_allowed"])
        self.assertFalse(row["engine_ownership_verified"])

    def test_unique_cover_of_two_polygons(self):
        e=(4.,0.,0.)
        f=(4.,2.,0.)
        tris=SQUARE+[(B,e,f),(B,f,C)]
        by={tuple(k):t for k,t in labelled(tris)}
        nodes=[node(),node(4,(3.,1.,0.,SPHERE[3]))]
        matches=[{"triangle":k,"candidate_nodes":[0,1]} for k in by]
        counts, rows=recover_ambiguous_polygons(nodes,by,matches)
        self.assertEqual(counts["ambiguity_unique_cover_components"],1)
        self.assertEqual(counts["ambiguity_assigned_triangles"],4)
        self.assertEqual(len(rows),2)

    def test_impossible_cover_and_caps(self):
        bad=node(5)
        by={tuple(k):t for k,t in labelled(SQUARE)}
        matches=[{"triangle":k,"candidate_nodes":[0,1]} for k in by]
        counts,rows=recover_ambiguous_polygons([bad,bad],by,matches)
        self.assertEqual(counts["ambiguity_no_cover_components"],1)
        self.assertEqual(rows,[])
        with patch("inspect_bsp_polygon_candidates.MAX_COVER_STEPS",1):
            counts,rows=recover_ambiguous_polygons([node(),node()],by,matches)
        self.assertEqual(counts["ambiguity_capped_components"],1)
        self.assertEqual(rows,[])
        with patch("inspect_bsp_polygon_candidates.MAX_SUBSET_TRIALS",0):
            counts,rows=recover_ambiguous_polygons([node(),node()],by,matches)
        self.assertEqual(counts["ambiguity_capped_components"],1)
        self.assertEqual(rows,[])

    def test_source_fixture_join_and_no_private_details_by_default(self):
        level,blocks,_=fixture(separate_blocks=True)
        rows,_=_source_triangle_rows(level,blocks)
        locs=[k for k,_ in triangles(blocks)]
        poly={"source_node":0,"original_render_triangle_locators":locs,
              "raw_candidate_surface_value":0,
              "assignment_method":"unique_complete_cover_hypothesis"}
        report=join_polygon_collision([poly],rows,locs)
        self.assertEqual(report["counts"]["collision_crosswalk_mopp_leaves"],2)
        self.assertEqual(report["counts"]["collision_crosswalk_all_leaf_polygons"],1)
        self.assertNotIn("polygon_collision_crosswalk",report)
        self.assertEqual(report["counts"]["collision_recovered_leaf_triangles"],2)
        self.assertEqual(report["counts"]["surface_compared_groups"],1)
        self.assertEqual(report["counts"]["surface_equals_all_provenance_A_polygons"],0)
        self.assertEqual(report["counts"]["surface_polygon_multiple_render_sections"],1)
        details=join_polygon_collision([poly],rows,locs,include_details=True)
        self.assertEqual([r["source_provenance_block_field_a"] for r in
                          details["polygon_collision_crosswalk"][0]["original_triangle_rows"]],[0,2])
        self.assertFalse(details["polygon_collision_crosswalk"][0]["native_write_allowed"])

    def test_partial_none_and_unassigned_leaf_accounting(self):
        locs=[(0,0,i) for i in range(4)]
        rows=[{"render_locator":k,"flattened_triangle_id":i,
               "original_mopp_terminal_leaf_present":i in (0,3)}
              for i,k in enumerate(locs)]
        polys=[{"source_node":0,"original_render_triangle_locators":locs[:2]},
               {"source_node":1,"original_render_triangle_locators":locs[2:3]}]
        counts=join_polygon_collision(polys,rows,locs)["counts"]
        self.assertEqual(counts["collision_crosswalk_partial_leaf_polygons"],1)
        self.assertEqual(counts["collision_crosswalk_none_leaf_polygons"],1)
        self.assertEqual(counts["collision_unassigned_mopp_leaves"],1)
        with self.assertRaises(ValueError):
            join_polygon_collision(polys+[polys[0]],rows,locs)
        with self.assertRaises(ValueError):
            join_polygon_collision(polys,rows,list(reversed(locs)))


if __name__=="__main__":
    unittest.main()
