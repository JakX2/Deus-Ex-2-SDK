# DX2Ed: exact original collision edge topology overlay (PR #35)

Read-only DX2Ed/Godot feature, stacked on #34 and the verified original Level/MOPP provenance chain from #27–33. Adds **source-validated per-triangle edge types** to the click-inspection overlay. Does not change the .gmp, .ibd, or GLB, and does not feed native Save As.

## Geometry and interpretation

The existing DX2 Level flattened collision-associated vertex array contains duplicates. Index-based edge matching would count many genuinely shared surfaces as open because they use distinct vertex indices. The new backend dx2_collision_edge_provenance.py therefore maps **exactly equal original Level f32 XYZ triples** to one welded position ID before classifying undirected edges among **reachable MOPP terminal-leaf triangles**.

Every selected original Level triangle now has three source edge classifications in AB, BC, CA order:

| Code | Overlay | Source-exact geometric condition |
|---:|---|---|
| 0 | Amber | Exactly two incident MOPP triangles, same **render-material** identifier |
| 1 | Cyan | Exactly one incident MOPP triangle (open boundary) |
| 2 | Pink | Exactly two incident MOPP triangles, different render-material identifiers |
| 3 | Red | Three or more incident MOPP triangles (non-manifold) |

Open boundaries and multiple incident triangles **do not imply invalid Havok collision**. Different render-material identifiers **do not authenticate Havok physics materials**, friction, contacts, original BSP surface IDs, or collision filtering.

No proximity tolerance, epsilon merge, or Godot-preview coordinate weld is used for source classification. Non-MOPP zero-area triangles are explicitly omitted. Every triangle retains its original Level ID and render block/section. Selection, section navigation, preview geometry and clipboard evidence stay editor-only.

## Cache versioning and validation

Because #34's v1 source collision selection cache never contained exact edge topology, the backend and Godot now require **v2** (DX2Ed-source-MOPP-collision-selection-cache-v2) and use the separate private cache filename source_collision_selection_v2.json.

The Python backend performs original triangle/section/MOPP verification before adding three per-triangle edge codes. The Godot cache loader checks every edge code and cross-checks total single-edge incidences and two-triangle shared/seam incidences against summary counts. Source-hash and map-name binding from #33 still apply.

This prevents silent acceptance of old cache data, corrupted edge categories, malformed source indices, and under-accounted geometry. Source files remain untouched.

## Evidence and validation

- native_editor/tests/test_dx2_collision_edge_provenance.py includes **12 new synthetic tests** for same/different render materials, index duplication with identical XYZ, nearby but *non-identical* XYZ, 3+ incident edges, non-MOPP degenerate omissions, malformed data and source nonmutation.
- Existing source cache tests gain v2 schema and edge-provenance assertions.
- Godot 4.3 fixture smoke validates the new v2 cache, refuses inconsistent edge counts and obsolete v1 metadata, verifies selected triangle edge colors and copyable source evidence, and preserves section-navigation/cleanup behavior.
- **Independent archived Seattle Hub OBJ cross-check:** exactly **1,668 welded positions**, **261 open edges**, **3,483 two-triangle same-render-material edges**, **1,227 cross-render-material edges**, **0 non-manifold edges**. These reproduce previously recorded retail-map topology counts. The archived OBJ is rounded textual data, so this is a *secondary reproducibility check*, not a replacement for original-byte validation.
- The previous original-retail 19-map topology audit (#31) established corpus-wide **3,343 open edges**, **63,034 two-triangle edges** (including **16,532 render-material seams**), **12 non-manifold edges**, and **0 two-triangle same-direction winding conflicts**. That is *prior* audit evidence, not a claim that every GMP was reprocessed during this PR.

## How to use

Open the same original GMP in DX2Ed, enable **Inspect source collision**, click a MOPP-linked triangle. The selected triangle's edges are colored by topology kind, and AB/BC/CA labels appear in the inspector. **Copy triangle evidence** includes integer edge codes and readable names. **Previous/Next in section** keeps source topology labels while navigating.

The cyan **Outline section** feature from #34 remains available and distinct from selected-triangle edge classification; it still has its 1,024-face cap. The four-color selected-triangle overlay does not claim to show whole-map edge boundaries.

## No writer yet

No original Havok shape writer, native BSP builder, certified physics-material table, collision reimport, or game-runtime compatibility test is part of this PR. Interactive Windows editor testing is still required.
