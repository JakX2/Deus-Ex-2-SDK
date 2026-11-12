# DX2Ed v0.78: private Polygon Brush Clip in the Godot editor

**Feature status:** working editor-side authoring and private project serialization, **NOT** native DX2 BSP/CSG, collision or terrain.

The original T3Ed includes a BrushClip tool. This milestone adds a deliberately bounded, smaller first part of that workflow to DX2Ed: the player can select one **private Brush::Polygon** draft and retain the portion of its extruded XZ footprint on either side of an axis-aligned clipping plane. The clipping plane is in the draft's normalized local space, not original game-world coordinates. The existing draft transform, Y extrusion, individual top/bottom/side preview materials and UV settings are preserved.

## Editor workflow

1. Select a private Brush::Polygon draft in the Godot editor. Original imported GMP geometry, actor meshes and other brush types are excluded.
2. In the custom Polygon Inspector's **Clip draft footprint (private preview only)** group, choose **Local X** or **Local Z**, enter a normalized plane coordinate within [-1,+1], and choose **Keep <= plane** or **Keep >= plane**.
3. Click **Clip polygon draft**. A valid clip rebuilds the three independent Godot preview mesh surfaces, updates footprint/handles, and records **one undoable edit**. Ctrl+Z / Ctrl+Y and private project Save/reopen use the existing editor infrastructure. All original source files remain unchanged.

The clipping routine is a conservative single-half-plane intersection of a validated simple polygon. It retains the source winding, bounds and numeric data, removes redundant collinear cut-plane corners, revalidates the result with the existing topology/triangulation rules and refuses unchanged, empty, tiny, self-crossing or oversize shapes. If the cut line crosses the source outline more than twice (e.g. a U-shape split into two disconnected islands), the operation is **refused** instead of manufacturing a bridge across the cut. The old draft remains intact and no Undo history is added.

This is a useful, explicitly **partial** entry in the 28-area T3Ed parity tracker. Intersect/deintersect, full arbitrary-plane 3D clipping, terrain, constructive-solid-geometry brush compilation, source BSP vertex and surface ownership, Havok collision cooking, native GMP writing and retail in-game verification remain unsupported.

## Verification

The fixture-only Godot smoke exercises left/right X and Z cuts, clockwise winding, rejection of invalid/disconnected cuts, **real editor Inspector controls**, three-surface preview mesh regeneration, one-step Undo/Redo, no-op refusal without state mutation and the private JSON Save/reopen workflow. The synthetic original source sentinel file is compared by SHA-256 before and after.

No proprietary retail game data is included in the tests or release archive. Any actual game-map modification continues to require independent native format, compiler and retail-engine verification.
