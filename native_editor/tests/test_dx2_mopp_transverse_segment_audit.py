"""No-retail-assets tests of original Level transverse segment/MOPP audit."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"dx2"))
from test_dx2_level_mopp_triangle_provenance import fixture
import audit_mopp_transverse_segments as audit


class TransverseLevelAuditTests(unittest.TestCase):
    def test_source_validated_level_reports_transverse_crossings(self):
        level,blocks,_=fixture()
        result=audit.audit_source_level(level,blocks)
        self.assertEqual(result["sampled_original_triangles"],2)
        self.assertGreaterEqual(result["totals"]["geometric_triangle_crossings"],2)
        self.assertEqual(result["totals"]["conservative_segments_tested"],2)
        self.assertEqual(result["totals"]["derived_diagonals_segments_tested"],2)
        self.assertFalse(result["mopp_segment_or_ray_traversal_implemented"])
        self.assertFalse(result["runtime_havok_contacts_verified"])

    def test_source_valid_synthetic_tree_can_miss_actual_crossing(self):
        level,blocks,_=fixture()
        result=audit.audit_source_level(level,blocks)
        self.assertGreater(result["totals"].get(
            "conservative_crossings_with_missing_geometry",0),0)
        self.assertTrue(result["first_missing_source_ID_examples"])
        self.assertTrue(all("point_xyz" not in row
                            for row in result["first_missing_source_ID_examples"]))

    def test_degenerate_nonleaf_keeps_original_source_ID_gap(self):
        level,blocks,_=fixture(
            degenerate=True,code=b"\x28\x00\xff\x31")
        result=audit.audit_source_level(level,blocks)
        self.assertEqual(result["original_source_triangles"],2)
        self.assertEqual(result["mopp_leaf_source_triangles"],1)
        self.assertEqual(result["sampled_original_triangles"],1)

    def test_max_samples_and_striding_do_not_claim_full_coverage(self):
        level,blocks,_=fixture()
        one=audit.audit_source_level(level,blocks,max_samples=1)
        self.assertEqual(one["sampled_original_triangles"],1)
        self.assertFalse(one["all_nondegenerate_source_triangle_ids_sampled"])
        other=audit.audit_source_level(level,blocks,sample_stride=2)
        self.assertEqual(other["sampled_original_triangles"],1)

    def test_source_level_bytes_are_unchanged(self):
        level,blocks,_=fixture()
        before=hashlib.sha256(level).hexdigest()
        audit.audit_source_level(level,blocks)
        self.assertEqual(hashlib.sha256(level).hexdigest(),before)

    def test_bad_parameters_rejected_before_audit(self):
        level,blocks,_=fixture()
        for kwargs in [{"sample_stride":0},{"sample_stride":True},
                       {"segment_half_length":0},
                       {"segment_half_length":float("inf")},
                       {"max_samples":-1},{"max_samples":True}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                audit.audit_source_level(level,blocks,**kwargs)

    def test_duplicate_paths_fail_before_source_reader(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"synthetic.gmp"
            p.write_bytes(b"not a real GMP")
            self.assertEqual(audit.main([str(p),str(p)]),1)
            self.assertEqual(p.read_bytes(),b"not a real GMP")

    def test_absent_map_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(audit.main([str(Path(folder)/"absent.gmp")]),1)


if __name__=="__main__":
    unittest.main()
