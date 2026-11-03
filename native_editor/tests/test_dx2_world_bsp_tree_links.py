"""Fixture-only, no retail assets: DX2 BSP eight-compact-field tree regression."""
from __future__ import annotations

import struct
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_world_bsp_tree_links as topology


def compact(value):
    if value == -1:
        return b"\x81"
    if not 0 <= value < 8192:
        raise ValueError("Unsupported synthetic compact value")
    return bytes([value]) if value < 64 else bytes([0x40 | (value & 63), value >> 6])


def node(links, plane=(1.,0.,0.,0.), center=(0.,0.,0.)):
    assert len(links) == 8
    prefix = struct.pack("<4f",*plane) + bytes(32)
    mids = b"".join(compact(v) for v in links)
    sphere = struct.pack("<4f",*center,4.)
    suffix = bytes(20) + b"\x04" + struct.pack("<iiII",-1,-1,0,0)
    return prefix + mids + sphere + suffix


def fake_model(rows):
    head = bytes(50) + bytes([len(rows)])
    starts = []
    data = bytearray(head)
    for vals, plane, center in rows:
        raw = node(vals, plane, center)
        starts.append({"start":len(data),"length":len(raw)})
        data.extend(raw)
    data.extend(struct.pack("<I",1) + bytes(69) + bytes(8))
    return bytes(data), {"candidate_node_count":len(rows),"node_records":starts}


def default_rows():
    return [
        ([0,0,0,1,2,3,-1,-1],(1.,0.,0.,0.),(0.,0.,0.)),
        ([0,128,0,-1,-1,-1,-1,-1],(0.,1.,0.,0.),(-2.,0.,0.)),
        ([0,0,0,-1,-1,-1,-1,-1],(0.,0.,1.,0.),(2.,0.,0.)),
        ([0,0,0,-1,-1,-1,-1,-1],(-1.,0.,0.,0.),(0.,0.,0.)),
    ]


class EightCompactTreeTests(unittest.TestCase):
    def test_rooted_tree_plane_sides_and_coplanar_chain(self):
        raw, frame = fake_model(default_rows())
        result = topology.inspect_link_graph(raw,frame,include_edges=True)
        self.assertEqual(result["status"],"validated_rooted_eight-compact-link_graph")
        self.assertEqual(result["edges"],3)
        self.assertEqual(result["max_depth"],1)
        self.assertEqual(result["compact_integers_per_node"],8)
        self.assertEqual(result["edges_by_column"],{"3":1,"4":1,"5":1})
        self.assertEqual(result["plane_side_evidence"],
                         {"field3_expected_side":1,"field4_expected_side":1})
        self.assertEqual(result["coplanar_chain_evidence"],
                         {"opposite_oriented_plane":1})
        self.assertEqual({(e["parent"],e["child"]) for e in result["graph_edges"]},
                         {(0,1),(0,2),(0,3)})
        self.assertEqual(frame["node_records"][1]["length"],110)

    def test_refuses_duplicate_parent_link(self):
        rows = default_rows()
        rows[0][0][4] = 1
        raw, frame = fake_model(rows)
        with self.assertRaisesRegex(ValueError,"unique-parent"):
            topology.inspect_link_graph(raw,frame)

    def test_refuses_self_and_out_of_range_reference(self):
        for value in (0,4):
            rows = default_rows()
            rows[0][0][3] = value
            raw, frame = fake_model(rows)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError,"invalid linked index"):
                topology.inspect_link_graph(raw,frame)

    def test_refuses_detached_cycle(self):
        rows = default_rows()
        rows[0][0][4] = -1
        rows[0][0][5] = -1
        rows[2][0][3] = 3
        rows[3][0][3] = 2
        raw, frame = fake_model(rows)
        with self.assertRaisesRegex(ValueError,"cannot reach all nodes"):
            topology.inspect_link_graph(raw,frame)

    def test_refuses_incorrect_compact_count_or_alignment(self):
        rows = default_rows()
        raw, frame = fake_model(rows)
        tampered = bytearray(raw)
        # This changes the first byte of compact field 0 to an unsupported flag.
        tampered[frame["node_records"][0]["start"]+48] = 7
        with self.assertRaisesRegex(ValueError,"field zero"):
            topology.inspect_link_graph(bytes(tampered),frame)
        frame_bad = {**frame, "node_records":list(frame["node_records"])}
        frame_bad["node_records"][0] = {"start":frame["node_records"][0]["start"],"length":108}
        with self.assertRaisesRegex(ValueError,"unsupported record framing"):
            topology.inspect_link_graph(raw,frame_bad)

    def test_coplanar_precision_exception_is_counted_not_erased(self):
        rows = default_rows()
        rows[3] = (rows[3][0], (0.,1.,0.,2.),rows[3][2])
        raw, frame = fake_model(rows)
        r = topology.inspect_link_graph(raw,frame)
        self.assertEqual(r["coplanar_chain_evidence"]["different_plane"],1)
        self.assertTrue(r["all_nodes_reachable"])

    def test_invalid_full_frame_count_rejected(self):
        raw, frame = fake_model(default_rows())
        for invalid in ({**frame,"candidate_node_count":3},
                        {**frame,"node_records":[]},
                        {**frame,"candidate_node_count":None}):
            with self.assertRaises(ValueError):
                topology.inspect_link_graph(raw,invalid)

    def test_aggregate_and_no_writer_flags(self):
        with tempfile.TemporaryDirectory() as dirname:
            src = Path(dirname)/"synthetic.gmp"
            src.write_bytes(b"source left unchanged")
            raw, frame = fake_model(default_rows())
            result = topology.inspect_link_graph(raw,frame)
            with patch.object(topology,"audit_map",
                              return_value={"file":"synthetic.gmp","licensee":68,**result}):
                report = topology.audit_maps([src])
                self.assertEqual(report["summary"]["nodes"],4)
                self.assertEqual(report["summary"]["edges"],3)
                self.assertEqual(report["summary"]["field3_expected_side"],1)
                self.assertFalse(report["native_gmp_written"])
                self.assertFalse(report["collision_generated"])
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                topology.audit_maps([src,src])
            self.assertEqual(src.read_bytes(),b"source left unchanged")


if __name__=="__main__":
    unittest.main()
