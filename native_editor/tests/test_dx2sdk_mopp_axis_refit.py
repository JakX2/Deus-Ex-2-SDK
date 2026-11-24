import unittest
from inspect_mopp_axis_refit import refit_axis_bounds, diagonal_diagnostics
from inspect_mopp_axis_point_candidates import ConservativeMoppPointCandidates

ORIGIN=(0.,0.,0.,65536.)

def tri(x):
    return [(x,0.,0.),(x+1,1.,0.),(x+2,0.,1.)]

class AxisRefitTests(unittest.TestCase):
    def test_dual_split_preserves_control_flow(self):
        code=bytes([0x26,0,255,0x10,10,10,1,0x30,0x31])
        original=[tri(1.),tri(11.)]
        target=[tri(11.),tri(11.)]
        new,r=refit_axis_bounds(code,original,target,ORIGIN)
        self.assertEqual(new,bytes([0x26,0,255,0x10,13,10,1,0x30,0x31]))
        self.assertTrue(r['exact_code_reversal'])
        self.assertEqual(r['refit_bytes_changed'],1)
        w=ConservativeMoppPointCandidates(new,2,ORIGIN)
        for tid,t in enumerate(target):
            for p in t:self.assertIn(tid,w.point(p)['candidate_triangle_ids'])
    def test_original_noop_and_unsigned_refusal(self):
        code=bytes([0x26,0,255,0x30])
        original=[tri(1.)]
        new,r=refit_axis_bounds(code,original,original,ORIGIN)
        self.assertEqual(new,code)
        new,r=refit_axis_bounds(code,original,[tri(-3.)],ORIGIN)
        self.assertIsNone(new)
        self.assertEqual(r['candidate_before']['infeasible_filter_lower'],1)
    def test_half_split_incompatible(self):
        code=bytes([0x26,0,255,0x20,10,1,0x30,0x31])
        new,r=refit_axis_bounds(code,[tri(1.),tri(11.)],[tri(13.),tri(11.)],ORIGIN)
        self.assertIsNone(new)
        self.assertEqual(r['candidate_before']['infeasible_half_split'],1)
    def test_rescaled_filter(self):
        code=bytes([0x26,0,255,0x01,5,0,0,0x26,0,10,0x30])
        new,r=refit_axis_bounds(code,[tri(5.)],[tri(10.)],ORIGIN)
        self.assertEqual(new[10:],code[10:])
        self.assertEqual(new[9],14)
        self.assertTrue(r['original_control_flow_preserved'])
    def test_24bit_filter(self):
        code=bytes([0x26,0,255,0x29,0,0,0,4,0,0,0x30])
        new,r=refit_axis_bounds(code,[tri(1.)],[tri(5.)],ORIGIN)
        self.assertEqual(int.from_bytes(new[7:10],'big'),6*65536+1)
    def test_invalid_source_refused(self):
        code=bytes([0x26,0,2,0x30])
        new,r=refit_axis_bounds(code,[tri(4.)],[tri(0.)],ORIGIN)
        self.assertIsNone(new)
        self.assertFalse(r['source_axis_path_coverage'])
    def test_diagonal_diagnostics_separate(self):
        code=bytes([0x26,0,255,0x13,5,5,1,0x30,0x31])
        a=tri(1.); b=[(1.,20.,20.),(2.,20.,21.),(3.,21.,20.)]
        c=[(1.,10.,10.),(2.,10.,11.),(3.,11.,10.)]
        new,r=refit_axis_bounds(code,[a,b],[c,b],ORIGIN)
        self.assertEqual(new,code)
        d=diagonal_diagnostics(code,[a,b],[c,b],ORIGIN)
        self.assertEqual(d['new_triangles_with_diagonal_violations'],1)
        self.assertEqual(d['new_diagonal_violations'],3)

if __name__=='__main__':unittest.main()
