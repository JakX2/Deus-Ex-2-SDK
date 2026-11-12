# DX2Ed v0.84: selected convex Box clipping-plane reordering

**Scope:** source-independent, editor-only Godot 4.3 geometry. Not a native DX2 BSP/CSG/collision writer.

## User workflow

For one selected editor-authored `Brush::Box` with at least two cuts in its private `clip_planes` stack, select a plane in the Inspector and click **Move plane up** or **Move plane down**. The selected plane trades its position with its adjacent neighbor. The Inspector follows the relocated selected plane and disables outward moves at the first and last positions. Each successful swap creates one Undo/Redo transaction. The original transforms, brush size, plane coefficients and kept sides are preserved. Private `DX2Ed-prop-draft-v1` Save/reopen preserves the new plane order.

## Why reordered intersections must be validated

Ideal convex halfspace intersection is commutative, but the editor intentionally requires **each sequential cut** to be a meaningful, strictly shrinking capped convex volume. Reordering can create an intermediate no-op, near-tangent, nonmanifold, numerically unstable, or otherwise invalid cut even when the final mathematical intersection appears equivalent. The operation therefore rebuilds the entire candidate stack through the existing source-private validation and mesh checks **before** mutating the active brush.

On rejection, no saved geometry, selected plane, or Undo/Redo history is changed. Invalid direction, missing selected plane and moving across stack boundaries are also harmless rejections. Successful operations preserve the existing closed-triangle edge incidence, finite positive signed volume, sequential shrink and up-to-eight-plane limit.

## Synthetic Godot 4.3 regression

The existing real editor fixture builds a private two-metre Box clipped at all eight corners and checks the closed **14-face / 44-triangle** result against analytical volume. The v0.84 extension checks:

- First/last plane reorder controls are disabled at forbidden boundaries; invalid moves do not add Undo transactions.
- Moving an interior plane one step downward selects the new index, preserves its original normal/offset, and produces a closed triangle soup with unchanged enclosed volume.
- Undo and Redo restore the two original plane orders without rebuilding the source game file.
- Saving the reordered stack, reopening private JSON and moving it back upward retains plane order, validated geometry and original synthetic source-file SHA.

Use `native_editor/godot_editor/tests/smoke_t3ed_face_edit_roundtrip.gd` in the native scene fixture workflow.

## Native limits

The operation touches no retail `.gmp`/`.ibd` source data, no original compiled World BSP surfaces or vertex ownership, no Havok/MOPP collision, and no playable retail mission. The capability remains **partial** in `native_editor/t3ed_parity.json`.