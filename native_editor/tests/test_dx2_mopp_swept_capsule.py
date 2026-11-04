"""Asset-free swept capsule geometry, MOPP enclosure and failure controls."""
from __future__ import annotations
import math
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"dx2"))
import inspect_mopp_swept_capsule as cap
import inspect_mopp_point_triangle_oracle as geo
import inspect_mopp_axis_point_candidates as mopp
import inspect_mopp_swept_aabb as aabb


def flat():
    return geo.LevelPointTriangleOracle(
        [(0.,0.,0.),(2.,0.,0.),(0.,2.,0.)],[(0,1,2,True)])
def walker(code=b"\x28\x00\xff\x30",triangles=1):
    return mopp.ConservativeMoppPointCandidates(code,triangles,(0.,0.,0.,65536.))


class CapsuleGeometryTests(unittest.TestCase):
    def test_sphere_crosses_triangle(self):
        r=cap.swept_capsule_triangle_hits(flat(),(.5,.5,-1),(.5,.5,1),.15,axis_half_length=0.)
        self.assertEqual(r["original_triangle_hit_ids"],[0])
        self.assertFalse(r["time_of_impact_solved"])

    def test_small_sphere_near_miss(self):
        r=cap.swept_capsule_triangle_hits(flat(),(3,3,-1),(3,3,1),.1,axis_half_length=0.)
        self.assertEqual(r["original_triangle_hit_ids"],[])

    def test_fixed_axis_capsule_hits_without_center_path_contact(self):
        r=cap.swept_capsule_triangle_hits(flat(),(.5,.5,1),(.5,.5,2),.1,axis_half_length=1.2)
        self.assertEqual(r["original_triangle_hit_ids"],[0])

    def test_capsule_far_above_plane_misses(self):
        r=cap.swept_capsule_triangle_hits(flat(),(.5,.5,3),(.5,.5,4),.2,axis_half_length=.5)
        self.assertEqual(r["original_triangle_hit_ids"],[])

    def test_stationary_capsule_contact(self):
        r=cap.swept_capsule_triangle_hits(flat(),(.5,.5,.25),(.5,.5,.25),.3,axis_half_length=0.)
        self.assertEqual(r["original_triangle_hit_ids"],[0])
        self.assertTrue(r["swept_axis_patch_collapsed_to_segment"])

    def test_stationary_capsule_no_contact(self):
        r=cap.swept_capsule_triangle_hits(flat(),(.5,.5,2),(.5,.5,2),.2,axis_half_length=.5)
        self.assertEqual(r["original_triangle_hit_ids"],[])

    def test_crossed_axis_surface_patch_intersects(self):
        r=cap.swept_capsule_triangle_hits(flat(),(-1,.5,.25),(2,.5,.25),.3,
                                          axis=(0,1,0),axis_half_length=.25)
        self.assertEqual(r["original_triangle_hit_ids"],[0])
        self.assertFalse(r["swept_axis_patch_collapsed_to_segment"])

    def test_zero_radius_surface_patch_is_geometric_not_capsule_sphere(self):
        r=cap.swept_capsule_triangle_hits(flat(),(-1,.5,0),(2,.5,0),0,
                                          axis=(0,1,0),axis_half_length=.25,tolerance=0.)
        self.assertEqual(r["original_triangle_hit_ids"],[0])

    def test_collapsed_axis_parallel_to_path(self):
        r=cap.swept_capsule_triangle_hits(flat(),(.5,.5,-1),(.5,.5,1),.1,
                                          axis=(0,0,1),axis_half_length=.5)
        self.assertEqual(r["original_triangle_hit_ids"],[0])
        self.assertTrue(r["swept_axis_patch_collapsed_to_segment"])

    def test_multisurface_capsule_contacts(self):
        v=[(0,0,0),(2,0,0),(0,2,0),(0,0,2),(2,0,2),(0,2,2)]
        o=geo.LevelPointTriangleOracle(v,[(0,1,2,True),(3,4,5,True)])
        r=cap.swept_capsule_triangle_hits(o,(.5,.5,-1),(.5,.5,3),.1,axis_half_length=.25)
        self.assertEqual(r["original_triangle_hit_ids"],[0,1])

    def test_zero_area_nonleaf_keeps_original_ids(self):
        v=[(0,0,0),(1,0,0),(2,0,0),(0,1,0)]
        o=geo.LevelPointTriangleOracle(v,[(0,1,2,False),(0,1,3,True)])
        r=cap.swept_capsule_triangle_hits(o,(.2,.2,-1),(.2,.2,1),.1)
        self.assertEqual(r["original_triangle_hit_ids"],[1])

    def test_reversed_winding_duplicate_triangles_both_reported(self):
        v=[(0,0,0),(2,0,0),(0,2,0),(0,0,0),(2,0,0),(0,2,0)]
        o=geo.LevelPointTriangleOracle(v,[(0,1,2,True),(5,4,3,True)])
        r=cap.swept_capsule_triangle_hits(o,(.2,.2,-1),(.2,.2,1),.15)
        self.assertEqual(r["original_triangle_hit_ids"],[0,1])

    def test_shape_axis_normalization_and_equivalence(self):
        a=cap.swept_capsule_triangle_hits(flat(),(.5,.5,-1),(.5,.5,1),.12,
                                          axis=(0,0,1),axis_half_length=.2)
        b=cap.swept_capsule_triangle_hits(flat(),(.5,.5,-1),(.5,.5,1),.12,
                                          axis=(0,0,40),axis_half_length=.2)
        self.assertEqual(a["original_triangle_hit_ids"],b["original_triangle_hit_ids"])

    def test_point_triangle_distance_known_perpendicular(self):
        a,b,c=(0,0,0),(2,0,0),(0,2,0)
        self.assertAlmostEqual(cap._point_triangle_distance_sq((.4,.4,3),a,b,c),9)
        self.assertAlmostEqual(cap._point_triangle_distance_sq((3,0,0),a,b,c),1)

    def test_segment_segment_distance_known_parallel(self):
        self.assertAlmostEqual(cap._segment_segment_distance_sq(
            (0,0,0),(1,0,0),(0,1,0),(1,1,0)),1)

    def test_segment_triangle_exact_crossing(self):
        t=((0,0,0),(2,0,0),(0,2,0))
        self.assertEqual(cap._segment_triangle_distance_sq((.5,.5,-1),(.5,.5,1),t),0)
        self.assertAlmostEqual(cap._segment_triangle_distance_sq((.5,.5,3),(.5,.5,4),t),9)

    def test_capsule_distance_monotone_by_radius(self):
        widths=[.0,.02,.1,.5,1.,2.]
        results=[bool(cap.swept_capsule_triangle_hits(
            flat(),(.5,.5,1),(.5,.5,1),r,axis_half_length=0.)["hits"]) for r in widths]
        self.assertEqual(results,[False,False,False,False,True,True])

    def test_reject_nonfinite_shape_dimensions_axis_and_coordinates(self):
        for kw in ({"radius":float("nan")},{"radius":-1},{"axis":(0,0,0)},
                   {"axis":(float("inf"),0,0)},{"axis_half_length":-1},
                   {"axis_half_length":True},{"tolerance":float("inf")},
                   {"tolerance":True}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                cap.swept_capsule_triangle_hits(
                    flat(),(0,0,1),(0,0,-1),**({"radius":.1}|kw))


class CapsuleMoppTests(unittest.TestCase):
    def test_mopp_expansion_is_exact_axis_aligned_enclosing_box(self):
        w=walker()
        r=cap.swept_capsule_mopp_candidates(w,(0,0,100),(0,0,200),.2,(0,0,1),.5)
        self.assertEqual(r["capsule_enclosing_AABB_half_extents_level_xyz"],[.2,.2,.7])
        self.assertFalse(r["capsule_is_exact_havok_shape_query"])

    def test_diagonal_axis_extents_are_exact_enclosure(self):
        w=walker()
        r=cap.swept_capsule_mopp_candidates(w,(0,0,100),(0,0,200),.1,(1,1,0),.6)
        e=r["capsule_enclosing_AABB_half_extents_level_xyz"]
        self.assertAlmostEqual(e[0],.1+.6/math.sqrt(2))
        self.assertAlmostEqual(e[1],e[0])
        self.assertEqual(e[2],.1)

    def test_bad_synthetic_mopp_still_misses_genuine_capsule_hit(self):
        v=[(0,0,0),(2,0,0),(0,2,0),(0,0,0),(2,0,0),(0,2,0)]
        o=geo.LevelPointTriangleOracle(v,[(0,1,2,True),(3,4,5,True)])
        w=walker(b"\x28\x00\xff\x20\x80\x01\x30\x31",2)
        r=cap.compare_swept_capsule(o,w,(.2,.2,-1),(.2,.2,1),.1,axis_half_length=.2)
        self.assertEqual(r["geometric_original_triangle_hit_ids"],[0,1])
        self.assertEqual(r["missing_original_triangle_ids"],[1])

    def test_capsule_candidate_superset_box_candidate(self):
        code=b"\x28\x00\xff\x20\x80\x01\x30\x31";w=walker(code,2)
        x=cap.swept_capsule_mopp_candidates(
            w,(110,0,50),(111,0,50),.1,axis=(1,0,0),axis_half_length=30)
        y=aabb.swept_aabb_mopp_candidates(w,(110,0,50),(111,0,50),(30.1,.1,.1))
        self.assertEqual(x["candidate_original_triangle_ids"],y["candidate_original_triangle_ids"])

    def test_aligned_capsule_zero_half_segment_is_sphere_sweep(self):
        r=cap.compare_swept_capsule(
            flat(),walker(),(.2,.2,-1),(.2,.2,1),.1,axis_half_length=0)
        self.assertTrue(r["all_geometric_hits_retained"])

    def test_unobserved_0x1b_explores_both_with_derived_mode(self):
        w=walker(b"\x28\x00\xff\x1b\x80\x7f\x01\x30\x31",2)
        r=cap.swept_capsule_mopp_candidates(
            w,(10,10,50),(20,20,50),.1,axis_half_length=.2,
            diagonal_mode="derived_diagonals")
        self.assertEqual(r["candidate_original_triangle_ids"],[0,1])

    def test_wrong_diagonal_mode_fails(self):
        with self.assertRaises(ValueError):
            cap.swept_capsule_mopp_candidates(
                walker(),(0,0,20),(0,0,30),.1,diagonal_mode="havok")


if __name__=="__main__":
    unittest.main()
