# DX2Ed prototype P103: save and verified reopen of private CSG recipes

**This is private authoring data, not a compiled Deus Ex: Invisible War level.** P103 extends P102's disposable CSG viewport preview with an explicitly saved `.dx2csg.json` recipe and independent recomputation on reopen. It does not change the existing map-specific `DX2Ed-prop-draft-v1` file format, and it does not write original GMP/IBD, BSP or Havok/MOPP data.

## Editor workflow

1. Create two **source-private**, valid clipped Box drafts and Ctrl-select exactly both. Names sort alphabetically into deterministic operand A and operand B.
2. Click **Preview CSG A ∩ B** or **Preview CSG A - B**. The result is a transient colored shell or multiple convex pieces.
3. With the same private drafts selected and the preview still active, click **Save CSG recipe...**. Choose a **new** `.dx2csg.json` file outside retail game map directories. The file must not already exist. A geometry/pose or selection change while the dialog is open refuses the save.
4. Click **Clear CSG preview**, reopen the editor, or load another map. Use **Open CSG recipe...** to choose the file. The independent Python backend verifies exact identity and **recomputes** the whole CSG result. Only a fresh bounded validated result is rendered in Godot. The source drafts need not currently be loaded because the recipe carries isolated private brush definitions.
5. Once reopened, the result remains an **unselectable preview overlay**. It is not converted into a draft actor, original BSP brush, physics collider or map write. To edit the operation, edit the original authored private Boxes and create a new recipe.

## File and verification contract

`dx2sdk.private_csg_recipe` allows **only** two explicit private Box specifications, two proper-rigid preview transforms, a supported operation (`intersection` or `subtraction`), deterministic private `DraftProp_N` provenance, operation/source payload SHA-256, independently recomputed CSG result SHA-256, volume/piece counts and explicit unsupported native flags.

On load, the file must have exactly the supported schema and field set; duplicate JSON keys, NaN/infinity, unsupported names, wrong source hashes, changed outputs, edited counts/capabilities, symlinks, non-regular files and oversized content are refused. The complete source-private CSG calculation is rerun from the saved inputs and its canonical output fingerprint compared. No serialized triangle mesh is accepted as authoritative.

Save uses exclusive `xb` NEW-file creation with no overwrites, no original resource input, and denies paths within any `Content/DX2/Maps` directory (case-insensitive). The CLI, Python SDK and Godot bridge do not use the game-native writer. Only the explicit private recipe is written; Godot cleans temporary `user://private_csg_recipe_stage` JSON after both success and refusal.

## CLI

```bash
python -m dx2sdk.private_csg_recipe save subtraction DraftProp_1 DraftProp_2 a_box.json b_box.json a_pose.json b_pose.json new_scene.dx2csg.json
python -m dx2sdk.private_csg_recipe load new_scene.dx2csg.json
python -m unittest native_editor.tests.test_dx2sdk_private_csg_recipe -v
```

The `load` command reports fresh computed geometry to stdout for the Godot bridge. The `save` command returns a compact proof report; neither command touches existing files. Synthetic tests cover 2 m³ overlap/difference, six-piece 44 m³ cavity replay, exact-digest reproducibility, malicious or changed recipe refusal, no overwrite, invalid transforms/actors, native path refusal, CLI behavior and an unchanged mock original `.gmp` sentinel.

The Godot 4.3 fixture tests the actual **Save/Open** toolbar events, manual clear, replay mesh, tampered file refusal, no Undo changes, no overwriting and unchanged original-file sentinel. Package source requirements, doctor, and Windows prototype include the new Python and Godot modules.

## Scope and next engineering boundary

This is an independent portable **recipe file**, not an automatically embedded component of the map's normal Save draft sidecar. It contains a source-private reconstruction of the two operands but no original map paths. In later work the editor can add recipe inventories, persistent object management or an optional attachment to private drafts with source identity checks.

Native World BSP/CSG construction, engine-compatible materials and UVs, zones/portals, Havok/MOPP collision rebuild, original GMP/IBD writes and in-game playable custom maps are **not implemented or verified**. P103 is prototype milestone numbering, not product v1.0.
