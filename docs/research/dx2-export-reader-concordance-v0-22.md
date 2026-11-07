# v0.22: candidate export-table concordance against the existing DX2 reader

Status: **draft research**, source-only, non-writable. This adds
`research/dx2/export_reader_concordance.py` on top of the
unmerged v0.21 audit in draft PR #88. No changes to the retail loader,
public SDK, editor scene UI, GameSys writer or any GMP writer.

## Why this exists

The strict v0.21 structural audit (`dx2_export_boundary_audit.py`)
checks candidate UE95/Ion 68–69 header/export table boundaries and
overlaps. The existing `map_exporter/dx2inspect.py::Package`
was independently implemented for game asset exploration but has a more
permissive package parser. Before exposing any source-derived export range
to future BSP/zone research, we can check that the *same source bytes*
produce identical table counts, one-based export identities, and nonempty
serialized export offsets/lengths in both implementations.

`compare_export_readers(Package_instance, expected_sha256=...)`
runs the strict candidate audit directly on the immutable `Package.data`
bytes read by the existing loader. The caller must supply the expected
lowercase SHA-256. It rejects mismatched version/licensee/table counts,
decoded row counts, malformed export identity, byte-size/offset disagreement
and any rejection by the stricter parser. Zero-size exports remain
non-owners. An invalid Package instance or a source SHA mismatch fails
closed. There is no second file read to create a new time-of-check/time-of-use
window between the two analyses.

## Owner-only local diagnostic (opt-in)

For a user-owned DX2 package on a local development machine, from the
repository root in PowerShell:

```powershell
$map = "C:\Path\To\Your\Installed\DX2\Map.gmp"
$sha = (Get-FileHash -LiteralPath $map -Algorithm SHA256).Hash.ToLowerInvariant()
python -B research/dx2/export_reader_concordance.py --map $map --sha256 $sha
```

This command only **reads** the specified local file. It prints
non-sensitive summary metadata: source hash/size, version, licensee,
table counts, number of matching nonempty exports, number of zero-size
exports, and explicit non-authority flags. No original asset names,
raw payloads, byte previews, export offsets, or local filesystem paths
are emitted on successful output. The script never writes output files,
changes the original package, or adds assets to source control.

The local diagnostic is *not* automatically invoked by DX2Ed, is not
part of the portable SDK user-facing commands, and should not run against
untrusted very large files (128 MiB maximum source bound). A file can be
correctly rejected by this intentionally narrow research parser despite
being accepted by the game. Such a reject must be investigated locally,
never bypassed or coerced to "verified".

## Synthetic regression coverage

`native_editor/tests/test_dx2sdk_export_reader_concordance.py`
uses only generated, invented v95 package bytes. It verifies positive
reader agreement, zero-size exclusion, SHA mismatch, malformed local
source, original file integrity, CLI no-payload/no-name output, and
deliberately corrupted legacy exports/counts. It demonstrates a useful
negative control: the older Package reader accepts two overlapping
serialized export ranges which the strict audit correctly rejects.

## What this does NOT prove

The report unconditionally retains:

- `export_envelopes_independently_verified: false`
- `native_bsp_leaf_zone_decoded: false`
- `runtime_game_verified: false`
- `writable: false`

Both readers were constructed from related UE package format assumptions.
Agreement is **implementation concordance**, not independent ground truth,
a retail compatibility guarantee, a DX2-native BSP/portal/zone proof,
or permission to change the source. Do not pass candidate offsets into
the scalar writer or an arbitrary package reserializer.

## Next gate

Use this tool on private, owner-provided original DX2 packages locally,
with an independently computed SHA-256, and record only aggregate pass/fail
counts. Study mismatches alongside the Thief 3 T3ED package reader and
current DX2 source evidence. Before any native BSP/zone decoder, establish
independently validated export ownership and record semantics. Keep all
proprietary package bytes and detailed offsets outside public CI and PRs.
