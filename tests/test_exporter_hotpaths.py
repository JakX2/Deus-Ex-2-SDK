"""Asset-free byte-equivalence tests for DX2 exporter fast paths.

Legacy reference is pinned separately. These never load game-owned assets,
and no performance timing threshold is asserted on CI hardware.
"""
from __future__ import annotations

import random
from pathlib import Path
import sys
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'map_exporter'))
sys.path.insert(0,str(ROOT/'tests'))

import reference_legacy_exporter as legacy
from dx2textures import Texture, rgba_pixels, png_bytes, to_png, to_dds
from dx2level import Builder


def synthetic_texture(fmt,w,h,raw,faces=None):
    return Texture(
        "Synthetic", fmt, w, h, 0, [(w,h,raw)],
        "SYNTHETIC_NOT_FROM_RETAIL_GAME", faces=faces)


def size(fmt,w,h):
    if fmt in ("BGRA8","BGRX8"):return w*h*4
    return ((w+3)//4)*((h+3)//4)*(8 if fmt=="DXT1" else 16)


class ExporterHotpathTests(unittest.TestCase):
    def test_byte_exact_random_textures_including_partial_dxt_blocks(self):
        rng=random.Random(20261113)
        for fmt in ("BGRA8","BGRX8","DXT1","DXT3","DXT5"):
            for w,h in ((1,1),(3,5),(7,9),(16,16),(31,17),(129,63)):
                with self.subTest(fmt=fmt,dimensions=(w,h)):
                    raw=rng.randbytes(size(fmt,w,h))
                    tex=synthetic_texture(fmt,w,h,raw)
                    old=legacy.rgba_pixels(tex)
                    self.assertEqual(rgba_pixels(tex),old)
                    self.assertEqual(to_png(tex),png_bytes(w,h,old[2]))
                    # DDS source mip bytes still come directly from the original.
                    self.assertEqual(to_dds(tex)[-len(raw):],raw)

    def test_dxt_explicit_transparency_and_alpha_interpolation_modes(self):
        # DXT1: force both opaque (c0>c1) and transparent (c0<=c1) palettes.
        dxt1=(struct.pack("<HHI",0xf800,0x07e0,0xffffffff),
              struct.pack("<HHI",0x001f,0xffff,0xffffffff))
        # DXT3: hand-picked 4-bit alpha values; DXT5 covers 8- and 6-alpha.
        dxt3=(b"\\x10\\x32\\x54\\x76\\x98\\xba\\xdc\\xfe"+dxt1[0],)
        dxt5=(
            bytes((250,8))+b"\\x13\\x57\\x9b\\xdf\\x13\\x57"+dxt1[0],
            bytes((8,250))+b"\\x13\\x57\\x9b\\xdf\\x13\\x57"+dxt1[1],
        )
        for fmt,blocks in (("DXT1",dxt1),("DXT3",dxt3),("DXT5",dxt5)):
            for raw in blocks:
                with self.subTest(fmt=fmt,raw=raw.hex()):
                    tex=synthetic_texture(fmt,4,4,raw)
                    self.assertEqual(rgba_pixels(tex),legacy.rgba_pixels(tex))

    def test_cubemap_six_faces_and_png_contact_sheet_equivalence(self):
        rng=random.Random(83)
        for fmt in ("BGRA8","BGRX8","DXT1","DXT3","DXT5"):
            w,h=9,7
            faces=[rng.randbytes(size(fmt,w,h)) for _ in range(6)]
            tex=synthetic_texture(fmt,w,h,faces[0],faces=[faces])
            sheet=bytearray(3*w*2*h*4)
            for face in range(6):
                old=legacy.rgba_pixels(tex,face)
                self.assertEqual(rgba_pixels(tex,face),old)
                ox=face%3*w;oy=face//3*h
                for y in range(h):
                    dst=((oy+y)*3*w+ox)*4
                    sheet[dst:dst+w*4]=old[2][y*w*4:(y+1)*w*4]
            self.assertEqual(to_png(tex),png_bytes(3*w,2*h,bytes(sheet)))
            with self.assertRaises(ValueError):
                rgba_pixels(tex,6)

    def test_malformed_mips_are_rejected_not_silently_truncated(self):
        for fmt in ("BGRA8","BGRX8","DXT1","DXT3","DXT5"):
            for invalid_length in (0,1,size(fmt,9,7)-1,size(fmt,9,7)+1):
                with self.subTest(fmt=fmt,length=invalid_length):
                    tex=synthetic_texture(fmt,9,7,bytes(invalid_length))
                    with self.assertRaises(ValueError):
                        rgba_pixels(tex)

    def test_vector_float32_buffer_and_gltf_bounds_match_original(self):
        rng=random.Random(42)
        samples=(
            (3,"VEC3",[(0,0,0),(-0.0,1.5,10.25),(7,-5,0)]),
            (3,"VEC3",[
                (rng.uniform(-100,100),rng.uniform(-100,100),
                 rng.uniform(-100,100))
                for _ in range(2000)
            ]),
            (2,"VEC2",[(0,0),(1,0.5),(-2.75,99)]),
            (2,"VEC2",[
                (rng.uniform(-10,10),rng.uniform(-10,10))
                for _ in range(1000)
            ]),
        )
        for width,kind,vectors in samples:
            with self.subTest(width=width,kind=kind):
                raw,bounds=legacy.vector_bytes_and_bounds(vectors,width,kind)
                exporter=Builder({}, {}, {})
                index=exporter.vectors(vectors,width,kind)
                self.assertEqual(index,0)
                self.assertEqual(bytes(exporter.binary),raw)
                accessor=exporter.doc["accessors"][index]
                self.assertEqual(accessor["count"],len(vectors))
                self.assertEqual(accessor["type"],kind)
                if bounds is None:
                    self.assertNotIn("min",accessor)
                    self.assertNotIn("max",accessor)
                else:
                    self.assertEqual(accessor["min"],bounds["min"])
                    self.assertEqual(accessor["max"],bounds["max"])
                    self.assertEqual(
                        list(map(type,accessor["min"])),
                        list(map(type,bounds["min"])))

    def test_vector_validation_still_refuses_malformed_and_nan(self):
        bad=(
            [],[(0.,0.)],[(0.,0.,float("nan"))],
            [(float("inf"),0.,0.)],[(0,0,0),(1,2)],
        )
        for vectors in bad:
            with self.subTest(vectors=vectors):
                exporter=Builder({}, {}, {})
                with self.assertRaises(ValueError):
                    exporter.vectors(vectors,3)


if __name__=="__main__":
    unittest.main()
