"""Asset-free toleranced capsule first-contact / normal research regressions."""
from __future__ import annotations
import math
import random
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research'/'dx2'))
import inspect_mopp_capsule_first_contact as toi
import inspect_mopp_swept_capsule as sweep
import inspect_mopp_point_triangle_oracle as geo


def floor():
    return geo.LevelPointTriangleOracle(
        [(0.,0.,0.),(2.,0.,0.),(0.,2.,0.)],[(0,1,2,True)])


def floors():
    return geo.LevelPointTriangleOracle(
        [(0.,0.,0.),(2.,0.,0.),(0.,2.,0.),
         (0.,0.,-1.),(2.,0.,-1.),(0.,2.,-1.)],
        [(0,1,2,True),(3,4,5,True)])


class FirstContactGeometryTests(unittest.TestCase):
    def test_analytic_sphere_plane_entry_time_and_positive_normal(self):
        r=toi.first_capsule_triangle_contacts(floor(),(.4,.4,2.),(.4,.4,-2.),
                                               .25,axis_half_length=0.)
        h=r['first_contact']
        self.assertEqual(h.original_triangle_id,0)
        self.assertAlmostEqual(h.t_first_inside,(2.-.25)/4.,places=5)
        self.assertAlmostEqual(h.contact_normal_from_triangle_to_capsule[2],1.,places=6)
        self.assertTrue(h.t_last_outside<h.t_first_inside)
        self.assertLessEqual(h.t_first_inside-h.t_last_outside,1.01e-8)
        self.assertFalse(r['authentic_havok_runtime_queried'])

    def test_analytic_vertical_capsule_plane_entry(self):
        h=toi.first_capsule_triangle_contacts(
            floor(),(.4,.4,2.),(.4,.4,-2.),.25,
            axis_half_length=.5)['first_contact']
        self.assertAlmostEqual(h.t_first_inside,(2.-(.5+.25))/4.,places=5)
        self.assertAlmostEqual(h.contact_normal_from_triangle_to_capsule[2],1.,places=5)

    def test_reverse_direction_has_reversed_normal(self):
        h=toi.first_capsule_triangle_contacts(
            floor(),(.4,.4,-2.),(.4,.4,2.),.25,
            axis_half_length=0.)['first_contact']
        self.assertAlmostEqual(h.t_first_inside,.4375,places=5)
        self.assertAlmostEqual(h.contact_normal_from_triangle_to_capsule[2],-1.,places=5)

    def test_empty_contact_for_missed_surface(self):
        result=toi.first_capsule_triangle_contacts(
            floor(),(4.,4.,2.),(4.,4.,-2.),.25,axis_half_length=0.)
        self.assertEqual(result['original_triangle_contact_ids'],[])
        self.assertIsNone(result['first_contact'])

    def test_multi_surface_hits_ordered_by_true_entry_time(self):
        r=toi.first_capsule_triangle_contacts(
            floors(),(.4,.4,2.),(.4,.4,-2.),.2,axis_half_length=0.)
        self.assertEqual([h.original_triangle_id for h in r['contacts']],[0,1])
        self.assertAlmostEqual(r['contacts'][0].t_first_inside,.45,places=5)
        self.assertAlmostEqual(r['contacts'][1].t_first_inside,.70,places=5)

    def test_initial_penetration_is_not_a_fabricated_first_collision(self):
        h=toi.first_capsule_triangle_contacts(
            floor(),(.4,.4,.1),(.4,.4,1.),.25,axis_half_length=0.)['first_contact']
        self.assertEqual(h.t_first_inside,0.)
        self.assertTrue(h.initial_overlap)
        self.assertIsNone(h.t_last_outside)
        self.assertLess(h.signed_gap_at_contact,0.)

    def test_zero_separation_initial_overlap_normal_is_unresolved(self):
        h=toi.first_capsule_triangle_contacts(
            floor(),(.4,.4,0.),(.4,.4,.5),.3,
            axis_half_length=0.)['first_contact']
        self.assertEqual(h.t_first_inside,0.)
        self.assertIsNone(h.contact_normal_from_triangle_to_capsule)
        self.assertFalse(h.contact_normal_resolved)

    def test_contact_at_stationary_capsule(self):
        h=toi.first_capsule_triangle_contacts(
            floor(),(.4,.4,.15),(.4,.4,.15),.2,
            axis_half_length=0.)['first_contact']
        self.assertEqual(h.t_first_inside,0.)
        self.assertTrue(h.initial_overlap)

    def test_stationary_separated_capsule_has_no_contact(self):
        r=toi.first_capsule_triangle_contacts(
            floor(),(.4,.4,.4),(.4,.4,.4),.2,
            axis_half_length=0.)
        self.assertEqual(r['contacts'],[])

    def test_edge_contact_normal_is_not_triangle_face_normal(self):
        h=toi.first_capsule_triangle_contacts(
            floor(),(1.,-.6,0.),(1.,.6,0.),.2,
            axis_half_length=0.)['first_contact']
        self.assertAlmostEqual(h.t_first_inside,1./3.,places=5)
        n=h.contact_normal_from_triangle_to_capsule
        self.assertAlmostEqual(n[1],-1.,places=5)
        self.assertAlmostEqual(n[2],0.,places=5)

    def test_corner_contact_normal_has_two_lateral_components(self):
        h=toi.first_capsule_triangle_contacts(
            floor(),(-1.,-1.,0.),(.2,.2,0.),.2,
            axis_half_length=0.)['first_contact']
        self.assertIsNotNone(h)
        n=h.contact_normal_from_triangle_to_capsule
        self.assertLess(n[0],-.6)
        self.assertLess(n[1],-.6)
        self.assertAlmostEqual(math.hypot(*n),1.,places=6)

    def test_zero_radius_transverse_intersection_has_explicit_tolerance(self):
        h=toi.first_capsule_triangle_contacts(
            floor(),(.4,.4,1.),(.4,.4,-1.),0.,axis_half_length=0.,
            distance_tolerance=1e-7)['first_contact']
        self.assertIsNotNone(h)
        self.assertAlmostEqual(h.t_first_inside,.5,places=4)
        self.assertFalse(h.initial_overlap)

    def test_grazing_motion_keeps_explicit_uncertainty_flag(self):
        h=toi.first_capsule_triangle_contacts(
            floor(),(-1.,.4,.2),(2.,.4,.2),.2,
            axis_half_length=0.)['first_contact']
        self.assertIsNotNone(h)
        self.assertTrue(h.near_tangency)

    def test_reversed_winding_preserves_original_triangle_ids(self):
        v=[(0,0,0),(2,0,0),(0,2,0),(0,0,0),(2,0,0),(0,2,0)]
        o=geo.LevelPointTriangleOracle(v,[(0,1,2,True),(5,4,3,True)])
        result=toi.first_capsule_triangle_contacts(
            o,(1.,.5,2.),(1.,.5,-2.),.2,axis_half_length=0.)
        self.assertEqual(result['original_triangle_contact_ids'],[0,1])

    def test_zero_area_nonleaf_preserves_level_triangle_id_gap(self):
        o=geo.LevelPointTriangleOracle(
            [(0,0,0),(1,0,0),(2,0,0),(0,1,0)],
            [(0,1,2,False),(0,1,3,True)])
        h=toi.first_capsule_triangle_contacts(
            o,(.2,.2,1),(.2,.2,-1),.2,axis_half_length=0.)
        self.assertEqual(h['original_triangle_contact_ids'],[1])

    def test_all_closest_feature_distances_match_previous_scalar_oracle(self):
        rng=random.Random(20261104)
        tri=((0.,0.,0.),(2.,0.,0.),(0.,2.,0.))
        for _ in range(400):
            a=tuple(rng.uniform(-3,3) for _ in range(3))
            b=tuple(rng.uniform(-3,3) for _ in range(3))
            ours=toi._closest_axis_triangle(a,b,tri)[0]
            prior=sweep._segment_triangle_distance_sq(a,b,tri)
            self.assertAlmostEqual(ours,prior,delta=1e-9)

    def test_first_contact_ids_match_complete_capsule_sweep_when_not_grazing(self):
        rng=random.Random(91)
        o=floor()
        for _ in range(40):
            a=(rng.uniform(.2,.7),rng.uniform(.2,.7),rng.uniform(.7,3))
            b=(a[0],a[1],-rng.uniform(.7,3))
            check=toi.compare_first_contact_with_full_sweep(
                o,a,b,radius=.2,axis_half_length=.2)
            self.assertTrue(check['matching_original_triangle_id_sets'])
            self.assertAlmostEqual(check['first_contact'].signed_gap_at_contact,0.,delta=2e-6)

    def test_source_vertices_are_not_mutated_by_contact_search(self):
        verts=[(0.,0.,0.),(2.,0.,0.),(0.,2.,0.)]
        o=geo.LevelPointTriangleOracle(verts,[(0,1,2,True)])
        original=verts[:]
        toi.first_capsule_triangle_contacts(o,(.4,.4,2),(.4,.4,-2),.2)
        self.assertEqual(verts,original)

    def test_invalid_user_data_fail_closed(self):
        o=floor()
        for kwargs in ({'radius':-1},{'radius':float('nan')},
                       {'axis':(0,0,0)},{'axis_half_length':True},
                       {'distance_tolerance':-1},
                       {'distance_tolerance':float('inf')},
                       {'time_tolerance':0},{'max_hits':True},{'max_hits':0}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                toi.first_capsule_triangle_contacts(o,(0,0,1),(0,0,-1),
                    **({'radius':.2}|kwargs))

    def test_unverified_mopp_is_not_part_of_contact_geometry(self):
        o=floor()
        r=toi.first_capsule_triangle_contacts(
            o,(.5,.5,1),(.5,.5,-1),.2,axis_half_length=0.)
        self.assertFalse(r['authentic_havok_runtime_queried'])
        self.assertFalse(r['contact_manifold_or_response_computed'])


if __name__=='__main__':unittest.main()
