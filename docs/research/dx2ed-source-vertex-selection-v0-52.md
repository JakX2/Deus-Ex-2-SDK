# DX2Ed v0.52: interactive exact-weld source-section vertex selection

## User-facing workflow

1. Open a user-owned original GMP through the existing read-only importer.
2. Enable **Inspect source collision** and select an authenticated MOPP-linked original Level triangle.
3. Choose **Analyze MOPP subset** in the source-section topology Inspector.
4. Enable **Show exact-weld vertex handles**.
5. Hover a handle to see its original Level float32 weld ID, incident edge count and incident original Level triangle count.
6. Click to open **Selected original Level weld vertex**.
7. Navigate to an incident original Level triangle or an observed adjacent MOPP-linked section representative. Copy the bounded source-pinned JSON report when needed.

## Data and selection model

The vertex inventory is derived only from the already validated v0.50 exact-weld edge report. It groups the two original weld endpoints of each edge, carries the preview coordinates, unions local incident Level triangle IDs, and gathers adjacent-section representative triangle IDs observed on incident cross-section edges.

The inventory is bounded by 24,576 input edges and 49,152 possible endpoints. Per-vertex limits are 4,096 incident edges, 8,192 incident Level triangles, and 1,024 adjacent-section representatives. Invalid counts, duplicate or unsorted weld IDs, non-finite coordinates, malformed edge keys, an edge key that does not contain its owning weld ID, and mismatched source identities refuse the complete report.

The viewport uses a 32-pixel screen grid and a 12-pixel hit radius. Its cache signature includes camera transform, projection, orthographic size, FOV, near/far clip, aspect policy, projection offsets and viewport dimensions. Only points inside the camera clip range are indexed. Hover and selection markers are transient, unshaded, depth-test-disabled editor-only geometry.

## Inspector and navigation

The selected vertex exposes:
- Original Level float32 weld ID.
- Godot preview XYZ.
- Incident exact-weld edge keys.
- Incident original Level triangle IDs.
- Adjacent MOPP-linked section representative triangle IDs observed through incident edges.
- Select incident triangle, jump to adjacent section, and copy selected vertex JSON actions.

Navigation is explicit. The target original Level triangle is revalidated through the existing source collision picker before selection changes.

## T3Ed relevance

The user's archived T3SDK inventory contains a Godot viewer/t3_pick.gd script (7,104 bytes) alongside t3_map_editor/t3_edits.gd and edit_dock.gd. That establishes a concrete reference workflow for viewport selection and editing docks, but the archive inventory does not prove that the original scripts' selection semantics or data structures are compatible with DX2. DX2Ed implements its own source-pinned MOPP-subset selection path rather than copying T3SDK code or treating T3 .unr BSP data as DX2 .gmp topology.

## Validation

The synthetic Godot 4.3 topology smoke now covers vertex report derivation, incident edge/triangle/neighbor provenance, MultiMesh handles, exact weld picking, forward camera depth, near/far clip behavior, camera cache invalidation, out-of-viewport misses, oversized hit-radius refusal, malformed incident-edge membership, conflicting weld coordinates, tampered selected records, Inspector population, local/adjacent navigation, JSON scope and selection cleanup.

The Windows prototype bundle includes the new helper and its offline doctor requires explicit vertex-picker and no-native-writer manifest flags. The bundled Windows START_DX2ED.cmd --self-test runs the same Godot fixture. The source-only native editor bundle copies the complete Godot editor tree.

## Evidence boundaries

- These are original Level float32 weld identities represented by a selected MOPP terminal-leaf subset, not native BSP vertex IDs.
- The report is not a complete Flesh render section or complete BSP vertex table.
- Screen-space nearest-point picking is a viewport convenience, not a ray/occlusion proof.
- Adjacent representatives are MOPP-linked render-section observations, not proof of native BSP adjacency, Havok contact, walkability or physics.
- Handles and highlights are transient; no original GMP/IBD or private draft geometry is modified.
- Native GMP/IBD/BSP/MOPP/collision/lightmap/material/GameSys/TriggerScript writers remain disabled. No retail game runtime acceptance or playable native custom level is claimed.
- No proprietary retail assets are included in GitHub or CI.
