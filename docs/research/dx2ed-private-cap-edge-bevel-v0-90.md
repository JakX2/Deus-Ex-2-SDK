# DX2Ed v0.90: validated private convex Box cap-edge bevel

**Scope:** Godot 4.3 editor-only mesh authoring on a freshly created `Brush::Box`. This is **not native DX2 BSP/CSG/World surface editing**, Havok/MOPP collision regeneration, or a runtime-verified custom Invisible War level.

## New Inspector workflow

1. Select an editor-authored Box with one to seven valid local 3D clipping planes.
2. Choose a clipping plane from the existing `Plane n` selector, or Alt+Shift+click its *visible* capped face.
3. The new **Cap edge** dropdown enumerates only genuine boundary edges of that selected cutting cap. A temporary bright cyan line highlights the chosen local edge, distinct from the existing gold cap-perimeter outline.
4. Choose a **0.05–0.50 m** inward bevel depth, default **0.10 m**, and click **Bevel edge**.
5. The editor appends one new validated dihedral-bisector half-space, selects its resulting cap, and records **one Undo/Redo transaction**. Existing cuts retain their original coefficients and order; the private `DX2Ed-prop-draft-v1` Save/reopen workflow continues unchanged.

The operation is unavailable on a missing, hidden or degenerate cap, an uncut Box, any imported/original StaticMeshActor, or when the private eight-plane limit is already reached. A failed candidate preserves the original mesh, selection, Undo stack, and source files.

## Derivation and safety

`private_box_cap_edge_bevel.gd` reads the already validated closed triangulated preview, and groups every edge by its canonical 3D endpoint key. An authentic cap perimeter edge must have **exactly two incident triangles**, only **one** of them belonging to the selected cap. This excludes the internal diagonals of the triangle fan, edges shared by multiple cap triangles, T-junctions, and ambiguous cap classification.

For a cap's outward unit normal `n_c` and the adjacent surface triangle's outward unit normal `n_a`, the new outward bevel normal is:

`n_b = normalize(n_c + n_a)`

For the original shared edge's midpoint `m` and inward cut depth `h`:

`d_b = n_b · m − h`

The new half-space retains `n_b · x ≤ d_b`. The editor must then validate the entire updated `clip_planes` stack and rebuild a **closed nondegenerate convex mesh with strictly reduced volume**, not just append a plane record. `h` is local Godot metres and is bounded to 0.05 through 0.5. Angles with parallel/antiparallel normals, too-short edges, nonfinite input, and the ninth cutting plane are refused.

Only private Box previews are scanned, and all created display-only outlines are children of the editor-authored preview node. The cyan overlay is excluded from the original actor registry, game assets and draft JSON.

## Source-independent Godot regression

`native_editor/godot_editor/tests/smoke_private_box_cap_edge_bevel.gd` builds an invented 2m Box clipped at x=0. It verifies four genuine 2m cap perimeter edges, selects the y=+1 edge, and checks that a 0.1m bevel appends the bisector `(+X,+Y)/√2` at signed offset `1/√2−0.1`, producing a closed mesh while preserving the original cut. Negative tests refuse nonexistent edges, incorrect depths, missing caps and a ninth plane.

The *actual Godot Editor* test also checks edge dropdown/highlight isolation, the Bevel action, the newly selected cap, one-step Undo/Redo and the absence of private controls on imported source actors. The native workflow compiles the new helper independently and runs this test. The Windows source-only prototype bundle and preflight require the helper.

## Remaining native requirements

Native Unreal-derived DX2 World Model surface ownership, arbitrary compiled polygon modifications, BSP/CSG rebuilds, collision generation, and retail loading/playability are **still missing**. This supports only the *partial* T3Ed-style face/edge authoring capability, not a complete native SDK or validated playable custom map.
