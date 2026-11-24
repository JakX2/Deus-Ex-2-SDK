"""Entirely synthetic x86 PE fixture, decoded by actual GNU objdump."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pe_loader_crosscheck import PE, analyze, parse_instruction, scan

BASE = 0x400000
CODE = BASE + 0x1000
DATA = BASE + 0x2000
TARGET = CODE + 0x80


def fixture():
    image = bytearray(0x600)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3c, 0x80)
    image[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", image, 0x84, 0x14c, 2, 0, 0, 0, 0xe0, 0x0102)
    opt = 0x98
    struct.pack_into("<H", image, opt, 0x10b)
    struct.pack_into("<7I", image, opt+4, 0x200, 0x200, 0, 0x1000, 0x1000, 0x2000, BASE)
    struct.pack_into("<II", image, opt+32, 0x1000, 0x200)
    struct.pack_into("<II", image, opt+56, 0x3000, 0x200)
    struct.pack_into("<H", image, opt+68, 3)
    struct.pack_into("<I", image, opt+92, 16)
    struct.pack_into("<II", image, opt+104, 0x2080, 40)
    for i, (name, rva, off, flags) in enumerate(((b".text",0x1000,0x200,0x60000020),(b".rdata",0x2000,0x400,0x40000040))):
        start=opt+0xe0+40*i
        image[start:start+len(name)] = name
        struct.pack_into("<IIII",image,start+8,0x200,rva,0x200,off)
        struct.pack_into("<I",image,start+36,flags)
    def put(rva, data):
        start = 0x400+rva-0x2000
        image[start:start+len(data)] = data
    for rva, data in ((0x2000,b".gmp\0"),(0x2010,b".ibd\0"),(0x2020,b".ibdm\0"),(0x2030,b"AStaticMeshActor\0"),(0x2050,b"FailedLoadPackage\0"),
                      (0x2080,struct.pack("<5I",0x20e0,0,0,0x20d0,0x2100)),(0x20d0,b"KERNEL32.dll\0"),
                      (0x20e0,struct.pack("<3I",0x2120,0x2140,0)),(0x2100,struct.pack("<3I",0x2120,0x2140,0)),
                      (0x2120,b"\0\0CreateFileA\0"),(0x2140,b"\0\0GetFileAttributesA\0")):
        put(rva,data)
    u32 = lambda v: struct.pack("<I", v)
    code=bytearray(b"\x68"+u32(DATA)+b"\x8b\x1d"+u32(DATA+0x100)+b"\x68"+u32(DATA+0x10)+b"\xff\xd3")
    code+=b"\xa1"+u32(DATA+0x10)+b"\x68"+u32(DATA+0x20)+b"\x68"+u32(DATA+0x31)
    failure=CODE+len(code)
    code+=b"\x68"+u32(DATA+0x50)
    code+=b"\xe8"+struct.pack("<i",TARGET-(CODE+len(code)+5))
    code+=b"\xe9"+struct.pack("<i",TARGET-(CODE+len(code)+5))
    code+=b"\xff\x15"+u32(DATA+0x104)
    # An import load followed by a register overwrite cannot prove an import call.
    code+=b"\x8b\x1d"+u32(DATA+0x100)+b"\xbb\x00\x00\x00\x00\xff\xd3\xc3"
    image[0x200:0x200+len(code)]=code
    image[0x280]=0xc3
    return bytes(image), failure


class CrosscheckTests(unittest.TestCase):
    def test_real_objdump_fixture(self):
        image,failure=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"fixture.exe"
            path.write_bytes(image)
            report=analyze(path,{".gmp":{TARGET},"loadpackage":{failure}})
        self.assertEqual(report["literal_evidence"]["gmp_extension"]["immediate_references"],1)
        ibd=report["literal_evidence"]["ibd_extension"]
        self.assertEqual((ibd["literals"],ibd["immediate_references"],ibd["absolute_memory_references"]),(1,1,1))
        self.assertEqual(report["literal_evidence"]["ibdm_extension"]["immediate_references"],1)
        self.assertEqual(report["literal_evidence"]["static_mesh_actor_name"]["immediate_references"],1)
        self.assertEqual(report["import_call_sites"],{"CreateFileA":1,"GetFileAttributesA":1})
        self.assertEqual(ibd["near_file_open_refs"],2)
        self.assertEqual(report["ghidra_leads"][".gmp"]["direct_call_sites"],1)
        self.assertEqual(report["ghidra_leads"][".gmp"]["direct_jump_sites"],1)
        self.assertEqual(report["ghidra_leads"]["loadpackage"]["direct_call_sites"],0)
        self.assertEqual(report["ghidra_leads"]["loadpackage"]["near_package_failure_candidates"],1)
        self.assertFalse(report["runtime_verified"])
        self.assertFalse(report["loader_verified"])
        self.assertFalse(report["actor_registration_verified"])
        self.assertFalse(report["game_assets_included"])
        self.assertNotIn("0x",json.dumps(report))

    def test_inconsistent_decoder_bytes_are_refused(self):
        image,_=fixture()
        with self.assertRaisesRegex(ValueError,"bytes do not match"):
            scan(PE(image),["  401000:\t68 01 20 40 00\tpush 0x402001\n"],{})

    def test_pe_and_import_bounds(self):
        image,_=fixture()
        pe=PE(image)
        self.assertEqual(pe.import_slots(),{DATA+0x100:"CreateFileA",DATA+0x104:"GetFileAttributesA"})
        with self.assertRaises(ValueError):
            pe.offset(DATA,1,code=True)
        with self.assertRaises(ValueError):
            PE(image[:0x500])
        with self.assertRaises(ValueError):
            PE(b"not a PE")

    def test_decoder_ignores_headers_and_accepts_wide_instruction(self):
        self.assertIsNone(parse_instruction("Disassembly of section .text:"))
        self.assertEqual(parse_instruction("  401000:\t68 00 20 40 00\tpush 0x402000"),
                         (CODE,b"\x68\x00\x20\x40\x00","push","0x402000"))


if __name__=="__main__":
    unittest.main()
