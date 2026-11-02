# WTO Terminal architectural frame: geometry visibility investigation

**Status (2026-11-02):** read-only original game data checked; Godot
diagnostic UI implemented; exact in-editor cause of the user's reported
missing right-hand section is **not yet confirmed**. This is not a
skybox or glass-material task.

## Original-source findings

The user selected `StaticMeshActor__578` (GMP export **889**),
resource `1Hub_wto_term-detail1-j`, in WTO Terminal. The user
contrasted a reference image with a brown right-hand support/base
present and a Godot screenshot where it appears missing.

An offline audit of the user's private original GMP + mission IBD found:

- Source placement Unreal XYZ = `(600, 480, 400)`, rotator
  `(0,0,0)`. No source transform correction is applied.
- Original IBD render mesh has **302 vertices**, one section,
  **612 indices = 204 triangles**.
- Original IBD declared bounds, GMP encoded bounds and observed
  rendered vertex bounds match exactly.
- Godot-exported GLB retains the same 204 triangles.
- Independent per-triangle normals audit: 204/204 original face
  windings agree with their stored vertex normals; 0 inverted and 0
  degenerate triangles.
- In a front-facing orthogonal projection of the **source mesh alone**,
  both end supports and the lower rail are present. Its major local
  extent is **480 Unreal units = 9.144 metres**. The end supports are
  far apart, not adjacent beside the same column.
- The screenshot's expected immediate right-hand support is therefore
  **not proven to be another face of this selected actor**. It might
  be a neighboring mesh/BSP surface, occluded geometry or a viewpoint
  difference. It is not justified to synthesize a mirrored copy or
  mutate retail geometry from the screenshots.

## Reversible Godot diagnostic controls

Added to Inspector beneath **Copy placement evidence**:

1. **Isolate selected** hides all other rendered mesh instances,
   including overlapping glass, *only in the running Godot preview*.
   The button becomes **Restore visibility**; toggling it again restores
   the exact original visible flags.
2. **Inspect both faces** replaces *only the selected instance's*
   `material_override` with a temporary opaque cyan,
   unshaded, no-culling material. The original override is restored
   by **Restore materials**. This is a diagnostic, not a permanent
   backface or glass fix.
3. Loading another GLB restores both modes before freeing the old
   scene. All controls are read-only with respect to the original GMP,
   shared GLB mesh/material resources and actor drafts.

Recommended evidence-gathering steps:

- Open the original WTO GMP in the updated editor.
- Select `StaticMeshActor__578`, press **Isolate selected**, then
  **F** to frame the entire long mesh and orbit around both supports.
- If both ends appear in isolation, the source mesh and renderer are
  capable of displaying them; compare the expected position with
  other scene actors. If a part vanishes only after restoring other
  meshes, suspect overlapping/occluding surfaces.
- If a surface is missing even in isolation, press **Inspect both faces**
  and view the cyan copy from both sides. If that reveals it, inspect
  culling, face orientation and camera conventions rather than
  duplicating triangles.
- Toggle both controls off and reopen the map to verify no geometry
  or material edits persist.

## Validation

Native Godot 4.3 headless smoke verifies that isolation hides other
mesh instances, retains the selected mesh, and restores visibility;
double-sided diagnostic only affects the selected instance and
restores original material and transform. The code does not modify
the original glass diffuse or the source GMP.

The screenshot-based geometry discrepancy still requires a user-visible
confirmation with the new controls. **Do not claim a missing-frame
repair before that observation.** No licensed game assets are committed
to this repo.
