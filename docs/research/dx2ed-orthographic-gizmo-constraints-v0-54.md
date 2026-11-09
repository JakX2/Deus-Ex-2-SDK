# DX2Ed v0.54: active-pane orthographic transform gizmos

## User-visible behavior

The quad viewport now gives interactive editor overlays a dedicated cull
layer. The hovered/active pane alone renders the transform gizmo and custom
Polygon footprint handles/wire. The other panes continue rendering the
shared preview scene, imported meshes and read-only source diagnostics, but
do not show a gizmo constrained for a different camera.

- Perspective: all three world-axis Move, Rotate and Scale handles.
- Top (XZ): X/Z Move and Scale; Y-axis Rotate ring; two-axis XZ Move plane.
- Front (XY): X/Y Move and Scale; Z-axis Rotate ring; two-axis XY Move plane.
- Side (ZY): Y/Z Move and Scale; X-axis Rotate ring; two-axis ZY Move plane.
- The axis normal to an orthographic view is intentionally hidden. Use
  Perspective or the Inspector to change depth.
- Orthographic gizmo size is based on camera world-height and viewport pixels.
- Ctrl Move snapping aligns the resulting world pivot to Grid m. Free drags
  remain continuous.
- A completed drag is one existing history transaction; Ctrl+Z/Ctrl+Y and
  private JSON Save/reopen preserve the transform.

## Implementation and verification

The orthographic authoring guide defines the view-plane axes, view normal,
interaction-layer cull mask, and bounded plane/axis drag math. The main editor
routes the active pane camera rays through those helpers. The plane handle
is a transient editor-only BoxMesh; it is not a brush, actor or collision
primitive.

The new Godot smoke creates an invented private Polygon brush in the actual
Godot editor, checks all four views and all three tools, checks active-pane
cull masks, drags the Top XZ plane handle, verifies one Undo transaction,
Undo/Redo and private draft Save/reopen. The existing quad-camera smoke also
checks that the interaction layer follows the active pane. Python contract
tests, Windows package manifest/doctor and bundled self-test require the new
helper behavior and smoke.

## T3Ed reference boundary

The user Library's T3SDK archive inventory lists a viewer picking script,
map-editor editing script and edit-dock script as separate components. This
is inventory metadata, not a source-level reconstruction of their gizmo
math. DX2Ed uses independently authored Godot code; no T3SDK code or binary
is copied, and no shared native DX2 format is inferred.

## Compatibility boundary

All transforms remain private Godot preview transforms in the existing JSON
draft. No original GMP/IBD is modified. No native BSP/CSG/MOPP/Havok,
collision, lightmap, GameSys or TriggerScript writer is enabled. No retail
game load or playable native level is claimed.
