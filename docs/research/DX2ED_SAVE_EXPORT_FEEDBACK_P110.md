# DX2Ed P110: Save / Export is now explicit

## Why this update exists

A Windows tester tried the new P109 bulk GMP exporter but the status bar
showed an error from **Legacy Combined Save As**, which still requires two
distinct native operation kinds. The old and new actions sat adjacent in
the same Native GMP menu. Their labels did not explain their different
requirements.

This update separates the workflows and makes the **actual menu ID**
part of the automated smoke test, instead of testing only the underlying
bulk save planner.

## User workflow

1. Open the unchanged original GMP and matching IBDs.
2. Move or copy objects and, if desired, create editor-only geometry.
3. Click the prominent **Save / Export map...** button on the quick bar.
4. Read the summary dialog. It saves the **private editor draft**, then
   displays the number of original-source static-prop moves, clones and
   staged unplacements that can potentially be serialized into one native
   GMP. Unsupported edits are listed by reason.
5. If eligible count is zero, **Export eligible GMP** is disabled. The
   editor draft has still been saved, and no playable GMP is implied.
6. If there are source-backed eligible edits and the original source is
   authenticated, use **Export eligible GMP...**, choose a fresh folder
   outside the retail game and keep the same original map filename.
   The old P109 native limits and full replay verification still apply.

The Native GMP (test) menu now explicitly distinguishes:

- **Legacy Combined GMP (requires 2 edit kinds)...**
- **Bulk GMP: eligible static props only (up to 256)...**

This is **not** a BSP writer. The Source World BSP read-only selection,
new Box/Polygon brushes, new unplaced mesh resources, custom GameSys
actors, gameplay interactions, arbitrary properties, and original map
rebuilding are still NOT supported by native bulk Save As.

## Safety and testing

The underlying P109 GMP serializer and older Combined/translation
writers are unchanged. Save / Export uses the existing per-map private
JSON writer, then the existing hash-pinned native checker. It does not
install edited maps or overwrite game files.

New Godot tests:

- Open the demo map, invoke the actual Save / Export button and
  assert that private JSON saves, zero native candidates are reported,
  and the native-export button is disabled.
- Click the **actual bulk menu item ID** from the PopupMenu against
  a synthetic scene with no original GMP and require a **Bulk GMP**
  source rejection rather than the legacy Combined message.
- Preserve all existing private project, BSP, geometry and writer
  regression tests.

Tests: `smoke_compact_toolbar.gd` and
`smoke_native_bulk_save.gd`, both included in GitHub Actions and
Windows launcher `--self-test`.
