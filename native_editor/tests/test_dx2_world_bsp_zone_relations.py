"""Asset-free tests for DX2 node zone-mask OR and 69-byte symmetric zone table."""
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
import inspect_world_bsp_zone_relations as zones


def node(*, links=(-1,-1,-1), za=0, zb=1, mask=2, vertex_count=4,
         plane=(1.,0.,0.,0.)):
    """One 109-byte source-observed node with eight compact one-byte ints."""
    compact = [0,1,2,*links,-1,-1]
    assert len(compact) == 8
    assert all(-1 <= x < 64 for x in compact)
    # Unreal signed compact -1 => 0x81, positive <64 => literal byte.
    fields = bytes((0x81 if i == -1 else i) for i in compact)
    body = (struct.pack("<4f",*plane) + mask.to_bytes(32, "little") + fields
            + struct.pack("<4f",0.,0.,0.,4.) + bytes(16)
            + struct.pack("<HHB",za,zb,vertex_count)
            + struct.pack("<iiII",-1,-1,0,0))
    assert len(body) == 109
    return body


def zone_row(bits, *, leading=0, second=None, tail=b"\0"*4):
    return (bytes([leading]) + bits.to_bytes(32, "little")
            + (bytes([1])*32 if second is None else second) + tail)


def synthetic_world(*, node_records=None, relation_masks=None):
    # Zone 0 self, zones 1/2 symmetrically connected.
    node_records = node_records if node_records is not None else [
        node(links=(1,2,-1),za=0,zb=0,mask=0b110),
        node(za=1,zb=1,mask=0b010),
        node(za=0,zb=2,mask=0b100),
    ]
    relation_masks = relation_masks if relation_masks is not None else [1,6,6]
    result = bytearray(bytes(50) + b"\x03")
    offsets=[]
    for data in node_records:
        offsets.append({"start":len(result),"length":len(data)})
        result.extend(data)
    zones_at = len(result)
    result.extend(struct.pack("<I",len(relation_masks)))
    for m in relation_masks:
        result.extend(zone_row(m))
    result.extend(bytes(8))
    return bytes(result), {
        "candidate_node_count":len(node_records),
        "node_records":offsets,
        "candidate_zone_count":len(relation_masks),
        "candidate_zone_array_start":zones_at+4,
    }


class ZoneRelationTests(unittest.TestCase):
    def test_exact_zone_graph_and_subtree_mask_recurrence(self):
        payload,frame=synthetic_world()
        result=zones.inspect_zone_relations(payload,frame,
                                             include_zones=True,include_nodes=True)
        self.assertEqual(result["status"],
                         "validated_symmetric_zone_relations_and_node_subtree_masks")
        self.assertEqual(result["zones"],3)
        self.assertEqual(result["nodes"],3)
        self.assertEqual(result["zone_relation_undirected_edges"],1)
        self.assertEqual(result["zone_relation_graph_components"],2)
        self.assertEqual(result["zone_relation_component_sizes_descending"],[2,1])
        self.assertEqual(result["exact_zone_mask_subtree_recurrence"],3)
        self.assertEqual(result["verified_parent_child_zone_mask_subsets"],2)
        self.assertEqual(result["nonzero_zone_a"],1)
        self.assertEqual(result["nonzero_zone_b"],2)
        self.assertEqual(result["node_candidate_vertices"],12)
        self.assertEqual(result["node_zone_records"][0]["zone_mask_set_bits"],[1,2])
        self.assertEqual(result["zone_relation_lists"][1]["related_zones"],[1,2])
        self.assertTrue(result["rooted_node_graph_validated"])
        self.assertTrue(result["zone_second_32_bytes_all_01"])
        json.dumps(result,allow_nan=False)

    def test_both_nonzero_zone_pair_must_exist_in_zone_relation_table(self):
        records=[
            node(links=(1,2,-1),za=1,zb=2,mask=6),
            node(za=1,zb=1,mask=2),
            node(za=0,zb=2,mask=4),
        ]
        payload,frame=synthetic_world(node_records=records)
        result=zones.inspect_zone_relations(payload,frame)
        self.assertEqual(result["both_nonzero_zones"],1)
        self.assertEqual(result["both_nonzero_pairs_compatible_with_zone_relations"],1)
        payload,frame=synthetic_world(node_records=records,relation_masks=[1,2,4])
        with self.assertRaisesRegex(ValueError,"zone pair absent"):
            zones.inspect_zone_relations(payload,frame)

    def test_reject_asymmetric_or_missing_self_relation(self):
        for masks, reason in (
            ([1,6,4],"Asymmetric"),
            ([1,4,6],"omits its own"),
            ([1,2,4 | (1<<10)],"links outside"),
        ):
            with self.subTest(masks=masks),self.assertRaisesRegex(ValueError,reason):
                p,f=synthetic_world(relation_masks=masks)
                zones.inspect_zone_relations(p,f)

    def test_second_array_and_trailer_not_silently_interpreted(self):
        p,f=synthetic_world()
        at=f["candidate_zone_array_start"]
        bad=bytearray(p);bad[at+33]=0
        with self.assertRaisesRegex(ValueError,"second 32-byte array"):
            zones.inspect_zone_relations(bytes(bad),f)
        bad=bytearray(p);bad[at+65]=1
        with self.assertRaisesRegex(ValueError,"four-byte trailer"):
            zones.inspect_zone_relations(bytes(bad),f)

    def test_node_zone_fields_and_mask_corruption_rejected(self):
        p,f=synthetic_world()
        start=f["node_records"][1]["start"]
        bad=bytearray(p);bad[start+16]=0
        with self.assertRaisesRegex(ValueError,"zone mask does not equal"):
            zones.inspect_zone_relations(bytes(bad),f)
        bad=bytearray(p);struct.pack_into("<H",bad,start+109-21,3)
        with self.assertRaisesRegex(ValueError,"zone fields out of bounds"):
            zones.inspect_zone_relations(bytes(bad),f)
        bad=bytearray(p);bad[start+109-17]=1
        with self.assertRaisesRegex(ValueError,"vertex count"):
            zones.inspect_zone_relations(bytes(bad),f)
        bad=bytearray(p);bad[start+16]=3
        with self.assertRaisesRegex(ValueError,"reserved bit 0"):
            zones.inspect_zone_relations(bytes(bad),f)

    def test_subtree_child_mask_mutation_refused(self):
        p,f=synthetic_world()
        bad=bytearray(p)
        root=f["node_records"][0]["start"]
        bad[root+16]=0b010  # misses the second child's zone bit
        with self.assertRaisesRegex(ValueError,"does not include child"):
            zones.inspect_zone_relations(bytes(bad),f)

    def test_wrong_record_extent_or_node_graph_rejected(self):
        p,f=synthetic_world()
        with self.assertRaisesRegex(ValueError,"zone-record array extent"):
            zones.inspect_zone_relations(p,{**f,"candidate_zone_array_start":100})
        bad=bytearray(p)
        root=f["node_records"][0]["start"]
        bad[root+48+4]=1  # 8-compact field 4 duplicates field 3's child
        with self.assertRaisesRegex(ValueError,"unique-parent"):
            zones.inspect_zone_relations(bytes(bad),f)

    def test_map_report_and_original_source_never_modified(self):
        p,f=synthetic_world()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/"Maps"/"Synthetic.gmp"
            source.parent.mkdir()
            source.write_bytes(b"asset-free fixture only")
            class FakePackage:
                def __init__(self,filename):
                    self.data=Path(filename).read_bytes()
                    self.version=95
                    self.licensee=68
                    self.exports=[{"index":1,"name":"Model__world"}]
                def payload(self,_exp): return p
            with patch.object(zones.topology.boundaries.world,"Package",
                              side_effect=FakePackage), \
                 patch.object(zones.topology.boundaries.world,"_parse_world_model",
                              return_value={"world_model_export_ref":1}), \
                 patch.object(zones.topology.boundaries,"parse_world_model",
                              return_value=f):
                report=zones.audit_maps([source])
            self.assertEqual(report["summary"]["zones"],3)
            self.assertEqual(report["summary"]["nodes"],3)
            self.assertEqual(report["summary"]["exact_zone_mask_subtree_recurrence"],3)
            self.assertFalse(report["native_gmp_written"])
            self.assertFalse(report["native_zones_rebuilt"])
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                zones.audit_maps([source,source])
            bad_report=source.parent/"audit.json"
            with self.assertRaisesRegex(ValueError,"outside original"):
                zones.topology.boundaries.world.write_report(report,bad_report,[source])
            output=root/"Results"/"audit.json"
            zones.topology.boundaries.world.write_report(report,output,[source])
            self.assertEqual(json.loads(output.read_text())["schema"],zones.SCHEMA)
            with self.assertRaises(FileExistsError):
                zones.topology.boundaries.world.write_report(report,output,[source])
            self.assertEqual(source.read_bytes(),b"asset-free fixture only")


if __name__ == "__main__":
    unittest.main()
