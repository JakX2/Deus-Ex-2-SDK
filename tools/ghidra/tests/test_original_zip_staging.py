"""Only synthetic PE headers in ZIP: no original game bytes."""
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stage_original_pe_from_zip import (
    OriginalPEError, load_expectations, stage_archive,
)


def fake_pe() -> bytes:
    data = bytearray(256)
    data[0:2] = b"MZ"
    data[0x3C:0x40] = (128).to_bytes(4, "little")
    data[128:132] = b"PE\x00\x00"
    data[132:134] = (0x14c).to_bytes(2, "little")
    return bytes(data)


class SyntheticZipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dx2-ghidra-zip-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.blob = fake_pe()
        self.archive = self.root / "system.zip"
        self.manifest = self.root / "expected.json"
        self.out = self.root / "staged"
        self.expect = [{
            "name": "DX2Synthetic.exe", "size": len(self.blob),
            "sha256": hashlib.sha256(self.blob).hexdigest(),
        }]
        self.manifest.write_text(json.dumps(self.expect))
        self._zip({"System/DX2Synthetic.exe": self.blob})

    def _zip(self, members):
        with zipfile.ZipFile(self.archive, "w") as file:
            for name, data in members.items():
                file.writestr(name, data)

    def test_verified_original_only_and_no_overwrite(self):
        result = stage_archive(self.archive, self.manifest, self.out)
        self.assertEqual(len(result), 1)
        self.assertEqual((self.out / "dx2synthetic.exe").read_bytes(), self.blob)
        self.assertEqual(load_expectations(self.manifest)["dx2synthetic.exe"][0], len(self.blob))
        with self.assertRaisesRegex(OriginalPEError, "empty"):
            stage_archive(self.archive, self.manifest, self.out)

    def test_unpinned_extras_ignored_and_duplicate_target_refused(self):
        self._zip({
            "System/DX2Synthetic.exe": self.blob,
            "System/unverified.dll": b"NOT ALLOWED",
        })
        stage_archive(self.archive, self.manifest, self.out)
        self.assertFalse((self.out / "unverified.dll").exists())
        self.out.joinpath("dx2synthetic.exe").unlink()
        self._zip({
            "System/DX2Synthetic.exe": self.blob,
            "Other/DX2Synthetic.exe": self.blob,
        })
        with self.assertRaisesRegex(OriginalPEError, "Duplicate"):
            stage_archive(self.archive, self.manifest, self.out)

    def test_wrong_hash_or_size_no_output(self):
        self.expect[0]["sha256"] = "0" * 64
        self.manifest.write_text(json.dumps(self.expect))
        with self.assertRaisesRegex(OriginalPEError, "SHA256"):
            stage_archive(self.archive, self.manifest, self.out)
        self.assertFalse(self.out.exists())

    def test_wrong_pe_header_rejected(self):
        self.blob = b"MZ" + b"\x00" * 254
        self.expect[0]["sha256"] = hashlib.sha256(self.blob).hexdigest()
        self.manifest.write_text(json.dumps(self.expect))
        self._zip({"System/DX2Synthetic.exe": self.blob})
        with self.assertRaisesRegex(OriginalPEError, "signature"):
            stage_archive(self.archive, self.manifest, self.out)

    def test_unsafe_zip_member_rejected(self):
        self._zip({"../escape.txt": b"BAD", "System/DX2Synthetic.exe": self.blob})
        with self.assertRaisesRegex(OriginalPEError, "Unsafe"):
            stage_archive(self.archive, self.manifest, self.out)
        self.assertFalse(self.out.exists())

    def test_symlink_member_rejected(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            info = zipfile.ZipInfo("System/symlink")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, b"/private/elsewhere")
            archive.writestr("System/DX2Synthetic.exe", self.blob)
        with self.assertRaisesRegex(OriginalPEError, "symbolic"):
            stage_archive(self.archive, self.manifest, self.out)

    def test_expected_manifest_must_be_exact_and_bounded(self):
        for raw in (
            [{"name": "../bad.exe", "size": 256, "sha256": "a" * 64}],
            [{"name": "untrusted.exe", "size": 256, "sha256": "G" * 64}],
            [{"name": "untrusted.exe", "size": 12, "sha256": "a" * 64}],
            [{"name": "sample.bin", "size": 256, "sha256": "a" * 64}],
            [self.expect[0], self.expect[0]],
            [],
        ):
            self.manifest.write_text(json.dumps(raw))
            with self.assertRaises(OriginalPEError):
                load_expectations(self.manifest)


if __name__ == "__main__":
    unittest.main()
