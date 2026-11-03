"""Asset-free tests for a source-observed DX2 Havok-MOPP-compatible Level tail."""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_level_mopp_triangle_tree as mopp


def fixture(*, code=b"\x28\x00\xff\x27\x00\xff\x26\x00\xff\x20\x80\x01\x30\x31",
            degenerate=False):
    if degenerate:
        coords = [(0.,0.,0.), (2.,0.,0.), (4.,0.,0.), (0.,2.,0.), (2.,2.,0.)]
        indices = (0,1,2,0,3,4)
    else:
        coords = [(0.,0.,0.), (2.,0.,0.), (2.,2.,0.), (0.,2.,0.)]
        indices = (0,1,2,0,2,3)
    nv, nt = len(coords), len(indices)//3
    blocks = [{"vertices": [(tuple(x/0.1905 for x in xyz),[0.,0.,1.],(0.,0.))
                           for xyz in coords],
               "sections": [{"indices": list(indices)}]}]
    header = bytes([255])*180 + struct.pack("<II6I", nv,nt,1,0,254,0,254,0) + b"Test\0"
    xyz = b"".join(struct.pack("<3fI",*v,0) for v in coords)
    triangles = struct.pack("<"+"I"*len(indices),*indices)
    mins = [min(v[i] for v in coords) for i in range(3)]
    maxs = [max(v[i] for v in coords) for i in range(3)]
    ext = max(maxs[i]-mins[i] for i in range(3))
    spatial = struct.pack("<4f",*(v-0.05 for v in mins),
                          254*65536/(ext+0.1))
    tail = struct.pack("<I",len(code)+20)+spatial+struct.pack("<I",len(code))+code+bytes(12)
    return header+xyz+triangles+tail, blocks


class LevelMoppTests(unittest.TestCase):
    def test_two_triangle_tree_and_spatial_scale(self):
        blob, blocks = fixture()
        report = mopp.inspect_mopp_link(blob, blocks)
        self.assertTrue(report["all_nondegenerate_triangle_ids_have_exactly_one_reachable_leaf"])
        self.assertEqual(report["unique_valid_mopp_triangle_leaves"],2)
        self.assertEqual(report["zero_area_triangle_count"],0)
        self.assertEqual(report["mopp_code_bytes"],14)
        self.assertLess(report["scale_relative_error"],1e-5)
        self.assertFalse(report["runtime_Havok_shape_instantiated"])

    def test_excluded_zero_area_triangle_is_allowed(self):
        blob,blocks = fixture(code=b"\x28\x00\xff\x31",degenerate=True)
        report=mopp.inspect_mopp_link(blob,blocks)
        self.assertEqual(report["omitted_zero_area_triangle_ids"],[0])
        self.assertEqual(report["unique_valid_mopp_triangle_leaves"],1)

    def test_unaccounted_nondegenerate_triangle_rejected(self):
        blob,blocks = fixture(code=b"\x28\x00\xff\x30")
        with self.assertRaisesRegex(ValueError,"coverage"):
            mopp.inspect_mopp_link(blob,blocks)

    def test_duplicate_leaf_ids_rejected(self):
        blob,blocks = fixture(code=b"\x28\x00\xff\x20\x80\x01\x30\x30")
        with self.assertRaisesRegex(ValueError,"Repeated terminal"):
            mopp.inspect_mopp_link(blob,blocks)

    def test_unknown_opcode_rejected(self):
        blob,blocks = fixture(code=b"\x28\x00\xff\xff")
        with self.assertRaisesRegex(ValueError,"Unknown reachable"):
            mopp.inspect_mopp_link(blob,blocks)

    def test_jump_outside_stream_rejected(self):
        blob,blocks = fixture(code=b"\x28\x00\xff\x05\xff\x30")
        with self.assertRaisesRegex(ValueError,"jump target"):
            mopp.inspect_mopp_link(blob,blocks)

    def test_truncated_operand_rejected(self):
        blob,blocks = fixture(code=b"\x28\x00\xff\x51")
        with self.assertRaisesRegex(ValueError,"Truncated"):
            mopp.inspect_mopp_link(blob,blocks)

    def test_bad_outer_and_inner_lengths_and_footer_rejected(self):
        blob,blocks = fixture()
        prefix = len(blob)-(14+36)
        for offset in (0,20):
            bad=bytearray(blob)
            struct.pack_into("<I",bad,prefix+offset,0xffffffff)
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError,"envelope"):
                mopp.inspect_mopp_link(bytes(bad),blocks)
        bad=blob[:-1]+b"\x01"
        with self.assertRaisesRegex(ValueError,"envelope"):
            mopp.inspect_mopp_link(bad,blocks)

    def test_invalid_origin_and_scale_rejected(self):
        blob,blocks = fixture()
        prefix = len(blob)-(14+36)
        for component in (0,3):
            bad=bytearray(blob)
            struct.pack_into("<f",bad,prefix+4+4*component,1000.)
            with self.subTest(component=component), self.assertRaisesRegex(ValueError,"spatial"):
                mopp.inspect_mopp_link(bytes(bad),blocks)

    def test_out_of_range_leaf_id_rejected(self):
        blob,blocks = fixture(code=b"\x28\x00\xff\x51\x03\xe8")
        with self.assertRaisesRegex(ValueError,"out of flattened geometry range"):
            mopp.inspect_mopp_link(blob,blocks)

    def test_output_base_and_16bit_split_grammar(self):
        # Filter; 8-bit base+0, then immediate leaf 0 and child leaf 1.
        code=b"\x28\x00\xff\x23\x80\x80\x00\x00\x00\x01\x30\x31"
        trace=mopp.trace_mopp_code(code,2)
        self.assertEqual(trace["reachable_terminal_triangle_ids"],[0,1])
        self.assertEqual(mopp.trace_mopp_code(b"\x28\x00\xff\x09\x01\x30",2)["reachable_terminal_triangle_ids"],[1])
        self.assertEqual(mopp.trace_mopp_code(b"\x28\x00\xff\x0b\x00\x00\x00\x01\x30",2)["reachable_terminal_triangle_ids"],[1])

    def test_original_bytes_untouched_and_paths_checked(self):
        blob,blocks=fixture()
        digest=hashlib.sha256(blob).digest()
        mopp.inspect_mopp_link(blob,blocks)
        self.assertEqual(hashlib.sha256(blob).digest(),digest)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"fake.gmp"
            p.write_bytes(blob)
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                mopp.audit_maps([p,p])


if __name__ == "__main__":
    unittest.main()
