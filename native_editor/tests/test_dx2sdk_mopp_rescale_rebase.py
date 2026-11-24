import unittest
from inspect_mopp_rescale_rebase import rebase_rescale
from inspect_mopp_axis_refit import refit_axis_bounds
from inspect_mopp_axis_point_candidates import ConservativeMoppPointCandidates

ORIGIN=(0.,0.,0.,65536.)
def tri(x):
    return [(x,0.,0.),(x+1,1.,0.),(x+2,0.,1.)]

class RescaleRebaseTests(unittest.TestCase):
    def test_single_offset_recovery(self):
        code=bytes([0x26,0,255,0x01,5,0,0,0x26,0,10,0x30])
        old=[tri(5.)]; new=[tri(4.)]
        self.assertIsNone(refit_axis_bounds(code,old,new,ORIGIN)[0])
        out,r=rebase_rescale(code,old,new,ORIGIN)
        self.assertEqual(out,bytes([0x26,0,255,0x01,4,0,0,0x26,0,10,0x30]))
        self.assertTrue(r['exact_code_reversal'])
        self.assertTrue(r['original_control_flow_preserved'])
        self.assertEqual(r['rescale_bytes_changed'],1)
        self.assertEqual(r['trial_count'],1)
        w=ConservativeMoppPointCandidates(out,1,ORIGIN)
        self.assertTrue(all(0 in w.point(p)['candidate_triangle_ids'] for p in new[0]))
    def test_unrepresentable_root_filter(self):
        code=bytes([0x26,0,255,0x30])
        out,r=rebase_rescale(code,[tri(1.)],[tri(-3.)],ORIGIN)
        self.assertIsNone(out)
        self.assertEqual(r['reason'],'bounded_rebase_search_exhausted')
        self.assertEqual(r['trial_count'],0)
    def test_noop_and_invalid_source(self):
        code=bytes([0x26,0,255,0x30])
        out,r=rebase_rescale(code,[tri(1.)],[tri(1.)],ORIGIN)
        self.assertIsNone(out)
        self.assertEqual(r['reason'],'rebase_not_required')
        out,r=rebase_rescale(code,[tri(-3.)],[tri(1.)],ORIGIN)
        self.assertIsNone(out)
        self.assertEqual(r['reason'],'source_path_violation')
    def test_unknown_diagonal_refused(self):
        code=bytes([0x26,0,255,0x1b,10,10,1,0x30,0x31])
        with self.assertRaises(ValueError):
            rebase_rescale(code,[tri(1.),tri(20.)],[tri(1.),tri(20.)],ORIGIN)

if __name__=='__main__':unittest.main()
