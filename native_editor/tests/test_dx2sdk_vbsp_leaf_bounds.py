import struct
import unittest
from inspect_vbsp_leaf_bounds import leaf_boxes,verify_leaf_boxes,sync_leaf_boxes

class LeafBoundsTests(unittest.TestCase):
    def setUp(self):
        self.p=[{'polygon':0,'vertices':[(0.,0.,0.),(2.,0.,0.),(0.,2.,0.)]}]
        self.row=(0,1,0,0,-1,0.,0.,0.,2.,2.,0.,0,0)
        self.empty=(1,1,0,0,-1,*([0.]*6),0,0)
        self.level=bytes(20)+struct.pack('<5i6f2i',*self.row)+struct.pack('<5i6f2i',*self.empty)+struct.pack('<4f',1.,0.,0.,0.)
        self.tail={'leaves':[self.row,self.empty],'plane_offsets':[(20+104+12,(1.,0.,0.,0.))],'end':len(self.level)}
    def test_source_leaf_boxes(self):
        self.assertEqual(leaf_boxes(self.tail,self.p),[(0.,0.,0.,2.,2.,0.),(0.,)*6])
        self.assertEqual(verify_leaf_boxes(self.tail,self.p),{'vbsp_exact_render_leaf_boxes':2,'vbsp_empty_zero_boxes':1})
        out,counts=sync_leaf_boxes(self.level,self.tail,self.p,self.p)
        self.assertEqual(out,self.level)
        self.assertEqual(counts['vbsp_leaf_bounds_changed'],0)
    def test_fixed_width_leaf_sync(self):
        new=[{'polygon':0,'vertices':[(1.,0.,0.),(3.,0.,0.),(1.,2.,0.)]}]
        out,counts=sync_leaf_boxes(self.level,self.tail,self.p,new)
        self.assertEqual(struct.unpack_from('<6f',out,40),(1.,0.,0.,3.,2.,0.))
        self.assertEqual(out[:40],self.level[:40]);self.assertEqual(out[64:],self.level[64:])
        self.assertEqual(counts['vbsp_leaf_bounds_changed'],1)
    def test_refuse_wrong_source_box_or_ownership(self):
        bad={'leaves':[self.row[:5]+(0.,)*6+self.row[11:],self.empty]}
        with self.assertRaises(ValueError):verify_leaf_boxes(bad,self.p)
        with self.assertRaises(ValueError):leaf_boxes({'leaves':[self.row,self.row]},self.p)
        with self.assertRaises(ValueError):sync_leaf_boxes(self.level,self.tail,self.p,[])
        with self.assertRaises(ValueError):sync_leaf_boxes(bytes(len(self.level)),self.tail,self.p,self.p)

if __name__=='__main__':unittest.main()
