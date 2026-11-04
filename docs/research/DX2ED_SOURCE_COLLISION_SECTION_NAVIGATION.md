# DX2Ed: inspect and browse original MOPP-linked render sections

Read-only DX2Ed/Godot follow-up to #33. This adds source-ID-preserving **render-section navigation**, optional bounded section wire overlays, and copyable evidence, without changing the source GMP, the GLB actor picker, property drafts, or native Save As behavior.

## Original-game provenance, not inferred physics

The existing original Level/MOPP validation establishes **triangle IDs and their associated packed Flesh render block and section**. Each section carries an observed render-material name. This is not an authenticated Havok friction/filter/material index, a native BSP polygon, or a runtime contact result.

The Godot sidecar from #33 has original Level triangle IDs, verified block/section ordinals, a render-material ID and source-hash-bound Level coordinates. The new inspector groups all *MOPP terminal-leaf triangles* sharing the **(source block ID, render block ordinal, render section ordinal)** tuple. This avoids accidentally merging two different sections with identical names, and avoids treating an ignored degenerate source triangle as a pickable collision face. A contradictory material ID within a single tuple is refused.

## UX

1. Open an original DX2 GMP in DX2Ed, enable **Inspect source collision**, and click a collision-linked surface.
2. The inspector displays the original triangle ID, material **name**, section identity, and **position/count within its original section**.
3. Use **Previous in section** and **Next in section** to step through original triangle IDs in numerical order. These are editor navigation operations at triangle centroids, **not new raycasts or Havok contacts**.
4. Enable **Outline section** to draw temporary cyan wire edges over every MOPP-linked triangle in that exact section. The preview is intentionally refused (with an explanation) for sections larger than **1,024 triangles**, to avoid UI stalls or incomplete, misleading partial outlines.
5. Use **Copy triangle evidence** for JSON with the original GMP name and SHA-256, triangle ID, section identity, render-material string, preview-space position and normal. The JSON explicitly disclaims physics-material identification and game writes.
6. Disable collision inspection or open another map to clear **all** section and single-triangle overlays and restore regular actor selection.

The section overlay is editor-only; it is *not* a collision map, an editable brush, a Havok MOPP view, or something that is included in the native writer. Preview coordinates retain the independently checked `(Level.x, Level.z, Level.y) * 0.1` conversion from PR #33. Geometry is never persisted back into a retail GMP.

## Verification

Headless Godot 4.3 tests in `native_editor/godot_editor/tests/smoke_source_collision_picker.gd` check: singleton and shared section grouping; deterministic previous/next original Level IDs; exact bounded outline vertex count; excessive preview refusal; missing original IDs; contradictory material IDs; source-bound evidence JSON; nav-at-centroid vs real ray-hit distinction; actual editor UI activation and cleanup. Earlier Python provenance tests continue to validate original source geometry.

Run headless fixture test (no retail assets required):

```bash
godot --headless --path native_editor/godot_editor --script res://tests/smoke_source_collision_picker.gd
```

Original 19-map geometry/MOPP/section/cache validation is documented in PRs #27 through #33. **No new claim is made of another full 19-map CI run in this PR.** The UI feature should be tested interactively on Windows after Godot CI succeeds.

## Limits and next steps

- Source MOPP triangle references may not behave like live Havok contacts or DX2 player collision.
- The overlay includes shared internal wire edges, and intentionally does not claim to reconstruct open/non-manifold geometric boundaries.
- No verified Havok physical-material indices, source BSP face vertex pool, collision shape writer, or playable edited level exists yet.
- A later optimization may support filtered larger sections and user-selected material-name displays, with performance tests.
