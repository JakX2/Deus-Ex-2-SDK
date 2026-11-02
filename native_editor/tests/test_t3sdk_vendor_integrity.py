"""Asset-free check that vendored T3SDK files remain attributed upstream snapshots.

Unlike the proprietary Thief 3 editor archive, these six source files
are MIT licensed upstream and belong in the public SDK.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "third_party" / "t3sdk_assets"
BLOBS = {
    "t3common.py": "315bff659b91c924940086f9de108eaa522ae380",
    "upkg.py": "3036e2b0864ff94f65a2182541e20c65ce26874c",
    "upkgwrite.py": "d0f5e0612e91e5f5817d5b1984a80f120ac9f3ab",
    "formats.json": "493d0a1cb6ed068bbc9976d936b5376842a4002f",
    "t3props.py": "6036ac4dc52e202bce6fd62b6eb919813f3b2025",
    "t3pack.py": "5c2f9e5429914298e457334df6c57523790ba5c8",
    "LICENSE": "76e2b4bc5fc14b9098a556d5dec0b5e60d772693",
}


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class T3SDKProvenanceTests(unittest.TestCase):
    def test_mit_notice_is_retained_verbatim(self):
        text = (VENDOR / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", text)
        self.assertIn("The T3SDK contributors", text)
        self.assertIn("Permission is hereby granted", text)

    def test_upstream_sources_are_pinned_without_hidden_forks(self):
        for filename, expected_sha in BLOBS.items():
            with self.subTest(filename=filename):
                raw = (VENDOR / filename).read_bytes()
                self.assertEqual(git_blob_sha1(raw), expected_sha,
                                 "Update THIRD-PARTY provenance and review license on changes")

    def test_provenance_documents_thief_vs_dx2_boundaries(self):
        note = (VENDOR / "README_DX2.md").read_text(encoding="utf-8")
        self.assertIn("upkgwrite.py", note)
        self.assertIn("t3pack.py", note)
        self.assertIn("MIT", note)
        self.assertIn("Public availability is not evidence", note)


if __name__ == "__main__":
    unittest.main()
