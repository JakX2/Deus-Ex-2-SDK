"""Synthetic IBD integrity and same-size writer fixtures; no retail assets."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "maps"))
from dx2_ibd_integrity import (
    audit_zip, header_digest, replace_same_size, verify_bundle, write_isolated,
)


def fixture():
    raw=bytearray(6144)
    struct.pack_into("<8I", raw, 0, 0xc0000001,2048,2048,4096,2048,2048,2,3)
    for i, (offset, payload, first, count) in enumerate(
            ((2048,b"abcde",0,2),(4096,b"wxyz",2,1))):
        at=52+i*304
        pad=2048-len(payload)
        raw[offset:offset+len(payload)]=payload
        # Deliberately nonzero padding to distinguish padded from raw hashes.
        raw[offset+len(payload):offset+2048]=bytes([0xa5+i])*pad
        struct.pack_into("<5I",raw,at,offset,len(payload),pad,first,count)
        raw[at+20:at+40]=hashlib.sha1(raw[offset:offset+2048]).digest()
        raw[at+40]=21
        raw[at+41:at+43]=b"A"+bytes([ord("0")+i])
    struct.pack_into("<3I",raw,52+2*304,2,3,4)
    raw[1000]=0x42  # header alignment bytes also participate in the digest
    raw[32:52]=hashlib.sha1(raw[:2048]).digest()
    return bytes(raw)


class IBDIntegrityTests(unittest.TestCase):
    def test_header_and_padded_resource_integrity(self):
        raw=fixture()
        bundle=verify_bundle(raw)
        self.assertEqual(len(bundle.resources),2)
        self.assertEqual(bundle.part_sizes,(2,3,4))
        self.assertNotEqual(hashlib.sha1(b"abcde").digest(),bundle.resources[0].digest)
        self.assertEqual(header_digest(raw,2048),raw[32:52])

    def test_header_table_padding_and_resource_damage(self):
        for pos in (32,1000,2048,2048+5,4096+2047):
            raw=bytearray(fixture())
            raw[pos]^=1
            with self.subTest(pos=pos), self.assertRaisesRegex(ValueError,"SHA-1 mismatch"):
                verify_bundle(bytes(raw))

    def test_replacement_preserves_other_payload_padding_and_part_table(self):
        original=fixture()
        after=replace_same_size(original,0,b"12345")
        self.assertEqual(len(after),len(original))
        parsed=verify_bundle(after)
        self.assertEqual(parsed.part_sizes,(2,3,4))
        self.assertEqual(list(parsed.parts(parsed.resources[0])),[b"12",b"345"])
        self.assertEqual(after[2053:],original[2053:])
        self.assertEqual(after[92:2048],original[92:2048])
        self.assertNotEqual(after[32:52],original[32:52])
        self.assertNotEqual(after[72:92],original[72:92])
        self.assertEqual(replace_same_size(after,0,b"abcde"),original)

    def test_refuse_invalid_replacement_and_corrupt_original(self):
        raw=fixture()
        for index, payload in ((-1,b"12345"),(2,b"12345"),(True,b"1234"),
                               (0,b"123"),(0,b"123456"),(0,b"abcde")):
            with self.subTest(index=index,payload=payload), self.assertRaises(ValueError):
                replace_same_size(raw,index,payload)
        broken=bytearray(raw)
        broken[4096]^=1
        with self.assertRaisesRegex(ValueError,"resource SHA-1 mismatch"):
            replace_same_size(bytes(broken),0,b"12345")

    def test_zip_aggregate_and_corrupt_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"fixture.zip"
            with zipfile.ZipFile(path,"w") as archive:
                archive.writestr("A.ibd",fixture())
                archive.writestr("B.ibd",fixture())
                archive.writestr("ignore.txt",b"synthetic")
            report=audit_zip(path)
            self.assertEqual(report["verified_bundles"],2)
            self.assertEqual(report["verified_resource_digests"],4)
            self.assertEqual(report["verified_part_records"],6)
            self.assertFalse(report["runtime_verified"])
            with zipfile.ZipFile(path,"w") as archive:
                archive.writestr("A.ibd",fixture())
                archive.writestr("a.IBD",fixture())
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                audit_zip(path)

    def test_isolated_write_hash_pin_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"original"/"map.ibd"
            source.parent.mkdir()
            raw=fixture()
            source.write_bytes(raw)
            payload=root/"replacement.bin"
            payload.write_bytes(b"12345")
            output=root/"candidate"/source.name
            pin=hashlib.sha256(raw).hexdigest()
            with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
                write_isolated(source,payload,output,0,"0"*64)
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_isolated(source,payload,source.parent/"nested"/source.name,0,pin)
            receipt=write_isolated(source,payload,output,0,pin)
            self.assertFalse(receipt["runtime_verified"])
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(verify_bundle(output.read_bytes()).raw(
                verify_bundle(output.read_bytes()).resources[0]),b"12345")
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_isolated(source,payload,output,0,pin)
            self.assertEqual(source.read_bytes(),raw)


if __name__=="__main__":
    unittest.main()
