# DX2Ed P113: private automated Ghidra survey

Status: the infrastructure is a draft branch. Public CI can validate source-only fixtures immediately. Actual Ghidra analysis of game executables is disabled until the owner installs/configures a private self-hosted runner and merges to main. The SDK does not have the user's original game binaries.

## What is implemented

- tools/ghidra/scripts/Dx2SymbolSurvey.java: a bounded Ghidra post-analysis script that inventories up to 500,000 defined data records, matches selected engine-related keywords, and follows references to at most 24 candidate function entry addresses per term.
- tools/ghidra/run_private_survey.py: Python 3.11+ wrapper. Validates a manifest of up to eight private Windows PE binaries, pins each SHA-256, runs headless Ghidra in a throwaway project, and emits only schema-validated keyword counts and addresses to a private output directory.
- .github/workflows/dx2-ghidra-survey.yml: daily 03:17 UTC source-only CI, plus an explicitly gated scheduled headless run on a self-hosted Linux machine labeled dx2-private-re.
- tools/ghidra/tests/test_private_survey.py: fabricated PE-header inputs and mock Ghidra reports, no game assets.
- No original executable bytes, decompiled function bodies, raw strings, input file paths, or reports are uploaded by the new workflow.

The output is research evidence, NOT reconstructed native map writing, working doors, or engine runtime proof.

## Manual first run on Windows

1. Install Ghidra, including the Java runtime required by the selected release.
2. Put an untracked text manifest outside Git, for example D:\DX2Private\original-targets.txt. List one absolute path to a legitimate DX2 EXE or DLL per line. Use names from your own game installation; this script does not guess filenames. Input PE files must start with MZ.
3. In a PowerShell terminal at the repository root, run:

    py -3.11 tools\ghidra\run_private_survey.py --manifest "D:\DX2Private\original-targets.txt" --check-inputs-only

    py -3.11 tools\ghidra\run_private_survey.py --manifest "D:\DX2Private\original-targets.txt" --ghidra-home "D:\Tools\ghidra" --report-dir "D:\DX2Private\reports\run001"

4. Read D:\DX2Private\reports\run001\dx2_research_summary.json. It contains binary fingerprints, function counts, allowed keywords and bounded candidate addresses. It contains no original binaries or decompiled source. Empty hits do not establish that the game lacks a feature.
5. Repeated runs need new output directories: the script refuses to overwrite earlier reports or original game assets.

Asset-free tests:

    py -3.11 -m unittest discover -s tools/ghidra/tests -p "test_*.py" -v

## Enabling recurring analysis on GitHub Actions

Scheduled workflows run on the repository's default branch. This draft PR alone will not launch the real daily analysis job.

1. Review and merge the P113 branch into main.
2. Provision a private self-hosted Linux GitHub Actions runner with labels self-hosted, Linux and dx2-private-re. Ghidra on Linux can statically analyze Windows PE binaries. Use restricted file permissions, an unprivileged runner account and a read-only copy of the game.
3. On the runner install Ghidra, place a private target manifest containing absolute local EXE/DLL paths outside the checkout, and make a protected, persistent report directory outside the game and repo.
4. In the repository's Actions variables set:
   - DX2_GHIDRA_ENABLED = true
   - DX2_RE_MANIFEST = absolute manifest path on the private runner
   - DX2_RE_GHIDRA_HOME = local Ghidra root
   - DX2_RE_REPORT_ROOT = protected existing folder on private runner
5. Run the workflow once manually, then leave the runner connected for daily 03:17 UTC jobs. GitHub may delay scheduled work. Analysis is never triggered on a PR from external contributors.

Reports remain ONLY on that private runner under a directory named for the Actions run ID/attempt. Nothing is uploaded to GitHub by default. To share findings, inspect and manually approve the sanitized JSON or write a concise research note based on it.

## Research priorities

1. Candidate references to original GMP/IBD package-loading paths.
2. StaticMeshActor deserialization and Level actor registration, compared with the existing isolated bulk GMP test.
3. BSP/collision structures and eventual native geometry compiler investigation.
4. GameSys, TriggerScript and interactive object behavior such as doors and vending machines.

A keyword hit or function address is only a lead. Stripped symbols, encoded strings and indirect calls may be missed. Runtime observation of a staged test GMP is still necessary.

## Failure modes

- Skipped job: not main, missing opt-in flag, or pull-request event.
- Job queued: no runner with exact self-hosted private labels.
- Refused inputs: missing/relative path, duplicate binary, bad PE signature, excessive size.
- Analysis failure: investigate locally; raw Ghidra stdout/stderr are intentionally not put into workflow logs.
- Unexpected content: output validator rejects raw strings, malformed addresses, invalid keywords, and forged reports.

Official headless usage: https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md
