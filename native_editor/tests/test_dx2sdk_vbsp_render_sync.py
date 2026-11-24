import unittest
from inspect_vbsp_render_sync import shadow_corner_order,_check_tangent,round_tuple

class RenderSyncTests(unittest.TestCase):
    def test_shadow_permutation_and_refusal(self):
        a,b,c=(0.,0.,0.),(2.,0.,0.),(0.,2.,0.)
        self.assertEqual(shadow_corner_order([(2.,0.,.3),(0.,2.,.3),(0.,0.,.3)],[a,b,c]),(b,c,a))
        with self.assertRaises(ValueError):
            shadow_corner_order([(0.,0.,0.),(0.,0.,0.),c],[a,(.1,0.,0.),c])
        with self.assertRaises(ValueError):
            shadow_corner_order([(2.,0.,.5),b,c],[a,b,c])
    def test_preserve_tangent_for_stretch_and_reject_rotated_uv(self):
        old=[(0.,0.,0.,0.,0.,1.,0.,0.),(2.,0.,0.,0.,0.,1.,1.,0.),
             (2.,2.,0.,0.,0.,1.,1.,1.),(0.,2.,0.,0.,0.,1.,0.,1.)]
        words=[b'\x80\x80\xff\xff'+b'\xff'*4]*4
        new=[((2*v[0],v[1],0.),(v[6]*2,v[7])) for v in old]
        _check_tangent(old,new,words)
        with self.assertRaises(ValueError):
            _check_tangent(old,[(v[:3],(v[7],v[6])) for v in old],words)
        with self.assertRaises(ValueError):
            _check_tangent(old,new,[b'\xff'*8]*4)
    def test_nonfinite_refused(self):
        with self.assertRaises(ValueError):round_tuple((float('nan'),0.,0.))

if __name__=='__main__':unittest.main()
