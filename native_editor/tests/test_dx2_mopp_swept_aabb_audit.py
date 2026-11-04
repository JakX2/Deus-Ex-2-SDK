"""Asset-free original-Level swept AABB source-audit integration tests."""
from __future__ import annotations
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research'/'dx2'))
from test_dx2_level_mopp_triangle_provenance import fixture
import audit_mopp_swept_aabb as audit


class SweptAABBSourceAuditTests(unittest.TestCase):
    def test_source_verified_fixture_with_both_sampling_strata(self):
        level,blocks,_=fixture()
        report=audit.audit_source_level(level,blocks,bbox_random=4,triangle_aimed=4)
        self.assertEqual(report['totals']['bbox_random_sweeps'],4)
        self.assertEqual(report['totals']['triangle_aimed_sweeps'],4)
        self.assertEqual(report['totals']['triangle_aimed_with_geometric_contact'],4)
        self.assertFalse(report['runtime_Havok_swept_shape_verified'])

    def test_structurally_valid_but_wrong_synthetic_mopp_can_miss_box_hit(self):
        level,blocks,_=fixture()
        result=audit.audit_source_level(
            level,blocks,bbox_random=0,triangle_aimed=16,seed=500)
        self.assertGreater(result['totals'].get(
            'triangle_aimed_conservative_missing_queries',0),0)
        self.assertGreater(len(result[
            'first_missing_ID_counterexamples_without_coordinates']),0)

    def test_degenerate_source_triangle_original_id_gap(self):
        level,blocks,_=fixture(degenerate=True,code=b'\x28\x00\xff\x31')
        report=audit.audit_source_level(level,blocks,bbox_random=0,triangle_aimed=4)
        self.assertEqual(report['original_source_triangle_count'],2)
        self.assertEqual(report['mopp_leaf_source_triangle_count'],1)

    def test_deterministic_and_retail_input_immutable(self):
        level,blocks,_=fixture()
        sha=hashlib.sha256(level).hexdigest()
        a=audit.audit_source_level(
            level,blocks,bbox_random=3,triangle_aimed=3,seed=94)
        b=audit.audit_source_level(
            level,blocks,bbox_random=3,triangle_aimed=3,seed=94)
        self.assertEqual(a,b)
        self.assertEqual(hashlib.sha256(level).hexdigest(),sha)

    def test_reject_invalid_dimensions_and_sampling_options(self):
        level,blocks,_=fixture()
        for kw in ({'half_extents':(-1,0,0)},
                   {'half_extents':(0,float('nan'),0)},
                   {'bbox_random':-1},
                   {'triangle_aimed':True},
                   {'seed':-1},
                   {'bbox_random':0,'triangle_aimed':0}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                audit.audit_source_level(level,blocks,**kw)

    def test_duplicate_source_gmp_refused_without_input_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            fake=Path(directory)/'synthetic.gmp'
            fake.write_bytes(b'fake')
            self.assertEqual(audit.main([str(fake),str(fake)]),1)
            self.assertEqual(fake.read_bytes(),b'fake')


if __name__=='__main__':
    unittest.main()
