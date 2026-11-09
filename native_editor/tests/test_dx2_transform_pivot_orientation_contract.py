"""Source contracts for DX2Ed v0.55 transform pivot/orientation preferences."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
GODOT = ROOT / "native_editor" / "godot_editor"


class DX2EdTransformPivotOrientationContractTests(unittest.TestCase):
    def test_helper_has_bounded_pivot_orientation_and_cursor_contracts(self):
        helper = (GODOT / "orthographic_authoring_guides.gd").read_text("utf-8")
        self.assertIn('const PIVOT_MODES := ["median", "active", "cursor"]', helper)
        self.assertIn('const ORIENTATION_MODES := ["world", "local"]', helper)
        self.assertIn("static func validate_cursor_position", helper)
        self.assertIn("static func gizmo_basis", helper)
        self.assertIn("mode != PERSPECTIVE", helper)

    def test_editor_exposes_preferences_and_undoable_cursor(self):
        main = (GODOT / "main.gd").read_text("utf-8")
        for token in (
            "transform_pivot_select", "transform_orientation_select",
            "_selection_pivot_median", '_selection_pivot() -> Vector3:',
            "_set_transform_cursor_from_selection", "_refresh_transform_cursor_marker",
            '"cursor_position": transform_cursor_position',
            "gizmo_root.global_basis = _gizmo_root_basis()",
            "best_axis = (gizmo_basis * best_axis).normalized()",
        ):
            self.assertIn(token, main)
        self.assertIn('value.get("pivot_mode"', main)
        self.assertIn('value.get("orientation_mode"', main)

    def test_real_godot_smoke_is_in_windows_and_linux_launchers(self):
        smoke = "native_editor/godot_editor/tests/smoke_transform_pivot_orientation.gd"
        builder = (ROOT / "tools" / "build_dx2ed_windows_prototype.py").read_text("utf-8")
        doctor = (ROOT / "prototype" / "prototype_doctor.py").read_text("utf-8")
        launcher = (ROOT / "prototype" / "START_DX2ED.cmd").read_text("utf-8")
        workflow = (ROOT / ".github" / "workflows" / "native-dx2ed.yml").read_text("utf-8")
        self.assertIn(smoke, builder)
        self.assertIn(smoke, doctor)
        self.assertIn("smoke_transform_pivot_orientation.gd", launcher)
        self.assertIn("smoke_transform_pivot_orientation.gd", workflow)

    def test_bundle_declares_preview_only_writer_boundary(self):
        builder = (ROOT / "tools" / "build_dx2ed_windows_prototype.py").read_text("utf-8")
        doctor = (ROOT / "prototype" / "prototype_doctor.py").read_text("utf-8")
        self.assertIn('"editor_transform_pivot_modes": True', builder)
        self.assertIn('"editor_transform_orientation_modes": True', builder)
        self.assertIn('"editor_transform_cursor_private_persistence": True', builder)
        self.assertIn('"editor_transform_native_writer": False', builder)
        self.assertIn('manifest.get("editor_transform_native_writer") is not False', doctor)


if __name__ == "__main__":
    unittest.main()
