"""Synthetic coupled corner solver, rank and refusal regression tests."""
import unittest
from inspect_vbsp_coupled_corners import solve_displacement,coupled_preview


class CoupledCornerTests(unittest.TestCase):
    def test_rank_and_minimum_norm(self):
        self.assertEqual(solve_displacement([((1.,0.,0.),2.)],10),((2.,0.,0.),1))
        self.assertEqual(solve_displacement([((1.,0.,0.),2.),((0.,1.,0.),3.),
                    ((-1.,0.,0.),-2.)],10),((2.,3.,0.),2))
        self.assertEqual(solve_displacement([((1.,0.,0.),2.),((0.,1.,0.),3.),
                    ((0.,0.,1.),4.)],10),((2.,3.,4.),3))
        with self.assertRaises(ValueError):
            solve_displacement([((1.,0.,0.),2.),((-1.,0.,0.),0.)],10)
        with self.assertRaises(ValueError):
            solve_displacement([((1.,0.,0.),2.)],1)

    def test_coupled_perpendicular_surfaces(self):
        # Both faces belong to the positive octant; their common edge
        # slides on stationary Y=0 when the X=0 plane moves to X=.5.
        planes=[(1.,0.,0.,0.),(0.,1.,0.,0.)]
        nodes=[(0,1,-1,*([0]*6)),(5,0,-1,*([0]*6))]
        tail={"planes":planes,"nodes":nodes,"leaves":[()]}
        xyz=[[(0.,0.,0.),(0.,2.,0.),(0.,2.,2.),(0.,0.,2.)],
             [(0.,0.,0.),(0.,0.,2.),(2.,0.,2.),(2.,0.,0.)]]
        polys=[{"polygon":i,"vertices":[(*v,*normal,v[0]+v[1],v[2]) for v in p]}
               for i,(p,normal) in enumerate(zip(xyz,[(1.,0.,0.),(0.,1.,0.)]))]
        result=coupled_preview(tail,polys,[0,0],0,-.5,include_geometry=True)
        self.assertTrue(result["coupled_corner_preview_passed"])
        self.assertEqual(result["counts"]["coupled_faces_passed"],2)
        self.assertEqual(result["counts"]["preview_shared_xyz_groups_agree"],2)
        faces=result["private_preview_geometry"]["faces"]
        self.assertEqual(faces[0]["vertices"][0]["xyz"],(.5,0.,0.))
        self.assertEqual(faces[1]["vertices"][0]["xyz"],(.5,0.,0.))
        self.assertEqual(faces[1]["vertices"][0]["primary_uv"],(.5,0.))
        self.assertFalse(result["native_geometry_writer_enabled"])

    def test_invalid_delta(self):
        with self.assertRaises(ValueError):
            coupled_preview({"planes":[(1.,0.,0.,0.)]},[],[],0,0.)


if __name__=="__main__":
    unittest.main()
