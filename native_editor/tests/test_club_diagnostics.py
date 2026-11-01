from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "godot_editor" / "main.gd").read_text(encoding="utf-8")

class ViewportDiagnosticsTests(unittest.TestCase):
    def test_selection_can_copy_transform_details(self):
        self.assertIn("func _format_actor_diagnostic", SOURCE)
        self.assertIn("DisplayServer.clipboard_set(selected_diagnostic)", SOURCE)
        self.assertIn("GMP rotation [Pitch, Yaw, Roll]", SOURCE)

    def test_picker_prefers_actors_and_falls_back_to_bsp(self):
        part = SOURCE.split("func _pick_actor() -> void:", 1)[1].split("func _ray_aabb(", 1)[0]
        self.assertIn("if not actors_by_name.has(name)", part)
        self.assertIn("_select_mesh_only(fallback_mesh)", part)

if __name__ == "__main__":
    unittest.main()
