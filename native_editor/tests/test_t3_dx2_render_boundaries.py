"""Asset-free tests for T3/DX2 cross-licensee Flesh render-block boundary audit."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "t3ed"))
import compare_t3_dx2_boundaries as tool


def make_blob(blocks, extra_tail=0):
    data = bytearray(b"H" * 4)
    spans = []
    for i in range(blocks):
        data.extend(struct.pack("<I", 80))
        start = len(data)
        header = bytearray(80)
        struct.pack_into("<10I", header, 0x28, 3, 3, 1, 1, 0, 0, 0, 1, 0xFFFFFFE0, 0)
        data.extend(header)
        end = len(data)
        spans.append((start, end, hashlib.sha256(data[start:end]).hexdigest()))
        # The following record writes the next four-byte length prefix.
    data.extend(b"TAIL" + b"T"*extra_tail)
    return bytes(data), spans


class FakePackage:
    def __init__(self, licensee, blocks, extra_tail=0):
        self.data, self.spans = make_blob(blocks, extra_tail)
        self.version = 95
        self.licensee = licensee
        self.exports = [
            {"class": "Level", "name": "MyLevel", "size": len(self.data)},
            {"class": "Brush", "name": "Brush__1", "size": 0},
            {"class": "Model", "name": "Model__1", "size": 0},
            {"class": "Camera" if licensee == 133 else "D_36", "name": "Other", "size": 0},
        ]

    def class_name(self, exp):
        return exp["class"]

    def payload(self, exp):
        return self.data


def fake_package(path):
    pkg = T3 if "T3" in path.name else DX2
    return pkg, {
        "file": path.name, "bytes": len(pkg.data), "sha256": hashlib.sha256(pkg.data).hexdigest(),
        "unreal_package_version": pkg.version, "licensee_version": pkg.licensee,
        "imports": 3, "exports": len(pkg.exports), "names": 12,
    }


def fake_flesh(pkg):
    return {
        "level_payload_bytes": len(pkg.data),
        "validated_render_blocks": len(pkg.spans), "render_triangles": 0,
        "triangle_count_by_material": {},
    }, {}, pkg.spans


T3 = FakePackage(133, 1)
DX2 = FakePackage(68, 2, 9)


class CrossLicenseeBoundaryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.t3 = self.root / "T3tutorial.gmp"
        self.dx2 = self.root / "Seattle.gmp"
        self.t3.write_bytes(b"synthetic T3")
        self.dx2.write_bytes(b"synthetic DX2")
        self.patcher1 = patch.object(tool.core, "_package", side_effect=fake_package)
        self.patcher2 = patch.object(tool.core, "_flesh_bsp", side_effect=fake_flesh)
        self.patcher1.start()
        self.patcher2.start()
        self.addCleanup(self.patcher2.stop)
        self.addCleanup(self.patcher1.stop)

    def test_shared_render_block_grammar_not_writer_interchange(self):
        result = tool.audit(self.t3, self.dx2)
        self.assertEqual(result["schema"], tool.SCHEMA)
        self.assertEqual(result["comparison"]["licensee_versions"], {"t3": 133, "dx2": 68})
        self.assertTrue(result["comparison"]["validated_render_header_layout_compatible"])
        self.assertFalse(result["comparison"]["flesh_bsp_native_writer_interchangeable"])
        self.assertFalse(result["comparison"]["collision_parity_proven"])
        self.assertEqual(result["comparison"]["shared_export_classes"], ["Brush", "Level", "Model"])
        self.assertEqual(result["comparison"]["t3_only_export_classes"], ["Camera"])
        self.assertEqual(result["comparison"]["dx2_only_export_classes"], ["D_36"])
        self.assertEqual(result["t3"]["level_regions_bytes"], {
            "prefix_before_first_render_block": 8,
            "between_render_blocks": 0,
            "validated_render_blocks": 80,
            "suffix_after_last_render_block": 4,
            "bytes_outside_validated_render_payloads": 12,
            "validated_four_byte_record_length_prefixes": 1,
            "known_length_prefix_bytes": 4,
            "unclassified_bytes_excluding_length_prefixes": 8,
        })
        self.assertEqual(result["dx2"]["between_block_gap_histogram"], {4: 1})
        self.assertTrue(result["comparison"]["four_byte_length_prefixed_render_records_shared"])
        self.assertEqual(result["dx2"]["level_regions_bytes"]["known_length_prefix_bytes"], 8)
        self.assertEqual(result["dx2"]["level_regions_bytes"]["suffix_after_last_render_block"], 13)

    def test_bad_render_header_refused(self):
        original = DX2.data
        try:
            d = bytearray(DX2.data)
            d[DX2.spans[0][0] + 0x44] = 99
            DX2.data = bytes(d)
            with self.assertRaisesRegex(ValueError, "marker missing"):
                tool.audit(self.t3, self.dx2)
        finally:
            DX2.data = original

    def test_incorrect_length_prefix_refused_even_with_valid_marker(self):
        original = DX2.data
        try:
            data = bytearray(DX2.data)
            struct.pack_into("<I", data, DX2.spans[0][0]-4, 123)
            DX2.data = bytes(data)
            with self.assertRaisesRegex(ValueError, "does not match payload byte length"):
                tool.audit(self.t3, self.dx2)
        finally:
            DX2.data = original

    def test_version_and_inputs_rejected(self):
        with self.assertRaisesRegex(ValueError, "different files"):
            tool.audit(self.t3, self.t3)
        other = self.root / "Other.unr"
        other.write_bytes(b"x")
        with self.assertRaisesRegex(ValueError, "must be .gmp"):
            tool.audit(other, self.dx2)
        old_version = DX2.version
        try:
            DX2.version = 94
            with self.assertRaisesRegex(ValueError, "Expected two Unreal v95"):
                tool.audit(self.t3, self.dx2)
        finally:
            DX2.version = old_version

    def test_read_only_report_guard(self):
        doc = tool.audit(self.t3, self.dx2)
        with self.assertRaisesRegex(ValueError, "outside original map directories"):
            tool.core._write_report(doc, self.t3.parent / "out.json", [self.t3, self.dx2])
        outside = self.root.parent / (self.root.name + "_report.json")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        tool.core._write_report(doc, outside, [self.t3, self.dx2])
        with self.assertRaises(FileExistsError):
            tool.core._write_report(doc, outside, [self.t3, self.dx2])
        self.assertEqual(self.t3.read_bytes(), b"synthetic T3")
        self.assertEqual(self.dx2.read_bytes(), b"synthetic DX2")


if __name__ == "__main__":
    unittest.main()
