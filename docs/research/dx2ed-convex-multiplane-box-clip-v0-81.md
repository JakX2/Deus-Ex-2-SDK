# DX2Ed v0.81: cumulative 3D convex Box plane clipping

**Scope:** private authoring in Godot 4.3, **not native DX2 BSP/CSG**.

v0.80 supported one arbitrary oriented 3D cut of a user-authored Box,
generating a capped preview mesh. v0.81 extends that preview to **up to four
successive local 3D half-space cuts**. It is deliberately limited to a
convex descendant of a Box, not a general polyhedron/mesh Boolean editor.

## User-facing behavior

Select exactly one privately authored \`Brush::Box\` preview. The 3D Box
Inspector keeps yaw, elevation, offset and Keep <= / Keep >= controls.
There are four operations:

- **Replace 3D Clip:** replace any existing source-private planes with one
  new cut (preserves v0.80's single-plane operation and legacy saved
  projects). An identical existing single plane remains a no-op.
- **Add plane:** intersect the *currently retained convex volume* with one
  additional unit-normal 3D half-space, up to four total. It is not a
  replacement. Each accepted addition is a single Undo/Redo transaction.
- **Remove last:** pop only the most recently added plane and rebuild the
  earlier volume. The last plane returns the private draft to an uncut Box.
  Removal itself is undoable.
- **Reset to Box:** remove all planes in one undoable operation.

The Inspector displays **Planes: N / 4** and disables Add at four.
Rotated/scaled private transforms and original Box size are preserved.
Cuboid-only face manipulation remains disabled while any cut exists because
a cut Box no longer has the source six rectangular faces.

The project uses one optional \`clip_plane\` for the v0.80 single-plane
format. Two through four cuts use one optional \`clip_planes\` array.
Both keys are forbidden simultaneously, and non-Box brush types cannot
receive either one. This maintains backward compatibility with existing
\`DX2Ed-prop-draft-v1\` private JSON rather than changing the source
GMP or private project schema.

## Mesh and geometry invariants

The source-only \`private_box_multiclip.gd\` starts with six original
outward-wound Box faces and sequentially clips the retained **face
polygons**, not the pre-triangulated mesh. After each cut it:

1. Requires that the plane has finite, source-sized parameters and
   meaningfully intersects the **current** convex volume. Redundant,
   unchanged, nearly empty or entirely excluded cuts fail closed.
2. Clips each existing outward-wound face to the retained half-space;
   collects all resulting points on the new plane, deduplicates and
   sorts them in a stable cut-plane basis to form a new oriented cap.
3. Triangulates the closed face set. Each geometric triangle edge must
   have exactly two incident triangles, all vertices must be finite,
   and triangle areas must be positive.
4. Checks signed enclosed volume is strictly positive, less than the
   original Box volume, and **strictly reduced** relative to the previous
   clip. Unknown, difficult and nonmanifold outcomes are refused rather
   than silently triangulated or reinterpreted as engine BSP.

The total is limited to four clips and ten polygon faces. No multiple
disconnected solids, concave CSG results, self-intersecting meshes,
arbitrary-source mesh modifications or collision editing are supported.

## Synthetic verification

The real headless Godot fixture tests the pure multi-plane mesher and
the actual editor controls:

- Source 2×2×2 cube, one X cut => **4 m³**, two orthogonal X/Y cuts
  => **2 m³**, three X/Y/Z cuts => **1 m³**, and a fourth angled X/Z
  cut yields a smaller positive, closed convex volume.
- Rejection of a fifth plane, mixed single/multi schema, malformed
  non-Box metadata, redundant second plane and sub-clearance slivers.
- Inspector Add plane, no-op refusal without Undo pollution, Remove last,
  undo/redo, Reset and backward-compatible one-plane restoration.
- Four-plane private \`DX2Ed-prop-draft-v1\` JSON Save/reopen,
  original synthetic source SHA unchanged and no original game assets.
- Existing v0.80 single-plane, v0.79 angled footprint and earlier
  viewport tests continue to run.

The Linux test runner independently compiles the helper, and the
Windows source-only prototype ZIP/doctor explicitly require it.

## Native-engine limits

These are Godot **preview** meshes only. T3Ed-style source brush
intersect/deintersect, arbitrary connected or disconnected polyhedral
CSG, native DX2 BSP surface/vertex serialization, regenerated Havok
MOPP collision and retail-game playable level compilation remain
unimplemented. The related T3Ed parity entry stays **partial**.
