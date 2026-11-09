# DX2Ed v0.49: source-section navigation and filled MOPP subset preview

## User-facing workflow

This draft stacks on v0.48 PR #116. With an authenticated original GMP open:

1. Enable **Inspect source collision** and select an original MOPP-linked triangle.
2. Run **Analyze MOPP subset** in the source-section topology Inspector.
3. Choose an adjacent render-section tuple discovered through exact-weld edge incidence and select it. DX2Ed jumps to the lowest observed original triangle ID in that neighboring MOPP section.
4. Optionally enable **Fill MOPP subset** in the source-collision toolbar to draw the selected section's MOPP terminal-leaf triangles as a translucent viewport overlay.

## Provenance and bounds

- Neighbor links come from the existing source-SHA-bound MOPP terminal-leaf edge-incidence table and exact original Level XYZ float32 weld IDs.
- They are not inferred from spatial proximity, render-material name equality or Godot preview-coordinate epsilon welding.
- Each neighbor record exposes the minimum observed original triangle ID as a deterministic navigation target, while retaining the source block/render block/render section tuple.
- The filled preview is generated from the same authenticated picker face/vertex tables and is capped atomically at 8,192 triangles.
- A 0.0015-Godot-unit normal offset is applied only to the transient display mesh to reduce z-fighting. Original cache vertices and imported meshes are not modified.
- Transparent fill uses depth testing, double-sided rendering and disabled shadow casting. It is an editor overlay, not a collision or render-material assignment.

## Evidence boundary

The source cache contains only MOPP terminal-leaf triangles. Consequently, both the neighbor graph and filled preview are a subset of original Level geometry. They are not a complete Flesh render section, original BSP surface polygon, Havok adjacency/contact mesh, walkability result, physics material, shader interpretation or native material index. Zero-area non-leaf Level triangles remain outside this workflow.

The 8,192-triangle cap refuses without partial geometry. The separate topology analysis still has its 8,192-triangle and 1,024-incidence-per-edge atomic limits. No GMP/IBD/BSP/material/collision/lightmap/GameSys/TriggerScript writer is enabled. No retail game runtime acceptance is claimed.

## Validation

Synthetic Godot 4.3 tests cover:
- exact-weld neighboring section provenance and deterministic representative triangle IDs;
- the selectable neighbor list and signal-driven navigation;
- filled triangle vertex count, translucent material, depth testing and disabled shadows;
- atomic preview cap and invalid cap refusal;
- main editor toolbar integration, selection changes and overlay cleanup when source inspection is disabled.

Python contract tests require the helper, UI wiring, Windows package manifest and explicit native-writer limitations. The official Windows prototype CI runs the same Godot smoke fixtures against the bundled Godot 4.3 executable. No retail assets are included in CI.
