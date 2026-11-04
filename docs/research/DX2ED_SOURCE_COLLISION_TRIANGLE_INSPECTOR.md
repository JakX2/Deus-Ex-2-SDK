# DX2Ed: source-authenticated MOPP-linked triangle picking

Experimental read-only integration of the source geometry/MOPP research from PRs #27–32 into DX2Ed's Godot 4 inspector. No native collision writer, Havok runtime execution or physical-material schema is implied.

## What the inspector actually picks

- The **original DX2 Level** flattened vertex and triangle arrays, cross-validated against packed Flesh render blocks, MOPP reachable terminal triangle IDs, and original render-section provenance.
- **One selectable triangle per source MOPP terminal leaf ID**, not a face ID synthesized from the Godot GLB importer. Original Level IDs are preserved even where an original map omits a zero-area triangle from MOPP.
- Reports the original triangle ID, source block ID, render block and section ordinal, original **render material name**, Godot-preview-space hit point, geometric normal and distance. Material names are **not** Havok physical-material assignments.
- Visual highlight is a dedicated Godot-only line overlay, not an actor, editable brush, saved property, or serialized `.gmp` object.

## Coordinate transform

Prior retail measurements established Level flattened XYZ = packed Flesh render XYZ * **0.1905** (floating-point tolerance), and the existing Godot exporter uses `(X,Z,Y) * 0.01905` on the original render vertices. Therefore the independent source triangle picker uses `(Level.X, Level.Z, Level.Y) * **0.1**` to align with GLB world coordinates. The permutation changes handedness; the inspector flips the geometric display normal to align with Godot's existing reversed-winding renderer.

This is a coordinate relationship for editor visual inspection, **not a claim about Havok physical units or gravity**.

## Workflow

1. Open an original user-owned UE95 DX2 GMP through **Open DX2 map (.gmp)**, letting the existing editor create its normal private GLB/actor cache.
2. Select **Inspect source collision** in the toolbar. This is disabled for demo-only GLBs or scenes without a matching original GMP and source SHA.
3. On first use, DX2Ed launches `dx2_collision_selection_cache.py` in its existing background worker pattern. The complete validated source atlas is transformed into a compact JSON sidecar under the **current private map-cache directory**, *never the retail Maps directory*.
4. Click in the 3D view. The separate CPU BVH selects the closest source MOPP triangle, displays its source identity in an independent inspector label, and adds a small unshaded highlight to the preview. Toggle the button off to restore ordinary actor picking.
5. Cached source attribution is bound to the original map's SHA-256. A mismatched/stale sidecar is refused; delete only the private `source_collision_selection.json` to force a rebuild. The original GMP never changes.

## Tests and safety gates

- `python -m unittest discover -s native_editor/tests -p 'test_dx2_collision_selection_cache.py' -v`
- Headless Godot 4.3: `godot --headless --path native_editor/godot_editor --script res://tests/smoke_source_collision_picker.gd`
- Open original-map integration (private): generate sidecars for 19 original maps, verify MOPP counts and source SHA, **do not commit sidecars or GMPs**.
- Fail closed on missing or inconsistent source SHA, wrong map, invalid vertex/triangle references, duplicate/reordered triangle IDs, unverified physics-material attribution, or output inside a retail source directory.

### Explicit limitations

This selects *research-derived source geometry*; it does not use Havok runtime contact queries, collision filters, physical friction, restitution, original native BSP surface IDs, or validated native collision material indices. Geometric ray hits may differ from actual DX2 character movement and physics. No native map writer/compiler, Havok MOPP serializer, reimport pipeline, or game-runtime test has been added.

The existing actor/gizmo picker and experimental GMP Save As commands remain separate. Do not treat the debug overlay or triangle identifiers as authoring input for those operations.