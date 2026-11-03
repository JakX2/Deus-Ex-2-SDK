# DX2Ed: first runtime GameSys scalar test (separate DX2 installation)

**Status (2026-11-02): USER-REPORTED SUCCESSFUL WTO TERMINAL LOAD
AND STABLE IN-LEVEL EXPLORATION.**
The user reported that the no-command edited-GameSys test package
worked, supplied a screenshot of a rendered WTO Terminal scene with
HUD and NPCs, then confirmed they explored the level without crashes
or instability. This is stronger runtime smoke evidence than an initial
successful load, but it is not independent proof of the edited GMP's
disk hash, a visible gameplay property change, or repeatability. See
[USER_RUNTIME_REPORT_2026-11-02.md](USER_RUNTIME_REPORT_2026-11-02.md)
for evidence boundaries and recommended confirmation checks.

This remains a reproducible checklist for the experimental
one-scalar serializer. Passing unit tests and a first reported map
load do not establish the in-game effect of this or other
properties. Do not replace retail assets.

## 1. Prepare an isolated copy of the installed game

Use a separate, legal working copy of your own DX2 game installation,
including all required GMP/IBD/System resources and its own writable map
path. Keep the retail installation backed up and untouched. Avoid
a shared mod launcher or folder if it writes into your retail content.

Make sure the original game launches a normal copy of the target mission
in the isolated installation BEFORE testing edited bytes. Record game
version, map name and whether the original mission loads.

## 2. Identify a low-impact existing property

The original supplied WTO Terminal source contains one demonstrable
candidate (not necessarily perceptually obvious in gameplay):

- Original map: M1_Seattle_Hub_WTOterminal.gmp
- Original actor export: 23
- Actor name: D_464__1
- Original existing GameSys property ID: 1586
- Source-declared property: EmissiveScale (float32)
- Original source value: 0.49803924560546875

This is only an example of **verified original bytes**, NOT proof that
an isolated game will use this value or that the actor is visible.

Get the SHA of **the particular original GMP you are about to modify**
in PowerShell, and confirm it matches the research source revision.

    $map = "C:\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp"
    $hash = (Get-FileHash $map -Algorithm SHA256).Hash.ToLower()
    $hash

The SHA check intentionally refuses other versions or unpacked revisions.

## 3. Check the in-memory two-writer parity first

Run from the repo checkout root:

    python native_editor/package_writer/dx2_gamesys_scalar_probe.py "$map" --source-sha256 $hash --actor-export 23 --actor-name D_464__1 --property-id 1586 --kind float --expect 0.49803924560546875 --replace 0.6

Only proceed when status is \`in-memory-match-only\`,
\`full_package_byte_match=true\`, and
\`edited_package_written=false\`.

## 4. Make an isolated, separately verified GMP copy

    python native_editor/package_writer/dx2_gamesys_scalar_probe.py "$map" --source-sha256 $hash --actor-export 23 --actor-name D_464__1 --property-id 1586 --kind float --expect 0.49803924560546875 --replace 0.6 --output "C:\DX2EdIsolatedTest\M1_Seattle_Hub_WTOterminal.gmp"

Output is refused if the filename differs, destination is inside the
source Maps tree, or GMP/manifest already exists. A report
\`M1_Seattle_Hub_WTOterminal.dx2ed-gamesys-scalar.json\` is written
beside the output. Read it and confirm:
- \`full_package_byte_match=true\`.
- \`changed_bytes\` is between 1 and 4.
- \`runtime_verified=false\`.
- \`original_source_modified=false\`.
- All original package names/exports remain present.

Keep this output file out of the retail game.

## 4b. Independently preflight the ORIGINAL and edited files

The saved GMP has passed two serializers at creation time. Before
installing it even in a **disposable** game copy, re-read the original
and experimental copies and the manifest using the separate native
preflight tool. This validates the actual bytes on disk, not just
the original writer's success flag:

    python native_editor/package_writer/dx2_gamesys_runtime_preflight.py --original "$map" --candidate "C:\DX2EdIsolatedTest\M1_Seattle_Hub_WTOterminal.gmp" --report "C:\DX2EdIsolatedTest\preflight.json"

The preflight **fails closed** unless:
- Both original and modified GMPs are accepted by the independently
  implemented DX2 parser and unchanged MIT T3SDK package reader.
- The source hash, edited hash, original and edited field contents,
  actor ID/export, original block version, raw GameSys encoding,
  byte offset, payload length and diff count all match reality.
- **Every changed byte** falls within the exact original four-byte
  scalar payload, and the manifest is adjacent to the candidate GMP.
- The original byte length, package GUID, export structure and names
  remain unchanged.

A successful report says
\`binary-preflight-passed-runtime-not-tested\` and
\`game_runtime_tested=false\`. It never claims that Invisible War
successfully loaded the map. The tool **does not install, replace,
repair or otherwise write GMP files**. The optional JSON report
must be a new separate file outside the original Maps directory.

The supplied original WTO Terminal package was independently
sampled in memory for \`D_464__1\`, GameSys 1586
(\`EmissiveScale\`, 0.49803924560546875 to 0.6), and both
T3SDK and a direct four-byte patch produced the exact same GMP
bytes. This is **not** evidence of in-game behavior.

## 5. Test only in a disposable game installation

Put the independently verified edited GMP into the appropriate mission
map location **of the isolated copy only**, retaining the exact original
filename, while keeping a safe original to restore. Do not change or
repack IBD/System or unrelated GMP data for this test.

Load the relevant mission **from a fresh entry point** if possible;
an existing save may retain previously loaded actor state. Record:

1. Does the game start normally with this copy?
2. Does entering the mission succeed, or is there a log/crash?
3. Does the changed value have an observable effect?
4. Does reverting only the GMP restore original behavior?
5. Do the map and object still load on a second fresh launch?

A lack of visible difference is an **inconclusive runtime behavior test**,
not proof of a corrupt map. The target actor or effect may never activate.

## 6. Report the result

Record the original and output SHA-256, target field ID, original
and proposed value, game build/version, whether the map loads,
what was observable and relevant log/error messages. If either map
load or gameplay fails, restore the clean test copy and investigate
rather than editing additional fields blindly.

**Only after reliable runtime evidence** should the normal Godot
Inspector expose native GameSys writes. The current GameSys panel,
Auto Roll, geometry editor and native Location-only Save As remain
independent of this research command.
