"""Fixture-free expanded Level polygon stream regression tests."""
import math
import struct
import unittest
from inspect_level_expanded_polygons import (
    parse_expanded_polygons,match_expanded_render,match_model_candidates,
    validate_counted_render_array,
)


def vertex(x,y,u,v):
    return (float(x),float(y),0.,0.,0.,1.,float(u),float(v),
            *([0.]*15))


def fixture():
    vs=[vertex(0,0,0,0),vertex(2,0,1,0),vertex(2,2,1,1),vertex(0,2,0,1)]
    raw=struct.pack("<H",4)+b"".join(struct.pack("<23f",*v) for v in vs)
    raw+=struct.pack("<I",5)+b"test\0"
    level=b"prefix"+raw+b"\0"*16
    block={"vertices":[(v[:3],v[3:6],v[6:8]) for v in vs],
           "sections":[{"material":"test","indices":[0,1,2,0,2,3]}]}
    return level,block


class ExpandedPolygonTests(unittest.TestCase):
    def test_counted_block_array_with_empty_native_entries(self):
        level=(b"head"+struct.pack("<II",5,0)+struct.pack("<I",3)+b"abc"
               +struct.pack("<II",0,2)+b"xy"+struct.pack("<I",0)+b"tail")
        blocks=[{"offset":16,"id":3,"end":19},{"offset":27,"id":2,"end":29}]
        rows=[{"render_locator":[0,0,0],"source_provenance_block_field_a":1},
              {"render_locator":[1,0,0],"source_provenance_block_field_a":3}]
        proof=validate_counted_render_array(level,blocks,rows)
        self.assertEqual(proof["render_block_count_offset"],4)
        self.assertEqual(proof["render_block_array_end"],33)
        self.assertEqual(proof["native_render_block_entries"],5)
        self.assertEqual(proof["native_render_empty_blocks"],3)
        bad=bytearray(level)
        struct.pack_into("<I",bad,4,2)
        with self.assertRaises(ValueError):
            validate_counted_render_array(bytes(bad),blocks,rows)
        with self.assertRaises(ValueError):
            validate_counted_render_array(level,blocks,[
                rows[0],dict(rows[1],source_provenance_block_field_a=2)])

    def test_exact_stream_and_indexed_disk(self):
        level,block=fixture()
        rows,framing=parse_expanded_polygons(level,6,len(level),4)
        self.assertTrue(framing["expanded_polygon_noop_byte_identical"])
        self.assertEqual(framing["expanded_polygon_zero_tail_bytes"],16)
        self.assertEqual(rows[0]["material"],"test")
        counts,links=match_expanded_render(rows,[block])
        self.assertEqual(counts["expanded_polygons"],1)
        self.assertEqual(counts["packed_triangles"],2)
        self.assertEqual(links[0]["triangle_locators"],[(0,0,0),(0,0,1)])

    def test_nonfan_and_whole_uv_repeat(self):
        level,block=fixture()
        rows,_=parse_expanded_polygons(level,6,len(level),4)
        block["sections"][0]["indices"]=[0,1,3,1,2,3]
        block["vertices"]=[(x,n,(uv[0]+10,uv[1]-2)) for x,n,uv in block["vertices"]]
        counts,links=match_expanded_render(rows,[block])
        self.assertEqual(counts["first_vertex_fan_polygons"],0)
        self.assertEqual(counts["exact_uv_polygons"],0)
        self.assertEqual(links[0]["packed_uv_integer_delta"],[10,-2])

    def test_refuse_bad_frame_and_material(self):
        level,block=fixture()
        for bad in (level[:-1]+b"\1",level[:6]+b"\x05\x00"+level[8:],
                    level[:-17]+b"x"+level[-16:]):
            with self.assertRaises(ValueError):
                parse_expanded_polygons(bad,6,len(bad),4)

    def test_refuse_material_uv_topology_and_duplicate_record(self):
        level,block=fixture()
        rows,_=parse_expanded_polygons(level,6,len(level),4)
        for changes in ({"material":"wrong"},{"indices":[0,2,1,0,2,3]},
                        {"indices":[0,1,2,0,1,2]}):
            with self.assertRaises(ValueError):
                match_expanded_render(rows,[{**block,"sections":[
                    {**block["sections"][0],**changes}]}])
        bad={**block,"vertices":[(x,n,(uv[0]+.25,uv[1]))
                                  for x,n,uv in block["vertices"]]}
        with self.assertRaises(ValueError):
            match_expanded_render(rows,[bad])
        with self.assertRaises(ValueError):
            match_expanded_render(rows+[dict(rows[0],polygon=1)],[block])

    def test_model_association_is_geometric_and_bidirectional(self):
        level,_=fixture()
        rows,_=parse_expanded_polygons(level,6,len(level),4)
        node=((0.,0.,1.,0.),(1.,1.,0.,math.sqrt(2)*1.001),4)
        counts,cand=match_model_candidates(rows,[node])
        self.assertEqual(cand,[[0]])
        self.assertEqual(counts["model_bidirectionally_unique_candidates"],1)
        counts,cand=match_model_candidates(rows,[node,node])
        self.assertEqual(cand,[[0,1]])
        self.assertEqual(counts["model_bidirectionally_unique_candidates"],0)
        counts,cand=match_model_candidates(rows+[dict(rows[0],polygon=1)],[node])
        self.assertEqual(counts["model_bidirectionally_unique_candidates"],0)


if __name__=="__main__":
    unittest.main()
