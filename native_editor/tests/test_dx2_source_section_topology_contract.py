from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SourceSectionTopologyContractTests(unittest.TestCase):
    def test_picker_uses_bounded_exact_original_weld_analysis(self) -> None:
        source = (ROOT / "native_editor/godot_editor/collision_source_picker.gd").read_text("utf-8")
        self.assertIn("func section_topology_details", source)
        self.assertIn("MAX_SECTION_TOPOLOGY_TRIANGLES := 8192", source)
        self.assertIn("MAX_SECTION_EDGE_INCIDENCE := 1024", source)
        self.assertIn('face["source_weld_ids"]', source)
        self.assertIn("original_edge_incidence.get(edge_key, [])", source)
        self.assertIn('"mopp_leaf_subset_only": true', source)
        self.assertIn('"area_measure": "sum_of_mopp_leaf_triangle_areas"', source)
        self.assertIn('"native_bsp_surface_verified": false', source)
        self.assertIn('"source_edge_classification_mopp_leaf_subset": true', source)

    def test_user_facing_panel_discloses_subset_and_native_limits(self) -> None:
        source = (ROOT / "native_editor/godot_editor/source_section_topology_panel.gd").read_text("utf-8")
        self.assertIn("Analyze MOPP subset", source)
        self.assertIn("Copy topology JSON", source)
        self.assertIn("not a complete render/BSP surface", source)
        self.assertIn("Native map written: NO.", source)

    def test_filled_mopp_subset_preview_is_bounded_translucent_and_read_only(self) -> None:
        picker = (ROOT / "native_editor/godot_editor/collision_source_picker.gd").read_text("utf-8")
        helper = (ROOT / "native_editor/godot_editor/source_section_fill_preview.gd").read_text("utf-8")
        main = (ROOT / "native_editor/godot_editor/main.gd").read_text("utf-8")
        self.assertIn("MAX_SECTION_SURFACE_PREVIEW_TRIANGLES := 8192", picker)
        self.assertIn("func section_surface_preview_details", picker)
        self.assertIn("PREVIEW_CAP := 8192", helper)
        self.assertIn("TRANSPARENCY_ALPHA", helper)
        self.assertIn("DISPLAY_OFFSET_GODOT_UNITS := 0.0015", helper)
        self.assertIn("native_bsp_surface_verified", picker)
        self.assertIn("Fill MOPP subset", main)
        self.assertIn("_toggle_source_collision_section_fill", main)

    def test_topology_neighbor_navigation_uses_representative_source_triangle(self) -> None:
        picker = (ROOT / "native_editor/godot_editor/collision_source_picker.gd").read_text("utf-8")
        panel = (ROOT / "native_editor/godot_editor/source_section_topology_panel.gd").read_text("utf-8")
        main = (ROOT / "native_editor/godot_editor/main.gd").read_text("utf-8")
        self.assertIn('"representative_triangle_id": other_id', picker)
        self.assertIn("signal triangle_requested", panel)
        self.assertIn("Select adjacent section", panel)
        self.assertIn("_select_neighbor", panel)
        self.assertIn("_navigate_source_collision_triangle", main)

    def test_windows_bundle_and_doctor_require_the_new_panel_and_smoke(self) -> None:
        builder = (ROOT / "tools/build_dx2ed_windows_prototype.py").read_text("utf-8")
        doctor = (ROOT / "prototype/prototype_doctor.py").read_text("utf-8")
        launcher = (ROOT / "prototype/START_DX2ED.cmd").read_text("utf-8")
        for path in (
            "native_editor/godot_editor/source_section_topology_panel.gd",
            "native_editor/godot_editor/source_section_fill_preview.gd",
            "native_editor/godot_editor/tests/smoke_source_section_topology.gd",
        ):
            self.assertIn(path, builder)
            self.assertIn(path, doctor)
        self.assertIn("smoke_source_section_topology.gd", launcher)
        self.assertIn('"editor_source_section_topology_diagnostics": True', builder)
        self.assertIn('"editor_source_section_topology_native_bsp_verified": False', builder)
        self.assertIn('"editor_source_section_fill_preview_native_writer": False', builder)
        self.assertIn('"editor_source_section_neighbor_navigation_native_surface_verified": False', builder)


    def test_edge_overlay_godot_smoke_covers_tampered_weld_refusal(self) -> None:
        smoke = (ROOT / "native_editor/godot_editor/tests/smoke_source_section_topology.gd").read_text("utf-8")
        self.assertIn("EdgeOverlay.build_marker", smoke)
        self.assertIn("source_weld_ids", smoke)
        self.assertIn("panel.edge_overlay_toggled", smoke)


    def test_picker_exports_bounded_exact_weld_edge_records(self) -> None:
        source = (ROOT / "native_editor/godot_editor/collision_source_picker.gd").read_text("utf-8")
        self.assertIn("MAX_SECTION_TOPOLOGY_EDGES := 24576", source)
        self.assertIn("edge_report_uses_original_float32_weld_ids", source)
        self.assertIn("source_weld_ids", source)
        self.assertIn("cross_section_neighbor_count", source)
        self.assertIn("edge_classification_counts", source)

    def test_edge_overlay_helper_revalidates_source_edge_identity(self) -> None:
        source = (ROOT / "native_editor/godot_editor/source_section_edge_overlay.gd").read_text("utf-8")
        self.assertIn("MAX_EDGE_COUNT := 24576", source)
        self.assertIn("original_float32_weld_ids", source)
        self.assertIn("distance_squared_to(b) <= 1e-12", source)
        self.assertIn("source_sha256.length() != 64", source)
        self.assertIn("seen_edge_keys.has(edge_key)", source)
        self.assertIn("vertex_color_use_as_albedo = true", source)
        self.assertIn("native_bsp_surface_verified", source)

    def test_topology_panel_and_main_wire_transient_edge_overlay(self) -> None:
        panel = (ROOT / "native_editor/godot_editor/source_section_topology_panel.gd").read_text("utf-8")
        main = (ROOT / "native_editor/godot_editor/main.gd").read_text("utf-8")
        self.assertIn("Show exact-weld edge overlay", panel)
        self.assertIn("Copy edge report JSON", panel)
        self.assertIn("signal edge_overlay_toggled", panel)
        self.assertIn("_toggle_source_section_edge_overlay", main)
        self.assertIn("source_collision_section_edge_marker.queue_free()", main)

    def test_screen_edge_picker_is_bounded_cached_and_provenance_pinned(self) -> None:
        helper = (ROOT / "native_editor/godot_editor/source_section_edge_picker.gd").read_text("utf-8")
        main = (ROOT / "native_editor/godot_editor/main.gd").read_text("utf-8")
        panel = (ROOT / "native_editor/godot_editor/source_section_topology_panel.gd").read_text("utf-8")
        self.assertIn("MAX_EDGE_COUNT := 24576", helper)
        self.assertIn("CELL_SIZE := 64.0", helper)
        self.assertIn("camera_signature_matches", helper)
        self.assertIn("record_belongs_to_report", helper)
        self.assertIn('analysis_skipped_for_edge_incidence", false', helper)
        self.assertIn("screen_distance_px", helper)
        self.assertIn("edge_selection_cleared", panel)
        self.assertIn("set_selected_edge", panel)
        self.assertIn("Select incident triangle", panel)
        self.assertIn("Jump to adjacent section", panel)
        self.assertIn("_update_source_section_edge_hover", main)
        self.assertIn("_select_source_section_edge", main)
        self.assertIn("editor_only", helper)


    def test_package_and_ci_require_edge_overlay_but_not_native_writer(self) -> None:
        builder = (ROOT / "tools/build_dx2ed_windows_prototype.py").read_text("utf-8")
        doctor = (ROOT / "prototype/prototype_doctor.py").read_text("utf-8")
        workflow = (ROOT / ".github/workflows/native-dx2ed.yml").read_text("utf-8")
        self.assertIn("source_section_edge_overlay.gd", builder)
        self.assertIn("source_section_edge_picker.gd", builder)
        self.assertIn("editor_source_section_edge_hover_pick", builder)
        self.assertIn("editor_source_section_edge_native_writer", builder)
        self.assertIn("editor_source_section_edge_overlay_native_surface_verified", doctor)
        self.assertIn("Compile exact-weld source-section edge overlay helper", workflow)
        self.assertIn("Compile source-section edge hover picker", workflow)

if __name__ == "__main__":
    unittest.main()
