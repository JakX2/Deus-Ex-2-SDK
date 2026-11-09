# DX2Ed v0.55: transform pivots, orientation and 3D cursor

## User-visible behavior

The prop toolbar offers three transform pivots:

- **Median:** arithmetic mean of the selected preview-object origins (the previous behavior).
- **Active:** the last selected preview object.
- **3D Cursor:** an editor-only world position represented by a visible RGB axis cross.

The **Set 3D cursor** action places the cursor at the selection median, or at the active view target when no object is selected. Cursor placement is one Undo/Redo transaction. The cursor is bounded to finite coordinates within +/-1,000,000 editor metres.

The toolbar also exposes **World / Local** orientation. World remains the default. Local orientation aligns Perspective gizmos to the orthonormalized basis of the active selected object. Top, Front and Side intentionally remain world-plane constrained so a local basis cannot make a 2D handle leave its active view plane.

Move/rotate/scale continue to transform the same selected preview nodes. The chosen pivot affects group rotation and scale, inspector group position and gizmo placement. Local handle axes are converted through the gizmo basis before drag math.

## Private workspace and history

The private JSON workspace grows from six to nine exact fields. It persists pivot mode, orientation mode and the 3D cursor as a finite three-number array. The loader continues accepting the legacy three-field and v0.53/v0.54 six-field workspace forms, migrating them to Median / World / origin cursor defaults. Unknown modes, wrong array lengths, nonfinite values and coordinates outside the bound are rejected before any current draft state is cleared.

Changing the cursor is undoable; changing pivot/orientation preferences is a workspace preference and does not add geometry history entries. Cursor state is also included in in-memory edit snapshots so Undo/Redo restores cursor placement without changing original scene resources.

## Verification

A real Godot 4.3 smoke creates two synthetic private Polygon brushes and checks median, active and cursor pivots; World and Perspective-local gizmo bases; orthographic world-plane constraints; cursor placement, one Undo and Redo; new nine-field workspace Save/reopen; legacy three- and six-field workspace migration; and malformed mode, nonfinite and out-of-bounds cursor rejection.

The smoke is included in Linux Godot CI, the bundled Windows prototype's preflight/self-test, and the source-only editor test bundle. Python source-contract coverage checks helper/UI/persistence/manifest wiring.

## T3Ed research boundary

The accessible user Library archive inventory identifies separate T3SDK viewer picking, editor editing, edit-dock and viewer-state scripts. This supports treating viewport interaction, selection state and edit transactions as separate editor concerns. The inventory is metadata, not a source-level reconstruction of T3Ed pivot semantics; DX2Ed code is independently authored and no T3SDK code is copied.

## Compatibility boundary

All pivot/orientation/cursor state is private Godot editor metadata. It does not enter native actor Location/Rotation/Scale, GMP/IBD, BSP/CSG, MOPP, Havok, collision, lightmap, GameSys or TriggerScript writers. No playable native map or retail runtime compatibility is claimed.
