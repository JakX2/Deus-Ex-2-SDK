# DX2Ed v0.79: angled private Polygon Brush Clip

**Scope:** user-authored Godot preview geometry, not native DX2 BSP/CSG,
collision generation, or playable map compilation.

v0.78 added a conservative local-X/local-Z half-plane cut for an extruded
private \`Brush::Polygon\` draft. This milestone removes the axis-only
constraint while deliberately retaining the original safety gates.

## Editor interaction

Select a single private Polygon draft and open **Clip draft footprint
(private preview only)** in the Inspector:

- **Local X:** the previous axis-aligned cut, offset between -1 and +1.
- **Local Z:** the previous axis-aligned cut, offset between -1 and +1.
- **Angled normal:** enter a normal angle in degrees (0 to 359.9) measured
  from local +X toward local +Z. Enter a signed offset along that **unit
  normal**, between -1.5 and +1.5, then choose **Keep <= plane** or
  **Keep >= plane**.

Example: 30°, offset 0 retains one side of
\`cos(30°)*local_X + sin(30°)*local_Z = 0\`.

This changes only the normalized 2D X/Z footprint. The same source brush
transform and Y extrusion remain, and Godot reconstructs the top, bottom,
and side preview surfaces. Material/UV settings survive. The original
DX2 GMP/IBD actors and source BSP triangles are not clipping targets.

A valid cut is **one Undo/Redo step** and its final outline is saved as a
private \`DX2Ed-prop-draft-v1\` project entry. Reopening the editor draft
reconstructs that preview. The angle and offset are **operation inputs**
rather than permanent surface semantics or DX2 geometry bytes.

## Fail-closed geometry rules

The old axis modes and new angled mode now call the same validated
half-plane clipping routine. The implementation:

- Rejects nonfinite angles/distances, angles outside [0,360), untrusted
  input footprints and cut offsets outside the configured bounds.
- Preserves winding (clockwise or counterclockwise); accepts cuts through
  original corners and removes redundant collinear cut-plane points.
- Does not introduce fake connecting edges across concave polygons with
  **more than two** inside/outside boundary crossings. Such disconnected
  cuts are refused, rather than returning an invented polygon.
- Reuses the original simple-polygon intersection/triangulation, bounded
  3-to-32 vertices, no self-intersections, minimum edge and area gates.
- Refuses no-op cuts, empty cuts, and disallowed tiny resulting polygons
  without changing the current draft or adding an Undo entry.

These checks are conservative; some valid complex cuts are also refused
until the editor has proper disconnected-piece support.

## Fixture evidence

The Godot 4.3 source-only smoke covers complementary 30° cuts with
area conservation, a 45° cut exactly through existing corners, clockwise
winding, nonfinite/out-of-bound input, disconnected concave U-shaped
refusal, actual Inspector angle selection, a styled three-surface mesh,
Undo/Redo, zero-history no-op refusal, private JSON save/reopen, and an
unchanged synthetic source file SHA-256.

The original v0.78 X/Z cases continue to run unchanged. No proprietary
game content or native collision data is needed or bundled.

## Engine-format boundary

This is a **2D extruded footprint** cut, **not** an arbitrary-plane 3D
polyhedron operation and **not** verified native BSP editing. Real
T3Ed-equivalent geometry workflows still need arbitrary 3D CSG clipping,
brush intersection/difference, native DX2 Model surface/vertex ownership,
compiled collision and source/retail game round-trip proof. The
"brush_boolean" parity area remains **partial**, not complete.
