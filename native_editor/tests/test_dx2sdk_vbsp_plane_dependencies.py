"""Synthetic source-plane dependency and hypothetical offset gates."""
import unittest
from inspect_vbsp_plane_dependencies import leaf_paths,inspect_dependencies
from inspect_level_spatial_vbsp import parse_spatial_tail
from test_dx2sdk_level_spatial_vbsp import fixture


class VBSPPlaneDependencyTests(unittest.TestCase):
    def test_shared_plane_and_hypothetical_violation(self):
        raw=fixture()
        tail=parse_spatial_tail(raw,0,len(raw))
        self.assertEqual(leaf_paths(tail["nodes"]),{0:((0,0),),1:((0,1),)})
        xyz=[(0.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
        polys=[{"polygon":i,"vertices":[(*p,n,0.,0.) for p in xyz]}
               for i,n in enumerate((1.,-1.))]
        result=inspect_dependencies(tail,polys,[0,1],plane_index=0,delta_d=-1.)
        counts=result["counts"]
        self.assertEqual(counts["polygon_path_plane_unique"],2)
        self.assertEqual(counts["polys_on_shared_plane"],2)
        impact=result["hypothetical_impact"]
        self.assertEqual(impact["leaf_paths_reusing_plane"],2)
        self.assertEqual(impact["unique_supporting_polygon_candidates"],2)
        self.assertEqual(impact["directly_referencing_portal_records"],1)
        self.assertEqual(impact["new_unchanged_polygon_path_violations"],1)

    def test_reject_cycle_and_bad_hypothetical_input(self):
        with self.assertRaises(ValueError):
            leaf_paths([(0,0,-1,*([0]*6))])
        raw=fixture()
        tail=parse_spatial_tail(raw,0,len(raw))
        for plane,delta in ((0,None),(1,1.),(0,0.),(0,float("nan"))):
            with self.assertRaises(ValueError):
                inspect_dependencies(tail,[],[],plane_index=plane,delta_d=delta)


if __name__=="__main__":
    unittest.main()
