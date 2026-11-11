import hashlib
import struct
import unittest
from unittest.mock import patch

from dx2sdk.bsp_plane_bytes import inspect_plane_bytes


def fixture():
    # Synthetic envelope: only the parser's boundary assertion is mocked.
    payload = bytearray(160)
    payload[52:68] = struct.pack("<4f", 1., 0., 0., 0.)
    return b"prefix!" + bytes(payload) + b"suffix!"

FRAME = {"node_records": [{"start": 52, "length": 109}]}


class OriginalPlaneByteProvenanceTests(unittest.TestCase):
    def test_exact_offsets_and_immutable_original(self):
        raw = fixture()
        with patch("dx2sdk.bsp_plane_bytes.parse_world_model", return_value=FRAME):
            result = inspect_plane_bytes(raw, export_offset=7, export_size=160,
                                         node_start=52, replacement=(1, 0, 0, 4))
        self.assertEqual(result["original_plane_absolute_offset"], 59)
        self.assertEqual(result["source_package_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["original_plane_sha256"],
                         hashlib.sha256(raw[59:75]).hexdigest())
        self.assertEqual(result["changed_byte_offsets_relative_to_plane"], [14, 15])
        self.assertTrue(result["original_bytes_unchanged"])
        self.assertFalse(result["native_writer_enabled"])
        self.assertEqual(raw, fixture())

    def test_refuse_forged_or_non_node_offsets(self):
        raw = fixture()
        with patch("dx2sdk.bsp_plane_bytes.parse_world_model", return_value=FRAME):
            for kw in [
                {"export_offset": -1, "export_size": 160, "node_start": 52},
                {"export_offset": 7, "export_size": 999, "node_start": 52},
                {"export_offset": 7, "export_size": 160, "node_start": 53},
                {"export_offset": 7, "export_size": 160, "node_start": True},
                {"export_offset": 7, "export_size": 160, "node_start": 52},
            ]:
                with self.subTest(kw=kw), self.assertRaises(ValueError):
                    inspect_plane_bytes(raw, replacement=(1, 0, 0, 0)
                                        if kw["node_start"] == 52 and kw["export_offset"] == 7
                                        else (1, 0, 0, 4), **kw)
            with self.assertRaises(ValueError):
                inspect_plane_bytes(raw, export_offset=7, export_size=160,
                                    node_start=52, replacement=(2, 0, 0, 4))

if __name__ == "__main__":
    unittest.main()
