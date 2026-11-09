# DX2Ed v0.45: MatLib stage-mask / slot correspondence audit

## User-facing workflow

Open Materials, import a user-owned IBD or Maps ZIP, and select Run
stage-mask / slot audit. The worker reads the already-generated private
catalog and reports:

- material count and exact/mismatching comparisons between
  stage_mask & 0x1ff and the bitset of non-empty ordered slot names;
- records with any stage-mask bits above the low nine;
- records with no named slots, nonzero masks without names, and named slots
  with a zero low-nine mask;
- per-slot counts of named and resolved references;
- per-slot texture usage_code frequencies and common raw reference names;
- the most common raw category IDs and flags;
- a small list of mismatching material examples.

The selected-material Inspector also displays its derived named-slot mask and
low-nine XOR. The comparison is explicitly marked as a candidate only.

## Evidence boundary

The source parser reads an observed MatLib record with nine ordered texture-name
strings and a separate 32-bit stage_mask. v0.45 tests one narrow hypothesis:
whether the low nine mask bits equal the presence/absence of the corresponding
non-empty slot strings across a user-supplied catalog.

An exact match is not proof that bit n enables shader slot n. A mismatch is
useful negative evidence. Bits above the low nine are preserved and counted,
not assigned guessed meanings. Texture usage_code values are counted by
ordered MatLib slot, but the existing human-readable usage labels remain
texture-resource parser labels, not verified shader-stage roles. Category IDs
and flags are displayed as raw numeric distributions only.

This audit does not infer blending, UV generation, animation, environment
mapping, normal-map behavior, shader execution order, or native BSP surface
indices. Authenticated source-surface binding and independently rendered
original output remain necessary to establish those semantics.

## Reliability and safety

- The worker accepts only a bounded, read-only catalog with a consistent
  material count and exactly nine ordered stage records per material.
- Stage masks, category IDs, flags and texture usage codes must be unsigned
  32-bit integers; booleans and malformed values are rejected.
- The report contains aggregate counts and bounded mismatch examples, not
  source file paths or original asset bytes.
- The audit does not write the catalog, IBD, Maps ZIP, GMP or any game file.
- The Materials importer now passes its Python worker script path explicitly
  to the launcher-verified interpreter; the same helper handles py -3.

## Regression coverage

Four new Python tests cover exact matches and per-slot usage counts,
mismatches and high bits, malformed masks/usage values, and read-only catalog
reporting without source paths. The real Godot 4.3 smoke invokes the worker's
--help and --audit-catalog modes through the launcher path, checks one
exact-match and one deliberate mismatch fixture, and verifies that the UI
does not claim shader semantics. No retail assets are included in CI.
