"""Point-on-edge source inventory and movement refusal regression."""
import unittest
from inspect_vbsp_junctions import junction_inventory,inspect_junction_motion
from inspect_vbsp_preview_seams import source_seam_inventory


class JunctionTests(unittest.TestCase):
    def test_interior_and_near_pairs(self):
        polys=[{"polygon":0,"vertices":[(0.,0.,0.),(4.,0.,0.),(0.,4.,0.)]},
               {"polygon":1,"vertices":[(2.,0.,0.),(2.,-2.,0.),(3.,-2.,0.)]},
               {"polygon":2,"vertices":[(0.,.001,0.),(-2.,0.,0.),(-2.,-2.,0.)]}]
        _,points=source_seam_inventory(polys,[0,1,2])
        counts,edges,near=junction_inventory(polys,points)
        self.assertIn(((0.,0.,0.),(4.,0.,0.),(2.,0.,0.)),edges)
        self.assertIn(((0.,0.,0.),(0.,.001,0.)),near)
        self.assertGreaterEqual(counts["source_exact_line_pairs"],1)
        counts,issues=inspect_junction_motion(points,edges,near,
                       {(2.,0.,0.):(2.,1.,0.)},{},{1:"preview_passed"})
        self.assertGreaterEqual(counts["affected_interior_point_edge_separated"],1)
        self.assertTrue(any(i["kind"]=="point_on_edge" for i in issues))
        counts,issues=inspect_junction_motion(points,edges,near,
                        {},{}, {1:"coupled_face_refused"})
        self.assertGreaterEqual(counts["affected_interior_point_edge_unresolved"],1)
        counts,issues=inspect_junction_motion(points,edges,near,
                        {v:tuple(x+1 for x in v) for v in points},{},
                        {i:"preview_passed" for i in range(3)})
        self.assertFalse(issues)
        self.assertEqual(counts["affected_interior_point_edge_preserved"],len(edges))
        self.assertEqual(counts["affected_near_corner_preserved"],len(near))


if __name__=="__main__":
    unittest.main()
