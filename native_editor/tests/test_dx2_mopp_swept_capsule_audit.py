"""Asset-free source Level/Flesh/MOPP capsule-sweep audit regression cases."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"dx2"))
from test_dx2_level_mopp_triangle_provenance import fixture
import audit_mopp_swept_capsule as audit


class SourceCapsuleAuditTests(unittest.TestCase):
    def test_source_verified_level_with_random_and_targeted_capsules(self):
        level,blocks,_=fixture()
        out=audit.audit_source_level(level,blocks,bbox_random=4,triangle_aimed=4)
        self.assertEqual(out["totals"]["bbox_random_sweeps"],4)
        self.assertEqual(out["totals"]["triangle_aimed_sweeps"],4)
        self.assertEqual(out["totals"]["triangle_aimed_with_geometric_hits"],4)
        self.assertTrue(out["capsule_geometry_subset_of_independent_swept_AABB"])
        self.assertFalse(out["native_Havok_runtime_capsule_tested"])

    def test_structurally_valid_synthetic_tree_misses_capsule_geometry(self):
        level,blocks,_=fixture()
        out=audit.audit_source_level(
            level,blocks,bbox_random=0,triangle_aimed=16,seed=500)
        self.assertGreater(out["totals"].get(
            "triangle_aimed_conservative_missing_queries",0),0)
        self.assertTrue(out["first_missing_original_ids_without_source_coordinates"])
        self.assertTrue(all("point_xyz" not in e for e in
                            out["first_missing_original_ids_without_source_coordinates"]))

    def test_zero_area_nonleaf_preserves_original_source_triangle_ids(self):
        level,blocks,_=fixture(degenerate=True,code=b"\x28\x00\xff\x31")
        out=audit.audit_source_level(level,blocks,bbox_random=0,triangle_aimed=4)
        self.assertEqual(out["original_flat_source_triangles"],2)
        self.assertEqual(out["mopp_leaf_source_triangles"],1)

    def test_reproducible_seed_and_immutable_source_level_bytes(self):
        level,blocks,_=fixture()
        sha=hashlib.sha256(level).hexdigest()
        a=audit.audit_source_level(level,blocks,bbox_random=3,triangle_aimed=3,seed=94)
        b=audit.audit_source_level(level,blocks,bbox_random=3,triangle_aimed=3,seed=94)
        self.assertEqual(a,b)
        self.assertEqual(hashlib.sha256(level).hexdigest(),sha)

    def test_refuse_invalid_shape_sizes_and_sampling(self):
        level,blocks,_=fixture()
        for kw in ({"radius":-1},{"radius":float("nan")},
                   {"axis":(0,0,0)},{"axis_half_length":-1},
                   {"triangle_aimed":True},{"bbox_random":-1},
                   {"bbox_random":0,"triangle_aimed":0},{"seed":-1}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                audit.audit_source_level(level,blocks,**kw)

    def test_duplicate_source_map_paths_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"synthetic.gmp"
            file.write_bytes(b"not a retail DX2 GMP")
            self.assertEqual(audit.main([str(file),str(file)]),1)
            self.assertEqual(file.read_bytes(),b"not a retail DX2 GMP")


if __name__=="__main__":
    unittest.main()
