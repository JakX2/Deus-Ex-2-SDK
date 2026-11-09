# DX2Ed v0.46: raw MatLib category/flags cohorts

## User-visible Materials workflow

After importing a user-owned IBD or Maps ZIP, the Materials workspace now
offers independent filters for the raw MatLib `category_id` and `flags`
fields. The selectors enumerate only values present in the loaded catalog,
sort them numerically, and display category IDs in decimal and flags in
zero-padded hexadecimal. The UI does not attach guessed enum labels or bit
meanings.

When a category/flags filter removes the currently selected material, the
browser clears the stale selection and Inspector preview rather than leaving
an invisible material as the active authoring target.

## Read-only cohort audit

The existing stage-mask / named-slot audit now also groups materials by the
raw pair `(category_id, flags)`. Each bounded cohort contains:

- material count;
- exact low-nine stage-mask / named-slot match count;
- mismatch count;
- records with high mask bits;
- up to four common low-nine raw mask patterns; and
- up to four common named-slot occupancy patterns.

Only the 24 most frequent cohorts are returned, with an explicit omitted
count. The report includes aggregate counts and raw numeric IDs only: no
material names, source paths, original bytes or asset payloads.

This is a useful way to see whether a candidate bit/slot relationship varies
between raw metadata families. It is **not** proof that category IDs or flag
bits have any particular engine meaning, and it does not decode shader stages,
blending, UV generation, animation or native surface indices.

## Regression coverage

The Python suite tests exact and mismatching cohorts, deterministic ordering,
raw values, omission of names/source paths, and the 24-cohort output bound.
The Godot 4.3 UI smoke loads three synthetic material records across two
category/flag pairs and checks category-only, flags-only, combined and reset
filters, stale-selection clearing, cohort display, and existing texture usage
filters. The same smoke is part of the Linux fixture job and bundled Windows
prototype self-test.

## Safety

- Original IBD and Maps ZIP inputs remain read-only.
- The private catalog and PNG preview cache remain separate from source files.
- No original MatLib, GMP, BSP, collision, lightmap, GameSys or TriggerScript
  writer is enabled.
- No retail runtime or shader-semantic compatibility is claimed.
