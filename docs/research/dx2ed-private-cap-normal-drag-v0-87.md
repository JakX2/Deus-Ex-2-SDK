# DX2Ed v0.87: snapped interactive private clipped-cap drag

**Feature:** use `Alt+Ctrl+left-drag` directly on a visible clipping cap of one selected, **editor-authored** `Brush::Box`. This is source-private Godot 4.3 authoring, not native DX2 BSP, game collision, original-world CSG or a playable retail mission edit.

## Viewport gesture

1. Create and select a private Box draft. Add one or more validated arbitrary 3D clipping planes, up to eight total.
2. Orbit to view a cap somewhat from the side. Hold **Alt+Ctrl** and press left mouse on its visible face. The same nearest-triangle cap picker used by v0.86 identifies its original private plane index; a hidden cap, imported actor, normal Box face, ambiguous edge or uncut brush cannot start the gesture.
3. Move the cursor along the projected cap normal. Only that plane's **local signed offset** changes. Its orientation, `keep_positive` setting, all other cuts, and draft object transform stay unchanged. Every candidate is snapped to the editor's `Grid m` spacing **relative to the offset at mouse-down**, so starting an off-grid cap does not jump at first contact.
4. The preview mesh is replaced only after `BrushGeometry` validates the entire candidate and rebuilds a closed, strictly shrinking convex hull. Invalid, tangent, no-op or nearly empty cuts leave the last valid preview in place.
5. Release anywhere to commit **one Undo transaction** if geometry changed, or none when no valid change occurred. The project remains a normal private `DX2Ed-prop-draft-v1` and can use the existing Save/reopen path.

The on-screen hint appears in the private Box Clip Inspector. Ordinary `Alt+Shift+click` cap/face picking, `Alt+left` orbit, and uncut Box/Wall/Floor face selection are preserved. The gesture is not enabled for imported game meshes, source BSP, original actors or other draft kinds.

## Coordinate and geometry handling

The view drag-plane contains the private cap's world-space displacement axis (`draft.basis * local_plane_normal`) and faces the camera as closely as the view allows. A camera viewed almost exactly along that axis cannot provide a stable normal drag, and the editor requests orbiting to a side angle. Mouse-ray intersections with this fixed plane determine an incremental **world-space displacement** relative to mouse-down.

`private_box_cap_drag.gd` transforms this increment through `draft.affine_inverse().basis`, projects it onto the local unit normal, snaps the increment in local metres, updates only `clip_plane.distance` or `clip_planes[index].distance`, and validates the resulting brush and closed mesh. This also preserves the correct meaning of `Grid m` under rotated and nonuniformly scaled draft transforms. Invalid transforms, nonfinite rays/displacements, grid steps out of [0.25,64], and illegal offsets are rejected.

The editor retains the initial validated brush and Undo state throughout the gesture. Motion evaluates **from that initial state**, avoiding cumulative snapping drift. Valid preview replacements do not independently add history entries; release compares the first and final draft states.

## Test strategy

`native_editor/godot_editor/tests/smoke_draft_brush_viewport_face_pick.gd` now covers:
- A rotated private two-plane clipped Box, with cap selection from a slanted world-space ray
- Local distance snapping of a 0.31m world-equivalent movement to 0.25m under rotation, and nonuniform scale
- Rejection of malformed indices, nonfinite input, singular transforms, undersized grid and fully redundant caps
- Actual Godot viewport-gesture begin, preview offset without history, invalid motion retaining the previous mesh, single Undo on release, correct Undo/Redo of the full stack, and zero-motion release without history
- Existing v0.86 refusal to target imported actors

The Godot 4.3 native fixture workflow compiles the helper independently and executes the real editor smoke. The Windows source bundle, prototype doctor and packaging tests must include the helper source. No retail assets are embedded.

## What this does not solve

Native UE95 World BSP surface/vertex ownership, arbitrary brush Boolean operations, MOPP/Havok collision regeneration, runtime gameplay validation and writable custom GMP levels still require separate reverse-engineering and tests. The T3Ed `vertex_face` and `brush_boolean` capability areas remain **partial**, not complete.
