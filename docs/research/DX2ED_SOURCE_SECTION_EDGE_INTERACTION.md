# DX2Ed v0.51: interactive exact-weld source-section edge selection

## User-facing workflow

1. Open an original GMP through the existing read-only importer.
2. Enable **Inspect source collision** and click an authenticated MOPP-linked Level triangle.
3. Analyze its bounded MOPP terminal-leaf render-section subset.
4. Enable **Show exact-weld edge overlay**.
5. Hover a visible edge. The screen-space picker highlights the nearest candidate
   and reports its original float32 weld-ID pair and incident section triangle count.
6. Click the edge to open **Selected exact-weld source edge** in the Inspector.
7. Choose a local incident Level triangle or jump to the adjacent MOPP-linked
   section's deterministic representative triangle. Copy selected-edge JSON
   for a source-pinned, read-only record.

## Selection implementation

The new source-section edge picker validates the complete bounded edge report
before building a screen-space index. It projects exact source endpoints through
the active Godot camera and stores them in a 64-pixel screen grid. Edges spanning
more than 64 cells are kept in a bounded fallback list. Hover queries inspect
only the current cell and that fallback list, then rank candidates by screen
distance and camera depth.

The projected index is tied to the source SHA and section key, and caches the
camera transform, projection, orthographic size, FOV and viewport dimensions.
Camera or viewport changes invalidate the index. The selection record is
rechecked against the currently active report before the Inspector accepts it.

Hover and selected-edge highlights are transient editor-only ribbon/sphere
markers. They do not become scene actors, brush geometry, saved draft data,
collision objects or native map bytes. The selected edge remains independent
from the selected source triangle; navigation is an explicit Inspector action.

## Evidence boundaries

- Weld IDs are exact original Level float32 position identities from the
  authenticated MOPP terminal-leaf subset. They are not native BSP vertex IDs.
- Local triangle IDs are original Level triangle IDs represented in the
  selected section's MOPP subset.
- External navigation uses the existing MOPP-section representative triangle
  provenance and revalidates the target through the source picker.
- The raw source edge-class code is copied without assigning new semantics.
- Screen-space nearest-segment picking is a viewport selection convenience,
  not a ray/occlusion proof or a complete topology query.
- This does not establish complete Flesh BSP edge/vertex identity, Havok
  contact adjacency, physical material, walkability, shader behavior or
  native surface/material indices.

## Validation

The synthetic Godot fixture checks exact-weld recovery, screen-grid indexing,
camera-signature invalidation, out-of-viewport misses, tampered-weld refusal,
transient highlight construction, selected-edge Inspector population, local
triangle navigation, adjacent-section navigation and read-only JSON scope.
The existing Windows self-test runs the same fixture. Python source-contract
and portable-package tests require the helper and keep native edge writers
explicitly disabled.

No proprietary retail assets are included in CI. No original GMP/IBD files are
modified, and no native BSP, MOPP, collision, lightmap, material, GameSys or
TriggerScript writer is enabled.
