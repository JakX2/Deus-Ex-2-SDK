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
            return {'placed_real_mesh_actors': 1, 'missing_mesh_actors': []}
        def actors(path, system):
            return ({'schema':'test'}, [{'name':'StaticMeshActor__1', 'class':'StaticMeshActor'}])
        with patch.object(backend, 'list_levels', return_value=[self.level]), \
             patch.object(backend, 'run_export', side_effect=exporter), \
             patch.object(backend, 'actor_records', side_effect=actors):
            first = backend.build(self.game_map, self.output)
            second = backend.build(self.game_map, self.output)
        self.assertFalse(first['cached'])
        self.assertTrue(second['cached'])
        self.assertEqual(len(calls), 1)
        data = json.loads(Path(first['actors_json']).read_text())
        self.assertEqual(data['meta']['source_sha256'], hashlib.sha256(self.game_map.read_bytes()).hexdigest())
        self.assertEqual(self.ibd.read_bytes(), b'owned bundle fixture')

    def test_scene_and_actor_metadata_stay_linked(self):
        script = (BACKEND.parent / 'main.gd').read_text(encoding='utf8')
        self.assertIn('Open DX2 map (.gmp)', script)
        self.assertIn('func open_gmp(', script)
        self.assertIn('load_glb(scene_path)', script)
        self.assertIn('func _backend_finished(', script)

if __name__ == '__main__':
    unittest.main()
