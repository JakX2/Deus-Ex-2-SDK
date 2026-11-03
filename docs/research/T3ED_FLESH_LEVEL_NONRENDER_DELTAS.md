# T3Ed source-to-cooked Level data: non-render region audit

**Research status:** read-only comparison of the user's original 2026-11-03
T3Ed archive. No T3Ed process launched, no custom map cooked, and no source
or runtime map was modified or committed. This note describes *opaque binary
differences*, not decoded collision, Havok, PVS, pathing, or lightmaps.

## Why this matters

The preceding original-map audit showed all 16 valid packed Flesh BSP
render blocks were byte-identical across four stock tutorial UNR/GMP pairs.
This investigation brackets those stable render-block bytes and compares
**everything between them and immediately around them**, without assuming
unknown bytes are a particular native subsystem.

The existing `research/t3ed/compare_editor_cooked.py` now additionally
emits `level_nonrender_regions` as a source-only, JSON metadata object.
It aligns only by **ordered byte-identical rendered BSP hashes**, preserving
exact source/cooked Level-relative offsets. If there are no validated
blocks, or if any block hash/order differs, the tool returns an
unavailable status instead of guessing the alignment.

## Verified original stock tutorial corpus

| Pair | Front region source / cooked | Front net delta | Three internal gaps | Tail source / cooked | Tail net delta | Tail common prefix |
|---|---:|---:|---|---:|---:|---:|
| Tutorial2 | 6,820 / 6,829 | +9 bytes | 4 bytes each, identical | 11,530 / 14,999 | +3,469 bytes | 11,508 bytes |
| Tutorial3 | 6,822 / 6,831 | +9 bytes | 4 bytes each, identical | 11,530 / 14,999 | +3,469 bytes | 11,508 bytes |
| Tutorial4 | 6,824 / 6,833 | +9 bytes | 4 bytes each, identical | 11,530 / 14,999 | +3,469 bytes | 11,508 bytes |
| Tutorial5 | 6,843 / 6,849 | +6 bytes | 4 bytes each, identical | 11,530 / 14,999 | +3,469 bytes | 11,508 bytes |

For **all four** pairs:
- Four validated render-block spans match byte-for-byte *in the same
  order* and have identical lengths (1,911, 3,923, 2,339, 5,079 bytes).
- The inter-render gaps are themselves the same four bytes in each
  corresponding source/cooked map.
- In the post-render region, the first **11,508 bytes** are identical,
  while the remaining **22 source bytes** differ from the final
  **3,491 cooked bytes**.
- The post-render 3,491-byte cooked divergent byte region has exactly
  the same SHA-256 in every pair:
  `ddbea2519b196f7201c649f48c5fbd439112199c9cf745f48af9e8bcfbbff8c6`.

**Interpretation boundary:** this is direct evidence of a common
source-to-cooked **trailer/layout delta** in these four closely related
stock tutorial samples. The four maps appear to share their built
render geometry and much of the Level payload, so their common
trailer fingerprint is unsurprising; it does *not* prove the presence
or function of a universal game collision/PVS/lightmap payload or
that copying this tail would produce a valid new level.

The before-first-render difference begins after a 22-byte common
prefix in every pair. Its internal fields remain **unclassified**.
Package-level absolute file offsets differ and should not be mistaken
for Level-relative spans.

## How to reproduce without changing original files

~~~powershell
python research/t3ed/compare_editor_cooked.py corpus "C:\T3ED\content\T3\Maps" --report "C:\DX2EdResearch\t3_levels.json"
~~~

The new JSON contains:
- explicit alignment status and source/cooked interval start/end offsets;
- region lengths, net cooked growth, and whether the entire region
  is byte-identical;
- length of the exact common prefix within each aligned interval;
- SHA-256 of each side's remaining divergent suffix, with **no raw
  game payloads** included.

The tool refuses to write JSON in the retail map directory or
overwrite an existing report. Directly comparing changed/reordered
render geometry correctly disables interval alignment, preserving
the distinction between a changed BSP topology and changes around it.

## Next experiments (separate from this PR)

1. A disposable Windows build using T3Ed on an *edited copy* of
   Tutorial3.unr; record freshly generated output and editor logs.
2. Compare the fresh Level interval topology and hashes against this
   four-map baseline. If only the non-render tail changes, isolate
   which native builder step added it, rather than naming it from
   its size alone.
3. Repeat on a complex original level whose source and cooked files
   are both available, to determine which intervals are invariant
   and which are map-dependent.
4. Only after confirming source-authoring and native tool behavior,
   investigate DX2 writer compatibility, collision and lighting
   in isolated disposable copies. Never patch licensee numbers to
   claim equivalent native serialization.

## Asset-free validation

The existing Godot/SDK source-test workflows run synthetic Python
regressions for exact ordered-block matching, source and cooked
prefix/suffix deltas, unchanged inter-block gaps, render-block
mismatch refusal, and no source byte inclusion. The tests need no
user-owned binaries or native Windows execution.
