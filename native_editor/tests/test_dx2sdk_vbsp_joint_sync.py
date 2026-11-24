import unittest
from inspect_vbsp_joint_sync import model_sphere,model_plane_update,relation,candidate_root,refit_root
from inspect_mopp_axis_point_candidates import ConservativeMoppPointCandidates

class JointSyncTests(unittest.TestCase):
    def test_model_plane_and_sphere(self):
        old=[(0.,0.,0.),(0.,2.,0.),(0.,0.,2.)]
        new=[(1.,0.,0.),(1.,4.,0.),(1.,0.,2.)]
        self.assertEqual(model_plane_update((1.,0.,0.,0.),old,new),(1.,0.,0.,1.))
        self.assertEqual(model_sphere(new)[:3],(1.,2.,1.))
        with self.assertRaises(ValueError):
            model_plane_update((1.,0.,0.,0.),old,[new[0],new[1],old[2]])
    def test_model_relation(self):
        a=((1.,0.,0.,0.),(0.,0.,0.,1.),3)
        b=((-1.,0.,0.,0.),(0.,0.,0.,1.),3)
        self.assertTrue(relation(a,b,5))
        c=((1.,0.,0.,1.),(1.,0.,0.,1.),3)
        self.assertTrue(relation(a,c,4))
        self.assertFalse(relation(a,c,3))
        self.assertFalse(relation(a,c,5))
    def test_root_refit(self):
        code=bytes([0x26,0,255,0x10,10,10,1,0x30,0x31])
        orig=[[(1.,0.,0.),(2.,1.,0.),(3.,0.,1.)],[(11.,0.,0.),(12.,1.,0.),(13.,0.,1.)]]
        root=(0.,0.,0.,65536.)
        new=(0.,0.,0.,4*65536.)
        out,rebased=refit_root(code,orig,orig,root,new)
        self.assertFalse(rebased)
        self.assertEqual(out[4],12)
        w=ConservativeMoppPointCandidates(out,2,new)
        for i,t in enumerate(orig):
            self.assertTrue(all(i in w.point(p)['candidate_triangle_ids'] for p in t))
        with self.assertRaises(ValueError):
            refit_root(code,orig,orig,root,(0.,0.,0.,300*65536.))
    def test_candidate_root(self):
        pts=[(0.,0.,0.),(10.,10.,10.)]
        root=candidate_root(pts,(0.,0.,0.,1.))
        self.assertAlmostEqual(root[0],-.05)
        self.assertEqual(candidate_root(pts,root),root)
        self.assertNotEqual(candidate_root(pts+[(11.,0.,0.)],root),root)

if __name__=='__main__':unittest.main()
