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

## Follow-up v0.19: bounded opaque-span observer (synthetic-only)

The independent source-only helper `research/dx2/opaque_source_spans.py`
now implements the **generic opaque envelope observation** part of this
plan. It accepts caller-supplied original bytes, exact SHA-256, ASCII
package identity, and explicit `{export, offset, length, evidence}`
records. It rejects bad source hashes, zero-length spans, negative
offsets, out-of-bounds lengths, overlapping ranges, duplicate evidence,
nonpositive or oversized exports, and more than 64 spans. Hex previews
are disabled by default and opt-in capped at 32 bytes per record.
Results are deterministically sorted by source offset, always marked
`unknown-payload`, `writable: false`, and
`native_bsp_leaf_zone_decoded: false`.

The file helper reads at most 128 MiB, verifies the source hash before
observing, and writes nothing. Synthetic tests in
`native_editor/tests/test_dx2sdk_opaque_source_spans.py` cover the
above fail-closed conditions and prove unchanged fixture bytes.

**Crucial trust boundary:** this API **does not authenticate the
caller-supplied envelope itself** or infer that a span belongs to any
specific export. The `evidence` field is an opaque caller-provided
identifier, **not independently validated provenance**. Until a
separate verified native parser supplies source-bound export ranges
and independent envelope proof, the helper is suitable for research
and synthetic fixtures only. It is not exposed as a retail GMP CLI
or native editor control, and its output must not be described as
decoded BSP leaf/zone records. No source-asset artifacts are emitted.


## Follow-up v0.20: caller-declared export containment negative controls

The experimental `observe_opaque_spans` and `observe_opaque_file` helpers
accept an optional `export_envelopes` iterable of
`{export, offset, length}` records. **These are caller declarations, not
native-parser-verified exports.** With this option, each observed span must
lie completely inside the sole declared envelope for its positive export
index. Envelopes must be nonempty, in bounds, unique by export, pairwise
nonoverlapping and capped at 64. A missing owner, boundary crossing,
duplicate export, ambiguous overlapping owner, or wrong export ID raises
`SpanEvidenceError` before any report is returned. An empty envelope list
cannot authorize nonempty spans. Existing default observations remain
backward compatible and do not require envelope input.

Reports explicitly distinguish
`caller_export_envelopes_checked: true/false` from
`export_envelopes_independently_verified: false` in **all** cases.
The additional check can reject internally inconsistent hypotheses; it
**cannot establish** real DX2 package ownership or leaf/zone identity.
The helper does not parse the GMP export table, does not infer BSP leaves,
does not write or generate game files, and remains outside the public
SDK and Godot UI. Synthetic regression tests include reversed envelope
order, cross-export records, holes, duplicate and overlapping envelopes,
invalid types, huge counts, source hash drift and unchanged input bytes.

**Next gate:** identify and independently validate actual package export
byte ranges in the checked-in native reader before permitting a
`verified-envelope` confidence label. Until then all observed payloads
remain `unknown-payload` and nonwritable.


## v0.20 follow-up: checked-in package reader evidence audit

Source inspected: `map_exporter/dx2inspect.py`, `Package.__init__`,
`Cursor.ci`, `Package.payload`, and `map_exporter/dx2scene.py::find_bsp`.
The package reader parses the Unreal header and export table, assigning
one-based export indices and reading each serialized export's compact-index
`size` and `offset`. It currently rejects negative lengths/offsets and
end positions beyond the loaded file. `Package.payload` slices the source
using these table-derived values. This is concrete source evidence for a
future export-envelope bridge, **not** an authenticated bridge today.

Additional independent checks required before trusting those ranges in the
opaque observer:

* Verify exact package format/version and table layout, including header,
  name/import/export table start/end boundaries. Reject overlapping or
  duplicate nonempty export payload ranges and payload/table collisions.
* Validate every compact-index and name/reference lookup before using the
  export table. The existing reader does not enforce all of these checks
  during construction and uses some direct list indexing.
* Reject zero-sized exports as observation owners. Ensure file identity is
  pinned to the same immutable bytes used for both table parsing and spans.
* Keep BSP render-block evidence separate from BSP **leaf/zone** evidence.
  `find_bsp` scans a Level export for validated *render geometry* records;
  it does not expose independently verified leaf/zone record layouts.
* Add invented synthetic package fixtures with malformed compact indices,
  out-of-range name refs, table/payload collisions, duplicate payload ranges,
  and zero-sized exports. No retail data should be committed.

**Decision:** no `export_envelopes_independently_verified: true` flag,
no implicit package-reader bridge, and no BSP leaf/zone decoder until the
above negative controls and source-format evidence exist. The present
opt-in caller envelopes remain explicitly untrusted.
