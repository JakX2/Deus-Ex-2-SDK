import unittest
from inspect_mopp_axis_refit import refit_axis_bounds
from inspect_mopp_diagonal_refit import refit_diagonal_bounds
from inspect_mopp_axis_point_candidates import ConservativeMoppPointCandidates

ORIGIN=(0.,0.,0.,65536.)

def tri(y):
    return [(1.,y,y),(2.,y,y+1),(3.,y+1,y)]

class DiagonalRefitTests(unittest.TestCase):
    def test_refit_and_independent_point_queries(self):
        code=bytes([0x26,0,255,0x13,5,5,1,0x30,0x31])
        original=[tri(1.),tri(20.)]
        candidate=[tri(10.),tri(20.)]
        axis,r=refit_axis_bounds(code,original,candidate,ORIGIN)
        self.assertEqual(axis,code)
        new,r=refit_diagonal_bounds(axis,original,candidate,ORIGIN)
        self.assertEqual(new,bytes([0x26,0,255,0x13,10,5,1,0x30,0x31]))
        self.assertTrue(r['original_control_flow_preserved'])
        self.assertTrue(r['exact_code_reversal'])
        self.assertFalse(r['projection_hypotheses_runtime_verified'])
        w=ConservativeMoppPointCandidates(new,2,ORIGIN)
        for tid,t in enumerate(candidate):
            for p in t:self.assertIn(tid,w.point(p,diagonal_mode='derived_diagonals')['candidate_triangle_ids'])
    def test_noop_and_infeasible(self):
        code=bytes([0x26,0,255,0x13,5,5,1,0x30,0x31])
        original=[tri(1.),tri(20.)]
        new,r=refit_diagonal_bounds(code,original,original,ORIGIN)
        self.assertEqual(new,code)
        new,r=refit_diagonal_bounds(code,original,[tri(300.),tri(20.)],ORIGIN)
        self.assertIsNone(new)
        self.assertEqual(r['candidate_before']['infeasible_diagonal_upper'],1)
    def test_unknown_opcode_refused(self):
        code=bytes([0x26,0,255,0x1b,5,5,1,0x30,0x31])
        with self.assertRaises(ValueError):
            refit_diagonal_bounds(code,[tri(1.),tri(20.)],[tri(1.),tri(20.)],ORIGIN)

if __name__=='__main__':unittest.main()
