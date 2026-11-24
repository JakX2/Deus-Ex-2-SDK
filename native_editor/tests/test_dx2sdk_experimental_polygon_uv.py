"""Synthetic byte-patch gates: no proprietary map fixtures."""
import struct
import unittest
from experimental_polygon_uv import _patch_level,_shift_pair,translate_polygon_uv


def fixture():
    coords=[(0.,0.,0.),(2.,0.,0.),(2.,2.,0.),(0.,2.,0.)]
    uvs=[(0.,0.),(1.,0.),(1.,1.),(0.,1.)]
    packed=bytearray(80)
    expanded=bytearray(struct.pack("<H",4))
    vs=[]
    pv=[]
    for xyz,uv in zip(coords,uvs):
        value=(*xyz,0.,0.,1.,*uv,*([0.]*9),*uv,*uv,*uv)
        expanded.extend(struct.pack("<23f",*value))
        vs.append(value)
        p=(uv[0]+10,uv[1]-5)
        pv.append((xyz,[0.,0.,1.],p))
        packed.extend(struct.pack("<3fI4f",*xyz,0x00ff8080,*p,.3,.4))
    expanded.extend(struct.pack("<I",5)+b"test\0")
    start=len(packed)
    level=bytes(packed+expanded+b"collision")
    row={"polygon":0,"start":start,"end":start+len(expanded),"vertices":vs}
    link={"polygon":0,"packed_block":0,"packed_vertex_start":0,
          "packed_vertex_count":4,"packed_uv_integer_delta":[10,-5]}
    block={"offset":0,"end":start,"vertices":pv}
    return level,row,link,[block]


class ExperimentalPolygonUVTests(unittest.TestCase):
    def test_exact_reverse_and_secondary_uv_unchanged(self):
        level,row,link,blocks=fixture()
        edited,spans=_patch_level(level,row,link,blocks,(.125,.25))
        self.assertEqual(len(spans),20)
        self.assertEqual(len(edited),len(level))
        self.assertEqual(edited[-9:],level[-9:])
        restored=bytearray(edited)
        for at,old,new in spans:
            self.assertEqual(edited[at:at+8],new)
            restored[at:at+8]=old
        self.assertEqual(bytes(restored),level)
        for i in range(4):
            at=80+i*32
            self.assertEqual(edited[at:at+16],level[at:at+16])
            self.assertEqual(edited[at+24:at+32],level[at+24:at+32])
            e=row["start"]+2+i*92
            u=edited[e+24:e+32]
            self.assertEqual(struct.unpack("<2f",u),
                             tuple(v+d for v,d in zip(row["vertices"][i][6:8],(.125,.25))))
            for j in (68,76,84):
                self.assertEqual(edited[e+j:e+j+8],u)

    def test_reject_unknown_expanded_profile(self):
        level,row,link,blocks=fixture()
        changed=bytearray(level)
        at=row["start"]+2+68
        changed[at:at+4]=struct.pack("<f",1.)
        row["vertices"][0]=struct.unpack_from("<23f",changed,row["start"]+2)
        with self.assertRaises(ValueError):
            _patch_level(bytes(changed),row,link,blocks,(.125,.25))

    def test_reject_bad_delta_precision_and_pin(self):
        level,row,link,blocks=fixture()
        for delta in ((0.,0.),(float("nan"),0.),(20.,0.)):
            with self.assertRaises(ValueError):
                _patch_level(level,row,link,blocks,delta)
        with self.assertRaises(ValueError):
            _shift_pair(struct.pack("<2f",1e20,0.),(.125,.25))
        with self.assertRaises(ValueError):
            translate_polygon_uv("test.gmp",level,expected_sha256="bad",
                                 polygon=0,delta=(.125,.25))


if __name__=="__main__":
    unittest.main()
