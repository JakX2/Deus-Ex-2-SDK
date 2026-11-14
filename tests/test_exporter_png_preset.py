"""Asset-free regression for optional PNG compression with unchanged pixels.

Default PNG compression remains zlib level 7 and must retain original
byte-identical output; nondefault modes trade larger files for faster writes.
Nothing in these tests needs or writes original Deus Ex 2 game files.
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "map_exporter"))
from dx2textures import Texture, png_bytes, rgba_pixels, to_png
from dx2level import Builder


def extract_png(data):
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    at = 8
    width = height = None
    idats = []
    while at < len(data):
        size = struct.unpack_from(">I", data, at)[0]
        at += 4
        tag = data[at:at+4]
        at += 4
        payload = data[at:at+size]
        at += size
        crc = struct.unpack_from(">I", data, at)[0]
        at += 4
        assert zlib.crc32(tag+payload) & 0xffffffff == crc
        if tag == b"IHDR":
            width,height,depth,kind,comp,filt,interlace = struct.unpack(
                ">IIBBBBB",payload)
            assert (depth,kind,comp,filt,interlace) == (8,6,0,0,0)
        if tag == b"IDAT":
            idats.append(payload)
        if tag == b"IEND":
            break
    raw = zlib.decompress(b"".join(idats))
    stride = width * 4 + 1
    assert len(raw) == stride * height
    rows = []
    for y in range(height):
        start = y * stride
        assert raw[start] == 0
        rows.append(raw[start+1:start+stride])
    return width,height,b"".join(rows)


def glb_view(path):
    data = path.read_bytes()
    magic, version, total = struct.unpack_from("<4sII",data)
    assert (magic,version,total) == (b"glTF",2,len(data))
    pos = 12
    size,kind = struct.unpack_from("<I4s",data,pos)
    pos += 8
    assert kind == b"JSON"
    doc = json.loads(data[pos:pos+size])
    pos += size
    size,kind = struct.unpack_from("<I4s",data,pos)
    pos += 8
    assert kind == b"BIN\x00"
    binary = data[pos:pos+size]
    images = {image["bufferView"] for image in doc["images"]}
    decoded_images = []
    geometry = []
    for index,view in enumerate(doc["bufferViews"]):
        raw = binary[view["byteOffset"]:view["byteOffset"]+view["byteLength"]]
        if index in images:
            decoded_images.append(extract_png(raw))
            del view["byteLength"]
        else:
            geometry.append(raw)
        view.pop("byteOffset",None)
    doc["buffers"][0]["byteLength"] = None
    return doc,decoded_images,geometry


class PNGPresetTests(unittest.TestCase):
    def test_png_levels_decode_same_and_default_exact_zlib7_bytes(self):
        rng = random.Random(177)
        for w,h in ((1,1),(3,5),(9,7),(34,13),(128,128)):
            rgba = rng.randbytes(w*h*4)
            original = png_bytes(w,h,rgba)
            rows = b"".join(
                b"\x00"+rgba[y*w*4:(y+1)*w*4] for y in range(h))
            self.assertIn(zlib.compress(rows,7),original)
            for level in (1,2,3,7,9):
                with self.subTest(size=(w,h),level=level):
                    output = png_bytes(w,h,rgba,level)
                    self.assertEqual(extract_png(output),(w,h,rgba))
                    if level == 7:
                        self.assertEqual(output,original)

    def test_invalid_compression_levels_fail_closed(self):
        for level in (0,10,-1,True,False,None,1.0,"7"):
            with self.subTest(level=level), self.assertRaises(ValueError):
                png_bytes(2,2,bytes(16),level)
            with self.subTest(builder=level), self.assertRaises(ValueError):
                Builder({}, {}, {}, png_compression_level=level)

    def test_cubemap_faces_and_regular_texture_keep_pixels(self):
        rgba = bytes(range(4*4*4))
        tex = Texture("ordinary","BGRA8",4,4,0,[(4,4,rgba)],"mock.ibd")
        decoded = rgba_pixels(tex)[2]
        for level in (1,7):
            self.assertEqual(extract_png(to_png(tex,level)),(4,4,decoded))
        faces = [bytes((i*17+j)%256 for j in range(64)) for i in range(6)]
        cube = Texture("cube","BGRA8",4,4,6,[(4,4,faces[0])],
                       "mock.ibd",faces=[[bytes(x) for x in faces]])
        width,height,sheet = extract_png(to_png(cube,1))
        self.assertEqual((width,height),(12,8))
        for face in range(6):
            _,_,expected = rgba_pixels(cube,face)
            x0,y0 = face%3*4,face//3*4
            actual = b"".join(
                sheet[((y0+y)*width+x0)*4:((y0+y)*width+x0+4)*4]
                for y in range(4))
            self.assertEqual(actual,expected)

    def test_gltf_geometry_and_embedded_image_rgba_are_unchanged(self):
        rng = random.Random(104)
        pixels = rng.randbytes(32*32*4)
        tex = Texture("wall","BGRA8",32,32,0,
                      [(32,32,pixels)],"mock.ibd")
        class Bundle:
            name = "mock.ibd"
        class Resource:
            index = 4
        def build(path,level=None):
            kwargs = {} if level is None else {
                "png_compression_level": level}
            builder = Builder(
                {},{},{"wall":(Bundle(),Resource())},**kwargs)
            # Geometry both before and after PNG, exercising changed
            # buffer offsets without silently changing any mesh data.
            builder.vectors([(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)],3)
            with patch("dx2level.parse_texture",return_value=tex):
                builder.material("wall")
            builder.vectors([(0.,0.),(1.,0.),(0.,1.)],2,"VEC2")
            builder.save(path)
        with TemporaryDirectory() as folder:
            root = Path(folder)
            standard,fast,explicit7 = (
                root/"default.glb",root/"fast.glb",root/"same.glb")
            build(standard)
            build(fast,1)
            build(explicit7,7)
            self.assertEqual(standard.read_bytes(),explicit7.read_bytes())
            self.assertEqual(glb_view(standard),glb_view(fast))
            self.assertNotEqual(standard.read_bytes(),fast.read_bytes())

    def test_run_export_rejects_invalid_setting_before_file_io(self):
        from dx2_map_exporter import run_export
        for invalid in (0,10,True,7.0):
            with self.subTest(level=invalid),self.assertRaises(ValueError):
                run_export(None,Path("not_created.glb"),
                           png_compression_level=invalid)


if __name__ == "__main__":
    unittest.main()
