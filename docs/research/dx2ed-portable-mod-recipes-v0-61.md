# DX2Ed v0.61: portable source-locked mod recipes

**Checkpoint:** 2026-11-10. **Status:** asset-free research format, automated tests;
**retail Invisible War runtime for combined edits is NOT verified**.

## Objective

A full T3Ed-like DX2 editor should let players make and **share** modifications.
Sharing complete cooked GMPs would distribute original game content. This
first narrow alternative exports only a JSON *instruction recipe* describing
original StaticMeshActor moves, original-source clones and Level-list
unplacements, pinned to the original map SHA-256.

The recipient must own their original map and run the rebuild locally.
Neither recipe export nor import installs anything into the retail game.

## Authoring with Godot

1. Open a clean, original DX2 GMP and matching resources in DX2Ed.
2. Prepare **at least two types** of native static-prop edits: translated
   original props, translated original-source preview duplicates, and/or
   temporary Stage/Unstage original prop Level-list unplacements. The
   v0.60 combined plan's strict size/class/transform limits still apply.
3. Choose **Export Mod Recipe...**, select a fresh .dx2edmod.json filename
   outside the game's Content/DX2/Maps and original map directories.
4. Confirm. DX2Ed calls the original-source-pinned Python compiler without
   writing any GMP. The resulting recipe contains an exact normalized edit
   plan, source basename/size/SHA-256, expected output size/SHA-256,
   operation counts and explicit runtime_game_verified=false.
5. Share ONLY this JSON recipe, not any original/modified game GMP, IBD,
   native game binaries or copied proprietary assets.

## Applying a shared recipe with Godot

1. Open the **same exact original** DX2 GMP in DX2Ed. Matching basename
   alone is insufficient: the SHA-256 and source size must be identical
   to the recipe's original.
2. Choose **Apply Mod Recipe to Isolated GMP...**, select the received
   .dx2edmod.json.
3. Before showing a GMP Save As chooser, DX2Ed recompiles the recipe
   **in memory only** from your source and checks the expected whole-file
   hash/size. If source is stale or different, the operation is refused.
4. Choose a new, otherwise unused directory for the output GMP. Retain
   exactly the original GMP filename; an existing GMP/manifest is never
   overwritten and a game Content/DX2/Maps destination is refused.
5. Review the original and candidate SHA-256 in the confirmation dialog.
   Confirm to create the candidate and its native plan manifest. The tool
   independently replays the original source changes and compares every
   saved output byte. Nothing is installed into the game.

Source hash drift between read-only preflight and confirmation is refused.
The recipient's currently loaded Godot scene remains the source; it does
not silently switch to or import the newly built candidate.

## Command-line version

Export a portable recipe from a validated v0.60 native plan:

    python native_editor/package_writer/dx2_mod_recipe.py "C:\OriginalDX2Maps\M1_Example.gmp" --source-sha256 ORIGINAL_64_HEX --plan-json "C:\DX2EdResearch\plan.json" --export-recipe "C:\DX2EdMods\MyExample.dx2edmod.json"

Read-only recipient validation. **Does not create a GMP:**

    python native_editor/package_writer/dx2_mod_recipe.py "C:\OriginalDX2Maps\M1_Example.gmp" --recipe "C:\DX2EdMods\MyExample.dx2edmod.json"

Reconstruct an isolated test candidate with a full source-pinned binary replay:

    python native_editor/package_writer/dx2_mod_recipe.py "C:\OriginalDX2Maps\M1_Example.gmp" --recipe "C:\DX2EdMods\MyExample.dx2edmod.json" --output "C:\DX2EdResearch\Output\M1_Example.gmp"

The resulting isolated GMP and native plan manifest are **not**
distributable parts of the content-free recipe. Original game content
remains on the user's own machine.

## Exact recipe format

Top-level schema: DX2Ed-portable-native-static-prop-recipe-v1.

- source_file: original GMP basename only, no absolute user path
- source_size, source_sha256: the exact owner's baseline
- candidate_size, candidate_sha256: expected isolated candidate
- native_plan: normalized
  DX2Ed-experimental-native-prop-change-plan-v1 operations
- operation_counts: moves, copies and unplaces
- includes_retail_assets: false
- automatic_game_installation: false
- runtime_game_verified: false

No embedded GMP/IBD contents, mesh blobs, textures, screenshots, compiled
source game objects, private player files or executable payloads.

The reader enforces an exact schema, size caps, source filename sanity,
finite bounded coordinates and a strict normalized plan, and recompiles
the target from the authenticated original. A forged hash alone cannot
turn an unrelated binary into a valid candidate. This is not a
cryptographic author identity or third-party signature, and it does not
assert that edits will work in retail gameplay.

## Automated verification

- Synthetic DX2 v95 source fixture with original static props and
  a combined move-and-clone plan.
- A content-free .dx2edmod.json is created without a new GMP.
- A separate identical source file can rebuild the same candidate.
- Original source mismatch, wrong basename, tampered plan/digest,
  malicious extra fields, false runtime/assets/installation flags,
  game-directory output, duplicate filenames and overwrite all refuse.
- CLI end-to-end test covers export, read-only verification, isolated
  GMP creation, exact whole-binary replay and refused source overwrite.
- Godot 4.3 smoke validates import/export file chooser types, signal
  wiring, explicit confirmation and absence of an original source.
- Bundled Windows Godot prototype includes the worker and UI smoke.

## Remaining engineering work

1. Confirm v0.59/v0.60 native Level unplace and combined authoring behavior
   in a disposable, backed-up retail game copy, including collision,
   level re-entry and save/load.
2. Add more authenticated native property, reference, class and IBD writers.
3. Reconstruct cooked BSP/CSG/collision and associated authoring assets.
4. Once mission authoring is reproducibly game-compatible, add real
   player-installable *mod packaging*. This JSON recipe only covers the
   tiny v0.60 native static-prop subset.
