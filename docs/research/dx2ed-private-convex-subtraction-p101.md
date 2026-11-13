# DX2Ed prototype milestone P101: source-private convex CSG subtraction

This research-stage feature calculates the **difference A minus B** of two independently validated, editor-authored clipped `Brush::Box` solids under proper rigid transforms. It does not serialize the results into original Deus Ex: Invisible War BSP, Havok/MOPP, `.gmp` or `.ibd` data. These are **private in-memory preview solids only**.

The milestone is named **P101** rather than a product 1.0 release. The preceding v1.00 intersection work was an internal development label, not T3Ed parity.

## Geometric method

A single convex representation cannot generally contain the result of subtraction: taking a smaller Box out of a larger one can leave a **non-convex cavity**. We therefore emit an ordered collection of validated convex shell pieces rather than pretending it is still one Box.

1. Independently preflight both editor-private Boxes using v0.92/v0.98 and their proper rigid transforms using v0.99. Compute an independent v1.00 intersection result.
2. Begin with the closed shell of A, anchored to A's preview position for numerical stability.
3. For each outward halfspace of B in source-private face order, split the **remaining inside piece** into its outside and inside convex parts. Emit the outside part of A, while carrying the inside part forward to the next B plane.
4. Every emitted piece and every intermediate remainder is rebuilt from 3-plane intersections and must independently pass finite face/vertex/edge bounds, reciprocal edge winding, Euler characteristic, plane containment, positive signed volume and centroid-tetrahedron validation.
5. The final B-inside remainder is discarded. Its volume must agree with the independent intersection of A and B. Sum of all emitted pieces plus removed intersection volume must equal the original A volume, within bounded floating-point tolerance.

Coincident source face metadata is retained. Cut cap planes are explicitly attributed to the B face whose complement they represent. The output records per-piece closed meshes, adjacency, source-private face provenance and SHA-256 fingerprints, plus numeric volume conservation checks. Piece interiors are disjoint by sequential halfspace construction; their boundaries may touch.

**Disjoint and boundary-only contact** preserve A as one closed piece. **A fully inside B** returns zero pieces. The output is an **in-memory preview decomposition**, not one compound native Brush, Havok collider or compiled map.

## CLI usage

```bash
python -m dx2sdk.private_brush_subtraction left_box.json right_box.json
python -m dx2sdk.private_brush_subtraction left.json right.json --transform-b right_rigid.json
python -m dx2sdk.private_brush_subtraction draft.json draft.json --copy-a DraftProp_4 --copy-b DraftProp_9
python -m unittest native_editor.tests.test_dx2sdk_private_brush_subtraction -v
```

Each file is an editor-private, bounded regular `.json` specification or named `DX2Ed-prop-draft-v1` copy; original game resource paths are rejected. The CLI emits JSON to stdout and writes no file. Source-private transforms are limited to proper rigid rotations and translations.

## Synthetic regression coverage

The asset-free suite validates half-Box subtraction with a 2 m³ retained piece, disjoint/touching pairs, identical solids, a B that engulfs A, an **internal cavity in a 48 m³ solid** cut by a 4 m³ B (six closed pieces, 44 m³ retained), rigid 90-degree and 45-degree rotations, distant preview origins, refused invalid native inputs, explicit draft selection and a SHA-unchanged synthetic original GMP sentinel. A finite interior sample grid ensures the six-piece cavity is empty and retained points are represented exactly once away from shared faces.

## Limits and next steps

This function intentionally refuses degenerate, near-coplanar or overly complex splits when a robust closed 3D shell cannot be proven. It performs **no boolean union, editing of generated pieces in Godot, original BSP/CSG compile, surface/material/UV/zone/portal rebuild, Havok/MOPP cooking, original map writes, or retail runtime validation**.

Future work can display the piece collection in the Godot viewport and independently study retail-format source boundaries. The gap to T3Ed-style gameplay-authoring remains significant.
