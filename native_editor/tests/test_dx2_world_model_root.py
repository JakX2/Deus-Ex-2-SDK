"""Asset-free DX2 Level -> native world Model reference regression tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_level_world_model as audit


def fstr(value):
    raw = value.encode("ascii") + b"\0"
    assert len(raw) < 64
    return bytes([len(raw)]) + raw


def level_data(actor_refs=(2,), model_ref=3, *, bad_count=False, port=7777,
               options=()):
    count = len(actor_refs)
    return (bytes(13) + struct.pack("<II", count, count+int(bad_count))
            + bytes(actor_refs)
            + fstr("unreal") + fstr("") + fstr("Autoplay.unr") + fstr("")
            + bytes([len(options)]) + b"".join(fstr(s) for s in options)
            + struct.pack("<II", port, 1) + bytes([model_ref]) + bytes(20))


def world_model(node_count=13):
    assert node_count < 64
    return (bytes(9) + struct.pack("<6f", *(0.,)*6) + b"\0"
            + struct.pack("<4f", 0.,0.,0.,0.) + bytes([node_count])
            + struct.pack("<4f", 0.,1.,0.,200.) + bytes(5000))


class FakePackage:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        self.version = 95
        self.licensee = 68
        self.exports = [
            {"index":1,"name":"MyLevel","class":"Level","size":80,
             "payload":level_data()},
            {"index":2,"name":"Brush__0","class":"Brush","size":14,
             "payload":b"brush source"},
            {"index":3,"name":"Model__World","class":"Model","size":5067,
             "payload":world_model()},
            {"index":4,"name":"Model__Brush","class":"Model","size":63,
             "payload":bytes(63)},
        ]

    def class_name(self, exp):
        return exp["class"]

    def payload(self, exp):
        return exp["payload"]


class DirectLevelWorldModelTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root/"GameMaps"/"Synthetic.gmp"
        self.source.parent.mkdir()
        self.source.write_bytes(b"fixture-only private map")
        self.pkg = FakePackage(self.source)
        p = patch.object(audit, "Package", return_value=self.pkg)
        p.start()
        self.addCleanup(p.stop)

    def test_direct_ref_and_candidate_node_count(self):
        result = audit.audit_map(self.source)
        self.assertEqual(result["level_actor_count"], 1)
        self.assertEqual(result["furl"]["port"], 7777)
        self.assertEqual(result["world_model_export_ref"], 3)
        self.assertEqual(result["world_model_export_name"], "Model__World")
        self.assertEqual(result["world_model_compact_node_count_at_50"], 13)
        self.assertTrue(result["world_model_first_plane_normal_unit"])
        self.assertTrue(result["world_model_zero_bounds_and_sphere"])
        self.assertTrue(result["level_model_matches_unique_large_invalid_box_candidate"])
        self.assertTrue(result["direct_model_ref_not_in_actor_list"])
        self.assertEqual(result["source_sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_furl_options_preserve_direct_model_alignment(self):
        self.pkg.exports[0]["payload"] = level_data(options=("foo","bar"))
        self.assertEqual(audit.audit_map(self.source)["furl"]["options"], ["foo","bar"])
        self.assertEqual(audit.audit_map(self.source)["world_model_export_ref"],3)

    def test_corrupt_actor_list_and_duplicates_refused(self):
        for corrupt, expected in [
            (level_data(bad_count=True), "actor count"),
            (level_data(actor_refs=(99,)), "actor list"),
            (level_data(actor_refs=(2,2)), "Duplicate")]:
            with self.subTest(expected=expected):
                self.pkg.exports[0]["payload"] = corrupt
                with self.assertRaisesRegex(ValueError, expected):
                    audit.audit_map(self.source)

    def test_direct_ref_must_target_non_actor_model(self):
        self.pkg.exports[0]["payload"] = level_data(model_ref=2)
        with self.assertRaisesRegex(ValueError, "does not target a Model"):
            audit.audit_map(self.source)
        self.pkg.exports[0]["payload"] = level_data(actor_refs=(2,3))
        with self.assertRaisesRegex(ValueError, "appears in Level actor list"):
            audit.audit_map(self.source)

    def test_bad_model_count_and_wrong_licensee_refused(self):
        self.pkg.exports[2]["payload"] = bytes(20)
        with self.assertRaisesRegex(ValueError, "too short"):
            audit.audit_map(self.source)
        self.pkg.exports[2]["payload"] = world_model(node_count=0)
        with self.assertRaisesRegex(ValueError, "node count"):
            audit.audit_map(self.source)
        self.pkg.exports[2]["payload"] = world_model()
        self.pkg.licensee = 133
        with self.assertRaisesRegex(ValueError, "UE95 DX2"):
            audit.audit_map(self.source)

    def test_invalid_ref_and_url_port_refused(self):
        self.pkg.exports[0]["payload"] = level_data(model_ref=99)
        with self.assertRaisesRegex(ValueError, "direct Level Model export"):
            audit.audit_map(self.source)
        self.pkg.exports[0]["payload"] = level_data(port=0)
        with self.assertRaisesRegex(ValueError, "port"):
            audit.audit_map(self.source)

    def test_report_exclusive_and_source_unchanged(self):
        report = audit.audit_maps([self.source])
        self.assertFalse(report["native_world_bsp_nodes_decoded"])
        self.assertFalse(report["collision_or_physics_decoded"])
        self.assertEqual(report["summary"]["world_model_unique_large_invalid_bbox_matches"],1)
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            audit.audit_maps([self.source,self.source])
        with self.assertRaisesRegex(ValueError,"outside original"):
            audit.write_report(report,self.source.parent/"report.json",[self.source])
        target=self.root/"Reports"/"audit.json"
        audit.write_report(report,target,[self.source])
        self.assertEqual(json.loads(target.read_text())["schema"], audit.SCHEMA)
        with self.assertRaises(FileExistsError):
            audit.write_report(report,target,[self.source])
        self.assertEqual(self.source.read_bytes(),b"fixture-only private map")


if __name__ == "__main__":
    unittest.main()
