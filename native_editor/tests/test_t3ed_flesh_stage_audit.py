"""Synthetic, asset-free tests for the native T3Ed .unr stage comparison."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "t3ed"))
import compare_editor_stages as tool


def make_block(start, end, label, xyz=0):
    return {
        "offset": start, "end": end, "id": 17,
        "vertices": [
            ((float(xyz + i), 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0))
            for i in range(3)
        ],
        "sections": [{"material": label, "indices": [0, 1, 2]}],
    }


class FakePackage:
    def __init__(self, after=False):
        self.version = 95
        self.licensee = 133
        self.guid = "synthetic-id"
        self.names = ["None", "MyLevel", "Brush", "Brick"]
        self.imports = []
        # The only byte-identical render block ("KEEP") moved between stages.
        self.data = b"BBBB_CCCC__KEEP" if after else b"AAAA__KEEP"
        self.exports = [
            {"class": "Level", "name": "MyLevel", "size": len(self.data),
             "payload": self.data},
            {"class": "Brush", "name": "Brush__1", "size": 4,
             "payload": b"same"},
        ]
        if after:
            self.bsp = [
                make_block(0, 4, "brick", 0),
                make_block(5, 9, "brick", 4),
                make_block(11, 15, "brick", 8),
            ]
        else:
            self.bsp = [
                make_block(0, 4, "brick", 0),
                make_block(6, 10, "brick", 8),
            ]

    def class_name(self, exp):
        return exp["class"]

    def payload(self, exp):
        return exp["payload"]


class FleshStageAuditTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.before = self.root / "After_Unreal_BSP" / "DX2SDK_Geo_Test.unr"
        self.after = self.root / "After_Flesh_BSP" / "DX2SDK_Geo_Test.unr"
        self.before.parent.mkdir()
        self.after.parent.mkdir()
        self.before.write_bytes(b"synthetic before")
        self.after.write_bytes(b"synthetic after")
        self.a = FakePackage()
        self.b = FakePackage(after=True)

    def audit(self):
        with patch.object(tool.core, "Package", side_effect=lambda path: (
                self.a if Path(path).parent.name == "After_Unreal_BSP" else self.b)), \
             patch.object(tool.core, "find_bsp", side_effect=lambda pkg: pkg.bsp):
            return tool.audit_stages(self.before, self.after)

    def test_additional_render_blocks_and_unique_hash_matching(self):
        result = self.audit()
        self.assertEqual(result["schema"], tool.SCHEMA)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["build_commands_observed_by_tool"])
        self.assertFalse(result["game_runtime_verified"])
        self.assertEqual(result["before"]["render"]["validated_render_blocks"], 2)
        self.assertEqual(result["after"]["render"]["validated_render_blocks"], 3)
        self.assertEqual(result["deltas"]["render_blocks"], 1)
        self.assertEqual(result["deltas"]["render_vertices"], 3)
        self.assertEqual(result["deltas"]["render_triangles"], 1)
        self.assertEqual(result["render_block_byte_matches"],
                         {"unchanged": 1, "before_only": 1, "after_only": 2})
        same = result["render_block_correspondence"]
        self.assertEqual([(x["before_index"], x["after_index"])
                          for x in same["byte_identical_block_matches"]], [(1, 2)])
        self.assertEqual(same["before_only_block_indices"], [0])
        self.assertEqual(same["after_only_block_indices"], [0, 1])
        self.assertFalse(same["spatial_lineage_proven"])
        self.assertEqual(result["exports"]["identical_payloads_by_class"], {"Brush": 1})
        self.assertNotIn("synthetic before", json.dumps(result))
        self.assertEqual(self.before.read_bytes(), b"synthetic before")

    def test_rejects_wrong_extension_name_version_or_missing_blocks(self):
        with self.assertRaisesRegex(ValueError, "different files"):
            tool.audit_stages(self.before, self.before)
        other = self.root / "After_Flesh_BSP" / "Other.unr"
        other.write_bytes(b"x")
        with self.assertRaisesRegex(ValueError, "basenames"):
            tool.audit_stages(self.before, other)
        with self.assertRaisesRegex(ValueError, "two .unr"):
            tool.audit_stages(self.before, self.after.with_suffix(".gmp"))
        self.b.licensee = 68
        with self.assertRaisesRegex(ValueError, "licensee mismatch"):
            self.audit()
        self.b.licensee = 133
        self.b.bsp = []
        with self.assertRaisesRegex(ValueError, "No validated Flesh render blocks"):
            self.audit()

    def test_report_is_exclusive_and_outside_input_folders(self):
        result = self.audit()
        with self.assertRaisesRegex(ValueError, "outside original map directories"):
            tool.core._write_report(result, self.before.parent / "report.json",
                                    [self.before, self.after])
        target = self.root / "audit" / "report.json"
        tool.core._write_report(result, target, [self.before, self.after])
        parsed = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(parsed["deltas"]["render_triangles"], 1)
        with self.assertRaises(FileExistsError):
            tool.core._write_report(result, target, [self.before, self.after])


if __name__ == "__main__":
    unittest.main()
