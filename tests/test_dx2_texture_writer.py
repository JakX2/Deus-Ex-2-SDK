"""Synthetic native texture writer regression suite."""
from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"maps"))
from dx2_ibd_integrity import verify_bundle
from dx2_texture_writer import (
    decode_dds_for_texture, inspect_layout, marker_mips, replace_dds,
    replace_mips, select_texture, to_dds, write_candidate,
)


def make_fixture(fmt=b"DXT1", *, usage=0, duplicate=False):
    def u(n): return struct.pack("<I",n)
    from dx2textures import mip_size
    name={b"DXT1":"DXT1",b"DXT3":"DXT3",b"DXT5":"DXT5",
          b"\x15\0\0\0":"BGRA8",b"\x16\0\0\0":"BGRX8"}[fmt]
    sizes=[mip_size(name,w,h) for w,h in ((8,4),(4,2),(2,1))]
    parts=[b"\1",fmt,u(3),u(usage),u(0),u(8),u(4),u(8),u(4),u(sum(sizes)),b"\1",b"\0"]
    for i,((w,h),size) in enumerate(zip(((8,4),(4,2),(2,1)),sizes)):
        if fmt==b"DXT1":
            block=struct.pack("<HHI",0xf800,0x001f,0xAAAAAAAA) if i!=1 else struct.pack("<HHI",0,0xffff,0xFFFFFFFF)
            pixels=block*(size//8)
        elif fmt in (b"DXT3",b"DXT5"):
            block=b"\x01\x02\x03\x04\x05\x06\x07\x08"+struct.pack("<HHI",0xf800,0x1f,0xAAAAAAAA)
            pixels=block*(size//16)
        else:
            pixels=b"\x01\x02\x03\x7f"*(size//4)
        parts.extend([u(i),u(w),u(h),u(size),bytes([i])*9,pixels])
    rows=[(b"fixture_tex",8,parts),(b"unrelated",21,[b"unrelated resource"])]
    if duplicate: rows.append((b"FIXTURE_TEX",8,parts))
    n=len(rows)
    lengths=[len(p) for _,_,row in rows for p in row]
    raw=bytearray(2048+n*2048)
    struct.pack_into("<8I",raw,0,0xc0000001,2048,2048,n*2048,
                     max(sum(map(len,row)) for _,_,row in rows),max(lengths),n,len(lengths))
    first=0
    for i,(label,typ,row) in enumerate(rows):
        at=52+304*i
        offset=2048*(i+1)
        data=b"".join(row)
        raw[offset:offset+len(data)]=data
        struct.pack_into("<5I",raw,at,offset,len(data),2048-len(data),first,len(row))
        raw[at+20:at+40]=hashlib.sha1(raw[offset:offset+2048]).digest()
        raw[at+40]=typ
        raw[at+41:at+41+len(label)]=label
        first+=len(row)
    struct.pack_into("<%dI"%len(lengths),raw,52+n*304,*lengths)
    raw[32:52]=hashlib.sha1(raw[:2048]).digest()
    return bytes(raw)


def layout(raw):
    b=verify_bundle(raw)
    return inspect_layout(b,select_texture(b,"fixture_tex"))


class TextureWriterTests(unittest.TestCase):
    def test_dds_roundtrip_and_exact_reversal_all_supported_formats(self):
        for fmt in (b"DXT1",b"DXT3",b"DXT5",b"\x15\0\0\0",b"\x16\0\0\0"):
            with self.subTest(fmt=fmt):
                raw=make_fixture(fmt)
                a=layout(raw)
                dds=to_dds(a.texture)
                mips=decode_dds_for_texture(dds,a)
                self.assertEqual(mips,tuple(data for _,_,data in a.texture.mipmaps))
                changed=replace_mips(raw,"fixture_tex",marker_mips(a,"magenta"))
                b=layout(changed)
                self.assertEqual(len(raw),len(changed))
                self.assertEqual(a.pixel_slots,b.pixel_slots)
                self.assertEqual(tuple(b.parts[i] for i in b.pixel_slots),marker_mips(a,"magenta"))
                self.assertEqual([p for i,p in enumerate(a.parts) if i not in a.pixel_slots],
                                 [p for i,p in enumerate(b.parts) if i not in b.pixel_slots])
                self.assertEqual(raw[4096:],changed[4096:])
                self.assertEqual(replace_dds(changed,"fixture_tex",dds),raw)

    def test_marker_preserves_bc1_transparency_modes_and_indices(self):
        a=layout(make_fixture())
        for palette in ("magenta","cyan"):
            for (_,_,before),after in zip(a.texture.mipmaps,marker_mips(a,palette)):
                for pos in range(0,len(before),8):
                    x,y=struct.unpack_from("<HH",before,pos)
                    u,v=struct.unpack_from("<HH",after,pos)
                    self.assertEqual(x>y,u>v)
                    self.assertEqual(before[pos+4:pos+8],after[pos+4:pos+8])

    def test_marker_preserves_bc2_bc3_and_bgra_alpha(self):
        for fmt in (b"DXT3",b"DXT5",b"\x15\0\0\0",b"\x16\0\0\0"):
            a=layout(make_fixture(fmt))
            for (_,_,before),after in zip(a.texture.mipmaps,marker_mips(a,"cyan")):
                if fmt in (b"DXT3",b"DXT5"):
                    for pos in range(0,len(before),16):
                        self.assertEqual(before[pos:pos+8],after[pos:pos+8])
                        self.assertEqual(before[pos+12:pos+16],after[pos+12:pos+16])
                else: self.assertEqual(before[3::4],after[3::4])

    def test_refuse_wrong_dds_header_format_mips_caps_and_payload(self):
        a=layout(make_fixture())
        original=to_dds(a.texture)
        for offset,data in ((0,b"BAD!"),(4,struct.pack("<I",123)),(16,struct.pack("<I",16)),
                            (28,struct.pack("<I",2)),(84,b"DXT5"),
                            (112,struct.pack("<I",0xfe00)),(20,struct.pack("<I",999))):
            bad=bytearray(original)
            bad[offset:offset+len(data)]=data
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                decode_dds_for_texture(bytes(bad),a)
        for bad in (original[:-1],original+b"x"):
            with self.assertRaises(ValueError):decode_dds_for_texture(bad,a)
        with self.assertRaises(ValueError):
            replace_dds(make_fixture(),"fixture_tex",original)

    def test_refuse_ambiguous_non_2d_and_invalid_mips(self):
        with self.assertRaisesRegex(ValueError,"exactly one"):
            layout(make_fixture(duplicate=True))
        with self.assertRaisesRegex(ValueError,"ordinary 2D"):
            layout(make_fixture(usage=6))
        raw=make_fixture()
        a=layout(raw)
        for mips in ([b"x"],[b"x"]*3,[bytearray(a.parts[i]) for i in a.pixel_slots]):
            with self.assertRaises(ValueError):replace_mips(raw,"fixture_tex",mips)

    def test_disk_pin_and_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"original"/"fixture.ibd"
            source.parent.mkdir()
            raw=make_fixture()
            source.write_bytes(raw)
            pin=hashlib.sha256(raw).hexdigest()
            output=root/"candidate"/source.name
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                write_candidate(source,output,"fixture_tex","0"*64,palette="magenta")
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_candidate(source,source.parent/"nested"/source.name,"fixture_tex",pin,palette="magenta")
            receipt=write_candidate(source,output,"fixture_tex",pin,palette="magenta")
            self.assertFalse(receipt["runtime_verified"])
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(layout(output.read_bytes()).parts[17],marker_mips(layout(raw),"magenta")[0])
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_candidate(source,output,"fixture_tex",pin,palette="magenta")


if __name__=="__main__":
    unittest.main()
