# DX2Ed v0.66: owner-reported retail observation recorder

**Checkpoint:** 11 November 2026. Human observation recording, not a retail-game test runner or runtime certification.

## Workflow and safety

v0.64 creates an original-GMP-pinned A/B test dossier and manual observations JSON. v0.65 offers a guarded stage/restore workflow for a disposable installation. v0.66 adds a CLI to inspect their combined state and record results with checks instead of editing observation JSON by hand.

It requires:
- unchanged original GMP and its pinned source SHA-256;
- isolated candidate GMP plus its native prop plan manifest;
- the matching dossier and observations JSON pair;
- the already prepared disposable-game directory named DX2Ed_Disposable_Test, including intact original-map backup and state journal.

Read-only inspect returns the current phase, target digest state, owner-reported result counts and the check IDs eligible for recording. To record a result, the user explicitly acknowledges that it was human-reported rather than independently game-verified. Valid results are pass, fail, inconclusive and not-tested. A nonblank note (maximum 1000 characters) is required for pass, fail or inconclusive. Evidence files are optional and are hashed without copying any bytes to the report.

## Phase constraints

- prepared and original map present: baseline check only
- staged and candidate map present: candidate-load, collision, reentry, save-reload and move/clone/unplace operation checks
- restored and original map present: restore check only
- interrupted staging/restoring or unknown map content: no new nonempty observation is accepted

Clearing a result to not-tested requires an empty note and no evidence. This is permitted regardless of phase and never claims gameplay truth.

## CLI usage

Run this command from the repository root (replace placeholders with owner paths and the real source SHA):

~~~powershell
python native_editor/package_writer/dx2_retail_observation_recorder.py --source "C:\OwnerOriginals\M1_Example.gmp" --candidate "C:\IsolatedCandidate\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256 --dossier "C:\DX2EdResearch\Trial.dx2trial.json" --observations "C:\DX2EdResearch\Trial.dx2observations.json" --test-root "C:\DX2Ed_Disposable_Test" --inspect
~~~

To record a collision problem after manually testing while the candidate remains staged, replace --inspect with:

~~~text
--record --check-id collision --result fail --note "Owner observed residual collision" --evidence "C:\DX2EdResearch\collision.png" --acknowledge OWNER_REPORTED_NOT_GAME_VERIFIED
~~~

The optional evidence path must refer to an existing nonempty regular file of at most 512 MiB. The program stores only its SHA-256, not its contents. It does not infer whether the evidence proves a gameplay result.

## Guarantees and limits

Before every record, the CLI independently recompiles and verifies the isolated candidate from the unchanged original source, validates both the dossier and observation schemas, checks the disposable trial journal against the same source/candidate identities and checks the actual test map digest. Only the private observations JSON is atomically replaced, retaining existing permissions. No game GMP, backup, game save or source archive is modified.

The tests use exclusively synthetic v95 GMP fixtures. Windows packaging includes the recorder source. **No actual retail runtime test has been executed or asserted.** Hash consistency and human reports do not certify working collision, script binding, native BSP cooking, or playable mod compatibility. The next acceptance gate is an owner-performed A/B test inside an independently backed-up game copy.
