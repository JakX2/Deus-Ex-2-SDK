from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SourceSectionTopologyContractTests(unittest.TestCase):
    def test_picker_uses_bounded_exact_original_weld_analysis(self) -> None:
        source = (ROOT / "native_editor/godot_editor/collision_source_picker.gd").read_text("utf-8")
        self.assertIn("func section_topology_details", source)
        self.assertIn("MAX_SECTION_TOPOLOGY_TRIANGLES := 8192", source)
        self.assertIn('face["source_weld_ids"]', source)
        self.assertIn("original_edge_incidence.get(edge_key, [])", source)
        self.assertIn('"mopp_leaf_subset_only": true', source)
        self.assertIn('"native_bsp_surface_verified": false', source)

    def test_user_facing_panel_discloses_subset_and_native_limits(self) -> None:
        source = (ROOT / "native_editor/godot_editor/source_section_topology_panel.gd").read_text("utf-8")
        self.assertIn("Analyze MOPP subset", source)
        self.assertIn("Copy topology JSON", source)
        self.assertIn("not a complete render/BSP surface", source)
        self.assertIn("Native map written: NO.", source)

    def test_windows_bundle_and_doctor_require_the_new_panel_and_smoke(self) -> None:
        builder = (ROOT / "tools/build_dx2ed_windows_prototype.py").read_text("utf-8")
        doctor = (ROOT / "prototype/prototype_doctor.py").read_text("utf-8")
        launcher = (ROOT / "prototype/START_DX2ED.cmd").read_text("utf-8")
        for path in (
            "native_editor/godot_editor/source_section_topology_panel.gd",
            "native_editor/godot_editor/tests/smoke_source_section_topology.gd",
        ):
            self.assertIn(path, builder)
            self.assertIn(path, doctor)
        self.assertIn("smoke_source_section_topology.gd", launcher)
        self.assertIn('"editor_source_section_topology_diagnostics": True', builder)
        self.assertIn('"editor_source_section_topology_native_bsp_verified": False', builder)


if __name__ == "__main__":
    unittest.main()
