"""Synthetic VBSP and spatial grid source framing/traversal gates."""
import struct
import unittest
from inspect_level_spatial_vbsp import parse_spatial_tail,locate_point,translate_spatial_prefix,validate_leaf_render_ownership
from inspect_level_prefix_graph import parse_prefix_graph
from test_dx2sdk_level_prefix_graph import fixture as graph_fixture


def fixture():
    grid=struct.pack("<IIii3fII",1,1,0,0,0.,0.,0.,1,64)+bytes([32])*64
    grid+=struct.pack("<I6f",1,24.,0.,0.,.70710677,.70710677,0.)
    p=0x10000058
    ptrs=[p,p+36,p+36+104,p+36+104+16,p+36+104+16+24,
          p+36+104+16+24+36,0,p+36+104+16+24+36+8]
    head=struct.pack("<23I",123,0x50534256,2,1,2,0,1,1,0,1,1,3,*ptrs,0,0,0)
    node=struct.pack("<9i",3,0,1,*([0]*6))
    leaf=lambda refs,box:struct.pack("<5i6f2i",*refs,-1,*box,0,0)
    leaves=leaf((0,1,0,1),(0.,-2.,-2.,2.,2.,2.))+leaf((1,1,1,1),(-2.,-2.,-2.,0.,2.,2.))
    plane=struct.pack("<4f",1.,0.,0.,0.)
    portal=struct.pack("<6i",0,1,0,3,0,0)
    xyz=struct.pack("<9f",0.,0.,0.,0.,1.,0.,0.,0.,1.)
    return grid+head+node+leaves+plane+portal+xyz+struct.pack("<I",0)


class SpatialVBSPTests(unittest.TestCase):
    def test_source_tree_and_portal(self):
        data=fixture()
        r=parse_spatial_tail(data,0,len(data))
        self.assertEqual(r["counts"]["grid_cells"],1)
        self.assertEqual(r["counts"]["vbsp_portal_leaf_pairs_verified"],1)
        self.assertEqual(r["portal_leaf_links"],[(0,1)])
        self.assertTrue(r["source_noop_byte_identical"])
        self.assertEqual(locate_point(r["nodes"],r["planes"],(1.,0.,0.)),0)
        self.assertEqual(locate_point(r["nodes"],r["planes"],(-1.,0.,0.)),1)

    def test_corrupt_pointer_or_portal(self):
        raw=fixture()
        r=parse_spatial_tail(raw,0,len(raw))
        for at in (r["vbsp_start"]+52,len(raw)-40-4):
            data=bytearray(raw)
            struct.pack_into("<I",data,at,0xffffffff)
            with self.assertRaises(ValueError):
                parse_spatial_tail(bytes(data),0,len(data))

    def test_leaf_render_crosswalk(self):
        data=fixture()
        tail=parse_spatial_tail(data,0,len(data))
        polygon={"polygon":0,"vertices":[(0.,0.,0.,1.,0.,0.),
                 (0.,1.,0.,1.,0.,0.),(0.,0.,1.,1.,0.,0.)]}
        links=[{"polygon":0,"triangle_locators":[(0,0,0)]}]
        rows=[{"render_locator":[0,0,0],"source_provenance_block_field_a":0}]
        frame={"native_render_block_entries":2,"native_render_nonempty_blocks":1,
               "native_render_empty_blocks":1}
        counts,owners=validate_leaf_render_ownership(tail,[polygon],links,rows,frame)
        self.assertEqual(owners,[0])
        self.assertEqual(counts["vbsp_polygon_normal_probe_owner_matches"],1)
        rows[0]["source_provenance_block_field_a"]=1
        with self.assertRaises(ValueError):
            validate_leaf_render_ownership(tail,[polygon],links,rows,frame)

    def test_translate_decoded_prefix(self):
        prefix=graph_fixture()[:-6]
        data=prefix+fixture()
        g=parse_prefix_graph(data,0,len(data))
        t=parse_spatial_tail(data,g["graph_end"],len(data))
        moved,report=translate_spatial_prefix(data,g,t,(.125,.25,0.))
        t2=parse_spatial_tail(moved,g["graph_end"],len(moved))
        self.assertEqual(t2["portal_leaf_links"],t["portal_leaf_links"])
        self.assertEqual(t2["planes"][0][3],-.125)
        self.assertEqual(report["translated_portal_side_probes"],2)
        self.assertNotEqual(moved,data)


if __name__=="__main__":
    unittest.main()
