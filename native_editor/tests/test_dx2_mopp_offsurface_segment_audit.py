"""Asset-free deterministic off-surface segment versus MOPP regression cases."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research'/'dx2'))
import audit_mopp_offsurface_segments as off
import inspect_mopp_point_triangle_oracle as geometry
import inspect_mopp_axis_point_candidates as mopp
from test_dx2_level_mopp_triangle_provenance import fixture


class OffsurfaceSegmentAuditTests(unittest.TestCase):
    def test_random_bbox_segment_has_no_triangle_target_and_offsurface_endpoints(self):
        atlas=geometry.LevelPointTriangleOracle(
            [(0,0,0),(2,0,0),(0,2,0)],[(0,1,2,True)])
        import random
        a,b=off._random_bbox_segment(atlas,random.Random(143),off._bbox(atlas))
        self.assertFalse(atlas.containing_triangle_ids(a))
        self.assertFalse(atlas.containing_triangle_ids(b))
        self.assertNotEqual(a,b)

    def test_targeted_ray_direction_random_not_fixed_to_normal(self):
        atlas=geometry.LevelPointTriangleOracle(
            [(0,0,0),(2,0,0),(0,2,0)],[(0,1,2,True)])
        import random
        a,b,tid=off._triangle_aimed_segment(atlas,random.Random(13),off._bbox(atlas),[0])
        self.assertEqual(tid,0)
        self.assertFalse(atlas.containing_triangle_ids(a))
        self.assertFalse(atlas.containing_triangle_ids(b))
        self.assertNotAlmostEqual(a[0],b[0])
        self.assertEqual([h.original_triangle_id for h in
            off.transverse.segment_crossings(atlas,a,b)['hits']],[0])

    def test_two_parallel_planes_both_counted_along_one_offsurface_segment(self):
        geo=geometry.LevelPointTriangleOracle(
            [(0,0,0),(1,0,0),(0,1,0),(0,0,2),(1,0,2),(0,1,2)],
            [(0,1,2,True),(3,4,5,True)])
        source=mopp.ConservativeMoppPointCandidates(
            b'\x28\x00\xff\x20\x80\x01\x30\x31',2,(0,0,-10,65536.))
        result=off.compare_independent_segment(geo,source,(.2,.2,-1),(.2,.2,3))
        self.assertEqual(result['geometry_hit_source_triangle_ids'],[0,1])
        for mode in off.mopp.DIAGONAL_MODES:
            self.assertEqual(result['mode_results'][mode]['missing_source_triangle_ids'],[1])

    def test_no_contact_segment_can_still_return_broadphase_candidates(self):
        geo=geometry.LevelPointTriangleOracle(
            [(0,0,0),(1,0,0),(0,1,0)],[(0,1,2,True)])
        source=mopp.ConservativeMoppPointCandidates(
            b'\x28\x00\xff\x30',1,(0,0,-10,65536.))
        result=off.compare_independent_segment(geo,source,(.2,.2,.5),(.4,.2,.5))
        self.assertEqual(result['geometry_hit_source_triangle_ids'],[])
        self.assertGreater(result['mode_results']['conservative']['candidate_count'],0)
        self.assertGreater(result['mode_results']['conservative']['false_positive_candidate_count'],0)

    def test_source_fixture_deterministic_seed_both_strata(self):
        level,blocks,_=fixture()
        a=off.audit_source_level(level,blocks,random_segments=4,aimed_segments=4,seed=17)
        b=off.audit_source_level(level,blocks,random_segments=4,aimed_segments=4,seed=17)
        self.assertEqual(a,b)
        self.assertEqual(a['summary']['bbox_random_segments'],4)
        self.assertEqual(a['summary']['triangle_aimed_segments'],4)
        self.assertEqual(a['summary']['triangle_aimed_with_geometric_contact'],4)
        self.assertTrue(a['all_endpoints_verified_off_source_surfaces'])
        self.assertFalse(a['runtime_havok_ray_tested'])

    def test_hash_unchanged_and_seed_changes_results(self):
        level,blocks,_=fixture()
        digest=hashlib.sha256(level).hexdigest()
        a=off.audit_source_level(level,blocks,random_segments=5,aimed_segments=2,seed=12)
        b=off.audit_source_level(level,blocks,random_segments=5,aimed_segments=2,seed=13)
        self.assertEqual(a['source_level_sha256'],digest)
        self.assertEqual(hashlib.sha256(level).hexdigest(),digest)
        self.assertNotEqual(a['summary'],b['summary'])

    def test_original_zero_area_triangle_not_targeted_or_returned(self):
        level,blocks,_=fixture(degenerate=True,code=b'\x28\x00\xff\x31')
        report=off.audit_source_level(level,blocks,random_segments=0,aimed_segments=6)
        self.assertEqual(report['source_triangle_count'],2)
        self.assertEqual(report['mopp_source_triangle_count'],1)
        self.assertEqual(report['summary']['triangle_aimed_with_geometric_contact'],6)

    def test_reversed_winding_duplicate_source_ids_both_detected(self):
        v=[(0,0,0),(1,0,0),(0,1,0),(0,0,0),(1,0,0),(0,1,0)]
        oracle=geometry.LevelPointTriangleOracle(v,[(0,1,2,True),(5,4,3,True)])
        walker=mopp.ConservativeMoppPointCandidates(
            b'\x28\x00\xff\x13\x00\xff\x01\x30\x31',2,
            (0,0,-10,65536.))
        result=off.compare_independent_segment(oracle,walker,(.3,.2,-1),(.3,.2,1))
        self.assertEqual(result['geometry_hit_source_triangle_ids'],[0,1])
        self.assertFalse(result['mode_results']['conservative']['missing_source_triangle_ids'])

    def test_invalid_counts_and_seed_refused(self):
        for args in ((0,0,1),(-1,3,1),(1,10001,1),(1,1,-1),
                     (True,1,1),(1,1,True),(1,1,2**64)):
            with self.subTest(args=args),self.assertRaises(ValueError):
                off._validated_options(*args)

    def test_aimed_segments_are_not_misdescribed_as_random_bbox_rays(self):
        level,blocks,_=fixture()
        report=off.audit_source_level(level,blocks,random_segments=1,aimed_segments=1)
        self.assertEqual(report['strata'],['bbox_random','triangle_aimed'])
        self.assertTrue(report['bbox_endpoints_are_independent_of_triangle_selection'])
        self.assertTrue(report['aimed_directions_are_randomized_not_only_face_normals'])

    def test_refuse_duplicate_source_paths_before_decoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.gmp'
            path.write_bytes(b'not a game map')
            self.assertEqual(off.main([str(path),str(path)]),1)
            self.assertEqual(path.read_bytes(),b'not a game map')

    def test_zero_length_and_foreign_mopp_rejected(self):
        geo=geometry.LevelPointTriangleOracle(
            [(0,0,0),(1,0,0),(0,1,0)],[(0,1,2,True)])
        with self.assertRaises(ValueError):
            off.compare_independent_segment(geo,None,(0,0,1),(0,0,2))
        with self.assertRaises(ValueError):
            off.compare_independent_segment(None,None,(0,0,1),(0,0,2))


if __name__=='__main__':unittest.main()
