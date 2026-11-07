# v0.23: DX2 export table concordance with the checked-in Thief 3 reader

Status: **experimental research only**, no source writes, runtime assertions,
public SDK commands, Godot UI, or native GameSys/actor/BSP editing.

## Why compare a Thief 3 reader?

The repository contains a separately implemented source package parser,
`third_party/t3sdk_assets/upkg.py::Package`, inherited from
Thief 3/T3SDK research. Both Thief 3 and DX2 use an Ion Storm Unreal package
fork. The Thief reader has an **in-memory bytes** constructor, making it
possible to check candidate UE95 header/table/export boundaries without
writing a source file or reading it again between implementations.

On top of draft #89 (v0.22), `research/dx2/thief3_export_concordance.py`
checks three paths against **the same SHA-pinned immutable bytes**:

1. Strict DX2 v0.21 source-only candidate boundary auditor.
2. Existing DX2 `map_exporter/dx2inspect.py::Package`.
3. The checked-in Thief 3 `third_party/t3sdk_assets/upkg.py::Package`
   (loaded with `data=source`, never a second game file read).

The third path must independently report the same UE package version and
licensee, decoded name/import/export counts, header end, import/export
table starts and ends, original **zero-based** Thief export IDs versus
the DX2 auditor's **one-based** IDs, and every nonempty export's
length/offset. Zero-size exports are not owners. Any mismatch causes a
`ReaderConcordanceError` instead of a partial "match" report.

## Local opt-in usage

From the repository root (PowerShell), on a **user-owned** DX2 package:

```powershell
$map = "C:\Path\To\Your\Installed\DX2\Map.gmp"
$sha = (Get-FileHash -LiteralPath $map -Algorithm SHA256).Hash.ToLowerInvariant()
python -B research/dx2/thief3_export_concordance.py --map $map --sha256 $sha
```

The script prints only bounded metadata: file hash and size, version,
licensee, decoded counts, numbers of nonempty and zero-size exports,
reader-match flags and explicit non-authority flags. It emits **no**
native export offsets, actor/asset names, original payload bytes,
mesh geometry, texture data, or absolute input file path in its success
report. It never modifies the source GMP/D2U or generates game files.
`-B` prevents Python interpreter bytecode-cache writes.

All three readers can reject a package that the original game could
load; rejection does not prove corruption. This is an intentionally
restricted research check for candidate UE95/Ion licensee 68/69 package
headers. User-owned sample files stay local; no retail packages or
private complete reports belong in public CI.

## Synthetic-only regression

`native_editor/tests/test_dx2sdk_thief3_export_concordance.py`
checks a generated v95 package, zero-sized export handling,
strict-reader veto against overlapping spans, SHA mismatch, missing/invalid
local sources, no-leak/no-write local CLI output, and injected Thief
reader field/offset/end/index/count disagreements. No user files are
copied into the repository.

## Non-authority boundary

Agreement among three readers is useful structural **corroboration**,
but they share the same reverse-engineered package-format assumptions.
Even if all checks pass:

- `export_envelopes_independently_verified: false`
- `native_bsp_leaf_zone_decoded: false`
- `runtime_game_verified: false`
- `writable: false`

No native leaf/zone records are identified, no map compiler exists,
no runtime acceptance or T3ED compatibility is implied, and the
data cannot authorize a reserializer. This is a precondition for
future local evidence audits, not a binary writer.

## Next practical milestone

Verify representative original DX2 v95 licensee 68/69 packages locally
and compare only aggregate passes/rejections, never sharing their data.
Investigate any strict-vs-legacy-vs-T3 divergences with the source readers,
then establish actual BSP/zone record boundaries independently before
creating read-only zone navigation in DX2Ed. Full T3ED-style map authoring
will still require native BSP, collision, lighting and cook/rebuild support.
