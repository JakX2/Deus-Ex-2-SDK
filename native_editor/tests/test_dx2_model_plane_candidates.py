"""Synthetic, fixture-free DX2 candidate plane reader regression tests."""
from __future__ import annotations

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
import inspect_model_plane_candidates as planes


def model_blob(normals, *, extra=b"", valid=1):
    lo = (-128.0, -64.0, -32.0)
    hi = (128.0, 64.0, 32.0)
    center = (0.0, 0.0, 0.0)
    r = math.sqrt(128*128 + 64*64 + 32*32) * 1.001
    count = len(normals)
    head = (b"\0"*9 + struct.pack("<6f", *(lo+hi)) + bytes([valid]) +
            struct.pack("<3f", *center) + struct.pack("<f", r) + bytes([count]))
    chunks = []
    for n in normals:
        c = bytearray(109)
        struct.pack_into("<4f", c, 0, *n)
        chunks.append(bytes(c))
    return head + b"".join(chunks) + b"\0"*12 + extra


class FakePackage:
    def __init__(self, file):
        self.data = Path(file).read_bytes()
        self.version = 95
        self.licensee = 68
        self.exports = [
            {"index":1, "name":"Model__1", "kind":"Model", "payload":model_blob([
                (-1.0,0.0,0.0,128.0), (1.0,0.0,0.0,128.0),
                (0.0,-1.0,0.0,64.0), (0.0,1.0,0.0,64.0),
                (0.0,0.0,-1.0,32.0), (0.0,0.0,1.0,32.0),
            ])},
            {"index":2, "name":"Model__2", "kind":"Model", "payload":model_blob([])},
            {"index":3, "name":"Model__3", "kind":"Model",
             "payload":model_blob([(0.,0.,1.,10.)], extra=b"\x11\x22\x33")},
            {"index":4, "name":"Brush__1", "kind":"Brush", "payload":b"unused"},
        ]

    def class_name(self, record):
        return record["kind"]

    def payload(self, record):
        return record["payload"]


class CandidatePlaneTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / "game" / "Test.gmp"
        self.path.parent.mkdir()
        self.path.write_bytes(b"fixture-only DX2 map")
        patcher = patch.object(planes.header, "Package", side_effect=FakePackage)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_six_planes_at_109_byte_intervals(self):
        data = FakePackage(self.path).exports[0]["payload"]
        row = planes.inspect_planes(data)
        self.assertEqual(row["status"], "candidate_planes_decoded")
        self.assertEqual(row["candidate_plane_count"], 6)
        self.assertEqual(row["unit_length_planes"], 6)
        self.assertEqual(row["nonunit_or_nonfinite_planes"], 0)
        self.assertEqual([p["relative_payload_offset"] for p in row["planes"]],
                         [51,160,269,378,487,596])
        self.assertEqual(row["planes"][0]["candidate_normal_xyz"], [-1.,0.,0.])
        self.assertEqual(row["planes"][0]["candidate_plane_w"], 128.)

    def test_nonunit_and_nan_kept_visible_but_safe_for_json(self):
        blob = model_blob([(0.,0.,0.,1.), (float("nan"),0.,1.,5.)])
        row = planes.inspect_planes(blob)
        self.assertEqual(row["unit_length_planes"], 0)
        self.assertEqual(row["nonunit_or_nonfinite_planes"], 2)
        self.assertIsNone(row["planes"][1]["candidate_normal_xyz"][0])
        json.dumps(row, allow_nan=False)

    def test_nonconforming_length_is_skipped_not_reinterpreted(self):
        blob = model_blob([(1.,0.,0.,2.)], extra=b"123")
        row = planes.inspect_planes(blob)
        self.assertEqual(row["status"], "skip_variable_length_case")
        self.assertEqual(row["length_delta_from_simple_rule"], 3)
        self.assertNotIn("planes", row)

    def test_count_zero_and_invalid_box_skipped(self):
        self.assertEqual(planes.inspect_planes(model_blob([]))["status"], "no_candidate_planes")
        self.assertEqual(planes.inspect_planes(model_blob([], valid=0))["status"],
                         "skip_invalid_box_or_unknown_flag")
        self.assertEqual(planes.inspect_planes(b"\0")["status"],"skip_unrecognized_header")

    def test_aggregate_does_not_infer_collision(self):
        summary = planes.audit_maps([self.path])
        self.assertEqual(summary["schema"], planes.SCHEMA)
        self.assertEqual(summary["total"]["model_exports"], 3)
        self.assertEqual(summary["total"]["candidate_planes_decoded"], 1)
        self.assertEqual(summary["total"]["no_candidate_planes"], 1)
        self.assertEqual(summary["total"]["skip_variable_length_case"], 1)
        self.assertEqual(summary["total"]["planes"], 6)
        self.assertEqual(summary["total"]["unit_length_planes"], 6)
        self.assertFalse(summary["bsp_or_collision_decoded"])
        self.assertFalse(summary["native_model_polygon_decoder_complete"])
        self.assertFalse(summary["game_runtime_verified"])

    def test_reject_wrong_licensee_and_duplicate_inputs(self):
        with patch.object(planes.header, "Package") as mock:
            pkg = FakePackage(self.path)
            pkg.licensee = 133
            mock.return_value = pkg
            with self.assertRaisesRegex(ValueError, "UE95 DX2"):
                planes.audit_map(self.path)
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            planes.audit_maps([self.path,self.path])

    def test_report_exclusive_and_source_untouched(self):
        doc = planes.audit_maps([self.path])
        bad = self.path.parent / "audit.json"
        with self.assertRaisesRegex(ValueError,"outside original"):
            planes.header.write_report(doc,bad,[self.path])
        out = self.root/"reports"/"audit.json"
        planes.header.write_report(doc,out,[self.path])
        self.assertEqual(json.loads(out.read_text())["schema"],planes.SCHEMA)
        with self.assertRaises(FileExistsError):
            planes.header.write_report(doc,out,[self.path])
        self.assertEqual(self.path.read_bytes(),b"fixture-only DX2 map")


if __name__ == "__main__":
    unittest.main()
