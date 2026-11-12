# DX2Ed v0.86: pick one visible private convex Box cap

**Source isolation:** This feature operates exclusively on editor-authored `Brush::Box` private drafts. It neither assigns nor edits original DX2 BSP surface indices, renderer geometry, GMP/IBD bytes, or Havok/MOPP collision.

## Interaction

- Select a private `Brush::Box` with one to eight validated local 3D cutting planes.
- **Alt+Shift+left-click** on a visible cap in the Godot viewport. The cap's corresponding plane becomes the selected Inspector item, and the existing yaw/elevation/offset/kept-side controls populate for that plane.
- A temporary gold line outline follows the cap perimeter. It lives under that private brush's preview node and never enters the private JSON draft, imported original geometry or actor selection.
- A click on an ordinary surviving Box face, a hidden cap behind that face, empty space, or an imported original actor cannot select a cap. Failed clicks leave the selected plane and Undo stack unchanged. Selecting a cap does not itself edit geometry or add history.
- Subsequent Inspector operations, including **Update selected**, **Remove selected** and **Move plane up/down**, retain their existing validation and Undo behavior.

## Geometry implementation

`native_editor/godot_editor/private_box_cap_picker.gd` validates source-independent brush metadata, rebuilds the same capped mesh as the preview and transforms a world-space ray through the private draft's affine inverse. The picker double-sided-tests all preview triangles and chooses the **nearest** hit, even if it is an original cuboid surface. It recognizes a cap triangle only when all three vertices lie on **exactly one** validated local cutting plane. Cap/source edges or competing caps at the same ray depth are refused as ambiguous.

For visual outlines, it collects only triangles on the selected cap, counts canonicalized edges, retains boundary edges that occur once, requires every boundary vertex to have degree two, and offsets the temporary lines along the cap's outward plane normal. This avoids making internal triangulation diagonals appear as editable edges.

There is no native BSP plane ownership or face ID mapping implied by these authoring-local plane indices. A clipped cap may cease to exist after additional cuts; such caps yield no outline and cannot be picked.

## Synthetic regression and packaging

`native_editor/godot_editor/tests/smoke_draft_brush_viewport_face_pick.gd` covers rays on a rotated, invented 2m Box, one and two clip planes, correct cap indices, boundary outlines, hidden source faces, off-target rays, invalid transforms, actual Inspector selection and editor-only outline isolation, and refusal to select imported actors. The native Godot 4.3 fixture workflow explicitly compiles the helper and runs this script.

The source-only prototype doctor, Windows build manifest and Windows bundle smoke now require the new helper. No original game assets are bundled.

## Remaining editor/runtime work

General private 3D polygon face/vertex manipulation, direct cutter plane drag handles, arbitrary source mesh booleans, native DX2 World BSP compiler, collision cooking and playable retail custom missions are still outstanding. The T3Ed `vertex_face` and `brush_boolean` areas remain **partial**.
