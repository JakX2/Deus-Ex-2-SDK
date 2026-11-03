"""Asset-free checks for the source-observed DX2 native Model header/size audit."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_model_serialization as model


def model_bytes(half=(32.0, 64.0, 128.0), center=(100.0, 200.0, 300.0),
                count=0, *, radius=None, valid=1, extra=b"", prefix=b"\0"*9):
    lo = tuple(c - h for c, h in zip(center, half))
    hi = tuple(c + h for c, h in zip(center, half))
    r = math.sqrt(sum(x*x for x in half)) * 1.001 if radius is None else radius
    return (prefix + struct.pack("<6f", *(lo + hi)) + bytes([valid]) +
            struct.pack("<3f", *center) + struct.pack("<f", r) +
            bytes([count]) + b"\0" * (12 + 109 * count) + extra)


def invalid_world_model(size=6000):
    return b"\0"*50 + b"\0" * (size-50)


class FakePackage:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        self.version = 95
        self.licensee = 68
        self.exports = [
            {"index":1, "name":"Model__Small", "kind":"Model",
             "payload":model_bytes()},
            {"index":2, "name":"Model__6", "kind":"Model",
             "payload":model_bytes(count=6)},
            {"index":3, "name":"Model__WorldCandidate", "kind":"Model",
             "payload":invalid_world_model()},
            {"index":4, "name":"Brush__2", "kind":"Brush", "payload":b"not a model"},
        ]

    def class_name(self, entry):
        return entry["kind"]

    def payload(self, entry):
        return entry["payload"]


class ModelHeaderAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.gmp = self.root / "game" / "Map.gmp"
        self.gmp.parent.mkdir()
        self.gmp.write_bytes(b"private user-owned synthetic map")
        p = patch.object(model, "Package", side_effect=FakePackage)
        p.start()
        self.addCleanup(p.stop)

    def test_box_and_sphere_positions_and_empirical_size_rule(self):
        data = model_bytes(count=6)
        row = model.inspect_model(data)
        self.assertEqual(len(data), 717)
        self.assertTrue(row["header_recognized"])
        self.assertEqual(row["box_valid_byte"], 1)
        self.assertEqual(row["bbox_min"], [68.,136.,172.])
        self.assertEqual(row["bbox_max"], [132.,264.,428.])
        self.assertEqual(row["sphere_center"], [100.,200.,300.])
        self.assertTrue(row["center_matches_bbox_midpoint"])
        self.assertTrue(row["radius_matches_1p001_halfdiagonal"])
        self.assertTrue(row["length_formula_exact"])
        self.assertEqual(row["observed_count_byte_at_50"], 6)

    def test_one_anomalous_radius_is_reported_not_suppressed(self):
        row = model.inspect_model(model_bytes(radius=15))
        self.assertTrue(row["center_matches_bbox_midpoint"])
        self.assertFalse(row["radius_matches_1p001_halfdiagonal"])

    def test_three_extra_bytes_preserved_as_size_outlier(self):
        row = model.inspect_model(model_bytes(count=19, extra=b"\x01\x02\x03"))
        self.assertFalse(row["length_formula_exact"])
        self.assertEqual(row["length_formula_delta"], 3)
        self.assertEqual(row["payload_bytes"], 2137)

    def test_empty_bounds_large_model_not_treated_as_compiled_world_bsp(self):
        row = model.inspect_model(invalid_world_model())
        self.assertEqual(row["box_state"], "marked_invalid")
        self.assertTrue(row["empty_zero_box_and_sphere"])
        self.assertFalse(row["length_formula_exact"])
        self.assertNotIn("center_matches_bbox_midpoint", row)

    def test_header_fail_closed(self):
        self.assertFalse(model.inspect_model(b"\0"*12)["header_recognized"])
        self.assertFalse(model.inspect_model(model_bytes(prefix=b"\xFF"+b"\0"*8))["header_recognized"])
        invalid = model_bytes(valid=4)
        row = model.inspect_model(invalid)
        self.assertEqual(row["reason"], "unexpected_box_valid_byte")
        strange = bytearray(model_bytes())
        struct.pack_into("<f", strange, 9, float("nan"))
        self.assertEqual(model.inspect_model(bytes(strange))["reason"],
                         "nonfinite_or_unordered_bounds_or_sphere")

    def test_map_audit_summary_and_licenses(self):
        report = model.audit_map(self.gmp)
        self.assertEqual(report["source"]["licensee"], 68)
        self.assertEqual(report["source"]["model_exports"], 3)
        self.assertEqual(report["summary"]["valid_box_flag"], 2)
        self.assertEqual(report["summary"]["invalid_box_flag"], 1)
        self.assertEqual(report["summary"]["large_invalid_box_candidates"], 1)
        self.assertEqual(report["summary"]["length_formula_exact"], 2)
        self.assertEqual(report["summary"]["length_histogram"]["717"], 1)
        self.assertEqual(len(report["models"]), 3)
        self.assertFalse(report["anomalies"])
        for licensee in (65,67,68,69):
            with patch.object(model, "Package") as mock:
                fake = FakePackage(self.gmp)
                fake.licensee = licensee
                mock.return_value = fake
                self.assertEqual(model.audit_map(self.gmp)["source"]["licensee"], licensee)
        with patch.object(model, "Package") as mock:
            fake = FakePackage(self.gmp)
            fake.licensee = 133
            mock.return_value = fake
            with self.assertRaisesRegex(ValueError, "UE95 DX2"):
                model.audit_map(self.gmp)

    def test_summary_only_and_bad_records(self):
        with patch.object(model, "Package") as mock:
            fake = FakePackage(self.gmp)
            fake.exports[0]["payload"] = model_bytes(radius=1)
            mock.return_value = fake
            result = model.audit_map(self.gmp, include_rows=False)
        self.assertNotIn("models", result)
        self.assertEqual(result["summary"]["valid_box_flag"], 2)
        self.assertEqual(result["summary"]["radius_matches_1p001_halfdiagonal"], 1)
        self.assertEqual(result["anomalies"][0]["failed_observations"],
                         ["radius_matches_1p001_halfdiagonal"])

    def test_output_never_overwrites_or_leaks_source_location(self):
        p2 = self.root / "other" / "Extra.gmp"
        p2.parent.mkdir()
        p2.write_bytes(b"synthetic map 2")
        result = model.audit_maps([self.gmp, p2], include_rows=False)
        self.assertEqual(result["maps_scanned"], 2)
        self.assertEqual(result["aggregate"]["models"], 6)
        self.assertNotIn("models", result["maps"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            model.audit_maps([self.gmp, self.gmp])
        with self.assertRaisesRegex(ValueError, "outside original"):
            model.write_report(result, self.gmp.parent / "audit.json", [self.gmp,p2])
        target = self.root / "reports" / "audit.json"
        model.write_report(result, target, [self.gmp,p2])
        saved = json.loads(target.read_text())
        self.assertEqual(saved["schema"], model.SCHEMA)
        self.assertNotIn(str(self.gmp.parent), target.read_text())
        with self.assertRaises(FileExistsError):
            model.write_report(result, target, [self.gmp,p2])
        self.assertEqual(self.gmp.read_bytes(), b"private user-owned synthetic map")

    def test_anomalous_length_without_spurious_radius_anomaly(self):
        with patch.object(model, "Package") as mock:
            fake = FakePackage(self.gmp)
            fake.exports[0]["payload"] = model_bytes(count=19, extra=b"XYZ")
            mock.return_value = fake
            report = model.audit_map(self.gmp)
        self.assertEqual(report["anomalies"][0]["failed_observations"], ["length_formula_exact"])
        self.assertEqual(report["anomalies"][0]["length_formula_delta"], 3)


if __name__ == "__main__":
    unittest.main()
