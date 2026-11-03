"""Synthetic regression tests for DX2 Level/Brush/Volume -> Model reference audit."""
from __future__ import annotations

from pathlib import Path
import json
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_brush_model_links as tool


def bounds_model(lo=(-64.0,-32.0,-16.0), hi=(64.0,32.0,16.0)):
    return b"\0"*9 + struct.pack("<6f", *(lo+hi)) + b"MODEL"


def level_payload(actor_refs):
    return b"L"*13 + struct.pack("<II", len(actor_refs), len(actor_refs)) + bytes(actor_refs) + b"TAIL"


class FakePackage:
    def __init__(self, licensee=68):
        self.data = b"synthetic DX2 package"
        self.version = 95
        self.licensee = licensee
        self.exports = [
            {"index":1, "name":"MyLevel","class":"Level","size":50,
             "payload":level_payload([2,4])},
            {"index":2, "name":"Brush__0","class":"Brush","size":15,"payload":b"brush"},
            {"index":3, "name":"Model__1","class":"Model","size":39,"payload":bounds_model()},
            {"index":4, "name":"NavMeshSubtractionVolume__0","class":"NavMeshSubtractionVolume",
             "size":16,"payload":b"navmesh"},
            {"index":5, "name":"Model__2","class":"Model","size":39,"payload":bounds_model()},
            {"index":6, "name":"Model__3","class":"Model","size":39,"payload":bounds_model()},
        ]

    def class_name(self, e):
        return e["class"]

    def payload(self, e):
        return e["payload"]


def fake_decode(pkg, exp, catalog):
    if exp["class"] == "Brush":
        return ({"CsgOper": 1}, [{"id":45, "encoding":"object",
                                  "value":{"ref":3,"name":"Model__1"}}])
    if exp["class"] == "NavMeshSubtractionVolume":
        return ({}, [{"id":45,"encoding":"object",
                       "value":{"ref":5,"name":"Model__2"}}])
    return ({}, [])


class BrushModelAuditTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.original = self.root / "Maps" / "synthetic.gmp"
        self.original.parent.mkdir()
        self.original.write_bytes(b"synthetic original bytes, never touch")
        self.pkg = FakePackage()
        p1 = patch.object(tool, "Package", return_value=self.pkg)
        p2 = patch.object(tool, "decode_full_actor", side_effect=fake_decode)
        p1.start()
        p2.start()
        self.addCleanup(p2.stop)
        self.addCleanup(p1.stop)

    def test_actor_to_model_and_single_unlinked_candidate(self):
        result = tool.audit_map(self.original)
        self.assertEqual(result["schema"], tool.SCHEMA)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["native_writer_executed"])
        self.assertEqual(result["level_actor_list"]["actor_count"], 2)
        self.assertEqual(result["summary"]["brush_exports"], 1)
        self.assertEqual(result["summary"]["model_exports"], 3)
        self.assertEqual(result["summary"]["brushes_with_valid_model_reference"], 1)
        self.assertEqual(result["summary"]["unique_models_referenced"], 2)
        self.assertEqual(result["summary"]["unreferenced_models"], 1)
        self.assertEqual(result["summary"]["owner_class_counts"],
                         {"Brush":1,"NavMeshSubtractionVolume":1})
        self.assertEqual(result["summary"]["models_matching_candidate_zero9_and_six_f32"],3)
        self.assertEqual(result["summary"]["brush_csg_oper_raw_tag_values"],{"1":1})
        self.assertEqual(result["unreferenced_model_exports"][0]["name"],"Model__3")
        self.assertEqual([x["model_export"] for x in result["owners"]],[3,5])
        self.assertEqual(result["owners"][0]["model_header"]["candidate_bounds_status"],
                         "six_ordered_f32_at_offset_9")
        self.assertEqual(result["owners"][0]["model_header"]["candidate_bounds_ue_units"],
                         {"min":[-64.0,-32.0,-16.0],"max":[64.0,32.0,16.0]})
        self.assertEqual(result["issues"], [])

    def test_malformed_actor_lists_refused(self):
        original = self.pkg.exports[0]["payload"]
        self.pkg.exports[0]["payload"] = b"L"*13 + struct.pack("<II",1,2) + b"\x02"
        with self.assertRaisesRegex(ValueError,"repeated Level actor count"):
            tool.audit_map(self.original)
        self.pkg.exports[0]["payload"] = level_payload([99])
        with self.assertRaisesRegex(ValueError,"invalid export ref"):
            tool.audit_map(self.original)
        self.pkg.exports[0]["payload"] = original

    def test_link_mismatch_and_duplicate_reference_detected(self):
        def duplicate(pkg, exp, catalog):
            if exp["class"] == "Brush":
                return ({"CsgOper":2}, [{"id":45,"encoding":"object",
                                         "value":{"ref":5,"name":"Model__2"}}])
            return fake_decode(pkg,exp,catalog)
        with patch.object(tool, "decode_full_actor", side_effect=duplicate):
            report = tool.audit_map(self.original)
            self.assertEqual(report["summary"]["multiply_referenced_models"],1)
            self.assertEqual(report["summary"]["unique_models_referenced"],1)
            self.assertEqual(report["summary"]["brush_csg_oper_raw_tag_values"],{"2":1})

    def test_missing_model_property_reported_not_silently_counted(self):
        def missing(pkg, exp, catalog):
            if exp["class"] == "Brush":
                return ({}, [])
            return fake_decode(pkg,exp,catalog)
        with patch.object(tool, "decode_full_actor", side_effect=missing):
            report = tool.audit_map(self.original)
            self.assertEqual(report["summary"]["brushes_with_valid_model_reference"],0)
            self.assertEqual(report["issues"][0]["issue"],"brush_missing_or_duplicate_model_property")

    def test_unknown_model_header_never_assumed_valid(self):
        self.pkg.exports[2]["payload"] = b"\xFF"*40
        report = tool.audit_map(self.original)
        self.assertEqual(report["summary"]["models_matching_candidate_zero9_and_six_f32"],2)
        self.assertEqual(report["owners"][0]["model_header"]["candidate_bounds_status"],
                         "unavailable_unrecognized_prefix")

    def test_all_source_observed_dx2_licensees_accepted(self):
        for licensee in (65, 67, 68, 69):
            with self.subTest(licensee=licensee):
                self.pkg.licensee = licensee
                report = tool.audit_map(self.original)
                self.assertEqual(report["source"]["licensee_version"], licensee)
        self.pkg.licensee = 68

    def test_refuses_thief_and_tampered_game_version(self):
        self.pkg.licensee = 133
        with self.assertRaisesRegex(ValueError,"Expected DX2 Unreal v95"):
            tool.audit_map(self.original)
        self.pkg.licensee = 68
        self.pkg.version = 94
        with self.assertRaisesRegex(ValueError,"Expected DX2 Unreal v95"):
            tool.audit_map(self.original)

    def test_exclusive_report_outside_original_map_directory(self):
        result = tool.audit_map(self.original)
        with self.assertRaisesRegex(ValueError,"outside the game map"):
            tool._write_report(result, self.original.parent/"audit.json", self.original)
        dest = self.root/"Reports"/"audit.json"
        tool._write_report(result,dest,self.original)
        self.assertEqual(json.loads(dest.read_text())["schema"],tool.SCHEMA)
        with self.assertRaises(FileExistsError):
            tool._write_report(result,dest,self.original)
        self.assertEqual(self.original.read_bytes(),b"synthetic original bytes, never touch")


if __name__ == "__main__":
    unittest.main()
