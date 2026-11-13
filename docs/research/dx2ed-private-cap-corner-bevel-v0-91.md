# DX2Ed v0.91: strict three-face private Box corner bevel

**Scope:** Godot 4.3 editor-only geometry derived from an authored `Brush::Box`, not compiled Deus Ex: Invisible War BSP, game collision, original GMP/IBD, or a playable retail mission.

## Authoring workflow

Select a private Box with one to seven existing convex clipping planes. Select a visible cap using the `Plane n` Inspector or the existing Alt+Shift viewport pick. The new **Cap corner** dropdown lists only eligible vertices where the visible cap meets **exactly two other independently oriented planar faces**. A temporary magenta sphere marks the selected vertex. Choose a local **0.05–0.40 m** inset and click **Bevel corner**.

A successful action appends one additional convex cutting plane, selects its new cap, and creates **one Undo/Redo transaction**. The remaining original planes retain their coefficients and order. The project keeps the existing `DX2Ed-prop-draft-v1` representation, including Save/reopen. The corner marker is editor-only, parented to the authored draft mesh and never registered as a game actor.

## Geometry and topology

`private_box_cap_corner_bevel.gd` reuses the v0.90 true cap-edge incidence ledger. It rejects interior triangulation fan diagonals and nonmanifold/open boundaries. Each candidate boundary vertex must have two incident genuine cap perimeter edges. The helper additionally scans **all triangles incident on the vertex** and deduplicates outward face normals; it accepts only three distinct incident planar face orientations. Thus a vertex where a fourth surface meets without sharing a cap edge is not treated as a simple trihedral corner.

For a selected corner `p` with three outward unit face normals `n_c`, `n_1`, and `n_2`, construct an inward corner chamfer with:

`n_b = normalize(n_c + n_1 + n_2)`

`d_b = n_b · p − h`, for `0.05 ≤ h ≤ 0.40` local Godot metres.

The new kept halfspace is `n_b · x ≤ d_b`. A minimum noncoplanar normal-triad determinant is required, and the complete new clip stack must pass existing strict `BrushGeometry` validation and rebuilding of a closed, finite, nondegenerate and shrinking convex triangle soup. Maximum total clipping planes remains **eight**. Failed actions leave the previous private brush and edit history intact.

## Synthetic Godot test

The test `native_editor/godot_editor/tests/smoke_private_box_cap_corner_bevel.gd` uses an invented **2×2×2 m** Box clipped at local x=0. It checks four 3-face cap corners and chamfers the (0,1,1) vertex using h=0.1 m. The newly appended outward normal must be `(1,1,1)/√3` and signed offset `2/√3−0.1`, while the original x-cut remains unchanged.

The expected volume is `4−(0.1√3)^3/6` cubic metres. The fixture verifies analytic volume, closed manifold triangle edges, invalid corner and depth refusal, the eight-plane ceiling, actual Inspector controls, correctly positioned editor-only marker, one Undo/Redo transaction, and refusal to expose the private controls on an imported `StaticMeshActor`. The Godot 4.3 native scene-fixture workflow now compiles the helper and runs the test. The Windows prototype manifest and prototype doctor require the helper.

## Remaining gaps

This feature is **vertex chamfering**, not unconstrained 3D vertex translation or arbitrary edge topology editing. Native DX2 World BSP mutation, CSG compilation, collision/Havok/MOPP regeneration, original game asset writing, and playable retail custom levels are still outstanding. T3Ed `vertex_face` and `brush_boolean` capabilities remain **partial**.
