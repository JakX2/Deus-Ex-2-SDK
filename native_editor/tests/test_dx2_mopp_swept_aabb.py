"""Asset-free continuous Level moving-AABB SAT and source-MOPP tests."""
from __future__ import annotations
import random
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research'/'dx2'))
import inspect_mopp_swept_aabb as swept
import inspect_mopp_point_triangle_oracle as geometry
import inspect_mopp_axis_point_candidates as mopp


def level():
    return geometry.LevelPointTriangleOracle(
        [(0.,0.,0.),(2.,0.,0.),(0.,2.,0.)],[(0,1,2,True)])


def layers():
    return geometry.LevelPointTriangleOracle(
        [(0.,0.,0.),(2.,0.,0.),(0.,2.,0.),
         (0.,0.,2.),(2.,0.,2.),(0.,2.,2.)],
        [(0,1,2,True),(3,4,5,True)])


def walker(code, count=1):
    return mopp.ConservativeMoppPointCandidates(
        code,count,(0.,0.,0.,65536.))


class SweptAABBGeometryTests(unittest.TestCase):
    def test_known_vertical_crossing_interval(self):
        r=swept.swept_aabb_triangle_hits(
            level(),(.5,.5,-2.),(.5,.5,2.),(.2,.2,.25),tolerance=0.)
        self.assertEqual(r['original_triangle_hit_ids'],[0])
        self.assertAlmostEqual(r['hits'][0].t_enter,.4375)
        self.assertAlmostEqual(r['hits'][0].t_exit,.5625)
        self.assertFalse(r['runtime_havok_contact_verified'])

    def test_short_box_near_miss_separate_from_hit(self):
        truth=level()
        miss=swept.swept_aabb_triangle_hits(
            truth,(3,3,-1),(3,3,1),(.1,.1,.2))
        hit=swept.swept_aabb_triangle_hits(
            truth,(1.9,.1,-1),(1.9,.1,1),(.15,.15,.2))
        self.assertEqual(miss['original_triangle_hit_ids'],[])
        self.assertEqual(hit['original_triangle_hit_ids'],[0])

    def test_zero_extents_reduces_to_transverse_segment(self):
        r=swept.swept_aabb_triangle_hits(
            level(),(.5,.5,-1),(.5,.5,1),(0,0,0),tolerance=0)
        self.assertAlmostEqual(r['hits'][0].t_enter,.5)
        self.assertAlmostEqual(r['hits'][0].t_exit,.5)

    def test_multiplane_contacts_are_ordered(self):
        r=swept.swept_aabb_triangle_hits(
            layers(),(.5,.5,-1),(.5,.5,3),(.1,.1,.2),tolerance=0)
        self.assertEqual(r['original_triangle_hit_ids'],[0,1])
        self.assertEqual([x.original_triangle_id for x in r['hits']],[0,1])
        self.assertAlmostEqual(r['hits'][0].t_enter,.2)
        self.assertAlmostEqual(r['hits'][1].t_enter,.7)

    def test_coplanar_box_motion_still_intersects_triangle(self):
        r=swept.swept_aabb_triangle_hits(
            level(),(-1.,.4,0.),(1.,.4,0.),(.1,.1,.2),tolerance=0)
        self.assertEqual(r['original_triangle_hit_ids'],[0])
        self.assertGreater(r['hits'][0].t_exit,r['hits'][0].t_enter)

    def test_initial_overlap_time_is_zero(self):
        r=swept.swept_aabb_triangle_hits(
            level(),(.3,.3,0.),(.3,.3,1.),(.2,.2,.25),tolerance=0)
        self.assertEqual(r['hits'][0].t_enter,0.)
        self.assertTrue(r['hits'][0].initial_overlap)

    def test_overlap_of_reversed_winding_faces_keeps_original_ids(self):
        v=[(0,0,0),(2,0,0),(0,2,0),(0,0,0),(2,0,0),(0,2,0)]
        oracle=geometry.LevelPointTriangleOracle(
            v,[(0,1,2,True),(5,4,3,True)])
        r=swept.swept_aabb_triangle_hits(
            oracle,(.2,.2,-1),(.2,.2,1),(.1,.1,.15))
        self.assertEqual(r['original_triangle_hit_ids'],[0,1])

    def test_zero_area_nonleaf_original_id_gap(self):
        oracle=geometry.LevelPointTriangleOracle(
            [(0,0,0),(1,0,0),(2,0,0),(0,1,0)],
            [(0,1,2,False),(0,1,3,True)])
        r=swept.swept_aabb_triangle_hits(
            oracle,(.2,.2,-1),(.2,.2,1),(.1,.1,.1))
        self.assertEqual(r['original_triangle_hit_ids'],[1])

    def test_stationary_aabb_intersects_source_triangle(self):
        r=swept.swept_aabb_triangle_hits(
            level(),(.25,.25,.05),(.25,.25,.05),(.1,.1,.1))
        self.assertEqual(r['original_triangle_hit_ids'],[0])
        self.assertEqual((r['hits'][0].t_enter,r['hits'][0].t_exit),(0.,1.))

    def test_axis_separation_despite_overlapping_all_xyz_bbox(self):
        r=swept.swept_aabb_triangle_hits(
            level(),(1.7,1.7,-1),(1.7,1.7,1),(.1,.1,.1),tolerance=0)
        self.assertEqual(r['original_triangle_hit_ids'],[])

    def test_reject_invalid_extents_nan_inf_boolean_and_overflow(self):
        for extents in [(-1,0,0),(float('inf'),0,0),
                        (float('nan'),0,0),(True,0,0),(1001,0,0)]:
            with self.subTest(extents=extents),self.assertRaises(ValueError):
                swept.swept_aabb_triangle_hits(
                    level(),(0,0,-1),(0,0,1),extents)
        with self.assertRaises(ValueError):
            swept.swept_aabb_triangle_hits(
                level(),(0,0,-1),(0,0,1),(0,0,0),tolerance=True)


class SweptMoppCandidateTests(unittest.TestCase):
    def test_box_extent_reaches_filter_not_reached_by_center_segment(self):
        w=walker(b'\x28\x00\xff\x30')
        self.assertEqual(w.point((.1,.1,260.))['candidate_triangle_ids'],[])
        r=swept.swept_aabb_mopp_candidates(
            w,(.1,.1,260),(.2,.1,260),(0,0,10))
        self.assertEqual(r['candidate_original_triangle_ids'],[0])

    def test_box_extent_crosses_split_not_reached_by_center(self):
        w=walker(b'\x28\x00\xff\x20\x80\x01\x30\x31',2)
        r=swept.swept_aabb_mopp_candidates(
            w,(110,0,50),(111,0,50),(30,0,0))
        self.assertEqual(r['candidate_original_triangle_ids'],[0,1])

    def test_zero_extents_match_previous_interval_walker(self):
        import inspect_mopp_segment_interval_candidates as previous
        codes=[b'\x28\x00\xff\x20\x80\x01\x30\x31',
               b'\x28\x00\xff\x13\x80\x7f\x01\x30\x31',
               b'\x28\x00\xff\x01\x01\x00\x00\x20\x80\x01\x30\x31',
               b'\x28\x00\xff\x23\x80\x7f\x00\x00\x00\x01\x30\x31']
        for code in codes:
            for mode in mopp.DIAGONAL_MODES:
                with self.subTest(code=code.hex(),mode=mode):
                    w=walker(code,2)
                    new=swept.swept_aabb_mopp_candidates(
                        w,(20,20,50),(220,20,50),(0,0,0),diagonal_mode=mode)
                    old=previous.segment_candidate_triangle_ids(
                        w,(20,20,50),(220,20,50),diagonal_mode=mode)
                    self.assertEqual(new['candidate_original_triangle_ids'],
                                     old['candidate_original_triangle_ids'])

    def test_expanded_candidate_contains_90_synthetic_mopp_point_queries(self):
        codes=[b'\x28\x00\xff\x20\x80\x01\x30\x31',
               b'\x28\x00\xff\x14\x80\x7f\x01\x30\x31',
               b'\x28\x00\xff\x01\x01\x00\x00\x20\x80\x01\x30\x31']
        a=(30.,40.,50.);b=(220.,140.,150.);h=(18.,20.,15.)
        rng=random.Random(42)
        for code in codes:
            w=walker(code,2)
            for mode in mopp.DIAGONAL_MODES:
                candidates=set(swept.swept_aabb_mopp_candidates(
                    w,a,b,h,diagonal_mode=mode)['candidate_original_triangle_ids'])
                for _ in range(90):
                    t=rng.random()
                    p=tuple(a[k]*(1-t)+b[k]*t+rng.uniform(-h[k],h[k])
                            for k in range(3))
                    self.assertLessEqual(set(w.point(
                        p,diagonal_mode=mode)['candidate_triangle_ids']),
                        candidates)

    def test_unobserved_0x1b_diagonal_is_always_both_branches(self):
        w=walker(b'\x28\x00\xff\x1b\x80\x7f\x01\x30\x31',2)
        r=swept.swept_aabb_mopp_candidates(
            w,(10,10,50),(20,20,50),(.1,.1,.1),
            diagonal_mode='derived_diagonals')
        self.assertEqual(r['candidate_original_triangle_ids'],[0,1])
        self.assertGreater(r['unknown_diagonals_explored_both'],0)

    def test_actual_geometry_dropped_by_bad_synthetic_split(self):
        v=[(0,0,0),(2,0,0),(0,2,0),(0,0,0),(2,0,0),(0,2,0)]
        o=geometry.LevelPointTriangleOracle(
            v,[(0,1,2,True),(3,4,5,True)])
        w=walker(b'\x28\x00\xff\x20\x80\x01\x30\x31',2)
        r=swept.compare_swept_aabb(
            o,w,(.2,.2,-1),(.2,.2,1),(.1,.1,.1))
        self.assertEqual(r['swept_geometric_original_triangle_ids'],[0,1])
        self.assertEqual(r['missed_geometrically_intersected_original_ids'],[1])
        self.assertFalse(r['all_geometric_swept_AABB_hits_retained'])

    def test_synthetic_positive_box_around_original_source_triangle(self):
        r=swept.compare_swept_aabb(
            level(),walker(b'\x28\x00\xff\x30'),
            (.3,.3,-1),(.3,.3,1),(.1,.1,.1))
        self.assertEqual(r['swept_geometric_original_triangle_ids'],[0])
        self.assertTrue(r['all_geometric_swept_AABB_hits_retained'])
        self.assertFalse(r['runtime_havok_verified'])

    def test_invalid_mopp_mode_and_half_extents_fail_closed(self):
        w=walker(b'\x28\x00\xff\x30')
        with self.assertRaises(ValueError):
            swept.swept_aabb_mopp_candidates(
                w,(0,0,1),(0,0,2),(1,2,3),diagonal_mode='havok')
        with self.assertRaises(ValueError):
            swept.swept_aabb_mopp_candidates(
                w,(0,0,1),(0,0,2),(-1,2,3))
        with self.assertRaises(ValueError):
            swept.swept_aabb_mopp_candidates(
                w,(0,0,1),(0,0,2),(0,0,0),
                tolerance_units=float('nan'))


if __name__=='__main__':
    unittest.main()
