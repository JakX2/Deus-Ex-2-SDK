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

The scheduled job (**03:41 and 15:41 UTC daily**) or default-branch
manual dispatch downloads the already identified owner DX2 `System.zip`
into ephemeral runner scratch, verifies every required PE by filename,
size, full SHA256 and valid PE header, then runs the bounded DX2 survey.

**The correct ZIP is confirmed:** `DX 2 Files/System/System.zip`
(Drive file ID `1I5LeElJswBMs-EIoDyH5sKqRTUlCW4ox`).
The other `T3 Files/System/System.zip` contains the Thief 3 executable
and must not be used. The actual DX2 archive was inspected from the
connected owner Drive, and the two engine-relevant Windows x86 binaries
were fingerprinted:

| File | Bytes | SHA256 |
|---|---:|---|
| `DX2Main.exe` | 6,111,232 | `f31db8c8d5c6ce33a4d8f4e0025e246dd3823026518f01f8bfa731a38f446692` |
| `dx2.exe` | 31,232 | `35ac158caa4cdd772748b587b82f108bb2902d2784d66db516979a008e61b604` |

These are the exact bytes from the user's supplied ZIP, **not proof of an
independently authenticated retail release**. No original game executable
bytes are checked into Git. The source-only pins are in
`tools/ghidra/dx2_system_pe_pins.json`.

One-time repository owner configuration:

1. Add GitHub Actions secret `DX2_ORIGINAL_SYSTEM_ZIP_ID` containing
   the ID of the owner's DX2 System.zip. This is an identifier, *not*
   a Drive authentication token; keep it out of public workflow logs.
2. Set repository Actions variable
   `DX2_HOSTED_GHIDRA_ENABLED=true` to opt into original binary analysis.
3. Review and merge the standalone PR #190 into `main`, then use
   **Actions -> DX2 hosted Ghidra 12.2 original research -> Run workflow**
   to perform an initial original-image run. Future runs can execute
   twice daily without the PC being on. If the Drive download is
   inaccessible from GitHub, authenticated Drive access must be
   configured or the download mechanism revised.

No owner-supplied SHA manifest secret is required anymore: the verified
hashes are pinned in the repository. Changing any of these files in the
original archive requires deliberately reviewing a new hash and updating
the manifest. Unknown or modified images are refused.

**Performance:** the official Ghidra distribution ZIP is cached after
SHA256 verification. A second cache holds **only the strictly sanitized
research JSON** using a key that changes when the pinned original hashes,
analyzer code or report validator changes. Every scheduled run still
downloads and validates the original ZIP first. If a matching validated
metadata report already exists, the expensive Ghidra reanalysis is
skipped, and the report is revalidated against the current pins before
creating a new artifact. Reanalysis is automatic when the inputs or
analysis code change.

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
- Runs on pull requests have NO original-binary secrets. Only the independently fingerprinted DX2 source ZIP identifies candidate originals; synthetic CI does not import the actual original game.
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
