"""Synthetic-only safety tests for research opaque-span observer."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
from opaque_source_spans import (
    MAX_SPANS, SCHEMA, SpanEvidenceError,
    observe_opaque_file, observe_opaque_spans,
)


class OpaqueSourceSpanTests(unittest.TestCase):
    def setUp(self):
        self.source = bytes(range(128))
        self.digest = sha256(self.source).hexdigest()
        self.spans = [
            {"export": 7, "offset": 60, "length": 12, "evidence": "test-envelope-B"},
            {"export": 3, "offset": 8, "length": 16, "evidence": "test-envelope-A"},
        ]

    def observe(self, spans=None, **kwargs):
        return observe_opaque_spans(
            self.source, source_sha256=self.digest,
            package_identity="synthetic-fixture", spans=self.spans if spans is None else spans,
            **kwargs,
        )

    def test_deterministic_sorted_opaque_report_no_default_bytes(self):
        a = self.observe()
        self.assertEqual(a, self.observe(list(reversed(self.spans))))
        self.assertEqual(a["schema"], SCHEMA)
        self.assertEqual([r["export"] for r in a["observations"]], [3, 7])
        self.assertEqual([r["offset"] for r in a["observations"]], [8, 60])
        self.assertFalse(a["native_bsp_leaf_zone_decoded"])
        self.assertFalse(a["writable"])
        self.assertTrue(all(r["classification"] == "unknown-payload"
                            and not r["writable"] and "hex_preview" not in r
                            for r in a["observations"]))

    def test_opt_in_hex_preview_bounded(self):
        r = self.observe(preview_bytes=4)
        self.assertEqual(r["observations"][0]["hex_preview"], "08090a0b")
        with self.assertRaises(SpanEvidenceError):
            self.observe(preview_bytes=33)
        with self.assertRaises(SpanEvidenceError):
            self.observe(preview_bytes=-1)

    def test_reject_bad_boundaries(self):
        invalid = [
            {"export": 1, "offset": 127, "length": 2, "evidence": "bad"},
            {"export": 1, "offset": -1, "length": 1, "evidence": "bad"},
            {"export": 1, "offset": 0, "length": 0, "evidence": "bad"},
            {"export": 1, "offset": 2**128, "length": 1, "evidence": "bad"},
            {"export": 1, "offset": 0, "length": 2**128, "evidence": "bad"},
            {"export": 0, "offset": 1, "length": 1, "evidence": "bad"},
            {"export": True, "offset": 1, "length": 1, "evidence": "bad"},
            {"export": 2**32, "offset": 1, "length": 1, "evidence": "bad"},
            {"export": 1, "offset": 1, "length": 1, "evidence": ""},
            {"export": 1, "offset": 1, "length": 1, "evidence": "bad\nname"},
        ]
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(SpanEvidenceError):
                self.observe([row])

    def test_overlap_and_duplicate_evidence_rejected(self):
        with self.assertRaises(SpanEvidenceError):
            self.observe([
                {"export": 1, "offset": 0, "length": 10, "evidence": "A"},
                {"export": 2, "offset": 9, "length": 5, "evidence": "B"},
            ])
        with self.assertRaises(SpanEvidenceError):
            self.observe([
                {"export": 1, "offset": 0, "length": 2, "evidence": "same"},
                {"export": 2, "offset": 3, "length": 2, "evidence": "same"},
            ])

    def test_huge_count_and_bad_source_identity(self):
        rows = ({"export": 1, "offset": 0, "length": 1,
                 "evidence": "unique" + str(i)} for i in range(MAX_SPANS + 1))
        with self.assertRaises(SpanEvidenceError):
            self.observe(rows)
        with self.assertRaises(SpanEvidenceError):
            observe_opaque_spans(
                self.source, source_sha256="0" * 64,
                package_identity="synthetic-fixture", spans=self.spans)
        with self.assertRaises(SpanEvidenceError):
            observe_opaque_spans(
                bytearray(self.source), source_sha256=self.digest,
                package_identity="synthetic-fixture", spans=self.spans)


    def test_opt_in_export_containment_rejects_cross_owner_and_gaps(self):
        owners = [
            {"export": 3, "offset": 0, "length": 32},
            {"export": 7, "offset": 48, "length": 32},
        ]
        report = self.observe(export_envelopes=owners)
        self.assertTrue(report["caller_export_envelopes_checked"])
        self.assertFalse(report["export_envelopes_independently_verified"])
        self.assertEqual([x["export"] for x in report["observations"]], [3, 7])
        self.assertEqual(report, self.observe(export_envelopes=list(reversed(owners))))
        invalid_spans = [
            [{"export": 3, "offset": 28, "length": 8, "evidence": "escapes"}],
            [{"export": 7, "offset": 32, "length": 1, "evidence": "gap"}],
            [{"export": 9, "offset": 50, "length": 1, "evidence": "missing-owner"}],
            [{"export": 3, "offset": 48, "length": 1, "evidence": "wrong-owner"}],
        ]
        for spans in invalid_spans:
            with self.subTest(spans=spans), self.assertRaises(SpanEvidenceError):
                self.observe(spans, export_envelopes=owners)
        with self.assertRaises(SpanEvidenceError):
            self.observe(export_envelopes=[])

    def test_reject_ambiguous_export_envelopes_and_invalid_types(self):
        bad = [
            [{"export": 3, "offset": 0, "length": 20},
             {"export": 7, "offset": 19, "length": 20}],
            [{"export": 3, "offset": 0, "length": 20},
             {"export": 3, "offset": 48, "length": 20}],
            [{"export": 3, "offset": 0, "length": 0}],
            [{"export": True, "offset": 0, "length": 10}],
            [{"export": 3, "offset": 0, "length": 129}],
            [{"export": 3, "offset": -1, "length": 8}],
            [{"export": 3, "offset": 2**128, "length": 8}],
            [{"export": 3, "offset": 0, "length": 2**128}],
            [{"export": 2**32, "offset": 0, "length": 8}],
            [{"export": 3, "offset": 0, "length": 8}, "bad"],
            [None],
        ]
        for owners in bad:
            with self.subTest(owners=owners), self.assertRaises(SpanEvidenceError):
                self.observe(export_envelopes=owners)
        with self.assertRaises(SpanEvidenceError):
            self.observe(export_envelopes=1)
        with self.assertRaises(SpanEvidenceError):
            self.observe(export_envelopes=(
                {"export": i + 1, "offset": i, "length": 1}
                for i in range(65)
            ))

    def test_file_containment_does_not_write_or_authenticate_owners(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "invented.bin"
            path.write_bytes(self.source)
            owners = [
                {"export": 3, "offset": 8, "length": 16},
                {"export": 7, "offset": 60, "length": 12},
            ]
            result = observe_opaque_file(
                path, expected_sha256=self.digest,
                package_identity="synthetic-fixture",
                spans=self.spans, export_envelopes=owners)
            self.assertTrue(result["caller_export_envelopes_checked"])
            self.assertFalse(result["export_envelopes_independently_verified"])
            self.assertEqual(path.read_bytes(), self.source)
            with self.assertRaises(SpanEvidenceError):
                observe_opaque_file(
                    path, expected_sha256="0" * 64,
                    package_identity="synthetic-fixture",
                    spans=self.spans, export_envelopes=owners)

    def test_file_read_only_and_sha_drift(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "invented.bin"
            path.write_bytes(self.source)
            before = path.read_bytes()
            result = observe_opaque_file(
                path, expected_sha256=self.digest,
                package_identity="synthetic-fixture", spans=self.spans)
            self.assertEqual(result, self.observe())
            self.assertEqual(path.read_bytes(), before)
            path.write_bytes(self.source + b"changed")
            with self.assertRaises(SpanEvidenceError):
                observe_opaque_file(
                    path, expected_sha256=self.digest,
                    package_identity="synthetic-fixture", spans=self.spans)


if __name__ == "__main__":
    unittest.main()
