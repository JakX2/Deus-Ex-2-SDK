# DX2Ed v0.48: source render-section topology subset Inspector

## User-facing workflow

This milestone is developed on a new isolated draft branch stacked on v0.47
PR #115; it does not merge earlier drafts.

With an authenticated original GMP open, enable **Inspect source collision** and
click a MOPP-linked Level triangle. The Inspector now offers **Analyze MOPP
subset** for the selected Flesh render-section tuple
(source_block_id/render_block_ordinal/render_section_ordinal).

The bounded report includes:

- MOPP-linked triangle count in the selected render-section subset;
- exact original Level-welded vertex and edge counts;
- area, area-weighted centroid and bounds converted back to original Level units;
- connected-component count and the largest component sizes;
- section-local perimeter/shared/non-manifold edge counts and perimeter length;
- cross-section shared edges found among the loaded MOPP leaf triangles;
- the original full-Level source edge-classification counts for each unique
  source edge touched by this section; and
- neighboring MOPP-linked render-section tuples, material names and shared
  exact-welded edge counts.

The **Copy topology JSON** action exports only this bounded derived report. It
does not export source bytes, file paths, material payloads or private assets.

## Geometry and provenance rules

- Section membership comes from the validated original source block/render
  block/section tuple, not from spatial proximity or material-name equality.
- Connectivity uses the exact original Level XYZ float32 weld IDs already
  validated by the source edge audit. It never welds preview coordinates with
  an epsilon.
- Area and bounds are calculated from the selected MOPP terminal-leaf subset.
  The Level-to-Godot preview transform is inverted as (x,z,y) * 10 for the
  reported Level XYZ values; area is scaled by 100.
- The 8,192-triangle cap is atomic. Oversized sections return identity/count
  metadata and a skipped marker, not partial statistics.
- Component-size output is capped at 16 entries; neighboring sections at 64,
  with omitted counts shown explicitly.

## Evidence boundary

This is **not** a complete Flesh render section, original BSP surface database,
native BSP polygon, Havok adjacency graph, collision response, walkability
classification, physics material, shader interpretation or native material
index. The source edge classes are inherited from the full original Level
edge audit, while connectivity and neighboring-section discovery are limited
to the MOPP terminal-leaf triangles present in the validated sidecar. A MOPP
omission therefore remains an explicit scope limit.

The panel is read-only. It does not modify GMP/IBD files, private draft scenes,
native material assignments, collision, lightmaps, GameSys or TriggerScript.
No retail game runtime acceptance is claimed.

## Validation

A synthetic Godot 4.3 fixture covers two connected triangles plus one
disconnected triangle in one section, an adjacent render section sharing an
exact-welded edge, Level-unit area/bounds conversion, edge-class totals,
component sizes, neighbor provenance, invalid IDs and atomic size-cap refusal.
The Windows bundled executable self-test includes the same fixture. A Python
contract test verifies the exact-weld, cap, scope labels and Windows packaging
requirements. No proprietary retail assets are included in CI.
