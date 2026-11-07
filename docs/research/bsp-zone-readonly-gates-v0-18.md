# BSP leaf/zone inspection: v0.18 read-only gate plan

Status: research only. Based on the source-only v0.17 SDK branch and its documented writer boundary; **not** a claim that DX2's proprietary native BSP/zone layout is understood.

## Source-verified baseline

- The public SDK currently reads original GMPs and source-hash-bound actor caches; the v0.17 Actor Workbench exposes original native tagged properties and separates inspection from the narrowly authorized existing StaticMeshActor scalar writer (see `README.md`, `dx2sdk/__init__.py`, and draft PR #82).
- Existing 2–8 scalar edits require originally serialized unique, unindexed, top-level four-byte int32/float32 properties, SHA identity, independent replay and isolated Save As. A tag's appearance in a tree is **not** proof of write eligibility.
- The project's README explicitly states that BSP/collision rebuilding and arbitrary actor creation are unsupported. T3Ed is inspiration, not a proven DX2-compatible compiler.

## Proposed minimal next milestone (read-only, opt-in)

Introduce a **separate experimental** BSP/zone observation report only after the native source parser identifies an independently bounded section from a verified package/export envelope. Do not infer a zone count or leaf topology from unrelated actor tags or from a Thief/T3Ed layout.

Each observed record should retain: source GMP SHA-256, package/export identity, byte range, byte length, parser evidence identifier, confidence status (`verified-envelope` versus `unknown-payload`), and an explicit `writable: false`. Expose raw bytes only as opt-in bounded hexadecimal previews, never as game assets in artifacts.

## Fail-closed acceptance gates

1. Reject negative, overlapping, out-of-file, integer-overflowing or unbounded offsets/lengths before any read.
2. Reject ambiguous package/export ownership; unknown native kinds remain opaque and cannot be called leaves, portals, planes or zones.
3. Preserve source SHA and package/export identifiers on every report; reject mismatched source and cache.
4. Enforce a small explicit preview limit, deterministic ordering, no recursive pointer following and no file writes.
5. Separate structural observations from hypotheses; a plausible integer or adjacency does not establish BSP topology.
6. Add invented synthetic fixtures for valid bounded envelope, zero-length record, truncation, overlap, huge count, wrong export, SHA drift, unknown type and deterministic output.
7. CI should assert no output GMP/IBD/GameSys files, no proprietary fixture bytes and no accidental widening of scalar-write permissions.

## Unresolved source evidence

Before implementing a leaf/zone decoder, identify in checked-in parser source the exact DX2-native section boundary and its owner, and document whether the suspected layout is supported by multiple independent structural constraints. Cross-licensee T3Ed similarities are hypotheses only. Until then, a generic opaque-span report is the maximum safe feature.

## Explicit non-goals

No leaf/zone editing, CSG, BSP rebuilding, portal generation, collision baking, runtime acceptance assertion, T3Ed binary substitution, or retail-data publishing. This plan changes **zero** serialization paths and is intended to be reviewed before implementing a parser.
