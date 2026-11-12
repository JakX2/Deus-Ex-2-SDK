#!/usr/bin/env python3
"""Offline, read-only preflight for the packaged Windows DX2Ed prototype.

No original retail game assets are required for the self-test. This script
reads only bundled files, creates no output and does not access the network.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SCHEMA = "DX2Ed-Windows-source-prototype-bundle-v1"
GODOT = ("Godot_v4.3-stable_win64.exe",
         "Godot_v4.3-stable_win64_console.exe")
REQUIRED = (
    "dx2sdk/__init__.py",
    "dx2sdk/api.py",
    "dx2sdk/bsp_mopp_plane_impact.py",
    "dx2sdk/mopp_leaf_bytes.py",
    "dx2sdk/bsp_surface_correlation.py",
    "dx2sdk/bsp_surface_plane_coherence.py",
    "dx2sdk/bsp_model_noop.py",
    "dx2sdk/bsp_model_spans.py",
    "research/dx2/inspect_world_model_spans.py",
    "research/dx2/inspect_world_model_noop.py",
    "research/dx2/inspect_bsp_surface_provenance_hypotheses.py",
    "dx2sdk/bsp_render_plane_impact.py",
    "research/dx2/inspect_level_mopp_triangle_provenance.py",
    "research/dx2/inspect_level_mopp_triangle_tree.py",
    "research/dx2/inspect_bsp_render_spatial_candidates.py",
    "research/dx2/inspect_bsp_mopp_plane_impact.py",
    "dx2sdk/catalog.py",
    "dx2sdk/scalars.py",
    "dx2sdk/clones.py",
    "dx2sdk/multi_clones.py",
    "dx2sdk/projects.py",
    "dx2sdk/__main__.py",
    "dx2sdk/README.md",
    "DX2SDK_CONSOLE.cmd",
    "native_editor/godot_editor/project.godot",
    "native_editor/godot_editor/main.tscn",
    "native_editor/godot_editor/main.gd",
    "native_editor/godot_editor/light_color_panel.gd",
    "native_editor/godot_editor/multi_light_color_panel.gd",
    "native_editor/godot_editor/backend/dx2_sdk_multi_lightcolor_worker.py",
    "native_editor/godot_editor/backend/dx2_sdk_scalar_worker.py",
    "native_editor/godot_editor/tests/smoke_multi_light_color_panel.gd",
    "native_editor/godot_editor/native_scalar_panel.gd",
    "native_editor/godot_editor/backend/dx2_sdk_scalar_worker.py",
    "native_editor/godot_editor/tests/smoke_native_scalar_panel.gd",
    "native_editor/godot_editor/multi_native_scalar_panel.gd",
    "native_editor/godot_editor/backend/dx2_sdk_multi_scalar_worker.py",
    "native_editor/godot_editor/tests/smoke_multi_native_scalar_panel.gd",
    "native_editor/godot_editor/tests/smoke_actor_property_workbench.gd",
    "native_editor/godot_editor/workbench_view_model.gd",
    "native_editor/godot_editor/tests/smoke_workbench_filter_view.gd",
    "native_editor/godot_editor/workbench_actor_navigation.gd",
    "native_editor/godot_editor/tests/smoke_workbench_actor_navigation.gd",
    "native_editor/godot_editor/scene_actor_workbench_bridge.gd",
    "native_editor/godot_editor/tests/smoke_scene_actor_workbench_bridge.gd",
    "native_editor/godot_editor/orthographic_authoring_guides.gd",
    "native_editor/godot_editor/tests/smoke_orthographic_authoring_views.gd",
    "native_editor/godot_editor/tests/smoke_multi_view_workspace.gd",
    "native_editor/godot_editor/tests/smoke_orthographic_gizmo_constraints.gd",
    "native_editor/godot_editor/tests/smoke_transform_pivot_orientation.gd",
    "native_editor/godot_editor/tests/smoke_draft_group_hierarchy.gd",
    "native_editor/godot_editor/tests/smoke_native_static_unplace.gd",
    "native_editor/godot_editor/tests/smoke_native_combined_prop_plan.gd",
    "native_editor/godot_editor/tests/smoke_native_mod_recipe.gd",
    "native_editor/godot_editor/tests/smoke_crosssource_reference_review.gd",
    "native_editor/godot_editor/tests/smoke_native_retail_trial_dossier.gd",
    "native_editor/godot_editor/tests/smoke_disposable_retail_trial.gd",
    "native_editor/godot_editor/retail_observation_panel.gd",
    "native_editor/godot_editor/tests/smoke_retail_observation_panel.gd",
    "native_editor/godot_editor/tests/smoke_t3ed_face_edit_roundtrip.gd",
    "native_editor/godot_editor/tests/smoke_draft_brush_viewport_face_pick.gd",
    "native_editor/godot_editor/custom_polygon_geometry.gd",
    "native_editor/godot_editor/private_box_clip.gd",
    "native_editor/godot_editor/private_box_multiclip.gd",
    "native_editor/godot_editor/private_box_cap_picker.gd",
    "native_editor/godot_editor/private_box_cap_drag.gd",
    "native_editor/godot_editor/tests/smoke_custom_polygon_geometry.gd",
    "native_editor/godot_editor/matlib_browser.gd",
    "native_editor/godot_editor/backend/dx2_matlib_catalog.py",
    "native_editor/godot_editor/tests/smoke_matlib_browser.gd",
    "native_editor/godot_editor/tests/smoke_matlib_polygon_assignment.gd",
    "native_editor/godot_editor/source_surface_matlib_crossref.gd",
    "native_editor/godot_editor/tests/smoke_source_surface_matlib_crossref.gd",
    "native_editor/godot_editor/source_section_topology_panel.gd",
    "native_editor/godot_editor/source_section_fill_preview.gd",
    "native_editor/godot_editor/source_section_edge_overlay.gd",
    "native_editor/godot_editor/source_section_edge_picker.gd",
    "native_editor/godot_editor/source_section_vertex_picker.gd",
    "native_editor/godot_editor/tests/smoke_source_section_topology.gd",
    "native_editor/godot_editor/backend/dx2_sdk_lightcolor_worker.py",
    "native_editor/godot_editor/backend/dx2_sdk_multi_lightcolor_worker.py",
    "native_editor/godot_editor/backend/dx2_sdk_scalar_worker.py",
    "native_editor/godot_editor/tests/smoke_light_color_panel.gd",
    "native_editor/godot_editor/backend/dx2_native_backend.py",
    "native_editor/godot_editor/backend/dx2_sdk_lightcolor_worker.py",
    "native_editor/godot_editor/backend/dx2_sdk_multi_lightcolor_worker.py",
    "native_editor/godot_editor/backend/dx2_sdk_scalar_worker.py",
    "native_editor/godot_editor/backend/dx2_collision_selection_cache.py",
    "native_editor/godot_editor/backend/dx2_script_ibd_provenance.py",
    "native_editor/godot_editor/backend/dx2_mission_kernel_script_diff.py",
    "native_editor/godot_editor/mission_kernel_script_view.gd",
    "native_editor/godot_editor/tests/smoke_mission_kernel_script_view.gd",
    "native_editor/godot_editor/backend/dx2_actor_script_name_candidates.py",
    "native_editor/godot_editor/backend/dx2_script_index_hypothesis_audit.py",
    "native_editor/godot_editor/script_index_audit_view.gd",
    "native_editor/godot_editor/tests/smoke_script_index_hypothesis_audit.gd",
    "native_editor/godot_editor/tests/smoke_original_script_ibd_provenance.gd",
    "tools/scripts/dx2_script_bundle_probe.py",
    "native_editor/godot_editor/capsule_sweep_panel.gd",
    "native_editor/godot_editor/source_edge_capsule_height_replay.gd",
    "native_editor/godot_editor/python_runtime.gd",
    "native_editor/godot_editor/startup_route.gd",
    "native_editor/godot_editor/mission_logic_draft.gd",
    "native_editor/godot_editor/tests/smoke_mission_logic_draft.gd",
    "native_editor/godot_editor/dialogue_design_draft.gd",
    "native_editor/godot_editor/tests/smoke_dialogue_design_draft.gd",
    "native_editor/godot_editor/demo/scene.glb",
    "native_editor/godot_editor/demo/actors.json",
    "native_editor/package_writer/dx2_actor_clone_probe.py",
    "native_editor/package_writer/dx2_actor_unplace_probe.py",
    "native_editor/package_writer/dx2_native_prop_plan.py",
    "native_editor/package_writer/dx2_mod_recipe.py",
    "native_editor/package_writer/dx2_incoming_ref_audit.py",
    "native_editor/package_writer/dx2_crosssource_ref_review.py",
    "native_editor/package_writer/dx2_retail_trial_dossier.py",
    "native_editor/package_writer/dx2_disposable_retail_trial.py",
    "native_editor/package_writer/dx2_retail_observation_recorder.py",
    "map_exporter/dx2_map_exporter.py",
    "actor_explorer/dx2_actor_explorer.py",
    "research/dx2/export_capsule_first_contact_preview.py",
    "research/dx2/audit_private_capsule_height_profiles.py",
    "third_party/t3sdk_assets/LICENSE",
    "GODOT_LICENSE.txt",
    "prototype-manifest.json",
    "DIAGNOSE_GMP.cmd",
    "map_import_preflight.py",
    "research/dx2/private_zip_package_audit.py",
    "research/dx2/dx2_export_boundary_audit.py",
    "research/dx2/export_reader_concordance.py",
    "research/dx2/thief3_export_concordance.py",
)
# Run these actual Python entry points with --help, not just AST.parse.
# stdlib-only imports should work on a clean machine without any DX2 game
# assets. The -B flag prevents __pycache__ writes in the extracted ZIP.
PREFLIGHT_WORKERS = (
    "native_editor/godot_editor/backend/dx2_native_backend.py",
    "native_editor/godot_editor/backend/dx2_matlib_catalog.py",
    "native_editor/godot_editor/backend/dx2_sdk_lightcolor_worker.py",
    "native_editor/godot_editor/backend/dx2_sdk_multi_lightcolor_worker.py",
    "native_editor/godot_editor/backend/dx2_sdk_scalar_worker.py",
    "native_editor/godot_editor/backend/dx2_zip_stage.py",
    "native_editor/godot_editor/backend/dx2_script_ibd_provenance.py",
    "native_editor/godot_editor/backend/dx2_mission_kernel_script_diff.py",
    "map_import_preflight.py",
    "native_editor/godot_editor/backend/dx2_collision_selection_cache.py",
    "research/dx2/export_capsule_first_contact_preview.py",
    "native_editor/package_writer/dx2_actor_clone_probe.py",
    "native_editor/package_writer/dx2_actor_unplace_probe.py",
    "native_editor/package_writer/dx2_native_prop_plan.py",
    "native_editor/package_writer/dx2_mod_recipe.py",
    "native_editor/package_writer/dx2_incoming_ref_audit.py",
    "native_editor/package_writer/dx2_crosssource_ref_review.py",
    "native_editor/package_writer/dx2_retail_trial_dossier.py",
    "native_editor/package_writer/dx2_disposable_retail_trial.py",
    "native_editor/package_writer/dx2_retail_observation_recorder.py",
)

RETAIL_EXT = {".gmp", ".ibd", ".d2u", ".t3u", ".ibt", ".pak", ".dds",
              ".mp3", ".wav", ".bik", ".tsd"}


def examine(root: Path) -> list[str]:
    root = Path(root).resolve()
    issues: list[str] = []
    if sys.version_info < (3, 11):
        issues.append("python_3_11_or_newer_required")
    for rel in REQUIRED:
        if not (root / rel).is_file():
            issues.append("missing:" + rel)
    if issues:
        return issues
    try:
        manifest = json.loads((root / "prototype-manifest.json").read_text("utf-8"))
        if (manifest.get("schema") != SCHEMA
                or manifest.get("engine") != "Godot 4.3 stable Standard Windows x86_64"
                or manifest.get("prototype_version") != "0.7.5-alpha"
                or manifest.get("includes_original_dx2_assets") is not False
                or manifest.get("includes_havok_runtime") is not False
                or manifest.get("gameplay_physics_or_walkability_verified") is not False
                or manifest.get("public_dx2sdk_api_version") != "0.27.0"
                or manifest.get("public_dx2sdk_cli_included") is not True
                or manifest.get("private_original_map_zip_aggregate_audit_available") is not True
                or manifest.get("private_original_map_zip_write_enabled") is not False
                or manifest.get("editor_orthographic_planar_grid_preview") is not True
                or manifest.get("editor_quad_multiview_layout") is not True
                or manifest.get("editor_quad_multiview_independent_cameras") is not True
                or manifest.get("editor_quad_multiview_per_view_grid_layers") is not True
                or manifest.get("editor_quad_multiview_private_workspace_persistence") is not True
                or manifest.get("editor_quad_multiview_native_writer") is not False
                or manifest.get("editor_quad_multiview_active_pane_interaction_overlays") is not True
                or manifest.get("editor_orthographic_gizmo_axis_constraints") is not True
                or manifest.get("editor_orthographic_gizmo_plane_drag") is not True
                or manifest.get("editor_orthographic_gizmo_world_grid_snap") is not True
                or manifest.get("editor_orthographic_gizmo_native_writer") is not False
                or manifest.get("editor_transform_pivot_modes") is not True
                or manifest.get("editor_transform_orientation_modes") is not True
                or manifest.get("editor_transform_cursor_private_persistence") is not True
                or manifest.get("editor_transform_native_writer") is not False
                or manifest.get("editor_group_hierarchy_parent_nodes") is not True
                or manifest.get("editor_group_hierarchy_group_transform_targets") is not True
                or manifest.get("editor_group_hierarchy_undo_redo") is not True
                or manifest.get("editor_group_hierarchy_private_persistence") is not True
                or manifest.get("editor_group_hierarchy_preflight") is not True
                or manifest.get("editor_group_hierarchy_duplicate_groups") is not True
                or manifest.get("editor_group_hierarchy_native_writer") is not False
                or manifest.get("editor_group_hierarchy_native_ownership_verified") is not False
                or manifest.get("editor_group_hierarchy_nested_groups") is not False
                or manifest.get("editor_draft_face_resize_preview") is not True
                or manifest.get("editor_draft_viewport_face_picking_preview") is not True
                or manifest.get("editor_custom_polygon_geometry_preview") is not True
                or manifest.get("editor_custom_polygon_viewport_vertex_handles") is not True
                or manifest.get("editor_custom_polygon_vertex_drag_grid_snap") is not True
                or manifest.get("editor_polygon_surface_material_preview") is not True
                or manifest.get("editor_polygon_surface_uv_editing") is not True
                or manifest.get("editor_matlib_source_browser") is not True
                or manifest.get("editor_matlib_stage_resource_diagnostics") is not True
                or manifest.get("editor_matlib_stage_mask_slot_audit") is not True
                or manifest.get("editor_matlib_raw_category_flags_filters") is not True
                or manifest.get("editor_matlib_category_flags_cohort_audit") is not True
                or manifest.get("editor_source_surface_matlib_name_crossref") is not True
                or manifest.get("editor_source_surface_matlib_native_binding_verified") is not False
                or manifest.get("editor_source_section_topology_diagnostics") is not True
                or manifest.get("editor_source_section_topology_native_bsp_verified") is not False
                or manifest.get("editor_source_section_topology_full_render_section_verified") is not False
                or manifest.get("editor_source_section_topology_havok_adjacency_verified") is not False
                or manifest.get("editor_source_section_topology_area_is_triangle_sum") is not True
                or manifest.get("editor_source_section_fill_preview") is not True
                or manifest.get("editor_source_section_fill_preview_triangle_cap") != 8192
                or manifest.get("editor_source_section_fill_preview_native_writer") is not False
                or manifest.get("editor_source_section_fill_preview_mopp_subset_only") is not True
                or manifest.get("editor_source_section_edge_overlay") is not True
                or manifest.get("editor_source_section_edge_overlay_max_edges") != 24576
                or manifest.get("editor_source_section_edge_overlay_exact_weld_ids") is not True
                or manifest.get("editor_source_section_edge_overlay_native_surface_verified") is not False
                or manifest.get("editor_source_section_edge_overlay_native_writer") is not False
                or manifest.get("editor_source_section_edge_hover_pick") is not True
                or manifest.get("editor_source_section_edge_selection_details") is not True
                or manifest.get("editor_source_section_edge_adjacent_triangle_navigation") is not True
                or manifest.get("editor_source_section_edge_pick_radius_pixels") != 18
                or manifest.get("editor_source_section_edge_native_surface_verified") is not False
                or manifest.get("editor_source_section_edge_native_writer") is not False
                or manifest.get("editor_source_section_vertex_overlay") is not True
                or manifest.get("editor_source_section_vertex_overlay_max_vertices") != 49152
                or manifest.get("editor_source_section_vertex_overlay_exact_weld_ids") is not True
                or manifest.get("editor_source_section_vertex_mopp_leaf_subset_only") is not True
                or manifest.get("editor_source_section_vertex_hover_pick") is not True
                or manifest.get("editor_source_section_vertex_pick_radius_pixels") != 12
                or manifest.get("editor_source_section_vertex_selection_details") is not True
                or manifest.get("editor_source_section_vertex_incident_edge_report") is not True
                or manifest.get("editor_source_section_vertex_incident_triangle_navigation") is not True
                or manifest.get("editor_source_section_vertex_native_bsp_verified") is not False
                or manifest.get("editor_source_section_vertex_native_writer") is not False
                or manifest.get("editor_source_section_neighbor_navigation") is not True
                or manifest.get("editor_source_section_neighbor_navigation_native_surface_verified") is not False
                or manifest.get("editor_matlib_python_worker_invocation_verified") is not True
                or manifest.get("editor_matlib_shader_stage_semantics_verified") is not False
                or manifest.get("editor_polygon_surface_source_diffuse_assignment_preview") is not True
                or manifest.get("editor_polygon_surface_source_diffuse_native_writer") is not False
                or manifest.get("editor_matlib_native_writer") is not False
                or manifest.get("editor_polygon_surface_material_native_writer") is not False
                or manifest.get("editor_custom_polygon_vertex_drag_native_writer") is not False
                or manifest.get("editor_custom_polygon_native_csg_writer") is not False
                or manifest.get("editor_draft_face_resize_native_bsp_writer") is not False
                or manifest.get("editor_orthographic_source_writes_enabled") is not False
                or manifest.get("public_dx2sdk_gameplay_runtime_verified") is not False):
            issues.append("invalid_prototype_manifest")
    except (OSError, ValueError, TypeError):
        return ["invalid_prototype_manifest"]
    try:
        glb = root / "native_editor/godot_editor/demo/scene.glb"
        if glb.read_bytes()[:4] != b"glTF" or glb.stat().st_size < 100:
            issues.append("synthetic_demo_glb_invalid")
        demo = json.loads(
            (root / "native_editor/godot_editor/demo/actors.json").read_text("utf-8"))
        if len(demo.get("actors", [])) != 2:
            issues.append("synthetic_demo_actors_invalid")
    except (OSError, ValueError, TypeError):
        issues.append("synthetic_demo_missing")
    for name in GODOT:
        binary = root / "runtime" / name
        minimum = 50_000 if name.endswith("_console.exe") else 1_000_000
        if not binary.is_file() or binary.stat().st_size < minimum:
            issues.append("godot_runtime_missing_or_invalid:" + name)
            continue
        with binary.open("rb") as handle:
            if handle.read(2) != b"MZ":
                issues.append("godot_runtime_missing_or_invalid:" + name)
                continue
            handle.seek(0)
            digest = hashlib.sha256()
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != manifest.get("runtime_sha256", {}).get(name):
            issues.append("godot_runtime_checksum_mismatch:" + name)
    try:
        for script in root.rglob("*.py"):
            if ".godot" not in script.parts and "__pycache__" not in script.parts:
                ast.parse(script.read_text("utf-8"), filename=script.name)
    except (SyntaxError, OSError, UnicodeError):
        issues.append("bundled_python_syntax_invalid")
    try:
        if not (root / "GODOT_LICENSE.txt").read_text("utf-8").find(
                "Permission is hereby granted") >= 0:
            issues.append("godot_license_notice_missing")
    except (OSError, UnicodeError):
        issues.append("godot_license_notice_missing")
    # A source file can pass syntax validation while its imports fail at
    # runtime (wrong relative layout, missing source worker, unbundled module).
    # Capture/suppress private exception text; report a fixed relative filename.
    for relative in PREFLIGHT_WORKERS:
        try:
            process = subprocess.run(
                [sys.executable, "-B", str(root / relative), "--help"],
                cwd=root, capture_output=True, timeout=20, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            issues.append("worker_import_failed:" + relative)
            continue
        if process.returncode != 0:
            issues.append("worker_import_failed:" + relative)

    # The SDK is a Python package, not a standalone script: --help must
    # import all its dependencies from THIS extracted source-only ZIP.
    try:
        process = subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", "--help"],
            cwd=root, capture_output=True, timeout=20, check=False,
        )
        if (process.returncode != 0
                or b"Deus Ex: Invisible War" not in process.stdout
                or b"move" not in process.stdout):
            issues.append("public_dx2sdk_cli_import_failed")
    except (OSError, subprocess.TimeoutExpired):
        issues.append("public_dx2sdk_cli_import_failed")

    # The private map ZIP audit must be exposed through the unified public
    # SDK console in the actual extracted Windows prototype, without needing
    # any commercial files or writing a report during the doctor check.
    try:
        audit_help = subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", "audit-map-zip", "--help"],
            cwd=root, capture_output=True, timeout=20, check=False,
        )
        if (audit_help.returncode != 0
                or b"--archive" not in audit_help.stdout
                or b"--max-files" not in audit_help.stdout):
            issues.append("private_map_zip_audit_cli_missing")
    except (OSError, subprocess.TimeoutExpired):
        issues.append("private_map_zip_audit_cli_missing")

    # Refuse accidental copied map files inside the distribution. This check
    # is deliberately read-only and does not enumerate outside the prototype.
    for file in root.rglob("*"):
        if file.is_file() and file.suffix.lower() in RETAIL_EXT:
            issues.append("retail_game_asset_detected")
            break
    return issues


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    issues = examine(args.root)
    if issues:
        for issue in issues:
            print("DX2Ed prototype FAILED: " + issue, file=sys.stderr)
        return 1
    print("DX2Ed prototype preflight: PASS")
    print("Python OK; Godot 4.3 verified; source parsers present; synthetic demo ready.")
    print("No packaged retail game files found. Original maps are owner-provided only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
