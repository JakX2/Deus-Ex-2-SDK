"""Synthetic texture basis and packed vector evidence tests."""
import math
import struct
import unittest
from inspect_level_polygon_uv_basis import (
    fit_affine_uv,evaluate_uv,preview_uv,decode_tangent_like,inspect_polygon_uv,
)


class PolygonUVBasisTests(unittest.TestCase):
    def setUp(self):
        self.xyz=[(0.,0.,0.),(2.,0.,0.),(2.,2.,0.),(0.,2.,0.)]
        self.uv=[(x/2,y/2) for x,y,z in self.xyz]

    def test_affine_projection_and_tangent(self):
        fit=fit_affine_uv(self.xyz,self.uv)
        self.assertLess(fit["max_uv_error"],1e-12)
        self.assertEqual(fit["tangent_direction"],(1.,0.,0.))
        self.assertEqual(evaluate_uv(fit,(1.,1.,0.)),(.5,.5))
        self.assertEqual(preview_uv(fit,self.xyz,self.uv,self.xyz[2]),((1.,1.),"original"))
        self.assertEqual(preview_uv(fit,self.xyz,self.uv,(1.,1.,0.)),((.5,.5),"affine"))

    def test_nonaffine_and_degenerate_refusal(self):
        uv=list(self.uv)
        uv[1]=(4.,0.)
        fit=fit_affine_uv(self.xyz,uv)
        self.assertGreater(fit["max_uv_error"],.0001)
        with self.assertRaises(ValueError):
            preview_uv(fit,self.xyz,uv,(1.,1.,0.))
        with self.assertRaises(ValueError):
            fit_affine_uv([(0.,0.,0.),(1.,0.,0.),(2.,0.,0.)],uv[:3])
        with self.assertRaises(ValueError):
            fit_affine_uv(self.xyz,[(float("nan"),0.)]*4)

    def test_packed_trailing_words_and_source_direction(self):
        raw=b"\x80\x80\xff\xff"+b"\xff"*4
        direction,alpha,white=decode_tangent_like(raw)
        self.assertEqual(alpha,255)
        self.assertTrue(white)
        self.assertAlmostEqual(direction[0],1.)
        packed=bytes(80)+b"".join(struct.pack("<3f",*p)+bytes(12)+raw for p in self.xyz)
        poly={"polygon":0,"vertices":[(*p,0.,0.,1.,*uv) for p,uv in zip(self.xyz,self.uv)]}
        link={"polygon":0,"packed_block":0,"packed_vertex_start":0,"packed_vertex_count":4}
        block={"offset":0,"end":len(packed),"vertices":[None]*4}
        counts=inspect_polygon_uv(packed,[block],[poly],[link])["counts"]
        self.assertEqual(counts["packed_final_word_all_ff"],4)
        self.assertEqual(counts["packed_texture_tangent_dot_above_098"],4)
        self.assertEqual(counts["packed_vector_normal_orthogonal_02"],4)


if __name__=="__main__":
    unittest.main()
