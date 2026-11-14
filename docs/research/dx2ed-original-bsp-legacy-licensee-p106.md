# DX2Ed Prototype P106: read-only BSP node access for UE95 licensees 65/67

## Problem P105 exposed

The new P105 Godot BSP node Inspector worked against 13 of the 19 original
Seattle maps supplied by the project owner. Their GMP source files were
original UE95 licensee versions 68 or 69. Six original maps were safely
refused because the **general DX2Map API intentionally allows only
licensees 68/69**, while older maps in the same retail corpus use
licensees 65 and 67.

This does **not** justify simply widening the general public SDK reader
or its experimental GMP actor writers. The older formats have separate
native fields and supported operations must be proven individually.

## Narrow read-only solution

P106 adds dx2sdk/bsp_legacy_licensee_readonly.py. When and only when the
standard DX2Map.open produces its **specific existing 68/69 allowlist
refusal**, the single-node dossier CLI invokes the older, previously
validated source-only **UE95 Level→World Model** research reader.

The fallback requires:
- An existing, regular original .gmp; strict 128 MiB source limit.
- An exact precomputed 64-hex input SHA-256; verified before parsing,
  against in-memory bytes, and after the source inspection.
- Original UE package version 95, with licensee **exactly 65 or 67**.
- A single independently parsed original Level, valid actor export list,
  native FURL and direct Level World Model reference.
- Independently source-verified first Model header, source-normalized
  first candidate plane and exact native Model export offset/length/hash.
- P105's original node inspector, requiring complete Model no-op byte
  identity, source-rooted BSP graph, zone-mask recurrence, all original
  node/zone framing, **19 contiguous node byte spans**, bounded selected
  node ordinal, and unchanged original raw compact field widths.

The result has the **same read-only JSON schema** as P105, so the Godot
Inspector handles both without rewriting the editor actor/brush paths.
Reports mark the older source licensee, the research adapter in use,
and explicitly say the general DX2Map *writer* licensee allowlist
**has not been expanded**.

A malformed GMP, different licensee, changed SHA, other SDK error,
out-of-bounds Model, corrupted node graph or zone table does **not**
trigger a generic unsafe fallback.

## Tests and boundaries

The new fixture-only Python tests verify both older licensees, existing
byte-exact Model framing, original absolute source offsets, false
BSP/collision write flags, wrong hashes, unsupported licensees, tampered
direct Model evidence and exact SDK allowlist-only CLI dispatch.

## Original Seattle corpus validation (owner-provided assets, local only)

I ran the exact packaged P106 CLI from the GitHub Actions portable
source-only ZIP against **all 19 original GMPs** supplied in the owner's
Seattle Maps ZIP, computing the SHA-256 of each source before and after.
All source GMPs were opened read-only; none were copied into GitHub or CI.

| Source GMP format | Maps | Dossier validation |
| --- | ---: | --- |
| Unreal package v95, licensee 68 | 12 | 12/12 passed |
| Unreal package v95, licensee 69 | 1 | 1/1 passed |
| Unreal package v95, licensee 67 | 3 | 3/3 passed (new research adapter) |
| Unreal package v95, licensee 65 | 3 | 3/3 passed (new research adapter) |
| **Total** | **19** | **19/19 passed** |

Across these maps the original World Model source readers validated
**17,743 original BSP node records and 688 candidate zone records**.
Every selected source node's exact Model record/no-op and complete
byte-span ledger passed; all native writer flags were false. All 19
original GMP SHA-256 fingerprints remained unchanged. A later test
with different node ordinals could add coverage of interactive
selection, though the full-model verifier already checks all native
node and zone framing for every map.

The six older maps were refused by the unchanged public DX2Map.open,
then accepted **only** through the standalone research path.
No general game-map writer allowlist was expanded.

Native BSP surfaces, actual vertex XYZ pools, materials/UV bindings,
Havok/MOPP collision, source GMP writes, and retail runtime behavior
remain **unknown or unsupported**.

This is read-only research and prototype milestone P106, not a
game-native BSP compiler or product 1.0.
