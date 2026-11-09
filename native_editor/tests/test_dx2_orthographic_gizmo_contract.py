"""Source contracts for DX2Ed v0.54 active-pane orthographic gizmos."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
GODOT = ROOT / "native_editor" / "godot_editor"


class DX2EdOrthographicGizmoContractTests(unittest.TestCase):
    def test_interaction_layer_is_distinct_and_active_pane_only(self):
        guides = (GODOT / "orthographic_authoring_guides.gd").read_text("utf-8")
        self.assertIn("const INTERACTION_LAYER_MASK := 1 << 5", guides)
        self.assertIn("static func viewport_cull_mask(view_id: String, active_view_id: String)", guides)
        self.assertIn("interaction_layer_mask(view_id, active_view_id)", guides)

    def test_orthographic_axis_and_plane_constraints_are_explicit(self):
        guides = (GODOT / "orthographic_authoring_guides.gd").read_text("utf-8")
        self.assertIn("static func gizmo_plane_axes(mode: String)", guides)
        self.assertIn("static func gizmo_view_normal(mode: String)", guides)
        self.assertIn("static func gizmo_axes(mode: String, tool: String)", guides)
        self.assertIn("static func plane_drag_delta(", guides)
        self.assertIn("static func axis_drag_delta(", guides)
        self.assertIn("snappedf(pivot_coordinate + amount, step)", guides)

    def test_main_editor_routes_gizmo_and_polygon_handles_through_active_layer(self):
        main = (GODOT / "main.gd").read_text("utf-8")
        self.assertIn("OrthoGuides.viewport_cull_mask(view_id, active_view_id)", main)
        self.assertIn("polygon_vertex_outline_node.layers = OrthoGuides.INTERACTION_LAYER_MASK", main)
        self.assertIn("marker.layers = OrthoGuides.INTERACTION_LAYER_MASK", main)
        self.assertIn("handle.layers = OrthoGuides.INTERACTION_LAYER_MASK", main)
        self.assertIn("func _begin_gizmo_drag_at(mouse_position: Vector2)", main)
        self.assertIn("func _apply_gizmo_drag_at(mouse_position: Vector2)", main)
        self.assertIn("OrthoGuides.plane_drag_delta(", main)

    def test_native_writers_remain_disabled_and_smoke_is_packaged(self):
        build = (ROOT / "tools" / "build_dx2ed_windows_prototype.py").read_text("utf-8")
        doctor = (ROOT / "prototype" / "prototype_doctor.py").read_text("utf-8")
        start = (ROOT / "prototype" / "START_DX2ED.cmd").read_text("utf-8")
        smoke = "native_editor/godot_editor/tests/smoke_orthographic_gizmo_constraints.gd"
        self.assertIn(smoke, build)
        self.assertIn(smoke, doctor)
        self.assertIn("smoke_orthographic_gizmo_constraints.gd", start)
        self.assertIn('"editor_orthographic_gizmo_native_writer": False', build)
        self.assertIn('manifest.get("editor_orthographic_gizmo_native_writer") is not False', doctor)


if __name__ == "__main__":
    unittest.main()
