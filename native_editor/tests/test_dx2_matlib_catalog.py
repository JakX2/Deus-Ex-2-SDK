"""Synthetic tests for the read-only source-backed MatLib catalog worker."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor" / "godot_editor" / "backend"))
sys.path.insert(0, str(ROOT / "map_exporter"))

from dx2_matlib_catalog import (
    audit_catalog_file,
    audit_stage_mask_correspondence,
    build_catalog_from_inventory,
)
from dx2textures import Texture


def material_record(name: str, stages: list[str]) -> dict:
    return {
        "name": name,
        "source_bundle": "synthetic.ibd",
        "version": 1,
        "flags": 3,
        "stage_mask": 1,
        "category_id": 7,
        "source": "synthetic-fixture",
        "colors": [[1.0, 1.0, 1.0, 1.0] for _ in range(3)],
        "params": [0.25, 0.5, 0.75],
        "stages": stages,
    }


class MatLibCatalogTests(unittest.TestCase):
    def setUp(self):
        self.texture = Texture(
            name="T_SYNTH_DIFFUSE",
            fmt="BGRA8",
            width=2,
            height=2,
            usage=0,
            mipmaps=[(2, 2, bytes([0, 0, 255, 255] * 4))],
            source="synthetic.ibd",
        )
        self.materials = {
            "m_synthetic": material_record(
                "M_SYNTHETIC", ["T_SYNTH_DIFFUSE", "T_MISSING"] + [""] * 7
            )
        }
        self.duplicates = {"textures": 0, "materials": 0}
        self.skipped = []
        self.sources = [{
            "path": "/private/synthetic.ibd",
            "sha256": "a" * 64,
            "bytes": 128,
        }]

    def test_catalog_resolves_stages_and_writes_hashed_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            preview_dir = Path(temporary) / "catalog_previews"
            catalog = build_catalog_from_inventory(
                {"t_synth_diffuse": self.texture},
                self.materials,
                self.duplicates,
                self.skipped,
                self.sources,
                preview_dir,
            )
            self.assertEqual(catalog["schema"], "DX2Ed-MatLib-catalog-v1")
            self.assertIs(catalog["read_only"], True)
            self.assertIs(catalog["native_writer_enabled"], False)
            self.assertIs(catalog["source_bytes_modified"], False)
            self.assertEqual(catalog["material_count"], 1)
            self.assertEqual(catalog["texture_count"], 1)
            self.assertEqual(catalog["preview_count"], 1)
            self.assertEqual(catalog["unresolved_stage_count"], 1)
            stages = catalog["materials"][0]["stages"]
            self.assertEqual(len(stages), 9)
            self.assertTrue(stages[0]["resolved"])
            self.assertFalse(stages[1]["resolved"])
            texture = stages[0]["texture"]
            self.assertEqual(texture["usage_code"], 0)
            self.assertEqual(texture["usage"], "diffuse")
            preview = Path(temporary) / texture["preview_path"]
            self.assertTrue(preview.is_file())
            content = preview.read_bytes()
            self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(hashlib.sha256(content).hexdigest(), texture["preview_sha256"])

    def test_preview_limit_keeps_metadata_without_emitting_png(self):
        with tempfile.TemporaryDirectory() as temporary:
            catalog = build_catalog_from_inventory(
                {"t_synth_diffuse": self.texture},
                self.materials,
                self.duplicates,
                self.skipped,
                self.sources,
                Path(temporary) / "limited_previews",
                max_previews=0,
            )
            self.assertEqual(catalog["preview_count"], 0)
            texture = catalog["materials"][0]["stages"][0]["texture"]
            self.assertEqual(texture["preview_path"], "")
            self.assertEqual(texture["preview_omitted_reason"], "preview_count_limit")

    def test_unknown_texture_usage_code_is_preserved_without_guessing(self):
        unknown = Texture(
            name="T_UNKNOWN_USAGE",
            fmt="BGRA8",
            width=2,
            height=2,
            usage=99,
            mipmaps=[(2, 2, bytes([0, 0, 0, 255] * 4))],
            source="synthetic.ibd",
        )
        stages = ["T_UNKNOWN_USAGE"] + [""] * 8
        with tempfile.TemporaryDirectory() as temporary:
            catalog = build_catalog_from_inventory(
                {"t_unknown_usage": unknown},
                {"unknown": material_record("M_UNKNOWN", stages)},
                self.duplicates,
                self.skipped,
                self.sources,
                Path(temporary) / "unknown_previews",
            )
            texture = catalog["materials"][0]["stages"][0]["texture"]
            self.assertEqual(texture["usage_code"], 99)
            self.assertEqual(texture["usage"], "99")

    def test_out_of_range_texture_usage_code_is_rejected(self):
        invalid = Texture(
            name="T_INVALID_USAGE",
            fmt="BGRA8",
            width=2,
            height=2,
            usage=-1,
            mipmaps=[(2, 2, bytes([0, 0, 0, 255] * 4))],
            source="synthetic.ibd",
        )
        stages = ["T_INVALID_USAGE"] + [""] * 8
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "usage code"):
                build_catalog_from_inventory(
                    {"t_invalid_usage": invalid},
                    {"invalid": material_record("M_INVALID", stages)},
                    self.duplicates,
                    self.skipped,
                    self.sources,
                    Path(temporary) / "invalid_usage_previews",
                )

    def test_invalid_stage_shape_is_rejected_before_catalog_creation(self):
        invalid = {"bad": material_record("M_BAD", ["T_ONLY"])}
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "nine stage slots"):
                build_catalog_from_inventory(
                    {"t_only": self.texture},
                    invalid,
                    self.duplicates,
                    self.skipped,
                    self.sources,
                    Path(temporary) / "bad_previews",
                )

    def test_preview_filename_is_not_derived_from_untrusted_resource_name(self):
        hostile = Texture(
            name="../../outside",
            fmt="BGRA8",
            width=2,
            height=2,
            usage=0,
            mipmaps=[(2, 2, bytes([0, 255, 0, 255] * 4))],
            source="synthetic.ibd",
        )
        stages = ["../../outside"] + [""] * 8
        with tempfile.TemporaryDirectory() as temporary:
            preview_dir = Path(temporary) / "safe_previews"
            catalog = build_catalog_from_inventory(
                {"../../outside": hostile},
                {"hostile": material_record("M_HOSTILE", stages)},
                self.duplicates,
                self.skipped,
                self.sources,
                preview_dir,
            )
            texture = catalog["materials"][0]["stages"][0]["texture"]
            relative = Path(texture["preview_path"])
            self.assertFalse(relative.is_absolute())
            self.assertNotIn("..", relative.parts)
            self.assertTrue((Path(temporary) / relative).is_file())


    def test_stage_mask_audit_matches_named_slots_and_counts_usage_per_slot(self):
        normal = Texture(
            name="T_SYNTH_NORMAL",
            fmt="BGRA8",
            width=2,
            height=2,
            usage=1,
            mipmaps=[(2, 2, bytes([128, 128, 255, 255] * 4))],
            source="synthetic.ibd",
        )
        record = material_record(
            "M_EXACT", ["T_SYNTH_DIFFUSE", "T_SYNTH_NORMAL"] + [""] * 7
        )
        record["stage_mask"] = 0x3
        with tempfile.TemporaryDirectory() as temporary:
            catalog = build_catalog_from_inventory(
                {"t_synth_diffuse": self.texture, "t_synth_normal": normal},
                {"exact": record},
                self.duplicates,
                self.skipped,
                self.sources,
                Path(temporary) / "audit_previews",
            )
            report = audit_stage_mask_correspondence(catalog["materials"])
        self.assertEqual(report["exact_low9_match_count"], 1)
        self.assertEqual(report["exact_nonempty_low9_match_count"], 1)
        self.assertEqual(report["mismatch_count"], 0)
        self.assertEqual(report["per_slot"][0]["usage_code_counts"][0]["code"], 0)
        self.assertEqual(report["per_slot"][1]["usage_code_counts"][0]["code"], 1)
        self.assertIs(report["source_bytes_modified"], False)
        self.assertIs(report["native_writer_enabled"], False)

    def test_stage_mask_audit_reports_mismatch_and_high_bits_without_guessing(self):
        normal = Texture(
            name="T_SYNTH_NORMAL",
            fmt="BGRA8",
            width=2,
            height=2,
            usage=1,
            mipmaps=[(2, 2, bytes([128, 128, 255, 255] * 4))],
            source="synthetic.ibd",
        )
        record = material_record(
            "M_MISMATCH", ["T_SYNTH_DIFFUSE", "", "T_SYNTH_NORMAL"] + [""] * 6
        )
        record["stage_mask"] = 0x201
        with tempfile.TemporaryDirectory() as temporary:
            catalog = build_catalog_from_inventory(
                {"t_synth_diffuse": self.texture, "t_synth_normal": normal},
                {"mismatch": record},
                self.duplicates,
                self.skipped,
                self.sources,
                Path(temporary) / "mismatch_previews",
            )
            report = audit_stage_mask_correspondence(catalog["materials"])
        self.assertEqual(report["mismatch_count"], 1)
        self.assertEqual(report["high_bits_set_count"], 1)
        example = report["mismatch_examples"][0]
        self.assertEqual(example["raw_stage_mask"], 0x201)
        self.assertEqual(example["named_slot_mask"], 0x5)
        self.assertEqual(example["low9_mask"], 0x1)
        self.assertEqual(example["xor_mask"], 0x4)

    def test_stage_mask_audit_rejects_malformed_masks_and_usage_codes(self):
        empty_stages = [
            {"index": index, "name": "", "resolved": False}
            for index in range(9)
        ]
        bad_mask = {
            "name": "M_BAD_MASK",
            "stage_mask": True,
            "flags": 0,
            "category_id": 0,
            "stages": empty_stages,
        }
        with self.assertRaisesRegex(ValueError, "stage_mask"):
            audit_stage_mask_correspondence([bad_mask])

        bad_usage_stages = [dict(stage) for stage in empty_stages]
        bad_usage_stages[0] = {
            "index": 0,
            "name": "T_BAD_USAGE",
            "resolved": True,
            "texture": {"usage_code": -1},
        }
        bad_usage = {
            "name": "M_BAD_USAGE",
            "stage_mask": 1,
            "flags": 0,
            "category_id": 0,
            "stages": bad_usage_stages,
        }
        with self.assertRaisesRegex(ValueError, "usage_code"):
            audit_stage_mask_correspondence([bad_usage])

    def test_audit_catalog_file_is_read_only_and_omits_private_source_paths(self):
        record = material_record("M_AUDIT_FILE", ["T_SYNTH_DIFFUSE"] + [""] * 8)
        record["stage_mask"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            catalog = build_catalog_from_inventory(
                {"t_synth_diffuse": self.texture},
                {"audit": record},
                self.duplicates,
                self.skipped,
                self.sources,
                Path(temporary) / "file_audit_previews",
            )
            path = Path(temporary) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            report = audit_catalog_file(path)
            self.assertEqual(report["material_count"], 1)
            self.assertNotIn("source_files", report)
            self.assertNotIn("path", report)
            catalog["native_writer_enabled"] = True
            path.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "read-only"):
                audit_catalog_file(path)



    def test_stage_mask_audit_groups_raw_category_flags_and_bounds_cohorts(self):
        def record(name, category, flags, stage_mask, occupied_slots):
            stages = [
                {
                    "index": index,
                    "name": "T_SLOT_%d" % index if index in occupied_slots else "",
                    "resolved": False,
                }
                for index in range(9)
            ]
            return {
                "name": name,
                "category_id": category,
                "flags": flags,
                "stage_mask": stage_mask,
                "stages": stages,
            }

        materials = [
            record("M_EXACT", 7, 3, 0x003, {0, 1}),
            record("M_MISMATCH", 7, 3, 0x201, {0, 2}),
            record("M_OTHER", 42, 16, 0x001, {0}),
        ]
        report = audit_stage_mask_correspondence(materials)
        self.assertEqual(report["category_flag_cohort_count"], 2)
        self.assertEqual(report["category_flag_cohorts_omitted"], 0)
        first, second = report["category_flag_cohorts"]
        self.assertEqual((first["category_id"], first["flags"]), (7, 3))
        self.assertEqual(first["material_count"], 2)
        self.assertEqual(first["exact_low9_match_count"], 1)
        self.assertEqual(first["mismatch_count"], 1)
        self.assertEqual(first["high_bits_set_count"], 1)
        self.assertEqual(
            {item["mask"] for item in first["top_named_slot_masks"]}, {0x3, 0x5}
        )
        self.assertEqual((second["category_id"], second["flags"]), (42, 16))
        self.assertEqual(second["material_count"], 1)
        self.assertNotIn("name", first)
        self.assertNotIn("source_files", report)

        many = [
            record("M_COHORT_%02d" % index, index, 100 + index, 0, set())
            for index in range(26)
        ]
        bounded = audit_stage_mask_correspondence(many)
        self.assertEqual(bounded["category_flag_cohort_count"], 26)
        self.assertEqual(len(bounded["category_flag_cohorts"]), 24)
        self.assertEqual(bounded["category_flag_cohorts_omitted"], 2)


if __name__ == "__main__":
    unittest.main()
