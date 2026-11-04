"""Asset-free integration tests of complete-source-triangle geometry audit."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
from test_dx2_level_mopp_triangle_provenance import fixture
import audit_mopp_all_point_hits as audit


class FullGeometryMoppAuditTests(unittest.TestCase):
    def test_original_level_provenance_fixture_probes_all_geometric_hits(self):
        level, blocks, _ = fixture()
        report = audit.audit_source_level(level, blocks)
        self.assertEqual(report["original_source_triangles"],2)
        self.assertEqual(report["nondegenerate_source_triangles"],2)
        self.assertEqual(report["probes_by_type"]["centroid"],2)
        self.assertEqual(report["probes_by_type"]["edge_ab"],2)
        self.assertEqual(report["probes_by_type"]["vertex_a"],1)
        self.assertEqual(report["probes_by_type"]["vertex_b"],1)
        self.assertEqual(report["probes_by_type"]["vertex_c"],1)
        self.assertEqual(report["diagonal_modes_tested"],
                         ["conservative","derived_diagonals"])
        self.assertFalse(report["runtime_havok_executed"])

    def test_synthetic_mopp_structure_may_miss_geometry_and_audit_reports_it(self):
        level, blocks, _ = fixture()
        report = audit.audit_source_level(level, blocks)
        # This fixture's X=128 split is synthetic, not geometry-derived.
        self.assertGreater(
            sum(report["probe_queries_missing_geometric_triangle_ids"].values()),0)
        self.assertGreater(len(report["first_missed_source_triangle_examples"]),0)
        self.assertTrue(all("point_xyz" not in row for row in
                            report["first_missed_source_triangle_examples"]))

    def test_original_source_bytes_unchanged(self):
        level, blocks, _ = fixture()
        before=hashlib.sha256(level).hexdigest()
        audit.audit_source_level(level, blocks)
        self.assertEqual(hashlib.sha256(level).hexdigest(),before)

    def test_degenerate_nonleaf_preserves_original_id(self):
        level,blocks,_=fixture(
            degenerate=True,code=b"\x28\x00\xff\x31")
        result=audit.audit_source_level(level,blocks)
        self.assertEqual(result["original_source_triangles"],2)
        self.assertEqual(result["nondegenerate_source_triangles"],1)
        self.assertEqual(result["probes_by_type"]["centroid"],1)

    def test_user_facing_probe_limits_and_bad_types_are_refused(self):
        level, blocks, _ = fixture()
        for opts in ({"max_source_triangles":-1},
                     {"max_source_triangles":True},
                     {"vertex_stride":0},
                     {"vertex_stride":True}):
            with self.subTest(opts=opts), self.assertRaises(ValueError):
                audit.audit_source_level(level,blocks,**opts)
        result=audit.audit_source_level(
            level,blocks,max_source_triangles=1,vertex_stride=1)
        self.assertFalse(result["all_original_leaf_ids_checked"])
        self.assertEqual(result["probes_by_type"]["centroid"],1)

    def test_duplicate_original_map_paths_refused_before_parsing(self):
        with tempfile.TemporaryDirectory() as folder:
            fake=Path(folder)/"synthetic.gmp"
            fake.write_bytes(b"not a real original")
            self.assertEqual(audit.main([str(fake),str(fake)]),1)
            self.assertEqual(fake.read_bytes(),b"not a real original")

    def test_missing_original_map_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(audit.main([str(Path(folder)/"missing.gmp")]),1)


if __name__ == "__main__":
    unittest.main()
