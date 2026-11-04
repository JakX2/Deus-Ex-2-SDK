"""Asset-free tests for coplanar Level geometry and interval MOPP traversal."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_mopp_point_triangle_oracle as geometry
import inspect_mopp_axis_point_candidates as spatial
import inspect_mopp_segment_interval_candidates as interval


def triangle():
    return geometry.LevelPointTriangleOracle(
        [(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)],[(0,1,2,True)])


def walker(code, triangles=2, origin=(0.,0.,0.), scale=65536.):
    return spatial.ConservativeMoppPointCandidates(
        code, triangles, (*origin,scale))


class CoplanarGeometryTests(unittest.TestCase):
    def test_in_plane_segment_crosses_interior_without_endpoint_hits(self):
        o=triangle()
        start=(-.5,.25,0.); end=(1.,.25,0.)
        self.assertEqual(o.containing_triangle_ids(start),[])
        self.assertEqual(o.containing_triangle_ids(end),[])
        hits=interval.coplanar_segment_overlaps(o,start,end)
        self.assertEqual([h.original_triangle_id for h in hits],[0])
        self.assertAlmostEqual(hits[0].t_enter,1/3,places=5)
        self.assertAlmostEqual(hits[0].t_exit,5/6,places=5)

    def test_segment_fully_inside_triangle(self):
        hits=interval.coplanar_segment_overlaps(
            triangle(),(.1,.2,0.),(.2,.3,0.))
        self.assertEqual((hits[0].t_enter,hits[0].t_exit),(0.,1.))

    def test_reversed_segment_preserves_geometry(self):
        o=triangle()
        a=(-.5,.25,0.);b=(1.,.25,0.)
        forward=interval.coplanar_segment_overlaps(o,a,b)[0]
        backward=interval.coplanar_segment_overlaps(o,b,a)[0]
        self.assertAlmostEqual(forward.t_enter,1-backward.t_exit,places=5)
        self.assertAlmostEqual(forward.t_exit,1-backward.t_enter,places=5)

    def test_shared_edge_is_returned_for_two_original_source_ids(self):
        v=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(1.,1.,0.)]
        o=geometry.LevelPointTriangleOracle(v,[
            (0,1,2,True),(1,3,2,True)])
        hits=interval.coplanar_segment_overlaps(o,(.8,.2,0.),(.2,.8,0.))
        self.assertEqual([h.original_triangle_id for h in hits],[0,1])

    def test_duplicate_reversed_winding_keeps_both_faces(self):
        v=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),
           (0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        o=geometry.LevelPointTriangleOracle(v,[
            (0,1,2,True),(5,4,3,True)])
        hits=interval.coplanar_segment_overlaps(o,(-.5,.25,0.),(.75,.25,0.))
        self.assertEqual([h.original_triangle_id for h in hits],[0,1])

    def test_vertex_tangent_is_included(self):
        hits=interval.coplanar_segment_overlaps(
            triangle(),(-.5,-.5,0.),(0.,0.,0.))
        self.assertEqual(len(hits),1)
        self.assertGreater(hits[0].t_enter,.999)
        self.assertEqual(hits[0].t_exit,1.)

    def test_off_plane_parallel_has_no_overlap(self):
        self.assertEqual(interval.coplanar_segment_overlaps(
            triangle(),(-.5,.25,.2),(1.,.25,.2)),[])

    def test_transverse_hit_is_separate_from_coplanar_results(self):
        self.assertEqual(interval.coplanar_segment_overlaps(
            triangle(),(.2,.2,-1),(.2,.2,1)),[])

    def test_degenerate_nonleaf_source_gap_preserved(self):
        v=[(0.,0.,0.),(1.,0.,0.),(2.,0.,0.),(0.,1.,0.)]
        o=geometry.LevelPointTriangleOracle(v,[
            (0,1,2,False),(0,1,3,True)])
        hits=interval.coplanar_segment_overlaps(o,(-.5,.25,0.),(.8,.25,0.))
        self.assertEqual([h.original_triangle_id for h in hits],[1])

    def test_invalid_segment_parameters_refused(self):
        o=triangle()
        for a,b in [((0,0,0),(0,0,0)),
                    ((0,0,0),(float('nan'),0,0)),
                    ((0,0,0),(float('inf'),0,0))]:
            with self.subTest(a=a,b=b),self.assertRaises(ValueError):
                interval.coplanar_segment_overlaps(o,a,b)
        with self.assertRaises(ValueError):
            interval.coplanar_segment_overlaps(
                o,(0,0,0),(1,0,0),plane_tolerance=True)


class IntervalMoppCandidateTests(unittest.TestCase):
    def test_filter_crossed_between_endpoints_is_retained(self):
        # Z source filter 0 <= z < 32: neither endpoint is inside, segment is.
        w=walker(b'\x28\x00\x20\x30',1)
        self.assertEqual(w.point((.1,.1,-10.))['candidate_triangle_ids'],[])
        self.assertEqual(w.point((.1,.1,40.))['candidate_triangle_ids'],[])
        answer=interval.segment_candidate_triangle_ids(
            w,(.1,.1,-10.),(.1,.1,40.))
        self.assertEqual(answer['candidate_original_triangle_ids'],[0])
        self.assertFalse(answer['mopp_havok_runtime_segment_query'])

    def test_two_leaf_split_union_of_all_positions(self):
        w=walker(b'\x28\x00\xff\x20\x80\x01\x30\x31')
        answer=interval.segment_candidate_triangle_ids(
            w,(0.,0.,100.),(200.,0.,100.),tolerance_units=0)
        self.assertEqual(answer['candidate_original_triangle_ids'],[0,1])

    def test_local_segment_candidate_contains_sampled_point_sets(self):
        codes=[
            b'\x28\x00\xff\x20\x80\x01\x30\x31',
            b'\x28\x00\xff\x01\x01\x00\x00\x20\x80\x01\x30\x31',
            b'\x28\x00\xff\x13\x80\x7f\x01\x30\x31',
            b'\x28\x00\xff\x23\x80\x7f\x00\x00\x00\x01\x30\x31',
        ]
        a=(20.,30.,100.); b=(220.,30.,100.)
        for code in codes:
            w=walker(code)
            for mode in ('conservative','derived_diagonals'):
                with self.subTest(code=code.hex(),mode=mode):
                    segment=set(interval.segment_candidate_triangle_ids(
                        w,a,b,diagonal_mode=mode)['candidate_original_triangle_ids'])
                    for k in range(11):
                        p=tuple(x+(y-x)*k/10 for x,y in zip(a,b))
                        self.assertLessEqual(
                            set(w.point(p,diagonal_mode=mode)['candidate_triangle_ids']),
                            segment)

    def test_root_with_rescale_reaches_later_branch(self):
        w=walker(b'\x28\x00\xff\x01\x01\x00\x00\x20\x80\x01\x30\x31')
        answer=interval.segment_candidate_triangle_ids(
            w,(30.,0.,100.),(100.,0.,100.))
        self.assertEqual(answer['candidate_original_triangle_ids'],[0,1])

    def test_unobserved_diagonal_both_branch_fallback(self):
        w=walker(b'\x28\x00\xff\x1b\x80\x7f\x01\x30\x31')
        answer=interval.segment_candidate_triangle_ids(
            w,(10,10,100),(230,230,100),diagonal_mode='derived_diagonals')
        self.assertEqual(answer['candidate_original_triangle_ids'],[0,1])
        self.assertGreaterEqual(answer['unknown_diagonal_branches_explored_both'],1)

    def test_experimental_diagonal_segment_projection(self):
        w=walker(b'\x28\x00\xff\x14\x80\x7f\x01\x30\x31')
        answer=interval.segment_candidate_triangle_ids(
            w,(10,10,100),(10,240,100),diagonal_mode='derived_diagonals')
        self.assertEqual(answer['candidate_original_triangle_ids'],[0,1])
        self.assertEqual(answer['experimental_diagonal_projections_used'],1)

    def test_coplanar_overlap_is_reported_in_geometry_comparison(self):
        o=triangle()
        w=walker(b'\x28\x00\xff\x30',1)
        result=interval.verify_segment_against_geometry(
            o,w,(-.5,.25,0.),(1.,.25,0.))
        self.assertEqual(result['transverse_crossing_events'],0)
        self.assertEqual(result['coplanar_overlap_events'],1)
        self.assertEqual(result['geometric_triangle_ids_intersecting_segment'],[0])
        self.assertTrue(result['all_classified_geometric_hits_retained'])
        self.assertFalse(result['runtime_havok_segment_query'])

    def test_structural_only_synthetic_tree_omits_coplanar_face(self):
        v=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),
           (0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        o=geometry.LevelPointTriangleOracle(v,[
            (0,1,2,True),(3,4,5,True)])
        w=walker(b'\x28\x00\xff\x20\x80\x01\x30\x31')
        result=interval.verify_segment_against_geometry(
            o,w,(-.5,.25,0.),(.75,.25,0.))
        self.assertEqual(result['coplanar_overlap_events'],2)
        self.assertEqual(result['missing_geometric_original_triangle_ids'],[1])

    def test_source_input_arrays_are_unchanged(self):
        v=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        before=copy.deepcopy(v)
        o=geometry.LevelPointTriangleOracle(v,[(0,1,2,True)])
        interval.coplanar_segment_overlaps(o,(-1,.25,0),(1,.25,0))
        self.assertEqual(v,before)

    def test_reject_invalid_modes_zero_length_and_tolerance(self):
        w=walker(b'\x28\x00\xff\x30',1)
        for kwargs in ({'diagonal_mode':'runtime'}, {'diagonal_mode':[]},
                       {'tolerance_units':float('nan')},
                       {'tolerance_units':5},
                       {'tolerance_units':True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                interval.segment_candidate_triangle_ids(
                    w,(0,0,10),(1,0,10),**kwargs)
        with self.assertRaises(ValueError):
            interval.segment_candidate_triangle_ids(w,(0,0,10),(0,0,10))


if __name__ == '__main__':
    unittest.main()
