"""Asset-free tests for source-verified DX2 window glass transparency.

The retail WTO glass uses an alpha-bearing DXT3 diffuse and a native
environment stage. An opaque glTF preview falsely hides geometry behind it.
No proprietary data is used or distributed by these synthetic tests.
"""
from __future__ import annotations

from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
EXPORTER = ROOT / "map_exporter"
if str(EXPORTER) not in sys.path:
    sys.path.insert(0, str(EXPORTER))

import dx2level


class WTOGlassPreviewTests(unittest.TestCase):
    def test_exact_wto_glass_pair_only(self):
        self.assertTrue(dx2level.preview_uses_glass_alpha(
            "GEN_GlassUnBreakableA01", "GEN_GLASS-UNBREAKABLEJ01"))
        self.assertTrue(dx2level.preview_uses_glass_alpha(
            "gen_glassunbreakablea01", "gen_glass-unbreakablej01"))
        self.assertFalse(dx2level.preview_uses_glass_alpha(
            "M1WTO_Goodness01.dds", "M1WTO_Goodness01"))
        self.assertFalse(dx2level.preview_uses_glass_alpha(
            "other_fake_glass", "GEN_GLASS-UNBREAKABLEJ01"))
        self.assertFalse(dx2level.preview_uses_glass_alpha(
            "GEN_GlassUnBreakableA01", "OTHER_TEXTURE"))

    def _builder(self, material_name, diffuse):
        materials = {material_name.casefold(): (object(), object())}
        textures = {diffuse.casefold(): (types.SimpleNamespace(name="synthetic"),
                                       types.SimpleNamespace(index=1))}
        builder = dx2level.Builder({}, materials, textures)
        md = {"name": material_name, "source_bundle": "synthetic.ibd",
              "stage_mask": 65, "stages": [diffuse, "", "", "", "", "",
                                           "env_noise_01", "", ""],
              "diffuse": diffuse}
        tex = types.SimpleNamespace(faces=None, name=diffuse)
        return builder, md, tex

    def test_glass_preserves_rgba_preview_and_shader_provenance(self):
        builder, md, tex = self._builder(
            "GEN_GlassUnBreakableA01", "GEN_GLASS-UNBREAKABLEJ01")
        with (patch.object(dx2level, "parse_material", return_value=md),
              patch.object(dx2level, "parse_texture", return_value=tex),
              patch.object(dx2level, "to_png", return_value=b"synthetic_png")):
            idx = builder.material("GEN_GlassUnBreakableA01",
                                   source="synthetic.ibd")
        entry = builder.doc["materials"][idx]
        self.assertEqual(entry["alphaMode"], "BLEND")
        self.assertTrue(entry["doubleSided"])
        self.assertIn("baseColorTexture", entry["pbrMetallicRoughness"])
        self.assertIn("native cubemap unavailable",
                      entry["extras"]["DX2ShaderApproximation"])
        self.assertEqual(builder.material_diagnostics[
            "GEN_GlassUnBreakableA01"]["resolution"],
            "translucent_glass_alpha")

    def test_other_material_does_not_get_unverified_transparency(self):
        builder, md, tex = self._builder(
            "M1WTO_Goodness01", "M1WTO_Goodness01")
        with (patch.object(dx2level, "parse_material", return_value=md),
              patch.object(dx2level, "parse_texture", return_value=tex),
              patch.object(dx2level, "to_png", return_value=b"synthetic_png")):
            idx = builder.material("M1WTO_Goodness01", source="synthetic.ibd")
        self.assertNotIn("alphaMode", builder.doc["materials"][idx])
        self.assertEqual(builder.material_diagnostics[
            "M1WTO_Goodness01"]["resolution"], "textured_diffuse")


if __name__ == "__main__":
    unittest.main()
