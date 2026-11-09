"""Synthetic tests for the read-only source-backed MatLib catalog worker."""
from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor" / "godot_editor" / "backend"))
sys.path.insert(0, str(ROOT / "map_exporter"))

from dx2_matlib_catalog import build_catalog_from_inventory
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


if __name__ == "__main__":
    unittest.main()
