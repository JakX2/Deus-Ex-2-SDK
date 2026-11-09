@echo off
setlocal EnableExtensions
cd /d "%~dp0"
call "%~dp0CHECK_DX2ED.cmd"
if errorlevel 1 (
  echo.
  echo DX2Ed cannot launch until the checks above pass.
  if /I not "%~1"=="--self-test" pause
  exit /b 1
)

set "DX2ED_PROJECT=%~dp0native_editor\godot_editor"
set "DX2ED_GODOT_GUI=%~dp0runtime\Godot_v4.3-stable_win64.exe"
set "DX2ED_GODOT_CONSOLE=%~dp0runtime\Godot_v4.3-stable_win64_console.exe"

if /I "%~1"=="--self-test" (
  echo.
  echo Running asset-free Godot 4.3 DX2Ed source fixtures...
  set "DX2ED_SELFTEST_FAILED=0"
  for %%S in (
    smoke_python_runtime.gd
    smoke_light_color_panel.gd
    smoke_multi_light_color_panel.gd
    smoke_native_scalar_panel.gd
    smoke_multi_native_scalar_panel.gd
    smoke_actor_property_workbench.gd
    smoke_workbench_filter_view.gd
    smoke_workbench_actor_navigation.gd
    smoke_scene_actor_workbench_bridge.gd
    smoke_orthographic_authoring_views.gd
    smoke_t3ed_face_edit_roundtrip.gd
    smoke_draft_brush_viewport_face_pick.gd
    smoke_custom_polygon_geometry.gd
    smoke_matlib_browser.gd
    smoke_matlib_polygon_assignment.gd
    smoke_source_surface_matlib_crossref.gd
    smoke_source_section_topology.gd
    smoke_mission_logic_draft.gd
    smoke_dialogue_design_draft.gd
    smoke_original_script_ibd_provenance.gd
    smoke_script_index_hypothesis_audit.gd
    smoke_mission_kernel_script_view.gd
    smoke_triangle_picking.gd
    smoke_source_collision_picker.gd
    smoke_capsule_contact_preview.gd
    smoke_interactive_capsule_sweep.gd
    smoke_source_surface_step_diagnostics.gd
    smoke_exact_source_edge_transitions.gd
    smoke_source_edge_capsule_probe.gd
    smoke_source_edge_capsule_height_overlay.gd
    smoke_source_edge_capsule_height_replay.gd
  ) do (
    echo Testing %%S
    "%DX2ED_GODOT_CONSOLE%" --headless --path "%DX2ED_PROJECT%" --script "res://tests/%%S"
    if errorlevel 1 (
      echo FAILED: %%S
      set "DX2ED_SELFTEST_FAILED=1"
    )
  )
  if "%DX2ED_SELFTEST_FAILED%"=="1" exit /b 1
  echo.
  echo Running project startup smoke check...
  "%DX2ED_GODOT_CONSOLE%" --headless --path "%DX2ED_PROJECT%" --quit-after 3
  if errorlevel 1 exit /b 1
  echo DX2Ed Windows prototype self-test: PASS
  exit /b 0
)

echo Starting DX2Ed Windows prototype...
echo Use Open DX2 map (.gmp) for original owner files, or Load demo cubes.
echo Original GMP/IBD will not be bundled or uploaded by this launcher.
if /I "%~x1"==".gmp" (
  if not exist "%~f1" (
    echo Original GMP path not found.
    exit /b 1
  )
  echo Opening dropped original GMP through the normal read-only cache importer.
  start "" "%DX2ED_GODOT_GUI%" --path "%DX2ED_PROJECT%" -- --gmp "%~f1"
) else (
  start "" "%DX2ED_GODOT_GUI%" --path "%DX2ED_PROJECT%"
)
if errorlevel 1 (
  echo Could not start bundled Godot 4.3. Try CHECK_DX2ED.cmd.
  pause
  exit /b 1
)
exit /b 0
