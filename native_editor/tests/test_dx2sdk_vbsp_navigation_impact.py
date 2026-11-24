import unittest
from inspect_vbsp_navigation_impact import inspect_samples,exact_motion

class NavigationImpactTests(unittest.TestCase):
    def test_open_to_solid_and_exact_motion(self):
        nodes=[(1,0,-1,*([0]*6))]
        old=[(1.,0.,0.,0.)]; new=[(1.,0.,0.,-.5)]
        p=(.25,0.,0.); q=(.75,0.,0.)
        c=inspect_samples({'graph_triangle_corner':[p,q]},nodes,old,new,0,{p:q})
        self.assertEqual(c['graph_triangle_corner_new_solid'],1)
        self.assertEqual(c['graph_triangle_corner_up_new_solid'],1)
        self.assertEqual(c['graph_triangle_corner_exact_moved_contact'],1)
        self.assertEqual(c['graph_triangle_corner_hypothetical_contact_new_solid'],0)
    def test_upward_probe_independent_of_original_point(self):
        nodes=[(1,0,-1,*([0]*6))]
        c=inspect_samples({'grid_origin':[(0.,0.,0.)]},nodes,[(0.,0.,1.,-.05)],[(0.,0.,1.,-.15)],0,{})
        self.assertEqual(c.get('grid_origin_leaf_changed',0),0)
        self.assertEqual(c['grid_origin_up_new_solid'],1)
    def test_motion_conflict(self):
        a={'polygon':0,'vertices':[(0.,0.,0.),(0.,0.,0.)]}
        b={'polygon':0,'vertices':[(1.,0.,0.),(0.,0.,0.)]}
        t={'counts':{'vbsp_portal_vertices':0}}
        with self.assertRaises(ValueError):exact_motion([a],[b],t,t)
    def test_refuse_other_plane_changes(self):
        with self.assertRaises(ValueError):inspect_samples({},[],[(1.,0.,0.,0.)],[(0.,1.,0.,0.)],0,{})

if __name__=='__main__':unittest.main()
