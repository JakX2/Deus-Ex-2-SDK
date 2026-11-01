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


## 0.5.1: Native Location audit before export

Select **Audit native GMP** from DX2Ed's top toolbar after importing an original
retail map. The read-only audit scans the original v95 GMP and its matching
actors.json. It reports how many placed static-mesh actors have independently
identifiable tagged Location.X/Y/Z float fields, and how many cannot be patched
because of incompatible tags, duplicate names, invalid export IDs, or decoded
source-coordinate mismatches.

The audit does **not** export, patch, create, or install any GMP. Eligible
means *serialized native position is known*, not that the object has an
in-game-working collision hull or verified correct pivot/rotation.

Command-line equivalent:

~~~powershell
python native_editor/godot_editor/backend/dx2_native_save_as.py --source "C:\DX2\Maps\M1_Seattle_hub.gmp" --actors "C:\DX2EdCache\mission\actors.json" --audit
~~~

The writer now also rejects **no-op Save As** operations with zero moved actors
or no meaningful changed coordinates, so an identical output cannot be
misrepresented as an edited map.

## 0.5.1: Independent exported GMP binary verification

After generating a test GMP copy, verify it again without trusting the writer's
previous return value:

~~~powershell
python native_editor/godot_editor/backend/dx2_native_save_as.py --source "C:\DX2\Maps\M1_Seattle_hub.gmp" --output "C:\DX2EdTests\M1_Seattle_hub.gmp" --verify
~~~

The verifier reads the adjacent DX2Ed save manifest by default. It validates:
original/output SHA-256, package version, GUID, export/import/name table
counts, original source actor classes and export identity, unmodified offsets,
original and edited Location values, and **every changed byte**. Any changed
byte outside those approved original Location float fields causes failure.
It also rejects a manifest falsely claiming that the map has been tested
inside the retail game.

The verifier returns \`verified_binary_structure: true\` and
\`game_verified: false\` on a clean binary comparison. This means the source
and exported bytes obey our known-safe constraints, **not** that the game
will accept the modified map. Actual game testing is still needed. For
a nonstandard manifest path, pass \`--manifest "path\to\manifest.json"\`.

All three CLI modes (audit, write, verify) operate on user-owned source
files and synthetic CI fixtures. No copyrighted GMP contents are checked
into the repository.
