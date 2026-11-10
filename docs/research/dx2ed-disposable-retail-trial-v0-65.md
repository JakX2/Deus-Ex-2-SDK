# DX2Ed v0.65: guarded, reversible retail game-copy trial

**Checkpoint:** November 10, 2026. **Status:** original-GMP-pinned
disposable-install A/B test helper, synthetic-only automated checks.
**No real Deus Ex: Invisible War retail runtime test has been performed
or claimed by the SDK.**

## Why this matters

A source-verified native GMP may still fail to load, retain invisible
collision, break triggers or behave differently after save/reload. v0.64
provided an immutable A/B test dossier and blank manual observations
but left all manual staging/restoration to the owner.

v0.65 adds a deliberately narrow way to place **exactly ONE previously
verified experimental GMP** into a separate test copy of the game and
restore the original map with a durable backup.

This is not an ordinary mod installer. It will not touch a game folder
that isn't named **exactly DX2Ed_Disposable_Test**, will not install new
assets, create directories for a game installation, launch the game,
create a save, alter missions/scripts or remove retail content.

## Essential prerequisites

1. Make a complete copy of YOUR legitimate Invisible War installation
   and name the copied installation's root directory exactly
   **DX2Ed_Disposable_Test**. Do not rename your only real install.
2. That directory must already contain **System** and
   **Content/DX2/Maps**, including a byte-identical copy of the
   unchanged original GMP map you want to test.
3. Keep the source original GMP and your previously exported
   experimental candidate GMP **outside** this copied game directory.
   The candidate needs its original v0.60
   .dx2ed-native-prop-plan.json manifest. It must pass full-GMP binary
   reconstruction from the original on every Prepare/Stage.
4. Close Invisible War completely before copying or restoring a map.
   The trial tool cannot guarantee the game process is closed.
5. Use a **disposable savegame**. Game-written saves and level transitions
   are outside the trial helper's rollback mechanism.

Example local file arrangement:

    C:\MyGames\InvisibleWar_Original\Content\DX2\Maps\M1_Example.gmp
    C:\DX2EdResearch\Candidate\M1_Example.gmp
    C:\DX2EdResearch\Candidate\M1_Example.dx2ed-native-prop-plan.json

    C:\DX2Ed_Disposable_Test\System\...
    C:\DX2Ed_Disposable_Test\Content\DX2\Maps\M1_Example.gmp

The original/candidate folders must be outside the disposable copy,
and the target GMP must be byte-identical to the original before Prepare.

## Godot DX2Ed user workflow

1. Open the original unchanged GMP in DX2Ed.
2. In the static prop toolbar select **Prepare backup** and click
   **Disposable Game Trial...**.
3. Choose your already-exported isolated candidate GMP, then select
   the **DX2Ed_Disposable_Test** root directory. Confirm. The tool
   recompiles the whole candidate from your original and writes a
   protected backup and state.json journal inside the disposable copy
   at .dx2ed-retail-trial-v1. **The test map remains unchanged.**
4. Select **Stage test GMP**, click the same button, choose the same
   isolated candidate and same test-copy root. Explicitly confirm the
   test-only overwrite. The Python worker repeats the whole-GMP replay
   and original/backup checks, then swaps the candidate over the test
   copy's single map file atomically. The original source and isolated
   candidate files remain untouched.
5. Manually run Invisible War **from the disposable game copy**.
   Verify map load, edited objects, visual placement, collisions,
   level re-entry and save/reload against v0.64's checklist.
6. Exit the game. Select **Restore original**, click **Disposable Game
   Trial...**, and select the same test-copy root. Confirm. The worker
   checks the intact original-map backup and refuses restoration if
   the currently staged GMP contains unknown changes. It atomically
   restores the original map, verifies its hash and retains the
   rollback backup/journal.
7. Choose **Inspect test copy** at any point to check the current
   state and exact target/backup digests without writing anything.

Even after restoration, NEVER treat the disposable game copy as an
untouched original save environment. Any user-generated test save data,
logs, configuration or other runtime state must be handled separately.

## CLI example

Make a backup and persistent journal **without changing the map**:

    python native_editor/package_writer/dx2_disposable_retail_trial.py --test-root "C:\DX2Ed_Disposable_Test" --prepare --source "C:\MyGames\InvisibleWar_Original\Content\DX2\Maps\M1_Example.gmp" --candidate "C:\DX2EdResearch\Candidate\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256

After explicit disposable-only confirmation, stage one GMP:

    python native_editor/package_writer/dx2_disposable_retail_trial.py --test-root "C:\DX2Ed_Disposable_Test" --stage --source "C:\MyGames\InvisibleWar_Original\Content\DX2\Maps\M1_Example.gmp" --candidate "C:\DX2EdResearch\Candidate\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256 --acknowledge YES_DISPOSABLE_TEST_COPY

Check without writing:

    python native_editor/package_writer/dx2_disposable_retail_trial.py --test-root "C:\DX2Ed_Disposable_Test" --status

Restore only after quitting the game:

    python native_editor/package_writer/dx2_disposable_retail_trial.py --test-root "C:\DX2Ed_Disposable_Test" --restore

The two restore/status commands do not require the source or candidate
to be selected again. They require the original hidden trial backup
and protected state journal to remain intact.

## Safety/refusal model

- The root directory **MUST** be literally named
  DX2Ed_Disposable_Test. No other install name is accepted.
- The root MUST already be a copied game with real System and
  Content/DX2/Maps directories and one existing, original GMP map.
  No map symlink is accepted.
- Original and candidate GMPs cannot be inside the test copy or be
  ancestors of its root path.
- Prepare verifies target map == source original bytes, candidate
  == exact reconstructed native GMP, plus manifest and source SHA.
- A unique internal trial journal and exclusive original-map backup
  are created, never silently replaced. Only one trial per test-copy
  directory is supported. Keep them after restoring.
- Stage requires explicit opt-in acknowledgement. It rechecks
  original source, whole candidate, backup and test-map current SHA.
- Stage and restore use a same-folder fsynced temporary file and an
  atomic replace operation. A durable journal records transition
  states and supports recovery from an interrupted transition.
- Restore refuses to replace any map whose bytes are neither the
  expected candidate nor the verified original. It **NEVER overwrites
  unknown game-modified or externally changed data**.
- Unexpected maps, files or changed original/backup manifest refuse
  rather than attempting a best-effort repair.
- The original installed game, standalone original GMP and isolated
  candidate are **never modified by this tool**. No arbitrary file
  deletion is performed; the private backup/journal is retained.

The root name and acknowledgement reduce accidental use on a main
installation. They cannot mathematically prove a folder is a copy:
**the user must independently ensure it is not the only original game
installation**.

## If staging or restoring is interrupted

Use **Inspect test copy** or CLI --status first. The state can be
prepared, staging, staged, restoring or restored. If the journal says
staging while the map matches the original GMP, a repeat Stage may
finish it. If staging already installed candidate bytes, Stage
recognizes that exact digest and seals the journal. If restoring
was interrupted, Restore accepts either verified original or verified
candidate bytes and finishes the rollback.

If the file differs from BOTH expected hashes, leave it intact and
restore your disposable game copy from a separate backup manually.
Do not delete the backup or journal to force an overwrite.
No automatic game process management is attempted.

## Automated checks

- Synthetic v95 source GMP plus exact source-derived combined candidate.
- Source-only identical target in a fake disposable root.
- Prepare backup without map changes; stage expected candidate; inspect
  digests; restore exact original; preserve immutable backup/journal.
- Rejection of missing acknowledgement, wrong game-folder name,
  source placed inside sandbox, symlinked target, changed target,
  tampered backup/journal/candidate and duplicate trial.
- Recovery of interrupted staging/restoring.
- Full CLI from an arbitrary cwd with PYTHONPATH removed.
- Godot 4.3 source-absent UI, action picker and confirmation wiring.
- Windows portable prototype bundle and doctor dependency checks.

No retail DX2 game is distributed, executed or verified by these tests.
**Playable mission compilation, BSP/collision baking, script references
and arbitrary new actors remain future editor milestones.**
