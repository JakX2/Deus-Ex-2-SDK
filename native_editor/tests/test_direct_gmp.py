"""Fixture-free direct GMP cache safety tests."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / 'godot_editor' / 'backend'
sys.path.insert(0, str(BACKEND))
import dx2_native_backend as backend
from dx2_map_exporter import LevelChoice

class DirectGMPTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.maps = self.root / 'game' / 'Content' / 'DX2' / 'Maps'
        self.maps.mkdir(parents=True)
        self.game_map = self.maps / 'M1_Test_Penthouse.gmp'
        self.game_map.write_bytes(b'owned map fixture')
        self.ibd = self.maps / 'm1_test_penthouse.ibd'
        self.ibd.write_bytes(b'owned bundle fixture')
        self.output = self.root / 'cache'
        self.level = LevelChoice(self.game_map, self.ibd, (), 1.0)

    def test_rejects_wrong_extension(self):
        with self.assertRaises(ValueError):
            backend.map_inputs(self.ibd, [])

    def test_cache_kept_outside_game(self):
        with patch.object(backend, 'list_levels', return_value=[self.level]):
            with self.assertRaisesRegex(ValueError, 'outside the retail Maps'):
                backend.build(self.game_map, self.maps / 'unsafe_cache')

    def test_hash_changes_on_bundle_edit(self):
        old, _ = backend.get_cache_key(self.game_map, [self.ibd])
        self.ibd.write_bytes(b'changed bundle fixture')
        new, _ = backend.get_cache_key(self.game_map, [self.ibd])
        self.assertNotEqual(old, new)

    def test_generation_and_reuse(self):
        calls = []
        def exporter(level, output, manual=None, preview_club_stairs=False):
            calls.append(1)
            output.write_bytes(b'glTF' + b' ' * 96)
            return {'placed_real_mesh_actors': 1, 'missing_mesh_actors': [],
                    'actor_skin_selections': [{'actor':'StaticMeshActor__1',
                        'export': 7, 'mesh': 'SyntheticStair', 'requested': 'Tan Stones',
                        'selected': 'Tan Stones', 'status': 'matched',
                        'material_status': [{'name':'SyntheticTan',
                                             'resolution':'missing_diffuse_texture'}]}]}
        def actors(path, system):
            return ({'schema':'test'}, [{'name':'StaticMeshActor__1', 'class':'StaticMeshActor', 'export':7}])
        with patch.object(backend, 'list_levels', return_value=[self.level]), \
             patch.object(backend, 'run_export', side_effect=exporter), \
             patch.object(backend, 'actor_records', side_effect=actors), \
             patch.object(backend, 'catalog_from_paths', return_value={
                 'schema':'DX2Ed-asset-catalog-v1', 'assets':[
                     {'name':'SyntheticStair','kind':'staticmesh','bundle':'fixture.ibd',
                      'type_id':4,'resource_index':0,'bytes':123}] }):
            first = backend.build(self.game_map, self.output)
            second = backend.build(self.game_map, self.output)
            # Emulate an older private cache without the new class catalog.
            Path(first['archetypes_json']).unlink()
            third = backend.build(self.game_map, self.output)
        self.assertFalse(first['cached'])
        self.assertTrue(second['cached'])
        self.assertTrue(third['cached'])
        self.assertTrue(Path(third['archetypes_json']).is_file())
        class_doc = json.loads(Path(third['archetypes_json']).read_text())
        self.assertEqual(class_doc['schema'], 'DX2Ed-archetype-catalog-v1')
        self.assertEqual(class_doc['classes'][0]['class'], 'StaticMeshActor')
        self.assertEqual(class_doc['classes'][0]['observed_actors'], 1)
        self.assertFalse(class_doc['native_spawn_supported'])
        self.assertTrue(Path(first['assets_json']).is_file())
        self.assertEqual(json.loads(Path(first['assets_json']).read_text())['assets'][0]['name'],
                         'SyntheticStair')
        self.assertEqual(len(calls), 1)
        data = json.loads(Path(first['actors_json']).read_text())
        self.assertEqual(data['meta']['source_sha256'], hashlib.sha256(self.game_map.read_bytes()).hexdigest())
        self.assertEqual(self.ibd.read_bytes(), b'owned bundle fixture')
        skin = data['actors'][0]['render_skin']
        self.assertEqual(skin['selected'], 'Tan Stones')
        self.assertEqual(skin['materials'][0]['resolution'], 'missing_diffuse_texture')

    def test_scene_and_actor_metadata_stay_linked(self):
        script = (BACKEND.parent / 'main.gd').read_text(encoding='utf8')
        self.assertIn('Open DX2 map (.gmp)', script)
        self.assertIn('func open_gmp(', script)
        self.assertIn('load_glb(scene_path)', script)
        self.assertIn('func _backend_finished(', script)

if __name__ == '__main__':
    unittest.main()
