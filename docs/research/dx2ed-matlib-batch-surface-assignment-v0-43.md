# DX2Ed v0.43: atomic MatLib diffuse assignment to multiple Polygon brushes

## User workflow

1. Select one or more editor-only Polygon brushes in the Hierarchy.
2. Open Materials and choose a source-backed MatLib record with a verified resolved diffuse preview.
3. Choose the target surface independently: Top cap, Bottom cap or Side walls.
4. Press **Apply diffuse to selected Polygon brush(es)**.

Every selected object must be a private Polygon draft. A mixed selection containing an original actor, imported BSP mesh, prop copy or non-Polygon brush is rejected before any mesh changes. All eligible Polygon brushes receive the same source-pinned diffuse on the chosen slot.

The entire batch is one existing editor history transaction. Ctrl+Z restores every previous surface style; Ctrl+Y reapplies every assignment. Selecting one Polygon remains the single-object case. The target surface selector lives in Materials, so the workflow remains usable while the Hierarchy has multiple objects selected and the single-object Inspector is hidden.

## Validation and persistence

- The selected diffuse must pass the v0.42 exact-field source-assignment validator and catalog/thumbnail SHA-256 re-verification.
- Every target's brush spec and surface style is validated and its geometry rebuild is preflighted before mutation.
- If any selected item is not an editor-only Polygon, the complete operation is refused.
- If a mesh rebuild fails during commit, the captured pre-edit scene is restored; no partial batch is retained.
- The existing private JSON project format already serializes each Polygon surface assignment and selected draft names. The smoke verifies two assignments and the multi-selection survive Save/reopen.
- A malformed assignment still fails the existing load preflight before the current editor scene is cleared.
- A changed thumbnail still falls back to the procedural checker; source IBD identity bytes remain unchanged.

The actual Godot 4.3 smoke uses two synthetic Polygon brushes, one synthetic Box for mixed-selection refusal, a generated PNG and invented IBD identity bytes. No retail assets are used.

## Scope and limits

This is a source-backed Godot preview binding for editor-created Polygon surfaces only. It does not interpret DX2 shader-stage semantics or write original BSP material indices. Original GMP/IBD files remain read-only. Native BSP/zone/CSG, collision/lightmap cooking, GameSys/TriggerScript execution, arbitrary retail actor spawning and retail game compatibility remain disabled or unverified.
