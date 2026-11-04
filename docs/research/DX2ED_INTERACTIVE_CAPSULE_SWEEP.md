# DX2Ed interactive capsule sweep research, PR #48

This adds the first **click-driven capsule path editor** to the existing source collision inspector, stacked on PR #47's verified first-contact overlay. It is intentionally **read-only**: no Havok runtime, native collision compilation, physics body, original Level save or GMP modification is involved.

## How to try it in the full DX2SDK checkout

1. Launch native DX2Ed and open an **original owner-supplied DX2 GMP** and matching assets.
2. Enable **Inspect source collision**, allowing its source-hash-gated original Level/Flesh/MOPP cache to load.
3. In Inspector's **INTERACTIVE CAPSULE SWEEP | RESEARCH ONLY** section, adjust four input fields:
   - **Start offset:** default +2 original Level units, along the picked triangle's winding-dependent geometric normal.
   - **End offset:** default -2 Level units, along the ending triangle's winding-dependent geometric normal.
   - **Radius:** default 0.2 original Level units.
   - **Half-axis:** default 0.5 Level units. The capsule is fixed along original source Level +Z and does not rotate.
4. Click **Pick Start**, then left-click an original collision surface. Repeat with **Pick End**. You can pick the same source face twice with opposite offsets to produce a segment crossing that face.
5. Click **Run read-only sweep**. DX2Ed executes the owner-map-validated PR #47 Python first-contact exporter on a worker thread, using the coordinates you selected in Godot but converted back into original Level XYZ. A **new JSON in DX2Ed's private cache** is produced; the original GMP/IBD is never written.
6. On success, the existing PR #47 overlay automatically loads the result, displaying capsule starting/ending outlines, the path, first numerical contact, original Level triangle ID and resolved geometric normal if available.

A no-contact path reports an explicit miss. Offset, dimensions, and selected triangle IDs are research controls, **not** established gameplay character-controller values. Winding normals are not proof of which way is gravity or whether a surface is physically solid.

The UI adds no new unverified triangle selecting logic: start/end selection uses the same source-hash-bound original triangle ray picker already in DX2Ed. Unrecognized triangle IDs, invalid normals, source changes, missing full-checkout research scripts, degenerate zero-length paths and invalid shapes fail without writing game data.

## Safeguards and lifecycle

- **Only active in source collision inspection** after original source file SHA, Level triangle and MOPP linkage have been checked.
- Start and end samples remember original Level triangle IDs and are invalidated by map changes.
- **No overlapping worker runs**. A worker gets immutable source path/hash/cache arguments; upon completion, DX2Ed discards any result whose source hash, source map or private-cache folder differs from the currently active scene.
- Generated sidecars use unique new filenames in the existing **private DX2Ed cache outside retail Maps**, never overwrite existing files, and are processed by the same strict PR #47 research loader.
- The Python exporter checks new numerical-contact IDs against an independent complete swept-capsule oracle and a conservative, source-validated MOPP candidate set. Its output is visual research evidence, not engine-verified Havok.
- **Clear points**, disabling original collision inspection, switching maps or closing the editor clears the point selection. The underlying worker is joined on editor shutdown. All actual original game files remain untouched.
- The coordinates in generated private JSON may reveal original-map-derived geometry; do **not** commit generated sidecars.

## Implementation

- `native_editor/godot_editor/capsule_sweep_picks.gd`: original triangle and source-SHA-bound start/end selection, explicit Level↔Godot conversion, signed geometric-normal offsets, bounded parameter validation.
- `native_editor/godot_editor/capsule_sweep_panel.gd`: compact inspector UI and isolated asynchronous, read-only Python exporter execution; source lifecycle guards.
- `native_editor/godot_editor/main.gd`: only minor glue to existing collision-picker click, activation, reset and shutdown hooks. Does not alter Save As or actor draft logic.
- `native_editor/godot_editor/tests/smoke_interactive_capsule_sweep.gd`: asset-free Godot 4.3 fixture exercises the two-click sequence, signed offsets, inverse coordinate mapping, original IDs, source-hash invalidation and cleanup.
- `.github/workflows/native-dx2ed.yml`: new fixture step alongside existing three headless Godot smoke tests.

Research requires a **full repository checkout**, because the Python script lives in `research/dx2/` and will not exist in Godot-only portable builds. Missing script refuses the operation with an explanation. No private retail test maps are in CI.

## What remains

The geometric ToI and displayed normal are numerical research estimates. Actual DX2/Havok world transforms, shape identity, collision filters, contact manifolds, penetration response, step/slide movement and writable Level/MOPP cooking are **not implemented**. The next gate is a user-side real-Windows-GMP interaction test, plus independent Havok runtime traces before any collision editing claims.
