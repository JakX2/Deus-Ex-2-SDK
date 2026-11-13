# DX2Ed v1.00: closed private convex CSG **intersection preview**

This milestone implements **intersection only**, for two independently preflighted, editor-authored `Brush::Box` previews. It is an entirely in-memory local geometry study for future CSG research. **It is not a native Deus Ex: Invisible War World BSP, original map editor, or Havok/MOPP collision generator.**

## Algorithm

1. Validate each private Box using the independent v0.92 convex preflight and the v0.98 closed oriented face/edge graph. Validate independent proper rigid (rotation/translation only) transforms from v0.99.
2. Run v0.99 complete SAT (face normals plus edge-cross axes). For disjoint or boundary-only contact, return **no 3D volume geometry**. A touch is not silently treated as a walkable solid or an engine collider.
3. Convert both source-private face boundaries into outward halfspaces in a shared Godot-preview metre coordinate frame, anchored at the first placement origin to reduce numeric cancellation.
4. Merge only same-oriented *coincident* source planes while retaining both private face provenance records. Other source planes remain input constraints.
5. Enumerate bounded intersections of triples of planes, retain only points satisfying *all* halfspaces, and weld numerically matching vertices.
6. Construct outward convex polygon loops and triangulations from the active planes. Check opposing uses on **every** perimeter edge, unique vertex/face counts, Euler `V-E+F=2`, finite positive signed volume, a second centroid-tetrahedron volume integral, and that every vertex satisfies all original private halfspaces. Ambiguous, degenerate or oversized arrangements fail closed.

All returned vertex IDs, face provenance, normals, areas and edge adjacency are **editor-private**, not retail BSP node/surface indices. Returned geometry includes an SHA-256 over the preview result. The operation does not produce a new `Brush::Box` clipping-plane document, because intersections may have more than eight cuts, the private editor limit.

## Source-only use

```bash
python -m dx2sdk.private_brush_intersection first_box.json second_box.json
python -m dx2sdk.private_brush_intersection first_box.json second_box.json --transform-b b_rigid.json
python -m dx2sdk.private_brush_intersection private_draft.json private_draft.json --copy-a DraftProp_7 --copy-b DraftProp_8
python -m unittest native_editor.tests.test_dx2sdk_private_brush_intersection -v
```

A private rigid transform JSON has a row-major `basis` (three 3-element rows) and `origin` in preview metres, as supported by v0.99. Inputs are **regular, nonsymlink, bounded private JSON**; native GMP/IBD is not accepted as an input or output. There is no output path option and no file write of any kind. Failure returns exit code 2.

## Tested geometric cases

The asset-free regression covers identical half-Boxes and co-planar source planes, a translated overlap (analytic volume **2 m³**), independently rotated intersection, contained private solids, a pair placed far from world origin, non-volume face/edge/corner contacts, separated pairs, eight-corner clipped convex self-intersection, invalid specs/transforms and an untouched synthetic `.gmp` sentinel.

## Non-goals and limitations

This release intentionally **does not** implement CSG union, subtraction, coplanar-material selection, UVs, original surface IDs, portal/zone rebuild, gameplay Actor creation, compiled original DX2 World BSP, native Havok/MOPP collision, or `.gmp`/`.ibd` writes. The private result is not claimed to be playable, collision-authentic, or a game-compatible level.

Numerical tolerances and finite topology limits mean certain extremely thin, near-tangent or high-complexity intersections are **refused rather than approximated**. Geometry is calculated in a source-private preview frame with no conversion to the engine's undocumented native BSP structure. This is an incremental testable foundation for later work toward T3Ed-style editing, not full T3Ed parity.
