# DX2Ed v0.83: bounded eight-plane convex Box authoring

**Status:** Godot 4.3 editor-private draft geometry. Not native Deus Ex: Invisible War BSP, CSG, collision, Havok/MOPP, or a working retail mission.

## What changed

- Increase editor-authored `Brush::Box` local clip stack from four to **eight** sequential unit-normal 3D half-space planes. Original `clip_plane` (one) and `clip_planes` (2–8) private JSON layouts are retained.
- Keep the v0.82 Inspector's individually selectable **Update selected**, **Remove selected**, **Add plane**, **Remove last**, **Replace 3D Clip** and **Reset to Box** actions. The counter, Add gate and feedback share `private_box_multiclip.gd::MAX_PLANES`.
- Cap convex face count at **14** (six original Box faces plus up to eight cut caps). Increase the closed triangle-soup bound from 36 to **44**. For a convex polyhedron with F ≤ 14 planar faces, Euler's relation and the planar simple-graph edge bound give T = 2E − 2F ≤ 4F − 12 = 44 triangular fan elements. The existing geometric edge-incidence, nonzero triangle area, outward signed volume, strict per-cut volume decrease and minimum clearance checks continue to reject ambiguous drafts.
- This does **not** enable intersect/deintersect, Boolean cuts across arbitrary source meshes, or any editor-to-native level compiler.

## Why the synthetic corner fixture matters

The fixture takes a new **2 × 2 × 2 metre** Box and applies all eight sign combinations of the normalized normals `(±1, ±1, ±1)/sqrt(3)`, each keeping `normal · point ≤ 1.4 m`. Each plane removes one disjoint corner tetrahedron.

With `L = 3 − sqrt(3) × 1.4`, exact expected enclosed volume is:

`8 − 8 × L³ / 6` cubic metres.

The result is a **14-face / 44-triangle** truncated cube: six surviving octagonal original faces, eight triangular cap faces, and 24 distinct corner vertices. This validates the increased complexity limit, not mere acceptance of eight plane records.

The actual Godot fixture also performs eight consecutive Inspector operations, confirms the ninth plane cannot modify draft/history, verifies closed geometry and expected volume, saves and reopens `DX2Ed-prop-draft-v1`, removes a nonterminal plane with Undo/Redo, and resets to the original Box. Its synthetic source-file SHA-256 must stay unchanged.

## Source and runtime boundaries

- Never modify an original user's `.gmp`, `.ibd`, T3Ed archives or game installation.
- Current clipping is in local Godot metres, and is preview-only private authoring.
- Source-derived World Model BSP surface ownership, native vertex/zone mutation, collision cooking, CSG compiler and retail load/play validation remain absent.
- The T3Ed parity tracker continues to count this capability as **partial**, not **verified**.

## Manual Godot workflow

1. Open the native Godot editor project in `native_editor/godot_editor`.
2. Create/select one editor-authored **Brush::Box**, not an imported original DX2 BSP/mesh.
3. Set local yaw, elevation, signed offset and kept side in the 3D Box clip Inspector.
4. Click **Add plane**, up to eight times; use the plane selector to revise or remove an earlier cap.
5. Use **Save Draft** and reopen to inspect the private project. These are *not* game-level exports.

The source-only CI Godot fixture is `native_editor/godot_editor/tests/smoke_t3ed_face_edit_roundtrip.gd`; no retail game files are required.