"""Asset-free DX2 native Model face-record boundary tests."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_model_face_records as reader


def record(size=109, first=0, nverts=4, normal=(-1.,0.,0.),
           d=64., point=(-64.,0.,0.), radius=32.):
    block = bytearray(size)
    struct.pack_into("<4f", block, 0, *normal, d)
    block[49] = first
    struct.pack_into("<3f", block, size-53, *point)
    struct.pack_into("<f", block, size-41, radius)
    block[-17] = nverts
    block[-16:-8] = b"\xff"*8
    struct.pack_into("<I", block, size-4, first)
    return bytes(block)


def make_model(records):
    blob = bytearray(51)
    struct.pack_into("<6f", blob, 9, -64.,-32.,-16.,64.,32.,16.)
    blob[33] = 1
    struct.pack_into("<3f", blob, 34, 0.,0.,0.)
    struct.pack_into("<f", blob, 46, 70.)
    blob[50] = len(records)
    return bytes(blob) + b"".join(records) + bytes(12)


class FakePackage:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        self.version = 95
        self.licensee = 68
        self.exports = [
            {"name":"Model__1","index":1,"class":"Model","payload":make_model([
                record(first=0),record(size=110,first=4,nverts=5),
                record(size=110,first=9,nverts=3),
            ])},
            {"name":"Model__2","index":2,"class":"Model","payload":make_model([])},
            {"name":"Brush__1","index":3,"class":"Brush","payload":b"brush"}
        ]

    def class_name(self, record):
        return record["class"]

    def payload(self, record):
        return record["payload"]


class NativeModelFaceTests(unittest.TestCase):
    def test_mixed_109_110_face_records_and_independent_vertex_indices(self):
        blob = make_model([
            record(first=0), record(size=110,first=4,nverts=5),
            record(size=110,first=9,nverts=3),
        ])
        result = reader.inspect_model_faces(blob)
        self.assertEqual(result["status"], "decoded_candidate_face_records")
        self.assertEqual(result["record_byte_histogram"], {"109":1,"110":2})
        self.assertEqual(result["candidate_vertex_slots"], 12)
        self.assertEqual([f["record_offset"] for f in result["faces"]],[51,160,270])
        self.assertEqual(result["faces"][1]["point_offset"], 217)
        self.assertEqual([f["vertex_slot_count"] for f in result["faces"]],[4,5,3])
        self.assertTrue(all(f["plane_dot_point_error"] < .001 for f in result["faces"]))
        json.dumps(result, allow_nan=False)

    def test_bad_independent_vertex_start_refused(self):
        blob = bytearray(make_model([record(),record(first=4)]))
        blob[160+49] = 7
        self.assertEqual(reader.inspect_model_faces(bytes(blob))["status"],
                         "ambiguous_or_unrecognized_face_boundary")

    def test_bad_suffix_refused(self):
        blob = bytearray(make_model([record()]))
        blob[51+92] = 0
        self.assertEqual(reader.inspect_model_faces(bytes(blob))["status"],
                         "ambiguous_or_unrecognized_face_boundary")

    def test_plane_point_must_satisfy_plane_equation(self):
        self.assertEqual(reader.inspect_model_faces(
            make_model([record(point=(-32.,0.,0.))]))["status"],
            "ambiguous_or_unrecognized_face_boundary")

    def test_tail_truncation_refused(self):
        self.assertEqual(reader.inspect_model_faces(make_model([record()])[:-1])["status"],
                         "unrecognized_model_tail")

    def test_empty_and_unsupported_models(self):
        self.assertEqual(reader.inspect_model_faces(make_model([]))["status"],
                         "no_face_candidates")
        self.assertEqual(reader.inspect_model_faces(b"bad")["status"],
                         "unsupported_model_header")

    def test_read_only_audit_flags_and_no_source_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root/"Game"/"Synthetic.gmp"
            original.parent.mkdir()
            original.write_bytes(b"fixture-only synthetic")
            with patch.object(reader.header, "Package", side_effect=FakePackage):
                result = reader.audit_maps([original], include_faces=True)
            self.assertEqual(result["schema"], reader.SCHEMA)
            self.assertEqual(result["totals"]["model_exports"], 2)
            self.assertEqual(result["totals"]["face_records"], 3)
            self.assertEqual(result["totals"]["records_bytes_110"], 2)
            self.assertEqual(result["totals"]["vertex_slots"], 12)
            self.assertFalse(result["native_gmp_written"])
            self.assertFalse(result["vertex_positions_decoded"])
            self.assertFalse(result["bsp_or_collision_decoded"])
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                reader.audit_maps([original,original])
            with self.assertRaisesRegex(ValueError, "outside original"):
                reader.header.write_report(result, original.parent/"bad.json", [original])
            report_path = root/"Audits"/"face.json"
            reader.header.write_report(result, report_path, [original])
            with self.assertRaises(FileExistsError):
                reader.header.write_report(result, report_path, [original])
            self.assertEqual(original.read_bytes(), b"fixture-only synthetic")


if __name__ == "__main__":
    unittest.main()
