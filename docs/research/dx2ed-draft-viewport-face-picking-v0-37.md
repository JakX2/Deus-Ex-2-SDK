# DX2Ed v0.37: selecting a draft brush face directly in the viewport

**Status:** editor-only Godot 4.3 feature, derived from the existing
v0.36 face Inspector, not a native BSP reader or a T3Ed renderer.

## Workflow

1. Open a map or the synthetic demo in DX2Ed.
2. Use Brush to create an editor-only Box, Wall or Floor.
3. Select exactly one such brush and point at its visible face in either
   the 3D Perspective or a Top/Front/Side orthographic view.
4. Hold **Alt+Shift** and **left-click** without dragging. The Inspector
   selects the matching local `-X/+X/-Y/+Y/-Z/+Z` face.
5. Press **In** or **Out** to resize the chosen face by the editor Grid m
   increment. The other plane stays anchored. Undo/Redo via Ctrl+Z/Y.
6. Save/reopen the private DX2Ed project as before. The modified brush
   geometry is saved; the ephemeral face choice itself is not written.

The gesture overrides normal Alt orbit only for the single selected eligible
draft brush. Regular Alt+drag orbit (or planar pan), Ctrl/Shift additive
selection, actor picking, and gizmo moves work as before. A missed face click
preserves the Inspector's previous choice. It never switches selection to an
original map mesh.

## Fail-closed geometry

`BrushGeometry.pick_draft_face` computes an oriented, local-axis ray/
cuboid intersection using the source-independent draft transform's affine
inverse. Six faces use the same order as Inspector. It explicitly gates:

- Unsupported brush types, including Stairs, Ramp, Cylinder, Cone, Sphere.
- Any preview that was not created via a valid `Brush::` draft source.
- Singular/nonfinite 3D transforms, zero/nonfinite rays, and parallel misses.
- Rays missing the selected brush, even if they cross another imported mesh.

A ray originating inside a box selects the first exiting face. The returned
result is the face index and a world-space hit for editor inspection only.

## Verification

A new Godot source-only smoke instantiates the actual DX2Ed UI and checks
all six faces on a rotated synthetic brush, inside/parallel/missed rays,
invalid/draft-only gates, Inspector selection, In/Out resizing, fixed
opposing plane, Undo/Redo, and refusal to pick original actor faces.
`START_DX2ED.cmd --self-test` runs this using the bundled official
Godot 4.3 Windows executable. The release manifest and offline doctor
require the new smoke script.

The existing full private scene save/reopen and selection roundtrip smoke
continues to run unchanged. No retail GMP, IBD or T3Ed game assets enter CI.

## Non-goals

Picking a face is not dragging that face with the mouse, and no original
Unreal brush topology, CSG operation, compiled BSP leaf/zone, collision,
lightmap, GameSys or runtime level export is implemented. Next milestones
are visible face highlighting, direct snapped drag handles, and explicit
material/UV draft authoring, while native geometry remains read-only
until separately authenticated.
