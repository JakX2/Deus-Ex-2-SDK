"""Asset-free tests for DX2Ed original collision selection sidecar."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'native_editor'/'godot_editor'/'backend'))
sys.path.insert(0,str(ROOT/'research'/'dx2'))
from test_dx2_level_mopp_triangle_provenance import fixture
import export_level_mopp_triangle_debug_mesh as debug
import dx2_collision_selection_cache as selector

HASH = '1'*64


def fixture_atlas(*, degenerate=False):
    if degenerate:
        level, blocks, _ = fixture(code=b'\x28\x00\xff\x31',degenerate=True)
    else:
        level, blocks, _ = fixture()
    return debug.inspect_mesh(level,blocks)


class CollisionCacheTests(unittest.TestCase):
    def test_original_triangle_ids_and_godot_coordinate_conversion(self):
        atlas=fixture_atlas()
        doc=selector.prepare_doc(atlas,source_name='Fixture.gmp',source_sha256=HASH)
        self.assertEqual(doc['schema'],selector.SCHEMA)
        self.assertEqual(doc['source_triangle_count'],2)
        self.assertEqual(doc['mopp_leaf_triangle_count'],2)
        self.assertEqual([x['triangle_id'] for x in doc['leaf_triangles']],[0,1])
        self.assertEqual(doc['vertices_godot_xyz'][1],[0.2,0.0,0.0])
        self.assertEqual(doc['vertices_godot_xyz'][2],[0.2,0.0,0.2])
        self.assertEqual(doc['render_material_names'],['MatA','MatB'])
        self.assertFalse(doc['physics_materials_verified'])
        self.assertTrue(doc['not_a_native_collision_writer'])

    def test_preserves_gapped_triangle_ids_after_degenerate_omission(self):
        doc=selector.prepare_doc(fixture_atlas(degenerate=True),source_name='Fixture.gmp',source_sha256=HASH)
        self.assertEqual(doc['source_triangle_count'],2)
        self.assertEqual(doc['mopp_leaf_triangle_count'],1)
        self.assertEqual(doc['leaf_triangles'][0]['triangle_id'],1)
        self.assertEqual(doc['leaf_triangles'][0]['render_section_ordinal'],1)

    def test_source_material_identifiers_never_promoted_to_physics(self):
        doc=selector.prepare_doc(fixture_atlas(),source_name='Fixture.gmp',source_sha256=HASH)
        self.assertNotIn('physical_material',json.dumps(doc).lower())
        self.assertFalse(doc['physics_materials_verified'])
        self.assertEqual(doc['leaf_triangles'][1]['render_material_id'],1)

    def test_source_sha_and_map_name_are_required(self):
        atlas=fixture_atlas()
        for sha in ('', 'z'*64,'0'*63,None):
            with self.subTest(sha=sha),self.assertRaises(ValueError):
                selector.prepare_doc(atlas,source_name='Fixture.gmp',source_sha256=sha)
        with self.assertRaises(ValueError):
            selector.prepare_doc(atlas,source_name='Fixture.txt',source_sha256=HASH)

    def test_refuse_malformed_material_provenance(self):
        atlas=fixture_atlas()
        atlas['materials'][0]['physics_material_verified']=True
        with self.assertRaisesRegex(ValueError,'render material'):
            selector.prepare_doc(atlas,source_name='Fixture.gmp',source_sha256=HASH)

    def test_refuse_bad_vertex_ids(self):
        atlas=fixture_atlas()
        atlas['triangles'][0]['vertex_indices_zero_based'][0]=12345
        with self.assertRaisesRegex(ValueError,'triangle'):
            selector.prepare_doc(atlas,source_name='Fixture.gmp',source_sha256=HASH)

    def test_refuse_triangle_reorder(self):
        atlas=fixture_atlas()
        atlas['triangles'][0]['triangle_id']=1
        with self.assertRaisesRegex(ValueError,'ID order'):
            selector.prepare_doc(atlas,source_name='Fixture.gmp',source_sha256=HASH)

    def test_same_source_map_directory_rejected_without_creation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'original.gmp';p.write_bytes(b'synthetic')
            sha=hashlib.sha256(p.read_bytes()).hexdigest()
            for dest in (Path(d)/'collision.json',p):
                with self.assertRaisesRegex(ValueError,'outside original'):
                    selector.build(p,dest,expected_sha256=sha)
            self.assertEqual(p.read_bytes(),b'synthetic')

    def test_source_hash_mismatch_fails_before_research_reader(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);maps=base/'maps';maps.mkdir();p=maps/'fixture.gmp';p.write_bytes(b'not original')
            with patch.object(selector.debug,'audit_map',side_effect=AssertionError('should not reach')):
                with self.assertRaisesRegex(ValueError,'hash differs'):
                    selector.build(p,base/'cache'/'collision.json',expected_sha256=HASH)
            self.assertFalse((base/'cache').exists())

    def test_exclusive_cached_output_and_hash_integrity(self):
        atlas=fixture_atlas()
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);maps=base/'maps';maps.mkdir();p=maps/'fixture.gmp';p.write_bytes(b'synthetic GMP')
            sha=hashlib.sha256(p.read_bytes()).hexdigest()
            dest=base/'cache'/'source_collision.json'
            with patch.object(selector.debug,'audit_map',return_value=(atlas,{'sha256':sha})) as mock:
                first=selector.build(p,dest,expected_sha256=sha)
                self.assertEqual(first['cache'],'created')
                again=selector.build(p,dest,expected_sha256=sha)
                self.assertEqual(again['cache'],'existing')
                self.assertEqual(mock.call_count,1)
            self.assertEqual(p.read_bytes(),b'synthetic GMP')
            doc=json.loads(dest.read_text())
            self.assertEqual(doc['source_sha256'],sha)
            doc['source_sha256']=HASH;dest.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,'stale'):
                selector.build(p,dest,expected_sha256=sha)

    def test_corrupted_cache_requires_rebuild_not_silent_adoption(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);maps=base/'maps';maps.mkdir();p=maps/'test.gmp';p.write_bytes(b'synthetic')
            sha=hashlib.sha256(p.read_bytes()).hexdigest()
            cache=base/'cache'/'collision.json';cache.parent.mkdir();cache.write_text('{}')
            with self.assertRaisesRegex(ValueError,'stale'):
                selector.build(p,cache,expected_sha256=sha)

    def test_source_hash_is_not_mutated_by_preparation(self):
        atlas=fixture_atlas();before=json.dumps(atlas,sort_keys=True)
        selector.prepare_doc(atlas,source_name='Fixture.gmp',source_sha256=HASH)
        self.assertEqual(json.dumps(atlas,sort_keys=True),before)


if __name__=='__main__':unittest.main()