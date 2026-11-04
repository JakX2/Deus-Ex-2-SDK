"""Synthetic geometric negative controls for exact-edge capsule crossing chords.

The two original floor triangles have a genuine shared edge and zero hinge.
That does NOT imply a moving capsule can clear unrelated geometry. Independent
PR45/46 source geometry oracles detect a wall intersecting the crossing path.
No retail data, Havok runtime, GMP writing or claim of controller walkability.
"""
from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"dx2"))
import inspect_mopp_point_triangle_oracle as oracle
import inspect_mopp_swept_capsule as capsule
import inspect_mopp_capsule_first_contact as timing

FLOOR_VERTICES=[
    (0.,0.,0.),(20.,0.,0.),(0.,20.,0.),(20.,20.,0.)]
FLOOR_FACES=[(0,1,2,True),(1,3,2,True)]
WALL_VERTICES=[
    (10.,0.,0.),(10.,20.,0.),(10.,0.,4.),(10.,20.,4.)]
WALL_FACES=[(4,5,6,True),(5,7,6,True)]
START=(8.,8.,1.)
END=(12.,12.,1.)


def world(*,with_wall=False):
    verts=list(FLOOR_VERTICES)
    tris=list(FLOOR_FACES)
    if with_wall:
        verts+=WALL_VERTICES
        tris+=WALL_FACES
    return oracle.LevelPointTriangleOracle(verts,tris)


class EdgeCrossingClearanceNegativeControls(unittest.TestCase):
    def test_unobstructed_coplanar_source_edge_has_no_contact_at_positive_clearance(self):
        o=world()
        r=capsule.swept_capsule_triangle_hits(
            o,START,END,.2,axis=(0,0,1),axis_half_length=.5)
        self.assertEqual(r["original_triangle_hit_ids"],[])
        t=timing.first_capsule_triangle_contacts(
            o,START,END,.2,axis=(0,0,1),axis_half_length=.5)
        self.assertEqual(t["original_triangle_contact_ids"],[])
        self.assertFalse(t["authentic_havok_runtime_queried"])

    def test_exact_shared_flat_edge_still_has_external_wall_obstruction(self):
        o=world(with_wall=True)
        r=capsule.swept_capsule_triangle_hits(
            o,START,END,.2,axis=(0,0,1),axis_half_length=.5)
        self.assertEqual(r["original_triangle_hit_ids"],[2,3])
        t=timing.compare_first_contact_with_full_sweep(
            o,START,END,.2,axis=(0,0,1),axis_half_length=.5)
        self.assertTrue(t["matching_original_triangle_id_sets"])
        self.assertEqual(t["contact_original_triangle_ids"],[2,3])
        first=t["first_contact"]
        self.assertIsNotNone(first)
        self.assertAlmostEqual(first.t_first_inside,.45,delta=1e-5)
        self.assertFalse(first.initial_overlap)
        self.assertIsNotNone(first.contact_normal_from_triangle_to_capsule)
        self.assertFalse(t["havok_runtime_verified"])

    def test_smaller_sphere_reaches_wall_later(self):
        o=world(with_wall=True)
        broad=timing.first_capsule_triangle_contacts(
            o,START,END,.3,axis_half_length=.5)["first_contact"]
        narrow=timing.first_capsule_triangle_contacts(
            o,START,END,.1,axis_half_length=.5)["first_contact"]
        self.assertLess(broad.t_first_inside,narrow.t_first_inside)
        self.assertAlmostEqual(broad.t_first_inside,.425,delta=1e-5)
        self.assertAlmostEqual(narrow.t_first_inside,.475,delta=1e-5)

    def test_higher_chord_clearance_may_miss_low_wall_but_does_not_prove_walkability(self):
        o=world(with_wall=True)
        start=(8.,8.,5.)
        finish=(12.,12.,5.)
        previous=capsule.swept_capsule_triangle_hits(
            o,start,finish,.2,axis_half_length=.5)
        self.assertEqual(previous["original_triangle_hit_ids"],[])
        current=timing.first_capsule_triangle_contacts(
            o,start,finish,.2,axis_half_length=.5)
        self.assertEqual(current["original_triangle_contact_ids"],[])
        self.assertFalse(current["authentic_havok_runtime_queried"])

    def test_floor_contact_at_lower_offset_is_not_a_proven_blocker(self):
        # The ground is an intended support candidate, not by itself a wall.
        o=world()
        hit=capsule.swept_capsule_triangle_hits(
            o,(8,8,.5),(12,12,.5),.2,axis_half_length=.5)
        self.assertEqual(hit["original_triangle_hit_ids"],[0,1])
        self.assertFalse(hit["native_havok_capsule_contact_verified"])

    def test_immutable_independent_geometry_and_source_triangle_id_domain(self):
        verts=list(FLOOR_VERTICES)+list(WALL_VERTICES)
        faces=list(FLOOR_FACES)+list(WALL_FACES)
        original_verts=list(verts)
        original_faces=list(faces)
        o=oracle.LevelPointTriangleOracle(verts,faces)
        timing.first_capsule_triangle_contacts(
            o,START,END,.2,axis_half_length=.5)
        self.assertEqual(verts,original_verts)
        self.assertEqual(faces,original_faces)
        self.assertEqual(sorted(o.tris),[0,1,2,3])


if __name__=="__main__":
    unittest.main()
