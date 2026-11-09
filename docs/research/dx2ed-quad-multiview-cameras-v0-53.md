# DX2Ed v0.53: independent quad viewport cameras

## Scope

This change implements a T3Ed-style four-pane navigation workspace in the
Godot editor prototype. It is editor-only. The panes show the same imported
preview scene and read-only source overlays; they are not four independent
maps and do not create native Unreal BSP, zones, MOPP, Havok, collision,
lightmap, TriggerScript or GameSys data.

## View model

- Perspective: independent orbit/fly camera.
- Top (XZ): fixed-axis orthographic camera.
- Front (XY): fixed-axis orthographic camera.
- Side (ZY): fixed-axis orthographic camera.
- Single layout displays the active view at full size.
- Quad layout displays all four views in a 2x2 grid.
- Hovering a visible pane makes its camera active for existing selection,
  source topology picking, gizmos and custom Polygon vertex dragging.
- Keys 1-4 activate a canonical view; key 5 toggles Single / Quad.

All viewports share one editor-only World3D. Each SubViewport owns its camera.
Each planar grid has a unique visibility layer, and each camera culls only the
shared scene layer plus its own grid layer. This keeps orthographic grids from
bleeding into other panes while retaining one shared scene and overlay graph.
Hidden viewports disable render-target updates in Single mode.

## Private workspace format

The existing three-field workspace record (view_mode, grid_step,
grid_enabled) remains accepted. New records add view_layout,
active_view_id, and view_states, containing exactly four camera states.
Each camera state has target (three finite bounded coordinates), distance,
yaw, and pitch. The validator rejects unknown keys, missing panes,
non-finite coordinates, extreme targets, invalid zoom, excessive yaw and
invalid pitch before the draft loader mutates the current scene.

This data remains inside the private JSON prop-draft workspace. It is not
copied into the original GMP/IBD or any native save plan.

## T3ED research boundary

The accessible 2026-11-01 T3SDK archive inventory lists separate Godot
viewer_state.gd, map_viewer.gd, t3_pick.gd, and map-editor scripts.
That inventory is useful evidence that viewer state, viewport picking and
editing-dock behavior are separate reference components. It does not expose
their source implementations in this Library item, and no T3SDK source code
was copied. No direct Google Drive connector was available during this run.

## Verification plan

- Godot 4.3 compiles the orthographic helper and full editor.
- Synthetic Godot smoke verifies four SubViewports share the same World3D,
  each camera has a distinct grid cull mask, visible quad panes render, hidden
  panes pause, and independent camera states survive switching.
- Private JSON transaction save/reopen preserves layout and all four camera
  states; legacy workspace migration and malicious state rejection are tested.
- Windows package manifest advertises the feature but explicitly says there
  is no native writer or native map compatibility claim.
