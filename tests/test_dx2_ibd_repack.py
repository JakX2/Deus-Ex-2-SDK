"""Canonical synthetic IBD repack tests, including alignment boundary relocation."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "maps"))
from dx2_ibd_integrity import verify_bundle
from dx2_ibd_repack import rebuild_canonical, write_repacked
from test_dx2_ibd_integrity import fixture


def canonical():
    raw=bytearray(fixture())
    raw[1000]=0
    struct.pack_into("<II",raw,16,5,4)
    raw[2053:4096]=bytes(4096-2053)
    raw[4100:6144]=bytes(6144-4100)
    for i, offset in enumerate((2048,4096)):
        at=52+i*304
        raw[at+20:at+40]=hashlib.sha1(raw[offset:offset+2048]).digest()
    raw[32:52]=bytes(20)
    raw[32:52]=hashlib.sha1(raw[:2048]).digest()
    return bytes(raw)


class RepackTests(unittest.TestCase):
    def test_exact_noop_and_noncanonical_source_refusal(self):
        raw=canonical()
        self.assertEqual(rebuild_canonical(raw),raw)
        verify_bundle(fixture())
        with self.assertRaisesRegex(ValueError,"not byte-identical"):
            rebuild_canonical(fixture())

    def test_growth_relocates_other_resource_and_reverse_is_exact(self):
        raw=canonical()
        replacement=[b"ab"+bytes(2048),b"cde"]
        candidate=rebuild_canonical(raw,{0:replacement})
        result=verify_bundle(candidate)
        self.assertEqual(len(candidate),len(raw)+2048)
        self.assertEqual(result.part_sizes,(2050,3,4))
        self.assertEqual(result.resources[1].offset,6144)
        self.assertEqual(result.raw(result.resources[1]),b"wxyz")
        self.assertEqual(list(result.parts(result.resources[0])),replacement)
        self.assertEqual(struct.unpack_from("<II",candidate,16),(2053,2050))
        self.assertEqual(rebuild_canonical(candidate,{0:[b"ab",b"cde"]}),raw)

    def test_multiple_parts_and_resources_resize_and_keep_metadata(self):
        raw=canonical()
        candidate=rebuild_canonical(raw,{0:[b"",b"xx"],1:[b"y"*5000]})
        parsed=verify_bundle(candidate)
        self.assertEqual(parsed.part_sizes,(0,2,5000))
        self.assertEqual(parsed.resources[1].offset,4096)
        for i in range(2):
            at=52+304*i
            self.assertEqual(candidate[at+40:at+304],raw[at+40:at+304])
        self.assertEqual(rebuild_canonical(candidate,{0:[b"ab",b"cde"],1:[b"wxyz"]}),raw)

    def test_invalid_or_noop_edits_refused(self):
        raw=canonical()
        for edits in ({},{-1:[b"ab"]},{True:[b"wxyz"]},{0:[b"only one"]},
                      {0:[b"",b""]},{0:[b"ab",b"cde"]},{0:[bytearray(b"ab"),b"cde"]}):
            with self.subTest(edits=edits),self.assertRaises(ValueError):
                rebuild_canonical(raw,edits)

    def test_numbered_part_directory_and_isolated_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"original"/"map.ibd"
            source.parent.mkdir()
            raw=canonical()
            source.write_bytes(raw)
            directory=root/"parts"
            directory.mkdir()
            (directory/"000000.bin").write_bytes(b"ab"+bytes(2048))
            (directory/"000001.bin").write_bytes(b"cde")
            output=root/"isolated"/"map.ibd"
            pin=hashlib.sha256(raw).hexdigest()
            with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
                write_repacked(source,output,0,directory,"0"*64)
            (directory/"extra.bin").write_bytes(b"extra")
            with self.assertRaisesRegex(ValueError,"exactly"):
                write_repacked(source,output,0,directory,pin)
            (directory/"extra.bin").unlink()
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_repacked(source,source.parent/"nested"/source.name,0,directory,pin)
            receipt=write_repacked(source,output,0,directory,pin)
            self.assertTrue(receipt["original_noop_byte_identical"])
            self.assertFalse(receipt["runtime_verified"])
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(len(output.read_bytes()),len(raw)+2048)
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_repacked(source,output,0,directory,pin)


if __name__=="__main__":
    unittest.main()
