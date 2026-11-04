"""Synthetic Level fixture validation for full finite-segment candidate audit."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research'/'dx2'))
from test_dx2_level_mopp_triangle_provenance import fixture
import audit_mopp_segment_interval_coverage as audit

class OriginalLevelIntervalAuditTests(unittest.TestCase):
    def test_source_verified_fixture_tests_coplanar_and_transverse(self):
        level,blocks,_=fixture()
        report=audit.audit_level(level,blocks)
        self.assertEqual(report['sampled_leaf_triangle_count'],2)
        self.assertEqual(report['totals']['coplanar_segments'],2)
        self.assertEqual(report['totals']['transverse_segments'],2)
        self.assertGreaterEqual(report['totals']['coplanar_triangle_overlap_events'],2)
        self.assertTrue(report['complete_leaf_coverage'])
        self.assertFalse(report['actual_Havok_segment_query_performed'])

    def test_valid_structural_synthetic_tree_can_fail_transverse_geometry(self):
        level,blocks,_=fixture()
        report=audit.audit_level(level,blocks)
        self.assertGreater(report['totals'].get('conservative_transverse_missing_queries',0),0)
        self.assertTrue(report['first_missed_original_triangle_IDs_no_coordinates'])

    def test_zero_area_original_triangle_keeps_source_ID_gap(self):
        level,blocks,_=fixture(degenerate=True,code=b'\x28\x00\xff\x31')
        report=audit.audit_level(level,blocks)
        self.assertEqual(report['source_level_original_triangle_count'],2)
        self.assertEqual(report['sampled_leaf_triangle_count'],1)

    def test_sampling_limit_does_not_claim_full_corpus(self):
        level,blocks,_=fixture()
        report=audit.audit_level(level,blocks,max_samples=1)
        self.assertEqual(report['sampled_leaf_triangle_count'],1)
        self.assertFalse(report['complete_leaf_coverage'])

    def test_invalid_sampling_options_refused(self):
        level,blocks,_=fixture()
        for kwargs in ({'stride':0},{'stride':True},{'max_samples':-1},
                       {'max_samples':True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                audit.audit_level(level,blocks,**kwargs)

    def test_source_input_is_not_mutated(self):
        level,blocks,_=fixture()
        sha=hashlib.sha256(level).hexdigest()
        audit.audit_level(level,blocks)
        self.assertEqual(hashlib.sha256(level).hexdigest(),sha)

    def test_duplicate_map_paths_refused_before_reader(self):
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)/'synthetic.gmp'
            fake.write_bytes(b'fake')
            self.assertEqual(audit.main([str(fake),str(fake)]),1)
            self.assertEqual(fake.read_bytes(),b'fake')

if __name__=='__main__':unittest.main()
