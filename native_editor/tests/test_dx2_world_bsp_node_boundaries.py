"""Synthetic, asset-free tests for observed DX2 world BSP node array boundaries."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_world_bsp_node_boundaries as audit


def compact(n: int) -> bytes:
    assert 0 <= n < 8192
    return bytes([n]) if n <= 63 else bytes([0x40 | (n & 0x3f), n >> 6])


def make_node(nbytes=112, *, first_ref=-1, second_ref=-1,
              normal=(1.0, 0.0, 0.0), w=16.0, zero_word=0):
    assert 109 <= nbytes <= 116
    b = bytearray(nbytes)
    struct.pack_into("<4f", b, 0, *normal, w)
    b[16] = 0x04  # nonzero observed mask byte, unknown semantics
    struct.pack_into("<iiII", b, nbytes-16,
                     first_ref, second_ref, zero_word, 40)
    return bytes(b)


def model(nodes=None, zone_count=3, *, invalid_box=False, tail=b"\0"*8):
    nodes = nodes if nodes is not None else [
        make_node(109), make_node(112,first_ref=1,second_ref=-1),
        make_node(116)]
    header = bytearray(50)
    header[33] = int(invalid_box)
    return (bytes(header) + compact(len(nodes)) + b"".join(nodes) +
            struct.pack("<I", zone_count) + b"\0"*(69*zone_count) + tail)


class FakePackage:
    def __init__(self, source: Path, payload: bytes):
        self.data = source.read_bytes()
        self.version = 95
        self.licensee = 68
        self.exports = [{"index": 1, "name": "Model__World", "size": len(payload)}]
        self.source_model = payload

    def payload(self, exp):
        return self.source_model

    def class_name(self, exp):
        return "Model"


class WorldNodeBoundariesTests(unittest.TestCase):
    def test_variable_size_nodes_and_zone_array_exact_end(self):
        raw = model()
        result = audit.parse_world_model(raw,include_nodes=True)
        self.assertEqual(result["status"],"observed_node_and_zone_array_boundaries")
        self.assertEqual(result["candidate_node_count"],3)
        self.assertEqual(result["candidate_node_count_width"],1)
        self.assertEqual(result["node_record_lengths"],{"109":1,"112":1,"116":1})
        self.assertEqual(result["node_array_start"],51)
        self.assertEqual(result["node_array_end"],51+109+112+116)
        self.assertEqual([x["start"] for x in result["node_records"]],
                         [51,160,272])
        self.assertEqual(result["candidate_zone_count"],3)
        self.assertEqual(result["candidate_zone_array_bytes"],207)
        self.assertTrue(result["everything_in_model_payload_accounted_for"])
        self.assertEqual(result["suffix_pair_kinds"],{"none/none":2,"ref/none":1})
        self.assertEqual(result["nodes_with_nonzero_32byte_mask"],3)
        json.dumps(result,allow_nan=False)

    def test_compact_two_byte_count_and_up_to_116_byte_width(self):
        nodes = [make_node(110)]*64
        result = audit.parse_world_model(model(nodes,zone_count=19))
        self.assertEqual(result["candidate_node_count_width"],2)
        self.assertEqual(result["candidate_node_count"],64)
        self.assertEqual(result["node_record_lengths"],{"110":64})
        self.assertEqual(result["candidate_zone_count"],19)

    def test_bad_normal_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"Bad candidate plane"):
            audit.parse_world_model(model([make_node(normal=(0,0,0))]))
        with self.assertRaisesRegex(ValueError,"Bad candidate plane"):
            audit.parse_world_model(model([make_node(normal=(float("nan"),0,0))]))

    def test_corrupted_bounded_suffix_fails_closed(self):
        cases = [
            model([make_node(first_ref=7)]),
            model([make_node(zero_word=1)]),
            model([make_node(first_ref=0)]), # terminal requires -1/-1
        ]
        for data in cases:
            with self.subTest(data=data[51:67].hex()),self.assertRaisesRegex(
                    ValueError,"Ambiguous/unrecognized node boundary"):
                audit.parse_world_model(data)

    def test_zone_extent_and_trailer_refused(self):
        for data in [
            model(zone_count=3,tail=b"\0"*7),
            model(zone_count=3,tail=b"\0"*7+b"\x01"),
            model(zone_count=0),
        ]:
            with self.subTest(length=len(data)),self.assertRaisesRegex(
                    ValueError,"Ambiguous/unrecognized node boundary"):
                audit.parse_world_model(data)

    def test_nonempty_bounds_and_count_rejected(self):
        with self.assertRaisesRegex(ValueError,"empty-bound"):
            audit.parse_world_model(model(invalid_box=True))
        with self.assertRaisesRegex(ValueError,"count unsupported"):
            audit.parse_world_model(model(nodes=[]))
        with self.assertRaisesRegex(ValueError,"too short"):
            audit.parse_world_model(b"\0"*20)

    def test_synthetic_package_integration_and_no_writes(self):
        with tempfile.TemporaryDirectory() as root_str:
            root = Path(root_str)
            source = root/"Maps"/"Test.gmp"
            source.parent.mkdir()
            source.write_bytes(b"private synthetic map bytes")
            fake = FakePackage(source,model())
            with patch.object(audit.world,"Package",return_value=fake), \
                 patch.object(audit.world,"_parse_world_model",
                              return_value={"world_model_export_ref":1}):
                result = audit.audit_maps([source])
            self.assertEqual(result["schema"],audit.SCHEMA)
            self.assertEqual(result["summary"]["nodes"],3)
            self.assertEqual(result["summary"]["candidate_zone_records"],3)
            self.assertFalse(result["native_bsp_node_semantics_complete"])
            self.assertFalse(result["new_native_map_written"])
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                audit.audit_maps([source,source])
            with self.assertRaisesRegex(ValueError,"outside original"):
                audit.world.write_report(result,source.parent/"report.json",[source])
            dest=root/"Reports"/"world_bsp.json"
            audit.world.write_report(result,dest,[source])
            self.assertEqual(json.loads(dest.read_text())["schema"],audit.SCHEMA)
            with self.assertRaises(FileExistsError):
                audit.world.write_report(result,dest,[source])
            self.assertEqual(source.read_bytes(),b"private synthetic map bytes")

    def test_wrong_licensee_and_wrong_model_class_rejected(self):
        with tempfile.TemporaryDirectory() as root_str:
            root=Path(root_str)
            source=root/"Test.gmp"
            source.write_bytes(b"fixture")
            fake=FakePackage(source,model())
            with patch.object(audit.world,"Package",return_value=fake), \
                 patch.object(audit.world,"_parse_world_model",
                              return_value={"world_model_export_ref":1}):
                fake.licensee=133
                with self.assertRaisesRegex(ValueError,"UE95 DX2"):
                    audit.audit_map(source)
                fake.licensee=68
                with patch.object(fake,"class_name",return_value="Brush"):
                    with self.assertRaisesRegex(ValueError,"not a Model"):
                        audit.audit_map(source)


if __name__ == "__main__":
    unittest.main()
