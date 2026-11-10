# DX2Ed v0.67: owner-reported retail observation dialog

**Status:** experimental Godot 4.3 UI over the v0.66 source-pinned Python recorder. Neither the GUI nor the worker launches, observes, or verifies retail Invisible War. No proprietary resources are bundled.

## What is new

The static-prop toolbar gains **Record Retail Test...**. Open the unchanged original GMP first. In the modal dialog, supply the isolated source-derived candidate GMP, its v0.64 dossier JSON, the adjacent .dx2observations.json and an already-prepared v0.65 disposable game-copy root named DX2Ed_Disposable_Test. The dossier chooser auto-suggests the matching observations filename.

Click **Inspect trial state** to run a background Python check. It separately recompiles the candidate, checks both JSON reports and compares their source/candidate SHA-256 against the disposable trial journal and the actual test-copy GMP hash. Only checks appropriate for the exact current prepared, staged or restored phase appear in the selector.

After personally running/testing the disposable copy, choose a check, an owner-reported result (pass, fail, inconclusive, or not-tested), and a note. Evidence files are optional; only the SHA-256 hash is saved. **Record owner result...** opens explicit confirmation that this is a human assertion and not independent proof. The background worker re-verifies hashes, notes, immutable check IDs and phase before atomically replacing the existing private observations JSON. The UI discards stale asynchronous reports if the paths, original SHA or candidate SHA changed during verification. Re-inspect after staging, restoring or recording an observation.

Only an already-existing private observations file is written by the worker. The original GMP, its isolated candidate, original source archive, retail game map, backup and state journal are read-only to the observation recorder. No game process management, mod installation, BSP/Havok rebuild or native script runtime verification is implied.

## Safety, limitations, next gate

- An unchanged original GMP must be loaded in DX2Ed to open the dialog.
- All paths are rechecked in the Python worker, including source size/hash and exact candidate byte replay. The chooser checks are convenience filters, not the sole safety boundary.
- The game test copy must be an actual disposable backed-up installation; folder naming alone cannot prove it.
- Prepared/original permits baseline, staged/candidate permits candidate and actor checks, restored/original permits restoration check. Interrupted or unknown-map states refuse recording.
- Real in-game behavior, collision, AI/script effects, transitions, save/load and original restoration still require explicit human observation.

**Tests:** A new source-free Godot smoke checks actual main-toolbar wiring, dialog controls, the acknowledgement confirmation, disabled initial recording and no-original-GMP refusal. This supplements v0.66's synthetic Python map/dossier/journal/CLI tests. Windows prototype bundling and doctor require the new script and smoke, and the Linux Godot 4.3 workflow compiles and runs it. A real Windows/GPU and retail-game manual test remains outstanding.
