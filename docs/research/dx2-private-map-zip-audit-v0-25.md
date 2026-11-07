# v0.25: private original-map ZIP concordance scan

Status: **experimental, source-only and read-only**. This branch stacks on
unmerged draft #91 (v0.24). It adds a way for the owner to investigate
several original DX2 \`.gmp\`/\`.d2u\` packages from a **local ZIP archive
without extracting its contents**. It does not create a map, write a
game package, or prove gameplay/engine compatibility.

## Why

The prior v0.21–v0.24 research compared a strict DX2 header/export
auditor, the legacy DX2 source reader and the checked-in Thief 3
reference reader, but only for one file at a time. The user's project
Drive includes the original DX2 Maps archive. Running local-only
aggregate checks against a copy of that archive is the next useful
source-evidence gate. No original map data is checked into this repo
or uploaded as GitHub Actions artifacts.

## Native data path

\`research/dx2/private_zip_package_audit.py\` opens one explicitly
selected local archive as immutable bounded bytes. Python's standard
\`zipfile\` module parses the ZIP's central directory in memory.
Eligible \`.gmp\`/\`.d2u\` members are inspected one at a time, using
the existing readers:

1. \`map_exporter/dx2inspect.py::Package(..., data=member_bytes)\`
   now optionally accepts bounded immutable in-memory bytes, without
   changing its existing path-based behavior.
2. The strict candidate export-table audit hashes and checks the
   exact same in-memory package data.
3. The Thief3 package reader cross-checks table boundaries, package
   symbol identities, import/export references, flags, and byte ranges.

The code does **not** extract a member, create temporary GMP/D2U files,
or write results to disk. The report uses only aggregate counts
(\`three_reader_concordant\`, \`legacy_reader_rejected\`,
\`cross_reader_rejected\`, \`unreadable_entry_rejected\`,
\`oversized_or_high_ratio_rejected\`, \`unsafe_entry_rejected\`
and \`unsupported_entry_rejected\`). No map names, actor names, byte
offsets, decoded symbols, source file paths, mesh data or package
payloads appear in the success report.

## Optional local command (Windows PowerShell)

Extract the source-only repo to your machine and supply **a path to a
user-owned ZIP**, not a game installation folder:

~~~powershell
$zip = "C:\Your\Private\OriginalDX2Maps\maps.zip"
$sha = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
python -B research/dx2/private_zip_package_audit.py --archive $zip --sha256 $sha --max-files 512
~~~

\`--sha256\` is optional, but if given must match the exact ZIP bytes.
Without it, the script pins all package reads to its own single
in-memory ZIP snapshot and explicitly reports
\`archive_sha256_independently_supplied: false\`.
It never claims independent verification of source identity.

The diagnostic prints JSON to standard output, **not a report file**.
Keep the ZIP in a private directory, avoid committing local ZIPs,
and never attach original asset bytes to a public PR.
To preserve the no-disk-source-copy property, use the \`-B\` flag
(avoids Python bytecode-cache generation).

## Fail-closed limits

- Maximum archive size: **384 MiB**; immutable, regular file only.
  Symlinked archives are refused.
- Maximum ZIP central-directory entries: **4096**.
- Eligible package count must be from **1 to the selected limit**
  (default 256, maximum 512). No silent partial scans.
- Each GMP/D2U member is bounded by the source reader's **128 MiB** cap.
  Total declared eligible uncompressed bytes are capped at **2 GiB**.
- Only unencrypted stored/deflated ZIP members are supported. Reject
  high expansion ratios (over 200:1), unsafe paths and ZIP symlinks.
- Case-insensitive duplicate member names reject the archive before
  any member is inspected. CRC/length errors are counted as rejections.
- Valid ZIPs can be rejected by these limits or by the deliberately
  restrictive experimental DX2 parser even if the game opens them.
  Rejection is not proof of a broken game package.

## Synthetic evidence

\`native_editor/tests/test_dx2sdk_private_zip_package_audit.py\`
creates invented UE95/Ion package ZIPs and verifies two valid
three-reader matches, malformed legacy source, overlapping export
ranges vetoed by the strict reader, source hash mismatches, duplicate
ZIP names, compression-ratio bounds, unsafe traversal paths, symlink
entries, input immutability and CLI non-leakage.

The viewer test harness also now explicitly imports the runnable
\`dx2ed_3d.py\` module instead of the name-colliding package directory,
avoiding an existing CI-only test-discovery problem. The viewer itself
is unchanged.

## What is still missing

All previous no-authority flags remain. This batch scan is evidence
collection, **not** a UE95 export authenticity certificate, BSP/zone
parser, portal/lightmap builder, T3ED compiler, or retail DX2
compatibility test. It does not modify GameSys, actor fields, original
lights, static meshes, collision, or in-game HUDs.

Record aggregate matches and rejected counts privately; review any
failure category locally and compare it against original reader source
and T3ED reference behavior. Do not unlock native BSP/zone writing
until independent format evidence and runtime tests exist.
