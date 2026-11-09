"""Asset-free end-to-end packaging checks for the Nov 7 Windows DX2Ed alpha.

Runtime ZIP entries are FAKE MZ bytes; real Godot 4.3 Windows execution is
separately checked in the Windows Actions job against official binaries.
No proprietary DX2 game asset is read or distributed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "prototype"))
import build_dx2ed_windows_prototype as builder
import prototype_doctor as doctor


class DX2EdPrototypeWindowsBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dx2sdk_prototype_fixture_")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.upstream = base / "OfficialGodotSynthetic.zip"
        self.notice = base / "Godot_LICENSE.txt"
        self.notice.write_text(
            "Copyright (c) Godot Engine contributors. "
            "Permission is hereby granted, free of charge, to any person "
            "obtaining a copy of this software and associated documentation files "
            "to deal in the Software without restriction. "
            "The above copyright notice shall be included in all copies.",
            encoding="utf-8")
        self.output = base / "DX2Ed_Windows_Prototype.zip"
        self.expected_fake_exe = b"MZ" + b"X" * 1_001_000
        self._runtime_zip()

    def _runtime_zip(self, *, include_console=True, append_game_asset=False):
        with ZipFile(self.upstream, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("Godot_v4.3-stable_win64.exe",
                             self.expected_fake_exe)
            if include_console:
                archive.writestr("Godot_v4.3-stable_win64_console.exe",
                                 self.expected_fake_exe)
            if append_game_asset:
                archive.writestr("sneaky/M1_Retail.gmp", b"PRIVATE DUMMY")

    def _build(self):
        return builder.build(ROOT, self.upstream, self.notice, self.output)

    def test_synthetic_prototype_zip_has_launcher_generated_demo_and_all_research(self):
        record = self._build()
        self.assertEqual(record["schema"], builder.SCHEMA)
        self.assertTrue(record["synthetic_scene_included"])
        self.assertFalse(record["includes_original_dx2_assets"])
        self.assertFalse(record["includes_havok_runtime"])
        prefix = builder.ARCHIVE_ROOT + "/"
        with ZipFile(self.output) as archive:
            self.assertIsNone(archive.testzip())
            files = set(archive.namelist())
            for name in [
                "START_DX2ED.cmd", "CHECK_DX2ED.cmd", "DIAGNOSE_GMP.cmd",
                "prototype_doctor.py", "map_import_preflight.py",
                "native_editor/godot_editor/project.godot",
                "native_editor/godot_editor/main.gd",
                "native_editor/godot_editor/source_surface_matlib_crossref.gd",
                "native_editor/godot_editor/tests/smoke_source_surface_matlib_crossref.gd",
                "native_editor/godot_editor/source_section_topology_panel.gd",
                "native_editor/godot_editor/source_section_fill_preview.gd",
                "native_editor/godot_editor/source_section_edge_overlay.gd",
                "native_editor/godot_editor/source_section_edge_picker.gd",
                "native_editor/godot_editor/source_section_vertex_picker.gd",
                "native_editor/godot_editor/tests/smoke_source_section_topology.gd",
                "native_editor/godot_editor/python_runtime.gd",
                "native_editor/godot_editor/startup_route.gd",
                "native_editor/godot_editor/tests/smoke_python_runtime.gd",
                "native_editor/godot_editor/demo/scene.glb",
                "native_editor/godot_editor/demo/actors.json",
                "native_editor/godot_editor/tests/smoke_source_edge_capsule_height_replay.gd",
                "research/dx2/export_capsule_first_contact_preview.py",
                "research/dx2/audit_private_capsule_height_profiles.py",
                "map_exporter/dx2_map_exporter.py",
                "actor_explorer/dx2_actor_explorer.py",
                "native_editor/package_writer/dx2_actor_clone_probe.py",
                "third_party/t3sdk_assets/LICENSE",
                "GODOT_LICENSE.txt",
                "runtime/Godot_v4.3-stable_win64.exe",
                "runtime/Godot_v4.3-stable_win64_console.exe",
                "prototype-manifest.json",
            ]:
                self.assertIn(prefix + name, files, name)
            self.assertFalse(any(
                file.lower().endswith((".gmp", ".ibd", ".d2u", ".dds", ".pak"))
                for file in files))
            self.assertTrue(archive.read(prefix + "native_editor/godot_editor/demo/scene.glb").startswith(b"glTF"))
            doc = json.loads(archive.read(prefix + "prototype-manifest.json"))
            self.assertEqual(doc["prototype_version"], "0.7.1-alpha")
            self.assertTrue(doc["editor_source_section_topology_diagnostics"])
            self.assertFalse(doc["editor_source_section_topology_native_bsp_verified"])
            self.assertFalse(doc["editor_source_section_topology_full_render_section_verified"])
            self.assertFalse(doc["editor_source_section_topology_havok_adjacency_verified"])
            self.assertTrue(doc["editor_source_section_topology_area_is_triangle_sum"])
            self.assertTrue(doc["editor_source_section_fill_preview"])
            self.assertEqual(doc["editor_source_section_fill_preview_triangle_cap"], 8192)
            self.assertFalse(doc["editor_source_section_fill_preview_native_writer"])
            self.assertTrue(doc["editor_source_section_fill_preview_mopp_subset_only"])
            self.assertTrue(doc["editor_source_section_edge_overlay"])
            self.assertEqual(doc["editor_source_section_edge_overlay_max_edges"], 24576)
            self.assertTrue(doc["editor_source_section_edge_overlay_exact_weld_ids"])
            self.assertFalse(doc["editor_source_section_edge_overlay_native_surface_verified"])
            self.assertFalse(doc["editor_source_section_edge_overlay_native_writer"])
            self.assertTrue(doc["editor_source_section_edge_hover_pick"])
            self.assertTrue(doc["editor_source_section_edge_selection_details"])
            self.assertTrue(doc["editor_source_section_edge_adjacent_triangle_navigation"])
            self.assertEqual(doc["editor_source_section_edge_pick_radius_pixels"], 18)
            self.assertFalse(doc["editor_source_section_edge_native_surface_verified"])
            self.assertFalse(doc["editor_source_section_edge_native_writer"])
            self.assertTrue(doc["editor_source_section_vertex_overlay"])
            self.assertEqual(doc["editor_source_section_vertex_overlay_max_vertices"], 49152)
            self.assertTrue(doc["editor_source_section_vertex_overlay_exact_weld_ids"])
            self.assertTrue(doc["editor_source_section_vertex_mopp_leaf_subset_only"])
            self.assertTrue(doc["editor_source_section_vertex_hover_pick"])
            self.assertEqual(doc["editor_source_section_vertex_pick_radius_pixels"], 12)
            self.assertTrue(doc["editor_source_section_vertex_selection_details"])
            self.assertTrue(doc["editor_source_section_vertex_incident_edge_report"])
            self.assertTrue(doc["editor_source_section_vertex_incident_triangle_navigation"])
            self.assertFalse(doc["editor_source_section_vertex_native_bsp_verified"])
            self.assertFalse(doc["editor_source_section_vertex_native_writer"])
            self.assertTrue(doc["editor_source_section_neighbor_navigation"])
            self.assertFalse(doc["editor_source_section_neighbor_navigation_native_surface_verified"])
            self.assertEqual(doc["runtime_sha256"]["Godot_v4.3-stable_win64.exe"],
                             hashlib.sha256(self.expected_fake_exe).hexdigest())
            extracted = Path(self.tmp.name) / "unpacked"
            archive.extractall(extracted)
        self.assertEqual(doctor.examine(extracted / builder.ARCHIVE_ROOT), [])

    def test_doctor_executes_real_worker_import_preflight_not_just_syntax(self):
        self._build()
        with ZipFile(self.output) as archive:
            extracted = Path(self.tmp.name) / "unpacked"
            archive.extractall(extracted)
        package = extracted / builder.ARCHIVE_ROOT
        worker = package / "map_import_preflight.py"
        worker.write_text('raise RuntimeError("PRIVATE_OWNER_PATH_MUST_NOT_LEAK")\n')
        issues = doctor.examine(package)
        self.assertIn("worker_import_failed:map_import_preflight.py", issues)
        self.assertNotIn("PRIVATE_OWNER_PATH_MUST_NOT_LEAK", json.dumps(issues))

    def test_windows_launchers_preserve_verified_python_and_owner_map_routing(self):
        check = (ROOT / "prototype/CHECK_DX2ED.cmd").read_text(encoding="utf-8")
        start = (ROOT / "prototype/START_DX2ED.cmd").read_text(encoding="utf-8")
        self.assertIn('DX2ED_PYTHON_EXE', check)
        self.assertIn('print(sys.executable)', check)
        self.assertIn('smoke_python_runtime.gd', start)
        self.assertIn('-- --gmp "%~f1"', start)
        self.assertIn('CHECK_DX2ED.cmd', start)

    def test_untrusted_extra_zip_asset_never_copied(self):
        self._runtime_zip(append_game_asset=True)
        self._build()
        with ZipFile(self.output) as archive:
            self.assertFalse(any("Retail" in name for name in archive.namelist()))

    def test_incomplete_official_godot_runtime_refuses_package(self):
        self._runtime_zip(include_console=False)
        with self.assertRaisesRegex(ValueError, "both Godot"):
            self._build()
        self.assertFalse(self.output.exists())

    def test_invalid_upstream_license_refuses_without_writing(self):
        self.notice.write_text("Copyright restricted" * 12, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "MIT redistribution"):
            self._build()
        self.assertFalse(self.output.exists())

    def test_existing_archive_remains_unmodified(self):
        self.output.write_bytes(b"EXISTING USER WORK")
        with self.assertRaisesRegex(ValueError, "fresh output"):
            self._build()
        self.assertEqual(self.output.read_bytes(), b"EXISTING USER WORK")

    def test_doctor_rejects_corrupted_runtime_and_missing_python_source(self):
        self._build()
        with ZipFile(self.output) as archive:
            root = Path(self.tmp.name) / "unpacked"
            archive.extractall(root)
        project = root / builder.ARCHIVE_ROOT
        (project / "runtime/Godot_v4.3-stable_win64.exe").write_bytes(b"MZBAD")
        self.assertTrue(any("godot_runtime_missing_or_invalid" in issue
                            for issue in doctor.examine(project)))
        (project / "native_editor/godot_editor/main.gd").unlink()
        self.assertTrue(any("missing:native_editor/godot_editor/main.gd" == issue
                            for issue in doctor.examine(project)))


if __name__ == "__main__":
    unittest.main()
