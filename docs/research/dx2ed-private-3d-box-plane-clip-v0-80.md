# DX2Ed v0.80: first capped 3D Box plane clip in private Godot drafts

**Boundary:** this is a single arbitrary 3D **local plane** clipping one
user-authored **Box preview brush**. It does not edit original DX2 BSP,
compile native CSG, rebuild Havok collision, or produce playable geometry.

## Workflow

Select one editor-created \`Brush::Box\`. Its Inspector exposes **3D Box
plane clip (private preview only)**:

- **Yaw** 0–359.9 degrees and **Elevation** -90–90 degrees define the cut
  plane's **outward unit normal in Godot local X/Y/Z**. This is not UE
  native BSP plane orientation.
- **Offset m** is the signed distance along that unit normal in local
  Godot metres; it is limited to [-256,+256]. Choose **Keep <= plane** or
  **Keep >= plane** to retain the desired halfspace.
- **Clip 3D Box** replaces any existing private clip on that same source
  Box. This is deliberately a one-plane operation rather than sequential
  CSG. **Reset to Box** removes the clip.

The unchanged Box's six outward-oriented quads are clipped against the
halfspace, and an oriented cap closes the intersection using the original
twelve box-edge crossings. The cap is sorted in plane coordinates. The
resulting preview uses one Godot triangular surface. The existing brush
size, transform and editor-private project persistence are retained.

## Defensive geometry rules

The \`private_box_clip.gd\` helper validates a finite unit normal, finite
offset, positive dimensions and both sides having clearance from the plane.
It rejects empty or unchanged cuts, near-tangent cuts, malformed input
normal vectors, zero/near-zero triangles, nonmanifold edges and near-zero
or nearly full retained volume.

For every accepted generated triangle mesh it requires **exactly two
incidences per undirected geometric triangle edge**, finite points and
a positive, strictly reduced signed enclosed volume. This is a
conservative manifold check that may refuse some valid cuts through
difficult corners rather than fabricate a crack or self-intersection.

The original Box face-resize and cuboid-specific picking tools become
unavailable while a clip exists because its faces are no longer six
unmodified axis-aligned rectangular faces. **Reset to Box** restores
those tools. Undo/Redo and private \`DX2Ed-prop-draft-v1\` Save/reopen use
the same validated \`Brush::Box\` data model, with one optional
\`clip_plane\` record.

No source GMP/IBD files, shaders, collision or gameplay state are written.

## Synthetic verification

The existing real Godot 4.3 brush authoring smoke is expanded with:

- Pure half-box volume = half the original box's volume, for both retained
  sides; a diagonal three-axis center cut and strict manifold checking.
- Nonunit, malformed, nonfinite, near-tangent and out-of-bounds plane
  refusal; unsupported clip metadata on Floor and invalid cuboid face
  interaction refusal.
- Actual Inspector operation on a rotated private Box, capped mesh
  verification, no-op Undo suppression, Undo/Redo, private JSON Save/reopen,
  Reset to Box and Reset undo/redo.
- An unchanged synthetic original-source file SHA, without any retail game
  files or assets in the test bundle.

### Remaining native-engine work

This does **not** implement arbitrary mesh clipping, multi-plane CSG,
Intersect/Deintersect, terrain, native surfaces/vertices, Havok/MOPP cooking,
or a verified retail-game level compiler. In the T3Ed parity tracker, the
brush/boolean area remains **partial**. Only this limited Box preview
plane-cut capability has advanced.
