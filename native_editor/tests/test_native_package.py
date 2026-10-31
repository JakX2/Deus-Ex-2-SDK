import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class NativeEditorTests(unittest.TestCase):
    def test_scene_and_actor_count(self):
        p = ROOT/'godot_editor'/'demo'/'scene.glb'
        blob = p.read_bytes()
        self.assertEqual(blob[:4], b'glTF')
        version, length = struct.unpack_from('<II', blob, 4)
        self.assertEqual(version, 2)
        self.assertEqual(length, len(blob))
        size, chunk_type = struct.unpack_from('<II', blob, 12)
        self.assertEqual(chunk_type, 0x4e4f534a)
        doc = json.loads(blob[20:20+size])
        self.assertEqual(len(doc['nodes']), 2)
        self.assertEqual([n['name'] for n in doc['nodes']],
                         ['StaticMeshActor__1', 'StaticMeshActor__2'])
        actors = json.loads((p.parent/'actors.json').read_text())['actors']
        self.assertEqual({a['name'] for a in actors}, {n['name'] for n in doc['nodes']})

    def test_scene_ships_with_no_game_data(self):
        for p in (ROOT/'godot_editor').rglob('*'):
            if p.is_file():
                self.assertNotIn(p.suffix.lower(), ('.gmp', '.ibd', '.d2u', '.tsd'))

    def test_project_points_to_real_scene_script(self):
        self.assertIn('res://main.tscn', (ROOT/'godot_editor'/'project.godot').read_text())
        self.assertIn('res://main.gd', (ROOT/'godot_editor'/'main.tscn').read_text())
        source=(ROOT/'godot_editor'/'main.gd').read_text()
        self.assertIn('GLTFDocument.new()', source)
        self.assertIn('append_from_file', source)
        self.assertIn('frame_whole_scene', source)
        self.assertIn('load_actors', source)

if __name__ == '__main__':
    unittest.main()
