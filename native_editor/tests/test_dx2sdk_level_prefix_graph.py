"""Synthetic Level prefix graph layout and redundant ownership gates."""
import struct
import unittest
from inspect_level_prefix_graph import parse_prefix_graph


def fixture(width=30):
    tri=lambda xyz:struct.pack("<I13fB",3,*xyz,0.,0.,1.,146.,0)
    return (bytes(width)+struct.pack("<I",2)
            +tri((0.,0.,0.,2.,0.,0.,0.,2.,0.))
            +tri((2.,0.,0.,2.,2.,0.,0.,2.,0.))
            +struct.pack("<I",1)
            +struct.pack("<B6f8s",0,1.5,.5,0.,.5,1.5,0.,bytes(8))
            +struct.pack("<6I",1,0,1,0,1,0)+b"opaque")


class PrefixGraphTests(unittest.TestCase):
    def test_both_source_header_widths_and_exact_roundtrip(self):
        for width in (30,31):
            data=fixture(width)
            result=parse_prefix_graph(data,0,len(data))
            self.assertEqual(result["zero_header_bytes"],width)
            self.assertTrue(result["source_graph_noop_byte_identical"])
            self.assertEqual(result["counts"]["prefix_graph_triangle_count"],2)
            self.assertEqual(result["counts"]["prefix_graph_triangle_edge_references"],2)
            self.assertEqual(result["counts"]["prefix_graph_edge_owner_pairs_verified"],1)
            self.assertEqual(result["counts"]["prefix_graph_edge_both_owner_planes_near"],1)
            self.assertEqual(result["counts"]["prefix_graph_opaque_following_bytes"],6)
            self.assertFalse(result["native_graph_write_allowed"])

    def test_refuse_corrupt_owner_pair_or_duplicate_ref(self):
        data=bytearray(fixture())
        struct.pack_into("<I",data,len(data)-6-4,1)
        with self.assertRaises(ValueError):
            parse_prefix_graph(bytes(data),0,len(data))
        data=bytearray(fixture())
        struct.pack_into("<I",data,len(data)-6-8-4,3)
        with self.assertRaises(ValueError):
            parse_prefix_graph(bytes(data),0,len(data))

    def test_refuse_truncated_source_graph(self):
        data=fixture()
        with self.assertRaises(ValueError):
            parse_prefix_graph(data,0,len(data)-12)


if __name__=="__main__":
    unittest.main()
