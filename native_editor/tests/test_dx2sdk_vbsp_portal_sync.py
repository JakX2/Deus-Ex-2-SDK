import struct
import unittest
from inspect_level_spatial_vbsp import parse_spatial_tail
from inspect_vbsp_portal_sync import portal_plan,sync_portals,path_regressions


def fixture():
    grid=struct.pack('<IIii3fII',1,1,0,0,0.,0.,0.,1,64)+bytes(64)+struct.pack('<I',0)
    p=0x10000058
    ptrs=[p,p+72,p+72+104,p+72+104+32,p+72+104+32+24,p+72+104+32+24+48,0,p+72+104+32+24+48+8]
    head=struct.pack('<23I',123,0x50534256,2,2,2,0,2,1,0,1,1,4,*ptrs,0,0,0)
    nodes=struct.pack('<18i',0,1,-1,*([0]*6),7,0,1,*([0]*6))
    leaves=struct.pack('<5i6f2i',0,1,0,1,-1,0.,0.,0.,0.,2.,2.,0,0)+struct.pack('<5i6f2i',1,1,1,1,-1,*([0.]*6),0,0)
    planes=struct.pack('<8f',1.,0.,0.,0.,0.,1.,0.,0.)
    port=struct.pack('<6i',0,1,0,4,1,0)
    xyz=struct.pack('<12f',0.,0.,0.,2.,0.,0.,2.,0.,2.,0.,0.,2.)
    return grid+head+nodes+leaves+planes+port+xyz+struct.pack('<I',0)


class PortalSyncTests(unittest.TestCase):
    def setUp(self):
        self.raw=fixture(); self.tail=parse_spatial_tail(self.raw,0,len(self.raw))
        xyz=[(0.,0.,0.),(0.,2.,0.),(0.,2.,2.),(0.,0.,2.)]
        self.old=[{'polygon':0,'vertices':[(*p,1.,0.,0.) for p in xyz]}]
        self.new=[{'polygon':0,'vertices':[(.5,*p[1:]) for p in self.old[0]['vertices']]}]
    def test_move_portal_edge_and_reparse(self):
        out,c=sync_portals(self.raw,self.tail,self.old,self.new,[0],0,-.5)
        self.assertIsNotNone(out)
        self.assertEqual(c['portal_vertices_moved'],2)
        self.assertEqual(c['portal_render_corner_contacts_tested'],2)
        t=parse_spatial_tail(out,0,len(out))
        self.assertEqual(t['planes'][0],(1.,0.,0.,-.5))
        self.assertEqual(t['portal_leaf_links'],self.tail['portal_leaf_links'])
        self.assertEqual(t['coordinates'][-4][1],(.5,0.,0.))
        self.assertEqual(t['coordinates'][-3][1],(2.,0.,0.))
    def test_stationary_render_contact_refused(self):
        out,c=sync_portals(self.raw,self.tail,self.old,self.old,[0],0,-.5)
        self.assertIsNone(out)
        self.assertEqual(c['portal_corner_constraints_refused'],2)
    def test_regression_and_inventory(self):
        self.assertEqual(path_regressions([(0.,0.,0.)],[(0.,0.,0.)],[(1.,0.,0.,0.)],[(1.,0.,0.,-1.)],[(0,0)]),1)
        with self.assertRaises(ValueError):portal_plan(self.tail,self.old,[],[0],0,-.5)

if __name__=='__main__':unittest.main()
