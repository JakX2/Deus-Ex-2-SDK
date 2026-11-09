"""Contract tests for the v0.53 independent quad-camera workspace."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DX2EdMultiViewWorkspaceContractTests(unittest.TestCase):
    def test_four_canonical_views_have_independent_bounded_state(self):
        guides = (ROOT / "native_editor/godot_editor/orthographic_authoring_guides.gd").read_text("utf-8")
        self.assertIn('const VIEW_IDS := ["perspective", "top", "front", "side"]', guides)
        self.assertIn("static func validate_view_states(value: Variant) -> Variant:", guides)
        self.assertIn("absf(coordinate) > 1000000.0", guides)
        self.assertIn("distance > 200000.0", guides)
        self.assertIn("static func grid_layer_mask(view_id: String) -> int:", guides)

    def test_quad_viewports_share_preview_world_but_isolate_camera_and_grid(self):
        main = (ROOT / "native_editor/godot_editor/main.gd").read_text("utf-8")
        self.assertIn("viewport.world_3d = world_view.world_3d", main)
        self.assertIn("view_camera.cull_mask = 1 | OrthoGuides.grid_layer_mask(view_id)", main)
        self.assertIn("func _activate_view_at_mouse() -> void:", main)
        self.assertIn("func _sync_view_layout_visibility() -> void:", main)
        self.assertIn('view_grid.columns = 2 if view_layout == "quad" else 1', main)

    def test_workspace_migrates_legacy_and_persists_all_four_cameras(self):
        main = (ROOT / "native_editor/godot_editor/main.gd").read_text("utf-8")
        self.assertIn("var legacy := value.size() == 3", main)
        self.assertIn("var extended := value.size() == 6", main)
        self.assertIn('"view_states": view_states.duplicate(true)', main)
        self.assertIn("_apply_draft_workspace(workspace)", main)

    def test_quad_smoke_is_in_both_linux_and_windows_self_tests(self):
        workflow = (ROOT / ".github/workflows/native-dx2ed.yml").read_text("utf-8")
        launcher = (ROOT / "prototype/START_DX2ED.cmd").read_text("utf-8")
        self.assertIn("smoke_multi_view_workspace.gd", workflow)
        self.assertIn("smoke_multi_view_workspace.gd", launcher)
        self.assertIn("editor._apply_draft_workspace(reopened_workspace)",
                      (ROOT / "native_editor/godot_editor/tests/smoke_multi_view_workspace.gd").read_text("utf-8"))

    def test_bundle_manifest_discloses_preview_only_multi_view(self):
        builder = (ROOT / "tools/build_dx2ed_windows_prototype.py").read_text("utf-8")
        doctor = (ROOT / "prototype/prototype_doctor.py").read_text("utf-8")
        self.assertIn('"editor_quad_multiview_layout": True', builder)
        self.assertIn('"editor_quad_multiview_native_writer": False', builder)
        self.assertIn('manifest.get("editor_quad_multiview_layout") is not True', doctor)
        self.assertIn('manifest.get("editor_quad_multiview_native_writer") is not False', doctor)
