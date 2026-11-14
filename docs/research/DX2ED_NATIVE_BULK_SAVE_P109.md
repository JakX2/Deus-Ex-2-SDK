# DX2Ed P109: experimental bulk "Save Supported GMP"

**Important:** This is **not** a general map serializer. No new BSP, collision,
arbitrary meshes, asset resources, actor GameSys archetypes, scripts or native
door/vending actors are authored by this command.

## Why it exists

The existing **Experimental GMP Save As** only supports translated original
StaticMeshActor instances and rejects all preview-only new objects. The
older **Experimental Combined Save As** allows at most 16 operations (up to 8
per category, at least two categories). Both remain unchanged.

**Experimental Save Supported GMP...** is a new opt-in workflow that:

1. Saves the complete editor-side project to the original per-map private
   JSON draft, including preview brushes/props and workspace settings.
2. Identifies all eligible **existing-source StaticMeshActor** translations,
   neutral original-actor clones, and staged original Level unplacements.
3. Displays how many edits are eligible and lists excluded preview-only
   object types and missing native identities *before* confirmation.
4. If confirmed, writes one isolated original-basename GMP with at most
   **256** qualifying operations through the same source-pinned T3SDK
   writer and independent native DX2 package reparse/whole-file replay.
5. Preserves original retail map bytes and outputs a separate native
   provenance manifest ending `.dx2ed-native-bulk-prop-plan.json`.

**The output GMP includes only listed eligible static-actor edits.**
Draft brushes, unsupported copies, rotation, scaling, private groups,
preview materials and property overrides remain in the saved **editor
draft**, not the native GMP. This is explicit *partial native output*;
nothing unsupported is secretly treated as a real game asset.

## Windows test procedure

1. Launch the prototype and open your unchanged original GMP and matching
   IBDs. Do not open a previously modified GMP as the input source.
2. Try moving an original StaticMeshActor a small amount **without**
   rotating or scaling. Optionally duplicate eligible original actors.
3. Save draft. The native button will save it again before export.
4. Select **Native GMP (test) > Experimental Save Supported GMP...**.
5. Choose a fresh, separate output directory, retaining the **exact
   original GMP basename**. Never choose a retail Maps directory.
6. Read the confirmation, especially omitted draft items. Confirm only if
   partial native output is what you intend.
7. On success, the candidate GMP and manifest appear outside the game.
   The output has passed binary reparse and full original-byte replay,
   **not** an in-game acceptance test.

Command line for independently verified, source-authenticated plans:

```powershell
py -3.11 .\native_editor\package_writer\dx2_native_prop_plan.py "D:\DX2\Maps\M1_Seattle_hub.gmp" --source-sha256 ORIGINAL_SHA --plan-json "D:\DX2EdPrivate\eligible-plan.json" --bulk --output "D:\DX2EdTrials\M1_Seattle_hub.gmp"
py -3.11 .\native_editor\package_writer\dx2_native_prop_plan.py "D:\DX2\Maps\M1_Seattle_hub.gmp" --source-sha256 ORIGINAL_SHA --bulk --verify --output "D:\DX2EdTrials\M1_Seattle_hub.gmp"
```

The JSON plan uses schema
`DX2Ed-experimental-native-bulk-prop-plan-v1` with `moves`, `copies`
and `unplaces` lists identical in shape to the older combined plan.
Source names/export IDs must be verified original map actors, not arbitrary
created geometry or new resource strings. More than 256 total native
operations are refused (no silent truncation).

No retail gameplay, collision behavior, save/reload stability, runtime
interaction, world compiler or native constructor is guaranteed. Test only
in a disposable game copy, with original checksums and a safe restore route.

## Regression tests

- `python -m unittest native_editor.tests.test_dx2_native_bulk_prop_plan -v`
- Godot 4.3 `--headless --path native_editor/godot_editor --script res://tests/smoke_native_bulk_save.gd`

All tests use fabricated actors and self-contained GMP fixtures, never
distributed retail game content.
