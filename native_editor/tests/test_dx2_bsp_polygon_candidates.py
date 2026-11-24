"""Synthetic BSP polygon candidate tests. No game assets."""
from pathlib import Path
import math
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"dx2"))
from inspect_bsp_polygon_candidates import (
    analyze_polygons, boundary_loop, classify_polygon, RADIUS_FACTOR,
)

A=(0.,0.,0.)
B=(2.,0.,0.)
C=(2.,2.,0.)
D=(0.,2.,0.)
SQUARE=[(A,B,C),(A,C,D)]
PLANE=(0.,0.,1.,0.)
SPHERE=(1.,1.,0.,math.sqrt(2.)*RADIUS_FACTOR)


def node(count=4,sphere=SPHERE):
    return {"plane":PLANE,"sphere":sphere,"count":count,
            "vertex_start":12,"surface":3}


def labelled(tris):
    return [([0,0,i],t) for i,t in enumerate(tris)]


class PolygonCandidateTests(unittest.TestCase):
    def test_convex_square_reconstruction_and_winding(self):
        for tris in (SQUARE,[tuple(reversed(t)) for t in SQUARE]):
            evidence,loop=classify_polygon(PLANE,SPHERE,4,tris)
            self.assertTrue(evidence["preview_candidate"])
            self.assertEqual(set(loop),{A,B,C,D})
            self.assertTrue(evidence["inflated_radius_match"])
            self.assertTrue(evidence["area_match"])

    def test_inflated_sphere_distinguishes_large_polygon(self):
        tris=[tuple(tuple(x*1000 for x in v) for v in t) for t in SQUARE]
        radius=math.sqrt(2)*1000
        evidence,loop=classify_polygon(PLANE,(1000.,1000.,0.,radius*RADIUS_FACTOR),4,tris)
        self.assertTrue(evidence["preview_candidate"])
        self.assertFalse(evidence["unscaled_radius_match"])
        evidence,loop=classify_polygon(PLANE,(1000.,1000.,0.,radius),4,tris)
        self.assertFalse(evidence["preview_candidate"])
        self.assertIsNone(loop)

    def test_wrong_count_center_or_radius_refused(self):
        for count,sphere in ((5,SPHERE),(4,(0.,1.,0.,SPHERE[3])),(4,(1.,1.,0.,4.))):
            evidence,loop=classify_polygon(PLANE,sphere,count,SQUARE)
            self.assertFalse(evidence["preview_candidate"])
            self.assertIsNone(loop)

    def test_bad_topology_refused(self):
        for tris in ([SQUARE[0],SQUARE[0]], [SQUARE[0],(A,D,C)],
                     [SQUARE[0],(A,(3.,3.,0.),(4.,3.,0.))],
                     SQUARE+[(A,C,(1.,3.,0.))]):
            self.assertIsNone(boundary_loop(tris)[1])

    def test_interior_vertex_and_concavity_excluded(self):
        mid=(1.,1.,0.)
        tris=[(A,B,mid),(B,C,mid),(C,D,mid),(D,A,mid)]
        evidence,loop=classify_polygon(PLANE,SPHERE,4,tris)
        self.assertTrue(evidence["vertex_count_match"])
        self.assertFalse(evidence["boundary_only_n_minus_2"])
        self.assertIsNone(loop)
        inset=(.5,.5,0.)
        concave=[(A,B,inset),(A,inset,D)]
        evidence,loop=classify_polygon(PLANE,SPHERE,4,concave)
        self.assertFalse(evidence["strict_convex"])
        self.assertIsNone(loop)

    def test_ambiguous_nodes_not_exported(self):
        result=analyze_polygons([node(),node()],labelled(SQUARE),include_polygons=True)
        self.assertEqual(result["counts"]["ambiguous_candidates"],2)
        self.assertEqual(result["preview_polygons"],[])
        # A unique triangle for node zero is still withheld if that node
        # also has an ambiguous triangle.
        result=analyze_polygons([node(),node(3,(1.5,.5,0.,1.6))],
                               labelled(SQUARE),include_polygons=True)
        self.assertEqual(result["preview_polygons"],[])

    def test_default_aggregate_and_opt_in_geometry(self):
        result=analyze_polygons([node()],labelled(SQUARE))
        self.assertNotIn("preview_polygons",result)
        self.assertEqual(result["counts"]["preview_candidate"],1)
        report=analyze_polygons([node()],labelled(SQUARE),include_polygons=True)
        polygon=report["preview_polygons"][0]
        self.assertEqual(polygon["raw_candidate_vertex_start"],12)
        self.assertEqual(polygon["raw_candidate_surface_value"],3)
        self.assertEqual(polygon["source_vertex_slots"],4)
        self.assertFalse(polygon["native_write_allowed"])
        self.assertFalse(polygon["engine_ownership_verified"])

    def test_duplicate_locator_rejected(self):
        with self.assertRaises(ValueError):
            analyze_polygons([node()],[([0,0,0],SQUARE[0]),([0,0,0],SQUARE[1])])


if __name__=="__main__":
    unittest.main()
