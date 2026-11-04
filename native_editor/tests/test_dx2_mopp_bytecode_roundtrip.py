"""Asset-free DX2 MOPP source-instruction no-op roundtrip tests."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"research"/"dx2"))
from test_dx2_level_mopp_triangle_tree import fixture
import inspect_mopp_bytecode_roundtrip as rt


class MoppByteExactRoundtripTests(unittest.TestCase):
    def test_source_root_conditional_and_two_leaves_all_bytes_covered(self):
        blob, blocks = fixture()
        out = rt.inspect_level_envelope(blob, blocks)
        self.assertEqual(out["code_length_bytes"], 14)
        self.assertTrue(out["envelope_byte_identical"])
        self.assertTrue(out["code_byte_identical"])
        self.assertEqual(out["reachable_triangle_leaves"], 2)
        self.assertEqual(out["reachable_instruction_bytes"], 14)
        self.assertEqual(out["unvisited_bytes_preserved_opaque"], 0)
        self.assertFalse(out["collision_writer_implemented"])
        self.assertFalse(out["mopp_spatial_f32_bits_recomputed"])

    def test_degenerate_nonleaf_allowed_with_identity(self):
        blob, blocks = fixture(code=b"\x28\x00\xff\x31", degenerate=True)
        out = rt.inspect_level_envelope(blob, blocks)
        self.assertEqual(out["reachable_triangle_leaves"], 1)
        self.assertEqual(out["code_length_bytes"], 4)

    def test_observed_big_endian_operand_widths_are_lossless(self):
        samples = [
            (b"\x28\x00\xff\x09\x01\x30", 2),
            (b"\x28\x00\xff\x0a\x00\x01\x30", 2),
            (b"\x28\x00\xff\x0b\x00\x00\x00\x01\x30", 2),
            (b"\x28\x00\xff\x23\x80\x80\x00\x00\x00\x01\x30\x31", 2),
            (b"\x28\x00\xff\x05\x00\x30", 1),
            (b"\x28\x00\xff\x06\x00\x00\x30", 1),
            (b"\x28\x00\xff\x51\x00\x00", 1),
            (b"\x28\x00\xff\x50\x00", 1),
            (b"\x28\x00\xff\x0b\x00\x00\x00\x00\x52\x00\x00\x00", 1),
        ]
        for code, count in samples:
            with self.subTest(opcodes=code.hex()):
                result = rt.inspect_code_roundtrip(code, count)
                self.assertTrue(result["code_byte_identical"])
                self.assertEqual(result["code_sha256"], hashlib.sha256(code).hexdigest())

    def test_preserve_unvisited_opaque_byte_with_explicit_gap(self):
        code = b"\x28\x00\xff\x05\x01\xfe\x30"
        result = rt.inspect_code_roundtrip(code, 1)
        self.assertEqual(result["unvisited_bytes_preserved_opaque"], 1)
        self.assertEqual(result["first_unvisited_spans"], [{"start":5, "end":6}])
        self.assertTrue(result["code_byte_identical"])

    def test_reachable_overlapping_instruction_spans_refused(self):
        code = b"\x28\x00\xff\x20\x80\x01\x01\x30\x00\x00\x31"
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            rt.inspect_code_roundtrip(code, 2)

    def test_unknown_opcode_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Unknown reachable"):
            rt.inspect_code_roundtrip(b"\x28\x00\xff\xee", 1)

    def test_invalid_reachable_jump_refused(self):
        with self.assertRaisesRegex(ValueError, "jump"):
            rt.inspect_code_roundtrip(b"\x28\x00\xff\x05\xff\x30", 1)

    def test_repeated_terminal_triangle_refused(self):
        with self.assertRaisesRegex(ValueError, "Repeated"):
            rt.inspect_code_roundtrip(b"\x28\x00\xff\x20\x80\x01\x30\x30", 1)

    def test_bad_spatial_header_refused(self):
        blob, blocks = fixture()
        bad = bytearray(blob)
        start = len(blob)-(14+36)
        struct.pack_into("<f", bad, start+4, 1000.)
        with self.assertRaisesRegex(ValueError, "spatial"):
            rt.inspect_level_envelope(bytes(bad), blocks)

    def test_bad_envelope_length_and_trailer_refused(self):
        blob, blocks = fixture()
        bad = bytearray(blob)
        start = len(blob)-(14+36)
        struct.pack_into("<I", bad, start+20, 15)
        with self.assertRaisesRegex(ValueError, "envelope"):
            rt.inspect_level_envelope(bytes(bad), blocks)
        with self.assertRaisesRegex(ValueError, "envelope"):
            rt.inspect_level_envelope(blob[:-1]+b"\x01", blocks)

    def test_unrecognized_extra_level_suffix_refused(self):
        blob, blocks = fixture()
        with self.assertRaises(ValueError):
            rt.inspect_level_envelope(blob+b"synthetic extra tail", blocks)

    def test_source_unchanged_by_inspection(self):
        blob, blocks = fixture()
        sha = hashlib.sha256(blob).hexdigest()
        rt.inspect_level_envelope(blob, blocks)
        self.assertEqual(hashlib.sha256(blob).hexdigest(), sha)

    def test_repeated_source_paths_refused_before_reader(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"fixture.gmp"
            path.write_bytes(b"synthetic")
            self.assertEqual(rt.main([str(path),str(path)]), 1)
            self.assertEqual(path.read_bytes(), b"synthetic")


if __name__ == "__main__":
    unittest.main()
