"""Asset-free independent finite-segment geometric intersection regression tests."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_mopp_segment_geometry_oracle as segment
import inspect_mopp_point_triangle_oracle as geom
import inspect_mopp_axis_point_candidates as spatial


def layered():
    vertices = [(0,0,0),(1,0,0),(0,1,0),
                (0,0,2),(1,0,2),(0,1,2)]
    return geom.LevelPointTriangleOracle(
        vertices,[(0,1,2,True),(3,4,5,True)])


class SegmentGeometryTests(unittest.TestCase):
    def test_two_transverse_surfaces_are_reported_in_distance_order(self):
        result = segment.segment_crossings(
            layered(),(.2,.2,-1),(.2,.2,3))
        self.assertEqual([h.original_triangle_id for h in result["hits"]],[0,1])
        self.assertAlmostEqual(result["hits"][0].t,.25)
        self.assertAlmostEqual(result["hits"][1].t,.75)
        self.assertAlmostEqual(sum(result["hits"][0].barycentric),1.)
        self.assertFalse(result["runtime_havok_collision_verified"])

    def test_reversed_segment_reverses_hit_order(self):
        result = segment.segment_crossings(
            layered(),(.2,.2,3),(.2,.2,-1))
        self.assertEqual([h.original_triangle_id for h in result["hits"]],[1,0])
        self.assertEqual([round(h.t,2) for h in result["hits"]],[.25,.75])

    def test_overlapping_reversed_winding_keeps_both_source_ids(self):
        v = [(0,0,0),(1,0,0),(0,1,0),
             (0,0,0),(1,0,0),(0,1,0)]
        oracle = geom.LevelPointTriangleOracle(v,[(0,1,2,True),(5,4,3,True)])
        result = segment.segment_crossings(
            oracle,(.2,.2,-1),(.2,.2,1))
        self.assertEqual([h.original_triangle_id for h in result["hits"]],[0,1])
        self.assertAlmostEqual(result["hits"][0].t,.5)
        self.assertAlmostEqual(result["hits"][1].t,.5)

    def test_actual_bad_synthetic_mopp_prunes_valid_intersection(self):
        v = [(0,0,0),(1,0,0),(0,1,0),
             (0,0,0),(1,0,0),(0,1,0)]
        oracle = geom.LevelPointTriangleOracle(
            v,[(0,1,2,True),(3,4,5,True)])
        code = b"\x28\x00\xff\x20\x80\x01\x30\x31"
        walker = spatial.ConservativeMoppPointCandidates(
            code,2,(0.,0.,-10.,65536.))
        result = segment.compare_segment_crossings(
            oracle,walker,(.2,.2,-1),(.2,.2,1))
        self.assertEqual(result["transverse_crossings"],2)
        self.assertEqual(result["missing_geometric_ids"],[1])
        self.assertFalse(result["all_transverse_geometric_hits_retained"])
        self.assertFalse(result["mopp_full_segment_traversal_performed"])

    def test_nonpruning_diagonal_keeps_overlapping_source_faces(self):
        v = [(0,0,0),(1,0,0),(0,1,0),
             (0,0,0),(1,0,0),(0,1,0)]
        oracle = geom.LevelPointTriangleOracle(v,[
            (0,1,2,True),(5,4,3,True)])
        code = b"\x28\x00\xff\x13\x01\xfe\x01\x30\x31"
        walker = spatial.ConservativeMoppPointCandidates(
            code,2,(0.,0.,-10.,65536.))
        result = segment.compare_segment_crossings(
            oracle,walker,(.2,.2,-1),(.2,.2,1))
        self.assertTrue(result["all_transverse_geometric_hits_retained"])
        self.assertEqual(result["intersection_point_mopp_comparisons"],2)

    def test_endpoints_alone_do_not_discover_middle_intersections(self):
        oracle = layered()
        start,end = (.2,.2,-1),(.2,.2,3)
        self.assertEqual(oracle.containing_triangle_ids(start),[])
        self.assertEqual(oracle.containing_triangle_ids(end),[])
        self.assertEqual(len(segment.segment_crossings(
            oracle,start,end)["hits"]),2)

    def test_coplanar_overlap_is_explicitly_unresolved(self):
        result = segment.segment_crossings(
            layered(),(-.1,.1,0),(.8,.1,0))
        self.assertEqual(result["hits"],[])
        self.assertEqual(result["parallel_or_coplanar_triangle_ids"],[0])
        self.assertFalse(result["coplanar_overlap_fully_supported"])

    def test_parallel_off_plane_segment_not_a_false_hit(self):
        result = segment.segment_crossings(
            layered(),(-.1,.1,1),(.8,.1,1))
        self.assertEqual(result["hits"],[])

    def test_segment_starting_on_triangle_has_zero_t_intersection(self):
        result = segment.segment_crossings(
            layered(),(.2,.2,0),(.2,.2,-1))
        self.assertEqual([h.original_triangle_id for h in result["hits"]],[0])
        self.assertEqual(result["hits"][0].t,0)

    def test_shared_edge_produces_two_original_triangle_ids(self):
        v = [(0,0,0),(1,0,0),(0,1,0),(1,1,0)]
        oracle = geom.LevelPointTriangleOracle(
            v,[(0,1,2,True),(1,3,2,True)])
        result = segment.segment_crossings(
            oracle,(.5,.5,-1),(.5,.5,1))
        self.assertEqual([h.original_triangle_id for h in result["hits"]],[0,1])

    def test_disjoint_segment_has_no_crossings(self):
        result = segment.segment_crossings(
            layered(),(100,100,-1),(100,100,3))
        self.assertEqual(result["hits"],[])

    def test_omitted_degenerate_nonleaf_preserves_source_ids(self):
        vertices = [(0,0,0),(1,0,0),(2,0,0),(0,1,0)]
        oracle = geom.LevelPointTriangleOracle(
            vertices,[(0,1,2,False),(0,1,3,True)])
        result = segment.segment_crossings(
            oracle,(.2,.2,-1),(.2,.2,1))
        self.assertEqual([h.original_triangle_id for h in result["hits"]],[1])

    def test_nonfinite_zero_length_and_invalid_tolerances_refused(self):
        oracle = layered()
        for a,b in [((0,0,0),(0,0,0)),
                    ((float("nan"),0,0),(0,0,1)),
                    ((0,0,0),(float("inf"),0,1))]:
            with self.subTest(a=a,b=b),self.assertRaises(ValueError):
                segment.segment_crossings(oracle,a,b)
        for kw in [{"plane_tolerance":-1},
                   {"barycentric_tolerance":True},
                   {"plane_tolerance":float("nan")}]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                segment.segment_crossings(oracle,(.2,.2,-1),(.2,.2,1),**kw)

    def test_determinism_and_source_geometry_nonmutation(self):
        v = [(0,0,0),(1,0,0),(0,1,0),
             (0,0,2),(1,0,2),(0,1,2)]
        before = copy.deepcopy(v)
        oracle = geom.LevelPointTriangleOracle(
            v,[(0,1,2,True),(3,4,5,True)])
        a = segment.segment_crossings(
            oracle,(.2,.2,-1),(.2,.2,3))
        b = segment.segment_crossings(
            oracle,(.2,.2,-1),(.2,.2,3))
        self.assertEqual(a,b)
        self.assertEqual(v,before)


if __name__ == "__main__":
    unittest.main()
