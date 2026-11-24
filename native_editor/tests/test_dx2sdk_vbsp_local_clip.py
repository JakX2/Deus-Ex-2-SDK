"""Synthetic convex clipping, bounded portal reconstruction and refusal gates."""
import unittest
from inspect_vbsp_local_clip import (
    clip_halfspace,convex,signed_area,boundary_error,portal_geometry,
    compare_loops,edge_dependencies,inspect_local_edit,plane_basis,project,lift,
)


class LocalClipTests(unittest.TestCase):
    def test_clip_and_area(self):
        sq=[(-2.,-2.),(2.,-2.),(2.,2.),(-2.,2.)]
        clipped=clip_halfspace(sq,1.,0.,0.)
        self.assertTrue(convex(clipped))
        self.assertAlmostEqual(abs(signed_area(clipped)),8.)
        self.assertEqual(len(clipped),4)
        self.assertEqual(clip_halfspace(sq,1.,0.,-3.),[])
        self.assertEqual(boundary_error(sq,list(reversed(sq))),0.)
        self.assertFalse(convex([(0.,0.),(2.,0.),(1.,.5),(2.,2.),(0.,2.)]))

    def test_plane_basis(self):
        basis=plane_basis((1.,0.,0.,-2.))
        self.assertEqual(lift(project((2.,3.,4.),basis),basis),(2.,3.,4.))

    def test_bounded_portal_and_hypothetical_clip(self):
        planes=[(1.,0.,0.,0.),(0.,1.,0.,2.),(0.,1.,0.,-2.),
                (0.,0.,1.,2.),(0.,0.,1.,-2.)]
        path=((1,0),(2,1),(3,0),(4,1))
        paths={0:path+((0,0),),1:path+((0,1),)}
        loop,basis,status=portal_geometry(planes,paths,(0,1),0,100.)
        self.assertEqual(status,"bounded")
        self.assertTrue(convex(loop))
        self.assertAlmostEqual(abs(signed_area(loop)),16.)
        xyz=[lift(p,basis) for p in loop]
        self.assertTrue(all(len(e)==1 for e in edge_dependencies(xyz,planes,path,0)))
        changed=list(planes)
        changed[1]=(0.,1.,0.,1.)
        small,_,_=portal_geometry(changed,paths,(0,1),0,100.)
        self.assertAlmostEqual(abs(signed_area(small)),12.)
        self.assertEqual(compare_loops(loop,small)[0],"different")
        self.assertEqual(portal_geometry(planes,{0:((0,0),),1:((0,1),)},(0,1),0,100.)[2],
                         "seed_boundary")

    def test_full_hypothetical_two_leaves(self):
        planes=[(1.,0.,0.,0.),(0.,1.,0.,2.),(0.,1.,0.,-2.),
                (0.,0.,1.,2.),(0.,0.,1.,-2.)]
        # Chain four enclosing planes, then split at X=0.
        nodes=[(4,1,-1,*([0]*6)),(8,-1,2,*([0]*6)),
               (12,3,-1,*([0]*6)),(16,-1,4,*([0]*6)),(3,0,1,*([0]*6))]
        xyz=[(0.,-2.,-2.),(0.,2.,-2.),(0.,2.,2.),(0.,-2.,2.)]
        tail={"planes":planes,"nodes":nodes,"leaves":[(0,1,0,1,-1,0.,-2.,-2.,2.,2.,2.,0,0),
               (1,2,1,1,-1,-2.,-2.,-2.,0.,2.,2.,0,0)],
              "portals":[(0,1,0,4,0,0)],"counts":{"vbsp_portal_vertices":4},
              "coordinates":[(i*12,v) for i,v in enumerate(xyz)]}
        polys=[{"polygon":i,"vertices":[(*v,n,0.,0.) for v in xyz]}
               for i,n in enumerate((1.,-1.))]
        counts=inspect_local_edit(tail,polys,[0,1],plane_index=1,delta_d=-1.)["counts"]
        self.assertEqual(counts["portal_rebuild_eligible"],1)
        self.assertEqual(counts["affected_portals_preview_passed"],1)
        self.assertEqual(counts["affected_faces_preview_area_reduced"],2)
        counts=inspect_local_edit(tail,polys,[0,1],plane_index=0,delta_d=.25)["counts"]
        self.assertEqual(counts["affected_faces_support_translated"],2)
        self.assertEqual(counts["affected_portals_preview_passed"],1)
        # Portal is smaller than the full path intersection: never regenerate.
        tail["coordinates"]=[(i*12,(v[0],v[1]*.5,v[2]*.5)) for i,v in enumerate(xyz)]
        counts=inspect_local_edit(tail,polys,[0,1],plane_index=0,delta_d=.25)["counts"]
        self.assertEqual(counts["affected_portals_source_gate_refused"],1)

    def test_refuse_invalid_delta(self):
        tail={"planes":[],"nodes":[(3,0,1)],"leaves":[(),()]}
        for index,delta in ((None,1.),(0,0.),(0,float("nan"))):
            with self.assertRaises(ValueError):
                inspect_local_edit(tail,[],[],plane_index=index,delta_d=delta)


if __name__=="__main__":
    unittest.main()
