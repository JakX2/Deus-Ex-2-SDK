# P114: GitHub-hosted Ghidra for Deus Ex: Invisible War

## Why this is preferable to a self-hosted machine

The SiN Episodes repo PR #310 independently proved SHA-pinned official
Ghidra 12.2 + JDK 25 can run its actual Java postScript headlessly on
GitHub's hosted Ubuntu runner, using a harmless synthetic executable.

P114 adapts that infrastructure to DX2, retaining P113's strict
aggregated-only JSON output. GitHub hosts CPU, Ghidra, and disposable
scratch. The owner's PC does not need to stay switched on. Both
setups remain alternatives: P113's private self-hosted workflow is
untouched.

## First phase: real Ghidra smoke, but NO game binaries

The workflow dx2-ghidra-hosted.yml runs on PRs:

1. Synthetic ZIP SHA256/PE structural validation tests.
2. Java 25 setup and official SHA256-pinned Ghidra 12.2 install.
3. Compile harmless C -> Linux ELF.
4. Run **the actual DX2 Java postScript Dx2SymbolSurvey.java** under
   headless Ghidra.
5. Check the resulting JSON against our original strict sanitizer:
   candidate entry addresses and bounded keyword counts only.

The installer verifies Ghidra_12.2 official SHA256 from the upstream
release: 2c2cd776db3c1f6a097ba418922378ac3649cadd5e844a6f5f088ae628a7be67.
Only this official Ghidra ZIP is cached. No original owner assets are
needed or accessed by the PR smoke job.

## Second phase: opt-in original DX2 EXE/DLL analysis

Only on the **default branch** after merging and setting a repository
Actions variable:

    DX2_HOSTED_GHIDRA_ENABLED = true

The scheduled job (03:41 UTC daily) or default-branch manual dispatch
will download exactly **one owner-selected original System.zip** to
ephemeral runner scratch, verify every required PE by filename, exact
size, full original SHA256, MZ + PE signature and sane ZIP paths,
then analyze with the existing private survey runner. Up to eight
owner-original EXEs/DLLs per run are supported.

Repository Actions secrets to configure:

- DX2_ORIGINAL_SYSTEM_ZIP_ID: the Google Drive file ID for the intended
  owner-original ZIP; **not** the SiN IDs.
- DX2_ORIGINAL_PE_MANIFEST_JSON: JSON array of exact original PE
  filenames, whole-file byte sizes and full SHA256 hashes.

Example structural shape (NOT real DX2 hashes or filenames):

    [
      {
        "name": "ExampleOriginal.exe",
        "size": 1234567,
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      }
    ]

Replace with the actual original values. Never copy these fictional
values into the real secret. A Ghidra job will refuse an unknown,
missing, modified, duplicated or incorrectly hashed image.

The user's Drive project currently has **two candidate System.zip files**,
one in DX 2 Files/System and another in T3 Files/System. We have
not established which one contains the correct DX2 retail game
executable or whether Google Drive will allow an unauthenticated
runner download. Do not use the SiN hashes for DX2.

**Drive privacy:** a Drive ID in GitHub Secrets is merely an obscured
locator. It is NOT an access credential and does not make an
anyone-with-link file private. This workflow uses gdown for a
downloadable owner shared link. If the owner wants fully private Drive
access, add an authenticated Google Drive API/service-account flow
before enabling the scheduled job. Do not change sharing permissions
just to make the automation work without understanding the risk.

## Reporting and safety

- The only artifact uploaded is dx2_research_summary.json, which is
  reconstructed from an allowlist of function entry addresses,
  fingerprint hashes, processor, function count, and selected keyword
  counts. Original bytes, raw strings, full symbol names, pseudocode,
  raw Ghidra logs and GMP files are NOT uploaded.
- **Artifacts of a public GitHub repository may be accessible to
  visitors.** Thus this summary is deliberately limited and retained
  for seven days. Do not add original function bodies without revisiting
  this safety boundary.
- ZIP, verified PE binaries, Ghidra projects and intermediate files
  reside only on the ephemeral GitHub runner and are removed after a job.
  Only the verified public Ghidra installation ZIP is cached.
- Runs on pull requests have NO original-binary secrets. Neither
  original files nor original hashes are inferred by tests.
- No code writes a GMP, patches DX2, or installs a retail game.
- This is standalone draft PR #190 against main, combining the P113
  survey and P114 hosted runner. No unrelated editor PR needs merging.
  GitHub schedules only execute workflows present on the default branch.

## Results interpretation

A successful synthetic CI job proves the Ghidra launcher, Java
script API and report sanitizer execute together. It **does not**
mean the owner's original DX2 binaries have been analyzed.

A successful original-hosted job proves original files were loaded and
candidate reference metadata emitted, not that the recovered functions,
objects, BSP/collision layout or runtime behavior are correct. Follow
the callgraph and do independent game runtime tests next.

First research priority: original GMP loader, StaticMeshActor
deserialization, Level actor registration. Second: BSP/collision
readers and geometry cooker. Third: interactive actor/script
constructors and T3Ed parity.

## CI

    python -m unittest discover -s tools/ghidra/tests -p 'test_*.py' -v
    bash -n tools/ghidra/install_pinned_ghidra.sh

Workflow: .github/workflows/dx2-ghidra-hosted.yml
