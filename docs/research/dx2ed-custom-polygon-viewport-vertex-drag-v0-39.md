# DX2Ed v0.39: snapped custom-polygon vertex handles

## User-visible workflow

Select one editor-created `Brush::Polygon` draft. In **Top (XZ)** or **Perspective**, the editor draws a footprint wire and one colored handle for each validated outline corner. Drag a handle to reshape the footprint directly in the viewport.

The drag ray intersects the selected brush's transformed top plane. The resulting world X and Z coordinates snap to the current **Grid m** spacing; the Y coordinate is solved back onto that same plane before conversion to local normalized X/Z. The entire candidate outline is validated before the preview mesh is replaced. A crossing, collapsed, non-finite or out-of-bounds candidate is rejected and the last valid mesh remains visible. Handle size tracks the current viewport zoom.

Front (XY) and Side (ZY) are deliberately view-only for this planar XZ editor. The current tool edits only the selected editor-owned `Polygon` draft, never an imported source actor, original BSP triangle, collision mesh or retail map.

## Transaction and persistence

A mouse press on a visible handle captures the existing complete private editor state and the original polygon outline. Pointer motion updates the live preview from that stable starting outline, avoiding cumulative coordinate drift. Mouse release records one `Drag custom polygon vertex N` history item. Existing Ctrl+Z/Ctrl+Y applies the complete before/after snapshots, including the brush spec, transform and selection. The polygon itself remains part of the existing private JSON Save draft / Load draft schema; temporary handle meshes and the footprint wire are not serialized.

The handle root and wire are tagged `editor_only` and live outside the imported scene subtree and actor mesh index. They are derived from the selected brush each time its selection, outline, size, view mode, camera zoom or transform changes.

## Tests

`smoke_custom_polygon_geometry.gd` now exercises the actual Godot editor path with invented data:

- six visible handles and editor-only overlay isolation from actor indexing;
- screen-space picking of a specific corner in Top (XZ);
- refusal to begin planar footprint dragging in Front (XY);
- transformed top-plane ray drag with world X/Z snapping;
- exactly one history entry for the completed gesture;
- exact Undo and Redo of the changed corner;
- persistence of the dragged corner through private Save/Load and malicious-draft refusal.

The same smoke is already part of the bundled `START_DX2ED.cmd --self-test` sequence and the native Godot fixture workflow. The source-only Windows bundle already includes `main.gd` and this smoke path, so no retail assets or new binary dependencies are introduced. The generated prototype manifest now declares the viewport-handle and grid-snap capability while explicitly declaring the vertex drag native writer unavailable; the offline doctor enforces those flags.

## Limits

This is an interactive Godot draft-preview editor feature. The tests do not establish native DX2 BSP/zone/CSG serialization, collision or lightmap cooking, arbitrary actor spawning, or retail game runtime compatibility. Original GMP/IBD bytes remain read-only and no native writer is enabled.
