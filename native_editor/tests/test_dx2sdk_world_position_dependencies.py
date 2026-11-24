"""Synthetic original position dependency and fixed-width translation gates."""
import math
import struct
import unittest
from inspect_world_position_dependencies import (
    BytePatch,bounds_of,scaled_position,SOURCE_SCALE,inspect_packed_positions,
    moved,translate_model,validate_delta,
)


class PositionDependencyTests(unittest.TestCase):
    def test_exact_float32_scale_and_bounds(self):
        xyz=[(1.,2.,3.),(5.,6.,7.)]
        box,center,radius=bounds_of(xyz)
        self.assertEqual(box,(1.,2.,3.,5.,6.,7.))
        self.assertEqual(center,(3.,4.,5.))
        self.assertEqual(radius,math.sqrt(12))
        self.assertEqual(struct.pack("<f",scaled_position((1234.5,0.,0.))[0]),
                         struct.pack("<f",1234.5*SOURCE_SCALE))

    def test_patch_exact_reverse_and_refuse_overlap(self):
        patch=BytePatch(b"abcdef")
        patch.add(1,b"XY")
        patch.add(4,b"Z")
        self.assertEqual(patch.finish(),b"aXYdZf")
        patch.add(2,b"Q")
        with self.assertRaises(ValueError):
            patch.finish()

    def test_source_shadow_caps_and_index_pattern(self):
        coords=[(0.,0.,0.),(2.,0.,0.),(0.,2.,0.)]
        box,center,radius=bounds_of(coords)
        header=struct.pack("<10f10I",*box,radius,*center,3,3,1,1,24,8,6,1,0xffffffe0,0)
        vertices=b"".join(struct.pack("<3f",*v)+bytes(20) for v in coords)
        shadow=b"".join(struct.pack("<3fI",v[0],v[1],.3,0x007f7f00)
                       for v in coords+[coords[0],coords[2],coords[1]])
        idx=(0,3,1,1,4,2,2,5,0,0,1,2,3,0,4,4,1,5,5,2,3,3,4,5)
        data=header+vertices+shadow+struct.pack("<24H",*idx)+struct.pack("<3H",0,1,2)
        block={"offset":0,"end":len(data),"vertices":[(v,(),()) for v in coords],
               "sections":[{"indices":[0,1,2]}]}
        counts,links,distance=inspect_packed_positions(data,[block])
        self.assertEqual(counts["shadow_caps"],2)
        self.assertEqual(counts["shadow_unique_render_index_caps"],2)
        self.assertEqual(links,[(0,0,((0,0,0),)),(0,1,((0,0,0),))])
        self.assertLess(distance,.301)
        bad=bytearray(data)
        struct.pack_into("<H",bad,80+3*32+6*16,5)
        with self.assertRaises(ValueError):
            inspect_packed_positions(bytes(bad),[block])

    def test_translate_plane_center_not_radius(self):
        raw=bytearray(109)
        plane=(1.,0.,0.,2.)
        sphere=(2.,3.,4.,5.)
        struct.pack_into("<4f",raw,0,*plane)
        struct.pack_into("<4f",raw,56,*sphere)
        frame={"node_records":[{"start":0,"length":109}]}
        result=translate_model(bytes(raw),frame,[(plane,sphere,3)],(1.,2.,3.))
        self.assertEqual(struct.unpack_from("<4f",result,0),(1.,0.,0.,3.))
        self.assertEqual(struct.unpack_from("<4f",result,56),(3.,5.,7.,5.))
        self.assertEqual(result[16:56],bytes(raw)[16:56])

    def test_refuse_bad_delta(self):
        for d in ((0.,0.,0.),(float("inf"),0.,0.),(17.,0.,0.)):
            with self.assertRaises(ValueError):
                validate_delta(d)
        self.assertEqual(moved((1.,2.,3.),(.125,0.,0.)),(1.125,2.,3.))


if __name__=="__main__":
    unittest.main()
