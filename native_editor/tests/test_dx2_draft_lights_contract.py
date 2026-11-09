"""Source contract checks for DX2Ed v0.57 editor-private Point/Spot lights."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DX2EdPrivateLightAuthoringContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ROOT / "native_editor/godot_editor/main.gd").read_text("utf-8")
        cls.helper = (ROOT / "native_editor/godot_editor/draft_light_authoring.gd").read_text("utf-8")
        cls.smoke = (ROOT / "native_editor/godot_editor/tests/smoke_draft_lights.gd").read_text("utf-8")
        cls.launcher = (ROOT / "prototype/START_DX2ED.cmd").read_text("utf-8")
        cls.workflow = (ROOT / ".github/workflows/native-dx2ed.yml").read_text("utf-8")
        cls.builder = (ROOT / "tools/build_dx2ed_windows_prototype.py").read_text("utf-8")
        cls.doctor = (ROOT / "prototype/prototype_doctor.py").read_text("utf-8")
        cls.manifest_test = (ROOT / "native_editor/tests/test_dx2_windows_prototype_bundle.py").read_text("utf-8")
        cls.parity = json.loads((ROOT / "native_editor/t3ed_parity.json").read_text("utf-8"))

    def test_point_and_spot_nodes_are_real_editor_only_godot_lights(self):
        self.assertIn('const KINDS = ["Point", "Spot"]', self.helper)
        self.assertIn("OmniLight3D.new()", self.helper)
        self.assertIn("SpotLight3D.new()", self.helper)
        self.assertIn('light.set_meta("editor_only", true)', self.helper)
        self.assertIn("point.omni_range", self.helper)
        self.assertIn("spot.spot_angle", self.helper)
        self.assertIn('const NODE_NAME := "DX2Ed_LightPreview_EDITOR_ONLY"', self.helper)

    def test_ui_selection_history_and_private_persistence_are_wired(self):
        for marker in (
            'DraftLight = preload("res://draft_light_authoring.gd")',
            "func _add_draft_light() -> void:",
            "func _draft_light_value_changed(value: Variant, key: String) -> void:",
            "draft_light_specs",
            '"light": draft_light_specs.get(name, {}).duplicate(true)',
            "DraftLight.validate(",
            "DraftLight.apply_to_node(",
            "func _refresh_draft_light_inspector() -> void:",
        ):
            self.assertIn(marker, self.main)

    def test_real_godot_smoke_covers_roundtrip_and_malicious_preflight(self):
        for marker in (
            "_add_draft_light()", "OmniLight3D", "SpotLight3D",
            "_draft_light_value_changed", "_save_prop_draft()",
            "_load_prop_draft(true)", "Out-of-range light metadata",
            "Negative light color", "_undo_edit()", "_redo_edit()",
            "_duplicate_selected_prop()", "_reset_selected_prop()",
        ):
            self.assertIn(marker, self.smoke)
        self.assertIn("smoke_draft_lights.gd", self.launcher)
        self.assertIn("smoke_draft_lights.gd", self.workflow)

    def test_packaging_declares_private_preview_without_native_writer(self):
        for source in (self.builder, self.doctor, self.manifest_test):
            self.assertIn("editor_private_light_preview", source)
            self.assertIn("editor_private_light_native_writer", source)
            self.assertIn("smoke_draft_lights.gd", source)

    def test_parity_keeps_native_dx2_light_semantics_unverified(self):
        lighting = next(row for row in self.parity["capabilities"] if row["id"] == "lighting")
        self.assertEqual(lighting["status"], "partial")
        self.assertIn("editor-private", lighting["evidence"])
        self.assertIn("native", lighting["next_step"].lower())


if __name__ == "__main__":
    unittest.main()
