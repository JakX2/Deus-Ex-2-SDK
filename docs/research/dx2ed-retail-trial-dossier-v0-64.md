# DX2Ed v0.64: controlled retail GMP A/B trial dossier

**Checkpoint:** November 10, 2026. **Status:** verified native binary
preflight plus a private manual game-test plan. **No retail gameplay is
automatically exercised or independently verified by this SDK.**

## Why a test dossier is the next milestone

DX2Ed v0.60 can export one atomic original-source-locked combination of
existing static prop movements, new source-derived copies and original
Level-list unplacements. Later v0.61 recipes and v0.62 reference checks
make the files more reproducible and conservative, but they do NOT tell
us if Invisible War's retail engine actually loads those edits, rebuilds
collision or preserves game behavior after level transition/save/load.

v0.64 turns each independently replay-verified native GMP candidate
into a **reproducible A/B test checklist** for the human running the game.
The dossier cannot exist unless the exact original GMP, candidate GMP,
adjacent v0.60 native plan manifest and full native-replay proof match.

## In DX2Ed (Windows Godot editor)

1. Open your **original, unchanged DX2 GMP** in DX2Ed.
2. Use v0.60 **Experimental Combined Save As...**, or import a v0.61
   content-free mod recipe, to produce an isolated GMP with the same
   basename in a separate research folder. The writer creates an
   adjacent .dx2ed-native-prop-plan.json provenance manifest.
3. Click **Prepare Retail Test Dossier...** in the static prop toolbar.
4. Choose the **previously exported isolated candidate GMP**, not the
   retail installation GMP.
5. Choose a new **private research directory** and a filename ending
   .dx2trial.json. The editor refuses the original map folder, candidate
   folder, game Content/DX2/Maps, unsafe ancestors and existing outputs.
6. Confirm. The read-only worker:
   - verifies exact original file SHA, candidate SHA and native manifest;
   - independently reconstructs **every candidate GMP byte** from the
     authenticated original and original StaticMeshActor edit plan;
   - creates two private, content-free JSON files: dossier and a blank
     .dx2observations.json file.
7. Review the test matrix and manually run tests **only** in a disposable
   backed-up copy of Invisible War. The SDK does not install a GMP,
   launch a game, copy saves or alter original game files.

The Godot editor does not automatically parse a human test result as a
runtime success claim. The observation assessment is a separate CLI
operation which deliberately reports only **owner-supplied observations**.

## CLI: prepare dossier

    python native_editor/package_writer/dx2_retail_trial_dossier.py --source "C:\OriginalDX2\Maps\M1_Example.gmp" --candidate "C:\DX2EdResearch\Candidate\M1_Example.gmp" --source-sha256 ORIGINAL_GMP_SHA256 --dossier "C:\DX2EdResearch\TestRecords\Initial.dx2trial.json" --prepare

Two new JSON files are generated, without any game assets:
- Initial.dx2trial.json: source/candidate hashes, operation counts,
  expected object positions and exact manual test checklist
- Initial.dx2observations.json: per-check result "not-tested" and blank
  note/evidence hash. Initially all tests remain **unperformed**.

Both JSON files are private records, **not** game mods. The generated
GMP remains where it was before the command.

## Manual retail test procedure

The dossier requires checking **each** of these conditions:

1. Baseline: enter unchanged map in a backed-up disposable retail copy;
   record original actor appearance, collision and general stability.
2. Candidate fresh load: place the isolated GMP using the player's
   **own manual disposable installation procedure**, boot and enter
   the level; note crashes and unrelated world/mesh anomalies.
3. Collision: inspect interaction with every moved/new/unplaced prop.
   Missing geometry can leave invisible collision or other hazards.
4. Level re-entry: leave the map and return, inspecting intended changes
   and unaffected source objects.
5. Save/reload: create a disposable game save, reload and inspect
   transforms, collision, scripts and basic AI.
6. Restoration: restore the backed-up original map manually and check
   that the baseline level and saves remain intact.

Additional checks are generated for **each moved original**, **each
new clone**, and **each Level-list unplaced original**. The document
records source export IDs and exact expected native Unreal X/Y/Z
coordinates. It cannot know what the retail game actually rendered.

**Never replace the only installed original GMP or overwrite important
game saves.** Use a separately backed-up installation, do not use an
unverified mod in a valuable ongoing save, and take manual notes of
game version/build, scenes and observed behavior outside the dossier.

## CLI: assess owner's recorded observations

Edit the .dx2observations.json manually after running each test.
Allowed result values are exactly:
- not-tested
- pass
- fail
- inconclusive

Keep the original check IDs/order and receipt hashes. Notes are capped
at 1000 characters per check. An optional 64-digit lowercase
evidence_sha256 can record a manually computed screenshot/log digest;
no screenshots or original game bytes are embedded.

    python native_editor/package_writer/dx2_retail_trial_dossier.py --source "C:\OriginalDX2\Maps\M1_Example.gmp" --candidate "C:\DX2EdResearch\Candidate\M1_Example.gmp" --source-sha256 ORIGINAL_GMP_SHA256 --dossier "C:\DX2EdResearch\TestRecords\Initial.dx2trial.json" --observations "C:\DX2EdResearch\TestRecords\Initial.dx2observations.json" --assess

Before reading observations, the assessment **repeats the independent
full-GMP candidate replay** and regenerates the exact expected
checklist from the source/manifest. It refuses altered source bytes,
modified candidates, forged dossiers, changed check IDs, unknown
fields or false runtime verification claims.

Possible summary statuses:
- owner-trial-incomplete-runtime-unverified
- owner-reported-issues-runtime-unverified
- owner-reported-all-checks-pass-not-independently-verified

**Even all human checks marked PASS are owner-reported, not independently
verified runtime correctness.** The tool always reports:
gameplay_runtime_verified=false,
observations_independently_verified=false,
safe_native_unplace_certified=false.

No automated installation, launch, byte editing or rollback script
is included. Runtime checks and restoration must be performed by the
person with the original game and a disposable installation.

## Tests and safety boundaries

Source-free synthetic UE95 fixtures cover:
- v0.60 original source move + new clone + source Level-list unplace;
- full byte-for-byte replay of original/candidate plus adjacent manifest;
- exact moved/clone/unplace expectations and six standard phases;
- initial empty observation log, manually reported PASS, FAIL and
  inconclusive cases;
- stale source SHA, candidate modifications, forged manifest/plan,
  false observation flags, altered check order and duplicate output;
- source/candidate/game directory refusal and source-byte preservation;
- standalone command-line execution without inherited PYTHONPATH;
- Godot 4.3 file dialog, confirmation and missing-original source refusal;
- Windows editor bundling and doctor checks.

No original Deus Ex: Invisible War or Thief 3 game assets are stored
in the repository. The GMP/IBD/BSP/collision/compiler and full
T3Ed-like mission editing challenges remain open.

## Subsequent high-value experiment

The next meaningful external evidence is a **real user-provided
observation** for one minimal isolated combined map with a harmless
static prop move + clone and another with a clone + unplace. Only
those game tests can distinguish binary parseability from playable
world state and collision compatibility. If they fail, the dossier
pins exactly which native edit and runtime phase failed, allowing a
narrower native writer or runtime dependency investigation.
