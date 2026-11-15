# P112: testing a bulk GMP export inside Invisible War

## What the user's screenshots established

DX2Ed P111 created `C:\Users\Dav\Desktop\M1_Seattle_hub.gmp`.
The editor reported **8 native static prop edits** and **11 preview-only
edits omitted from the GMP**. The retail-game screenshot did not show the
expected draft changes, but the user had not independently demonstrated
that the candidate GMP was loaded from the active game's Maps directory.

**Creating an isolated GMP on the Desktop does NOT install it.** A native
manifest and package reparse prove binary reconstruction, not gameplay.

## The previous trial-helper gap

The P109 bulk writer emits
`M1_Seattle_hub.dx2ed-native-bulk-prop-plan.json`, while the existing
v0.64 dossier/v0.65 disposable test tool looked only for
`M1_Seattle_hub.dx2ed-native-prop-plan.json` (legacy combined writer).
The guarded retail-testing workflow could not authenticate the new bulk
candidate even though its own source writer verified it.

This milestone extends the existing dossier's proof chain to recognize
**exactly one** adjacent recognized manifest:

- Legacy: `.dx2ed-native-prop-plan.json`
- Bulk: `.dx2ed-native-bulk-prop-plan.json`

Ambiguous, missing, forged or modified manifests fail closed. The
candidate is still independently recompiled from original source,
compared byte-for-byte and pinned to the original GMP hash. Legacy
operation limits remain in force. Bulk dossiers may contain up to 256
per-operation manual checks plus six common gameplay/restore checks.
The game is **never** started by these scripts, and no original
installation is modified.

## Safe first test on Windows

1. Keep the original retail install unchanged. Make a **complete copy**
   into a separate root named exactly `DX2Ed_Disposable_Test`,
   containing `System` and `Content\DX2\Maps`.
2. Keep the unchanged original `M1_Seattle_hub.gmp` and the generated
   Desktop candidate outside that copied installation. Retain the
   adjacent bulk JSON manifest.
3. Close the game. Load the **original GMP** in DX2Ed.
4. Enable **Advanced controls**. In the disposable trial action
   dropdown choose **Prepare backup**, click **Disposable Game Trial...**,
   choose the Desktop candidate, then select the copied game root.
   This creates a protected backup/journal; the test map remains original.
5. Choose **Stage test GMP**, click the same button and choose the
   **same source candidate and copied game root**. Confirm the
   disposable-only overwrite. This puts the candidate at
   `DX2Ed_Disposable_Test\Content\DX2\Maps\M1_Seattle_hub.gmp`.
6. Start the **copied game's executable**, preferably enter the level
   freshly rather than loading a save made while already in the map.
   Compare the eight eligible native changes against the manifest
   `moved`, `copied`, `unplaced` fields. The eleven omitted
   preview-only changes are NOT expected to appear.
7. Close the game. Choose **Restore original** in the trial dropdown,
   select the same copy root and let the tool verify the rollback.
   Keep test saves separate.

**Diagnostics if no change appears after staging:** Verify the journal
state with **Inspect test copy**. It should report
`target_content=matches-candidate` and a staged receipt. If it does,
confirm the executable launched from the copied installation and test
a fresh map entry. If it still looks original, the remaining issue is
native runtime adoption/actor loading, which requires a genuine game
observation rather than inventing further writer support.

## Test coverage

`native_editor/tests/test_dx2_bulk_disposable_retail_trial.py` uses
fabricated GMP fixtures with **20 clones**. It verifies independent
candidate replay, the per-operation checklist, backup preparation,
acknowledged staging, candidate hash checking, restoration and original
source integrity. It also tests ambiguous dual manifests and tampering.
Existing legacy test suites continue unchanged.

No claim is made that bulk clones, BSP, collision, new brushes,
working doors, vending machines or private draft assets are supported
by the game at runtime.
