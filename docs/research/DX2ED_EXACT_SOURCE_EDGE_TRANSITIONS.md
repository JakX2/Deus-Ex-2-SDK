# DX2Ed exact original Level edge links and hinge diagnostics

Research milestone **PR #50**, stacked on #49. This creates a read-only, source-authenticated neighbor inspector, not Havok runtime physics, navigation, a MOPP writer or actual collision editing.

## Cache provenance upgrade

The existing source picker knew which original Level edges were boundary, interior, render-material seams or non-manifold. But it did not retain the **exact original-coordinate welded vertex IDs**, so computing new neighbors from rounded Godot preview positions could falsely join unrelated faces.

The new Python exporter retains per-vertex exact source weld IDs from original Level XYZ *before* preview conversion and writes per-face arrays named source_weld_ids. Duplicate raw vertex indices are welded when source XYZ is equal, but near-coincident distinct source XYZ is **not** epsilon-welded.

The cache schema is now **DX2Ed-source-MOPP-collision-selection-cache-v3**. DX2Ed writes a separate, fresh **source_collision_selection_v3.json** cache under its private editor cache directory. Old v2 caches are not silently reused or overwritten.

The Godot loader independently reconstructs source incidence from exact welded IDs and checks original edge classes, source render-material ID differences, unique edge counts, maximum incidence and original MOPP-leaf triangle IDs against validated source metadata. Contradictions are rejected. Open edges have one incident face, unique neighbor edges have two, and non-manifold edges have three or more incident faces.

## Read-only editor controls

1. Open an owner-supplied original DX2 GMP and enable **Inspect source collision**.
2. Click an original MOPP-linked triangle.
3. Use the new **EXACT SOURCE EDGE LINKS | RESEARCH ONLY** Inspector section to examine AB/BC/CA original neighbor triangle IDs.
4. Pick an edge. DX2Ed draws the exact shared edge and, where there is one unique source neighbor, that neighbor's triangle outline.
5. Select **Follow original neighbor** to navigate to its original Level triangle ID. This is source-centroid navigation and is **not** represented as a real mouse ray hit.

For one unique two-face connection, the panel shows:
- **Unsigned plane hinge angle:** angle between plane normals ignoring winding sign. 0° is coplanar, 90° is perpendicular, not a signed convex/concave contact angle.
- Neighbor triangle's unsigned slope relative to preview Up (original Level +Z).
- Whether the two opposite triangle corners lie on opposite sides of the shared edge in horizontal XZ projection. Same-side overlaps and vertically projected edges do not receive a positive floor-continuity inference.
- An explicitly **geometric proxy only** when the opposite-side check, selected maximum hinge (default 15°), and both selected maximum floor-like slopes (default 45°) are satisfied.

A boundary has no neighbor to follow. A non-manifold edge has multiple potential neighbors and is not treated as a unique connection. Render-material seams are **not physical-material boundaries**. The current UI does not infer actual gameplay walkability, Havok controller step height, shape clearance, collision masks, physical materials, stairs or a reachable navmesh.

No existing original GMP/IBD file, native Save As path, actor or collision shape is changed.

## Tests and implementation

- Source Python edge classification now returns original exact weld IDs. Cache exporter produces v3 with per-face source weld IDs.
- Godot source collision picker recomputes original edge incidence and validates the source's per-edge class.
- New source_edge_transition_diagnostics.gd analyzes unique original edge links, unsigned hinge angle and horizontal opposite-side evidence.
- New source_edge_transition_panel.gd offers source-exact edge navigation and editor-only line overlays.
- Existing main.gd hooks the panel into original collision inspection activation, selection and reset only.
- New smoke_exact_source_edge_transitions.gd exercises synthetic duplicates, false preview-coordinate matches, wrong edge classifications, original IDs and editor navigation.
- Six new source-only Python tests check duplicate-index welding, no-epsilon separation, original source ID gaps and provenance.
- Upgraded source collision picker and slope histogram synthetic fixtures to v3.
- Native GitHub Actions gains a sixth headless Godot 4.3 fixture.

**All test fixtures are synthetic and carry no proprietary DX2 level geometry.** Original retail map inspection on Windows and authorized Havok runtime comparison are still needed.

## Future gate

The next stage should measure local 3D crossing and capsule clearance around these exact source-connected edges, independently of game collision semantics. Even exact geometric adjacency cannot establish a traversable Havok connection or a native-writable MOPP compiler.
