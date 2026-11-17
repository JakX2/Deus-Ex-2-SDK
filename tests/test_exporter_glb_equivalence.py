"""Asset-free checks for exporter stack GLB byte and pixel equivalence.

These tests use minimal source-only GLB fixtures. No retail maps or assets are
bundled, loaded or modified by GitHub CI.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'map_exporter'))

from verify_dx2_glb_equivalence import verify, _png_rgba
from dx2textures import png_bytes


def synthetic_glb(pixels, png_level=7, geometry=b'abcdefg', note='same'):
    compressed = png_bytes(9, 7, pixels, png_level)
    offset = (len(compressed) + 3) // 4 * 4
    binary = compressed + b'\0' * (offset - len(compressed)) + geometry
    binary += b'\0' * (-len(binary) % 4)
    doc = {
        'asset': {'version': '2.0'},
        'scene': 0,
        'scenes': [{'name': note}],
        'buffers': [{'byteLength': len(binary)}],
        'images': [{'mimeType': 'image/png', 'bufferView': 0}],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': 0,
             'byteLength': len(compressed)},
            {'buffer': 0, 'byteOffset': offset,
             'byteLength': len(geometry)},
        ],
    }
    json_chunk = json.dumps(doc, separators=(',', ':')).encode('utf-8')
    json_chunk += b' ' * (-len(json_chunk) % 4)
    total = 12 + 8 + len(json_chunk) + 8 + len(binary)
    return (
        struct.pack('<4sII', b'glTF', 2, total)
        + struct.pack('<I4s', len(json_chunk), b'JSON') + json_chunk
        + struct.pack('<I4s', len(binary), b'BIN\x00') + binary
    )


class GLBEquivalenceTests(unittest.TestCase):
    def test_identical_default_and_lossless_png_preset(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Path(directory) / 'original.glb'
            b = Path(directory) / 'fast.glb'
            pixels = bytes(x % 256 for x in range(9 * 7 * 4))
            a.write_bytes(synthetic_glb(pixels, 7))
            b.write_bytes(synthetic_glb(pixels, 1))
            before = (a.read_bytes(), b.read_bytes())
            self.assertNotEqual(*before)
            exact = verify(a, a, 'exact')
            self.assertTrue(exact['equivalent'])
            self.assertTrue(exact['byte_identical'])
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                verify(a, b, 'exact')
            decoded = verify(a, b, 'decoded-png')
            self.assertTrue(decoded['equivalent'])
            self.assertFalse(decoded['byte_identical'])
            self.assertEqual(decoded['embedded_images_checked'], 1)
            self.assertEqual(decoded['nonimage_views_checked'], 1)
            self.assertEqual((a.read_bytes(), b.read_bytes()), before)

    def test_pixels_geometry_and_scene_metadata_cannot_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Path(directory) / 'original.glb'
            b = Path(directory) / 'modified.glb'
            pixels = bytes(x % 256 for x in range(9 * 7 * 4))
            a.write_bytes(synthetic_glb(pixels, 7))
            modifications = (
                synthetic_glb(pixels[:-1] + b'\0', 1),
                synthetic_glb(pixels, 1, geometry=b'xxxxxxx'),
                synthetic_glb(pixels, 1, note='changed'),
            )
            for changed in modifications:
                with self.subTest(case=changed[-12:]):
                    b.write_bytes(changed)
                    with self.assertRaisesRegex(ValueError, 'differ'):
                        verify(a, b, 'decoded-png')

    def test_reject_bad_glb_and_corrupted_png_crc(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Path(directory) / 'a.glb'
            b = Path(directory) / 'b.glb'
            pixels = bytes([42]) * (9 * 7 * 4)
            a.write_bytes(synthetic_glb(pixels, 7))
            b.write_bytes(b'not a GLB')
            with self.assertRaises(ValueError):
                verify(a, b, 'decoded-png')
            corrupt = bytearray(png_bytes(3, 5, bytes([42])*60, 1))
            corrupt[-17] ^= 1
            with self.assertRaisesRegex(ValueError, 'CRC'):
                _png_rgba(bytes(corrupt))
            with self.assertRaisesRegex(ValueError, 'must exist'):
                verify(a, Path(directory)/'missing.glb', 'exact')
            with self.assertRaisesRegex(ValueError, 'mode'):
                verify(a, a, 'unsupported')

    def test_partial_and_unusual_sizes(self):
        for w, h in ((1,1), (3,5), (9,7), (33,15)):
            raw = bytes((i * 19) % 256 for i in range(w*h*4))
            with self.subTest(size=(w, h)):
                self.assertEqual(_png_rgba(png_bytes(w,h,raw,1)),
                                 _png_rgba(png_bytes(w,h,raw,7)))
                self.assertEqual(_png_rgba(png_bytes(w,h,raw,1)),
                                 (w,h,raw))


if __name__ == '__main__':
    unittest.main()
