# DX2Ed v0.88: cap-centroid anchored plane rotation

## What this changes
A selected **editor-created** convex Box clipping cap gains four Inspector buttons: **Y −5°, Y +5°, X −5°, X +5°**. Each turns only that cut's local unit normal around the specified local axis, and updates its distance so that the current cap's **area-weighted triangle centroid remains on the new plane**. The remaining cuts, their keep-sides, and the Box's object transform are unchanged. A successful turn is one Undo/Redo operation.

This is private Godot preview authoring, **not** a native Deus Ex: Invisible War World BSP/CSG write, native DX2 face drag, or collision/cook path.

## Mathematical rule

For the selected clipping plane `n·x=d` and the **visible** polygonal cap, compute an area-weighted centroid `c = Σ (A_i (a_i+b_i+c_i)/3) / Σ A_i` from coplanar triangles in the existing validated preview mesh. For an axis rotation matrix `R` and step angle `θ = ±5°`, set `n' = normalize(R n)` and `d' = n'·c`. The old cap center remains fixed on the proposed cutting plane even if the old cap is offset or asymmetric. This is not a mere change to yaw/elevation with the same signed distance.

The helper `private_box_cap_rotate.gd` refuses malformed input, invisible or empty caps, invalid plane indices, a parallel-axis no-op, angles greater than 30°, nonfinite vectors, or caps without a trustworthy area-weighted centroid. Every candidate must pass the original private Box specification checks and rebuild a fully closed, strictly shrinking convex mesh. Invalid requests preserve the previous mesh and Undo history.

## Implementation scope

- Only `Brush::Box` copies that are originally authored inside the Godot editor can use these controls.
- The current private plane remains selected after a valid turn, and its Inspector yaw, elevation and signed distance are refreshed from the new geometry.
- A selected plane may be rotated around local X or local Y; if the normal is parallel to a chosen axis, the turn is refused without geometry changes.
- The action reuses existing private `DX2Ed-prop-draft-v1` metadata, Save/reopen, Undo/Redo and source-isolated edit transactions. There is no new incompatible project format.
- Native imported BSP/StaticMeshActor geometry and original GMP/IBD files remain entirely read-only.

## Tests

`native_editor/godot_editor/tests/smoke_private_box_cap_rotate.gd` exercises an invented 2-metre Box clipped once and twice:
- Single central cap area=4m² and centroid=(0,0,0); a local Y turn retains its center and creates a valid cut.
- An asymmetric cap after a second Y cut has area=2m² and centroid=(0,−0.5,0). A +5° local Z test creates a **nonzero** signed offset of `−sin(5°)/2`, demonstrating an anchored rather than arbitrary rotation.
- Refusals for no cut, invalid index, zero/nonfinite axis, parallel axis, zero angle, and oversized rotation.
- Actual Godot Inspector button activation, valid closed preview, unchanged other plane, one-step Undo/Redo, and imported actor isolation.

The native Godot 4.3 CI compiles this helper and executes the new fixture. The Windows prototype, source manifest and prototype doctor are required to bundle it and its smoke test.

## Outstanding engineering

Native DX2 World BSP surface ownership and writable CSG, stable vertex/polygon indexing, MOPP/Havok collision regeneration and retail-game load/play tests remain unsolved. This is further progress toward T3Ed-style authoring controls but **does not** establish native playability or complete any T3Ed parity capability.
