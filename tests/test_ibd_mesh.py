"""Fixture-free resource/GLB tests for the original read-only DX2 inspector."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "maps"))
from dx2bundles import Bundle, Mesh, glb_mesh
from test_ibd_probe import example_bundle


class BundleMeshTests(unittest.TestCase):
    def test_resource_table_from_synthetic_ibd(self):
        b = Bundle('test.ibd', example_bundle())
        r = b.find('TS_TEST', 21)
        self.assertIsNotNone(r)
        self.assertEqual(r.kind, 'triggerscriptdef')
        self.assertEqual(list(b.parts(r)), [b'abcd', b'efgh'])
        self.assertEqual(b.raw(r), b'abcdefgh')

    def test_rejects_bad_partitions(self):
        with self.assertRaisesRegex(ValueError, 'invalid size/part layout'):
            Bundle('bad.ibd', example_bundle(broken_part=True))

    def test_glb_header_with_synthetic_triangle(self):
        m = Mesh('synthetic', [{'materials': ['test_material']}], 0, [],
                 [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
                 [(0, 0, 1)] * 3,
                 [(0, 0), (1, 0), (0, 1)], [0, 1, 2],
                 [{'name': 'tri', 'first_index': 0, 'index_count': 3}],
                 [0, 0, 0, 1, 1, 0])
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'triangle.glb'
            glb_mesh(m, path)
            content = path.read_bytes()
        magic, version, size = struct.unpack_from('<III', content)
        self.assertEqual((magic, version, size), (0x46546C67, 2, len(content)))
        json_length, kind = struct.unpack_from('<II', content, 12)
        self.assertEqual(kind, 0x4E4F534A)
        doc = json.loads(content[20:20 + json_length])
        self.assertEqual(doc['meshes'][0]['name'], 'synthetic')
        self.assertEqual(doc['materials'][0]['name'], 'test_material')


if __name__ == '__main__':
    unittest.main()
