"""Source-level contracts for the read-only Seattle Club viewport diagnostics.

These tests check the GDScript wiring. For actual picking, run the Godot
headless smoke script described in native_editor/README.md.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "godot_editor" / "main.gd").read_text(encoding="utf-8")


class ViewportDiagnosticsTests(unittest.TestCase):
    def test_selection_can_copy_transform_details(self):
        self.assertIn("func _format_actor_diagnostic", SOURCE)
        self.assertIn("DisplayServer.clipboard_set(selected_diagnostic)", SOURCE)
        self.assertIn("GMP rotation [Pitch, Yaw, Roll]", SOURCE)

    def test_actor_explorer_schema_is_supported(self):
        # The actual Actor Explorer writes mesh as a string, mesh_bounds as
        # a separate value, and an [x, y, z] location array.
        self.assertIn('actor.get("mesh_bounds", null)', SOURCE)
        self.assertIn('elif typeof(mesh_data) == TYPE_STRING', SOURCE)
        self.assertIn('actor.get("location", null)', SOURCE)

    def test_picking_uses_faces_not_just_aabb(self):
        picker = SOURCE.split("func _pick_actor() -> void:", 1)[1].split(
            "func _ray_mesh_triangles(", 1
        )[0]
        self.assertIn("_ray_aabb(origin, direction", picker)
        self.assertIn("_ray_mesh_triangles(instance, origin, direction)", picker)
        self.assertIn("candidates.sort_custom", picker)
        self.assertIn("if hit.is_empty():", picker)
        self.assertIn("actors_by_name.has(chosen_name)", picker)
        self.assertIn("_select_mesh_only(closest_mesh)", picker)
        self.assertNotIn("_select_mesh_only(fallback_mesh)", picker)

    def test_exact_hit_is_both_sided_and_cache_is_cleared(self):
        ray = SOURCE.split("func _ray_mesh_triangles(", 1)[1].split(
            "func _ray_aabb(", 1
        )[0]
        self.assertIn("Geometry3D.ray_intersects_triangle(", ray)
        self.assertIn("faces[i + 2], faces[i + 1], faces[i]", ray)
        self.assertIn("instance.global_transform.affine_inverse()", ray)
        self.assertIn("pick_faces_by_mesh[mesh_id] = faces", ray)
        self.assertIn("pick_faces_by_mesh.clear()", SOURCE)
        self.assertIn("Pick method: rendered triangle (not AABB)", SOURCE)


if __name__ == "__main__":
    unittest.main()
