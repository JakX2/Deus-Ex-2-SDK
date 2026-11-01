# Experimental native GMP Save As (translation-only)

**Status:** tested on synthetic v95 GMP data; **NOT yet verified in retail Deus Ex: Invisible War**. Do not install into a production game installation or trust valuable saves to it.

DX2Ed has a guarded binary write path. It patches **only** the three original float32 coordinates of an existing StaticMeshActor's tagged Location FVector. Original export/import tables, other actor fields and the package byte count remain unchanged.

## Editor workflow

1. Import an original retail GMP and IBD resource bundles.
2. Select an **original** static-mesh actor, and edit **position only** using the move gizmo or Inspector X/Y/Z. Do not rotate/scale it. Some experimental preview transforms will also cause Save As to refuse export.
3. Click **Experimental GMP Save As...** in the upper toolbar. DX2Ed saves the current private draft before exporting.
4. Select a **different directory outside the original Maps folder** and retain the **exact original GMP filename**. For example, select C:\DX2EdTests\M1_Seattle_hub.gmp rather than the installed game Maps directory.
5. On success, the tool writes a GMP and an adjacent JSON manifest with hashes and actor offsets. The source package is never overwritten.
6. To attempt an actual game test, first create a full backup/test copy of the game installation. Replace the map in the test copy only; use a disposable save. There is no automated installation or verified game-play guarantee.

This initial writer **refuses** drafts with new copies, asset placements, brushes, property edits, actor rotation or scale changes. No changes are silently discarded.

## Command-line workflow

To inspect a possible patch without writing an output:

~~~powershell
python native_editor/godot_editor/backend/dx2_native_save_as.py --source "C:\DX2\Maps\M1_Seattle_hub.gmp" --actors "C:\DX2EdCache\mission\actors.json" --draft "C:\DX2EdDrafts\saved-editor-draft.json" --output "C:\DX2EdTests\M1_Seattle_hub.gmp" --dry-run
~~~

Remove the dry-run flag to write the GMP copy. The UI button automatically finds its current draft and actor metadata.

## Validations

- Ion Storm package version must be 95.
- Original map bytes SHA-256 and basename must match Actor Explorer's cached source data.
- Draft must belong to the current map, and contain only existing rendered StaticMeshActor translation changes.
- Source class/name/export must match exactly; duplicate actor names and ambiguous offsets are refused.
- Unmodified Godot basis must match the original importer, so unsupported rotation/scale changes cannot be quietly lost.
- Each original serialized Location.X/Y/Z must match the decoded source metadata.
- Only the three approved 4-byte floats are modified, never package header, tables or any other data.
- The output reopens with the existing Package parser with the same package GUID, header table counts and total file length.
- Output hash and coordinates are verified; existing output files are never overwritten; the retail Maps directory is forbidden.
- The emitted manifest has game_verified=false until a real retail engine test.

CI uses a tiny synthetic but genuinely parseable Ion Storm v95 package, patches nested FVector tag data, reparses the package and verifies source byte preservation and rejection scenarios.

## Still unsupported

Native rotations, scale/skin changes, property changes, actor placement/deletion, scripts, AI, physics, collision, lighting, BSP/CSG brush geometry and IBD writing. All need additional reverse engineering, binary round-trip tests and in-game validation.

The first sensible runtime experiment is moving a single small decorative static mesh in Seattle Hub a short distance and comparing a copied game installation against the original. Successful synthetic parsing is not the same as confirming in-game compatibility.
