"""Asset-free original-Level capsule first-contact research audit regressions."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research'/'dx2'))
from test_dx2_level_mopp_triangle_provenance import fixture
import audit_mopp_capsule_first_contact as audit


class OriginalSourceCapsuleTOITests(unittest.TestCase):
    def test_source_level_fixture_has_original_ID_contacts_and_bounded_times(self):
        level,blocks,_=fixture()
        result=audit.audit_source_level(level,blocks,bbox_random=4,triangle_aimed=4)
        self.assertEqual(result['counts']['bbox_random_sweeps'],4)
        self.assertEqual(result['counts']['triangle_aimed_sweeps'],4)
        self.assertEqual(result['counts']['triangle_aimed_sweeps_with_contact'],4)
        self.assertFalse(result['havok_runtime_contacts_verified'])
        self.assertEqual(result['time_bracket_tolerance'],1e-8)

    def test_wrong_synthetic_mopp_split_flagged_without_false_havok_claim(self):
        level,blocks,_=fixture()
        result=audit.audit_source_level(level,blocks,bbox_random=0,triangle_aimed=16,seed=500)
        self.assertGreater(result['counts'].get(
            'triangle_aimed_conservative_missing_hit_queries',0),0)
        self.assertTrue(result['first_failure_original_IDs_without_coordinates'])

    def test_source_degenerate_nonleaf_is_not_renumbered(self):
        level,blocks,_=fixture(degenerate=True,code=b'\x28\x00\xff\x31')
        result=audit.audit_source_level(level,blocks,bbox_random=0,triangle_aimed=3)
        self.assertEqual(result['source_triangle_count'],2)
        self.assertEqual(result['original_mopp_leaf_count'],1)
        self.assertEqual(result['counts']['triangle_aimed_sweeps'],3)

    def test_same_seed_reproduces_original_fixture_and_preserves_bytes(self):
        level,blocks,_=fixture()
        sourcehash=hashlib.sha256(level).hexdigest()
        a=audit.audit_source_level(level,blocks,bbox_random=3,triangle_aimed=3,seed=93)
        b=audit.audit_source_level(level,blocks,bbox_random=3,triangle_aimed=3,seed=93)
        self.assertEqual(a,b)
        self.assertEqual(sourcehash,hashlib.sha256(level).hexdigest())

    def test_invalid_capsule_params_and_probe_counts_refused(self):
        level,blocks,_=fixture()
        for options in ({'radius':-1},{'radius':float('nan')},
                        {'axis_half_length':True},{'axis':(0,0,0)},
                        {'bbox_random':-1},{'triangle_aimed':True},
                        {'bbox_random':0,'triangle_aimed':0},{'seed':-1}):
            with self.subTest(options=options),self.assertRaises(ValueError):
                audit.audit_source_level(level,blocks,**options)

    def test_duplicate_original_input_paths_refused_before_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'fake.gmp'
            p.write_bytes(b'not an authentic original map')
            self.assertEqual(audit.main([str(p),str(p)]),1)
            self.assertEqual(p.read_bytes(),b'not an authentic original map')

    def test_missing_retail_input_refused_without_generating_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.assertEqual(audit.main([str(root/'missing.gmp')]),1)
            self.assertEqual(list(root.iterdir()),[])


if __name__=='__main__':unittest.main()
