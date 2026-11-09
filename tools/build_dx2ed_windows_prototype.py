#!/usr/bin/env python3
"""Create the no-retail-assets, launchable Windows DX2Ed research prototype.

Source-only Godot project + the official Godot 4.3 Standard Windows runtime,
plus the existing stdlib Python map/actor/Level research workers. The user
supplies original GMP and IBD files locally. No DX2 games or copyrighted map
assets ever enter the package. The only GLB is generated synthetic cubes.

Usage:
 python tools/build_dx2ed_windows_prototype.py \
   --godot-archive /private/Godot_v4.3-stable_win64.exe.zip \
   --godot-license /private/Godot_LICENSE.txt \
   --output /private/DX2Ed_Windows_Prototype.zip
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import runpy
import shutil
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = "DX2Ed_Windows_Prototype"
GODOT_BINARIES = (
    "Godot_v4.3-stable_win64.exe",
    "Godot_v4.3-stable_win64_console.exe",
)
GODOT_VERSION = "4.3-stable"
SCHEMA = "DX2Ed-Windows-source-prototype-bundle-v1"
ZIP_DATE = (2026, 11, 5, 0, 0, 0)

# Explicit source-only allowlist. No reader/user game path is ever traversed.
ALLOWED = {
    "dx2sdk": {".py", ".md"},
    "native_editor/godot_editor": {".gd", ".tscn", ".godot", ".json", ".md", ".py"},
    "native_editor/package_writer": {".py", ".md", ".json"},
    "map_exporter": {".py", ".md"},
    "actor_explorer": {".py", ".md"},
    "research/dx2": {".py"},
    "third_party/t3sdk_assets": {".py", ".json", ".md"},
    "docs/research": {".md"},
    "prototype": {".cmd", ".py", ".md"},
    "tools/scripts": {".py"},
}
EXTRA = ("README.md", "native_editor/README.md", "native_editor/ARCHITECTURE.md")
REQUIRED = (
    "dx2sdk/__init__.py",
    "dx2sdk/__main__.py",
    "dx2sdk/api.py",
    "dx2sdk/catalog.py",
    "dx2sdk/scalars.py",
    "dx2sdk/clones.py",
    "dx2sdk/multi_clones.py",
    "dx2sdk/projects.py",
    "dx2sdk/README.md",
    "prototype/DX2SDK_CONSOLE.cmd",
    "native_editor/godot_editor/project.godot",
    "native_editor/godot_editor/main.tscn",
    "native_editor/godot_editor/main.gd",
    "native_editor/godot_editor/light_color_panel.gd",
    "native_editor/godot_editor/multi_light_color_panel.gd",
    "native_editor/godot_editor/backend/dx2_sdk_multi_lightcolor_worker.py",
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
    "native_editor/godot_editor/tests/smoke_t3ed_face_edit_roundtrip.gd",
    "native_editor/godot_editor/tests/smoke_draft_brush_viewport_face_pick.gd",
    "native_editor/godot_editor/custom_polygon_geometry.gd",
    "native_editor/godot_editor/tests/smoke_custom_polygon_geometry.gd",
    "native_editor/godot_editor/matlib_browser.gd",
    "native_editor/godot_editor/backend/dx2_matlib_catalog.py",
    "native_editor/godot_editor/tests/smoke_matlib_browser.gd",
    "native_editor/godot_editor/tests/smoke_matlib_polygon_assignment.gd",
    "native_editor/godot_editor/backend/dx2_sdk_lightcolor_worker.py",
    "native_editor/godot_editor/tests/smoke_light_color_panel.gd",
    "native_editor/godot_editor/backend/dx2_native_backend.py",
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
    "native_editor/package_writer/dx2_actor_clone_probe.py",
    "map_exporter/dx2_map_exporter.py",
    "actor_explorer/dx2_actor_explorer.py",
    "research/dx2/private_zip_package_audit.py",
    "research/dx2/dx2_export_boundary_audit.py",
    "research/dx2/export_reader_concordance.py",
    "research/dx2/thief3_export_concordance.py",
    "research/dx2/export_capsule_first_contact_preview.py",
    "research/dx2/audit_private_capsule_height_profiles.py",
    "third_party/t3sdk_assets/upkg.py",
    "third_party/t3sdk_assets/LICENSE",
    "prototype/START_DX2ED.cmd",
    "prototype/CHECK_DX2ED.cmd",
    "prototype/DIAGNOSE_GMP.cmd",
    "prototype/map_import_preflight.py",
    "prototype/prototype_doctor.py",
    "prototype/README_FIRST.md",
)
# Only these two executable files enter the archive, from a separately
# authenticated Godot release ZIP, never a game binary or repo checkout.
DENIED_EXT = {
    ".gmp", ".ibd", ".ibt", ".unr", ".d2u", ".t3u", ".pro", ".ski",
    ".pan", ".psk", ".psa", ".dds", ".glb", ".gltf", ".exe", ".dll",
    ".pak", ".tsd", ".lbd", ".ogg", ".wav", ".mp3", ".bik", ".zip",
}


def _zip_info(name: str) -> ZipInfo:
    info = ZipInfo(f"{ARCHIVE_ROOT}/{name}", ZIP_DATE)
    info.compress_type = ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _add_bytes(archive: ZipFile, name: str, data: bytes) -> None:
    archive.writestr(_zip_info(name), data)


def _source_paths(root: Path) -> list[tuple[str, Path]]:
    if any(not (root / name).is_file() for name in REQUIRED):
        raise ValueError("Missing required editor or source files")
    result: dict[str, Path] = {}
    for folder, suffixes in ALLOWED.items():
        for file in (root / folder).rglob("*"):
            if not file.is_file() or file.is_symlink():
                continue
            rel = file.relative_to(root).as_posix()
            if any(x.startswith(".") or x == "__pycache__" for x in file.relative_to(root / folder).parts):
                continue
            if rel.startswith("native_editor/godot_editor/demo/"):
                continue  # regenerated as original synthetic sample below
            if file.suffix.lower() in DENIED_EXT:
                continue
            if file.suffix.lower() in suffixes or (
                    folder == "third_party/t3sdk_assets" and file.name == "LICENSE"):
                result[rel] = file
    for rel in EXTRA:
        source = root / rel
        if not source.is_file() or source.is_symlink():
            raise ValueError("Missing source-only documentation")
        result[rel] = source
    if any(item not in result for item in REQUIRED):
        raise ValueError("Required source file was omitted by explicit allowlist")
    return sorted(result.items())


def _godot_zip_entries(archive: ZipFile) -> dict[str, str]:
    paths = {}
    for item in archive.infolist():
        name = item.filename.replace("\\", "/")
        if item.is_dir():
            continue
        base = name.rsplit("/", 1)[-1]
        if base in GODOT_BINARIES:
            minimum = 50_000 if base.endswith("_console.exe") else 1_000_000
            if (base in paths or item.file_size < minimum
                    or item.file_size > 250_000_000
                    or item.compress_size > 250_000_000):
                raise ValueError("Invalid official Godot Windows runtime entry")
            paths[base] = item.filename
    if set(paths) != set(GODOT_BINARIES):
        raise ValueError("Expected both Godot 4.3 Standard Windows runtime executables")
    return paths


def build(source_root: Path, godot_zip: Path, godot_license: Path,
          output: Path) -> dict:
    source_root = source_root.resolve()
    godot_zip = godot_zip.resolve()
    godot_license = godot_license.resolve()
    output = output.resolve()
    if (not godot_zip.is_file() or not godot_license.is_file()
            or godot_zip == output or godot_license == output
            or not output.parent.is_dir() or output.exists()
            or output.suffix.lower() != ".zip"):
        raise ValueError("Expected fresh output and official Godot input files")
    license_bytes = godot_license.read_bytes()
    if (not 100 <= len(license_bytes) <= 100_000
            or b"Permission is hereby granted" not in license_bytes
            or b"Godot" not in license_bytes):
        raise ValueError("Missing Godot engine MIT redistribution notice")

    sources = _source_paths(source_root)
    generated: dict[str, bytes] = {}
    with tempfile.TemporaryDirectory(prefix="dx2ed_synthetic_demo_") as tmp:
        generator = runpy.run_path(str(source_root / "native_editor/tests/make_demo_scene.py"))
        generator["generate_demo"](Path(tmp))
        for filename in ("scene.glb", "actors.json"):
            generated[f"native_editor/godot_editor/demo/{filename}"] = (
                Path(tmp) / filename).read_bytes()
    if not generated["native_editor/godot_editor/demo/scene.glb"].startswith(b"glTF"):
        raise ValueError("Synthetic demo generator did not create a GLB")

    result = {
        "schema": SCHEMA,
        "prototype_version": "0.6.4-alpha",
        "engine": "Godot 4.3 stable Standard Windows x86_64",
        "engine_archive_sha512": hashlib.sha512(godot_zip.read_bytes()).hexdigest(),
        "python_minimum": "3.11",
        "launch_mode": "Godot source project using bundled Godot runtime",
        "includes_original_dx2_assets": False,
        "includes_havok_runtime": False,
        "gameplay_physics_or_walkability_verified": False,
        "native_bsp_or_mopp_writer_available": False,
        "native_gmp_save_as_location_experiment": True,
        "public_dx2sdk_api_version": "0.27.0",
        "editor_orthographic_planar_grid_preview": True,
        "editor_draft_face_resize_preview": True,
        "editor_draft_viewport_face_picking_preview": True,
        "editor_custom_polygon_geometry_preview": True,
        "editor_custom_polygon_viewport_vertex_handles": True,
        "editor_custom_polygon_vertex_drag_grid_snap": True,
        "editor_polygon_surface_material_preview": True,
        "editor_polygon_surface_uv_editing": True,
        "editor_matlib_source_browser": True,
        "editor_matlib_stage_resource_diagnostics": True,
        "editor_matlib_stage_mask_slot_audit": True,
        "editor_matlib_python_worker_invocation_verified": True,
        "editor_matlib_shader_stage_semantics_verified": False,
        "editor_polygon_surface_source_diffuse_assignment_preview": True,
        "editor_polygon_surface_source_diffuse_native_writer": False,
        "editor_matlib_native_writer": False,
        "editor_polygon_surface_material_native_writer": False,
        "editor_custom_polygon_vertex_drag_native_writer": False,
        "editor_custom_polygon_native_csg_writer": False,
        "editor_draft_face_resize_native_bsp_writer": False,
        "editor_orthographic_source_writes_enabled": False,
        "public_dx2sdk_cli_included": True,
        "private_original_map_zip_aggregate_audit_available": True,
        "private_original_map_zip_write_enabled": False,
        "public_dx2sdk_gameplay_runtime_verified": False,
        "synthetic_scene_included": True,
        "file_count_excluding_runtime": len(sources) + len(generated) + 2,
        "read_only_default": True,
    }
    try:
        with ZipFile(godot_zip, "r") as upstream:
            runtime = _godot_zip_entries(upstream)
            checksums = {}
            for name in GODOT_BINARIES:
                digest = hashlib.sha256()
                with upstream.open(runtime[name]) as file:
                    if file.read(2) != b"MZ":
                        raise ValueError("Official Godot binary is not a Windows PE executable")
                    file.seek(0)
                    for block in iter(lambda: file.read(1024 * 1024), b""):
                        digest.update(block)
                checksums[name] = digest.hexdigest()
            result["runtime_sha256"] = checksums
            with ZipFile(output, "x", compression=ZIP_DEFLATED, compresslevel=6,
                         allowZip64=True) as archive:
                for name, src in sources:
                    destination = name[len("prototype/"):] if name.startswith("prototype/") else name
                    _add_bytes(archive, destination, src.read_bytes())
                for name, data in sorted(generated.items()):
                    _add_bytes(archive, name, data)
                _add_bytes(archive, "GODOT_LICENSE.txt", license_bytes)
                _add_bytes(archive, "prototype-manifest.json",
                           (json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
                for name in GODOT_BINARIES:
                    # Only copy named upstream Godot exe members. Do not
                    # extract arbitrary files from a supply-chain archive.
                    info = _zip_info(f"runtime/{name}")
                    with upstream.open(runtime[name]) as source, archive.open(info, "w") as dest:
                        shutil.copyfileobj(source, dest, length=1024*1024)
        with ZipFile(output, "r") as verification:
            if verification.testzip() is not None:
                raise ValueError("Generated prototype ZIP failed integrity validation")
            members = [x.filename for x in verification.infolist()]
            if len(members) != len(set(members)):
                raise ValueError("Duplicate paths in prototype ZIP")
            safe_demo = (f"{ARCHIVE_ROOT}/native_editor/godot_editor/demo/scene.glb")
            forbidden = [x for x in members if Path(x).suffix.lower() in DENIED_EXT
                         and not x.startswith(f"{ARCHIVE_ROOT}/runtime/")
                         and x != safe_demo]
            if forbidden:
                raise ValueError("Retail asset or executable outside Godot runtime included")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", type=Path, default=ROOT)
    ap.add_argument("--godot-archive", type=Path, required=True)
    ap.add_argument("--godot-license", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    result = build(args.source_root, args.godot_archive,
                   args.godot_license, args.output)
    print(json.dumps({"status":"ok", "schema":SCHEMA,
                      "prototype_version":result["prototype_version"],
                      "no_retail_assets":True,
                      "output":str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
