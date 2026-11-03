"""Asset-free regression tests for the original T3Ed UNR/GMP research auditor."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "t3ed"))
import compare_editor_cooked as tool


class FakePackage:
    """Two intentionally synthetic UE95-like package views, no game assets."""

    def __init__(self, cooked=False):
        self.version = 95
        self.licensee = 133
        self.guid = "synthetic-map-id"
        self.names = ["None", "Level", "Brush", "Polys", "Light"]
        self.imports = [{"name": "X"}]
        self.data = b"BBAA" if cooked else b"AABBAA"
        self.exports = [
            {"class": "Level", "name": "MyLevel",
             "size": len(self.data), "payload": self.data},
            {"class": "Brush", "name": "Brush__1",
             "size": 3, "payload": b"NEW" if cooked else b"OLD"},
            {"class": "Light", "name": "Light__0",
             "size": 5, "payload": b"same!"},
        ]
        if not cooked:
            self.exports.append({"class": "Polys", "name": "Polys__1",
                                 "size": 4, "payload": b"POLY"})
        # Source has two duplicate identical "AA" render blocks;
        # multiset comparison must preserve multiplicity.
        self.bsp = (
            [{"offset": 0, "end": 2, "sections":
              [{"material": "brick", "indices": [0, 1, 2]}]},
             {"offset": 2, "end": 4, "sections":
              [{"material": "brick", "indices": [0, 1, 2]}]}]
            if cooked else
            [{"offset": 0, "end": 2, "sections":
              [{"material": "brick", "indices": [0, 1, 2]}]},
             {"offset": 2, "end": 4, "sections":
              [{"material": "brick", "indices": [0, 1, 2]}]},
             {"offset": 4, "end": 6, "sections":
              [{"material": "brick", "indices": [0, 1, 2]}]}]
        )

    def class_name(self, exp):
        return exp["class"]

    def payload(self, exp):
        return exp["payload"]


class CookAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.map_dir = self.root / "Maps"
        self.map_dir.mkdir()
        self.src = self.map_dir / "Tutorial3.unr"
        self.dst = self.map_dir / "TUTORIAL3.gmp"
        self.src.write_bytes(b"source private synthetic identity")
        self.dst.write_bytes(b"cooked private synthetic identity")
        self.source_pkg = FakePackage(cooked=False)
        self.cooked_pkg = FakePackage(cooked=True)

    def _audit(self):
        with (patch.object(tool, "Package", side_effect=lambda path: (
                self.source_pkg if path.suffix.casefold() == ".unr" else self.cooked_pkg)),
              patch.object(tool, "find_bsp", side_effect=lambda pkg: pkg.bsp)):
            return tool.audit_pair(self.src, self.dst)

    def test_structural_diff_and_bsp_multiset(self):
        doc = self._audit()
        self.assertEqual(doc["schema"], tool.SCHEMA)
        self.assertTrue(doc["read_only"])
        self.assertFalse(doc["native_compiler_executed"])
        self.assertEqual(doc["exports"]["source_only_exports_by_class"], {"Polys": 1})
        self.assertEqual(doc["exports"]["changed_payloads_by_class"],
                         {"Brush": 1, "Level": 1})
        self.assertEqual(doc["exports"]["identical_payloads_by_class"], {"Light": 1})
        self.assertEqual(doc["bsp"]["source"]["validated_render_blocks"], 3)
        self.assertEqual(doc["bsp"]["cooked"]["validated_render_blocks"], 2)
        self.assertEqual(doc["bsp"]["byte_identical_render_blocks"], 2)
        self.assertEqual(doc["bsp"]["source_only_render_blocks"], 1)
        self.assertEqual(doc["bsp"]["cooked_only_render_blocks"], 0)
        self.assertFalse(doc["bsp"]["collision_visibility_lighting_parity_proven"])
        self.assertNotIn("source private synthetic identity", json.dumps(doc))
        self.assertTrue(self.src.exists() and self.dst.exists())

    def test_refuses_mismatched_inputs_and_unrecognized_packages(self):
        with self.assertRaisesRegex(ValueError, "different files"):
            tool.audit_pair(self.src, self.src)
        with self.assertRaisesRegex(ValueError, "Expected source"):
            tool.audit_pair(self.dst, self.src)
        wrong = self.map_dir / "Other.gmp"
        wrong.write_bytes(b"x")
        with self.assertRaisesRegex(ValueError, "basenames"):
            tool.audit_pair(self.src, wrong)
        self.cooked_pkg.licensee = 68
        with self.assertRaisesRegex(ValueError, "licensee mismatch"):
            self._audit()
        self.cooked_pkg.licensee = 133
        self.cooked_pkg.version = 94
        with self.assertRaisesRegex(ValueError, "Unsupported UE package version"):
            self._audit()
        self.cooked_pkg.version = 95
        self.cooked_pkg.exports = []
        with self.assertRaisesRegex(ValueError, "Missing Level"):
            self._audit()

    def test_ambiguous_exports_never_guess_identity(self):
        self.source_pkg.exports.append({"class": "Light", "name": "Light__0",
                                        "size": 2, "payload": b"X"})
        doc = self._audit()
        self.assertEqual(doc["exports"]["ambiguous_export_identities"], [
            {"class": "Light", "name": "Light__0",
             "source_count": 2, "cooked_count": 1}])
        self.assertNotIn("Light", doc["exports"]["identical_payloads_by_class"])

    def test_case_insensitive_pairs_and_safe_exclusive_report(self):
        (self.map_dir / "Tutorial4.unr").write_bytes(b"x")
        (self.map_dir / "tutorial4.GMP").write_bytes(b"y")
        self.assertEqual([(a.name, b.name) for a, b in tool.collect_pairs(self.map_dir)],
                         [("Tutorial3.unr", "TUTORIAL3.gmp"),
                          ("Tutorial4.unr", "tutorial4.GMP")])
        doc = self._audit()
        with self.assertRaisesRegex(ValueError, "outside original map directories"):
            tool._write_report(doc, self.map_dir / "research.json", [self.src, self.dst])
        output = self.root / "Audit" / "result.json"
        tool._write_report(doc, output, [self.src, self.dst])
        self.assertEqual(json.loads(output.read_text())["schema"], tool.SCHEMA)
        with self.assertRaises(FileExistsError):
            tool._write_report(doc, output, [self.src, self.dst])
        self.assertEqual(self.src.read_bytes(), b"source private synthetic identity")
        self.assertEqual(self.dst.read_bytes(), b"cooked private synthetic identity")

    def test_nonrender_segmentation_uses_exact_render_anchors(self):
        # Two immutable render payloads, one immutable 4-byte inter-block gap.
        # The cooked Level can contain a differently-sized prefix and trailer.
        left = b"HEADER" + b"R1R1" + b"SIZE" + b"R2R2" + b"UNCHANGED" + b"old"
        right = b"HEADER++" + b"R1R1" + b"SIZE" + b"R2R2" + b"UNCHANGED" + b"new-build-data"
        sha1 = tool._sha(b"R1R1")
        sha2 = tool._sha(b"R2R2")
        src_spans = [(6, 10, sha1), (14, 18, sha2)]
        cooked_spans = [(8, 12, sha1), (16, 20, sha2)]
        report = tool._level_nonrender_regions(left, src_spans, right, cooked_spans)
        self.assertTrue(report["render_block_order_aligned"])
        self.assertFalse(report["unknown_native_sections_parsed"])
        self.assertFalse(report["collision_visibility_lighting_inferred"])
        start, middle, end = report["regions"]
        self.assertEqual(start["region"], "before_first_render_block")
        self.assertEqual(start["cooked_minus_source_bytes"], 2)
        self.assertEqual(start["aligned_common_prefix_bytes"], 6)
        self.assertTrue(middle["whole_region_equal"])
        self.assertEqual(middle["source_bytes"], 4)
        self.assertEqual(middle["aligned_common_prefix_bytes"], 4)
        self.assertEqual(end["region"], "after_last_render_block")
        self.assertEqual(end["aligned_common_prefix_bytes"], len(b"UNCHANGED"))
        self.assertEqual(end["source_divergent_bytes"], len(b"old"))
        self.assertEqual(end["cooked_divergent_bytes"], len(b"new-build-data"))
        self.assertEqual(end["cooked_divergent_sha256"], tool._sha(b"new-build-data"))
        self.assertNotIn("new-build-data", json.dumps(report))

    def test_nonrender_analysis_fails_closed_when_render_blocks_change(self):
        left = b"headerAAAAtail"
        right = b"headerBBBBtail"
        src = [(6, 10, tool._sha(b"AAAA"))]
        dst = [(6, 10, tool._sha(b"BBBB"))]
        report = tool._level_nonrender_regions(left, src, right, dst)
        self.assertFalse(report["render_block_order_aligned"])
        self.assertEqual(report["status"], "unavailable_render_blocks_changed_or_reordered")
        self.assertEqual(report["regions"], [])
        absent = tool._level_nonrender_regions(left, [], right, [])
        self.assertEqual(absent["status"], "unavailable_no_render_anchors")

    def test_nonrender_analysis_reports_full_region_equality(self):
        source = b"PREFIX" + b"RENDER" + b"suffix" 
        cooked = source
        span = [(6, 12, tool._sha(b"RENDER"))]
        report = tool._level_nonrender_regions(source, span, cooked, span)
        self.assertTrue(all(x["whole_region_equal"] for x in report["regions"]))
        self.assertTrue(all(x["source_divergent_bytes"] == 0 for x in report["regions"]))
        self.assertTrue(all(x["cooked_minus_source_bytes"] == 0 for x in report["regions"]))

    def test_case_collisions_rejected(self):
        (self.map_dir / "tutorial3.UNR").write_bytes(b"case collision")
        with self.assertRaisesRegex(ValueError, "Duplicate case-insensitive"):
            tool.collect_pairs(self.map_dir)


if __name__ == "__main__":
    unittest.main()
