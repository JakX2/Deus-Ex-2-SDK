# v0.24: source-native package symbol identity concordance

Status: **research-only, read-only, unmerged draft**. This extends the
three-reader DX2/Thief3 structural check from v0.23, without changing
the SDK actor writer, Godot scene, map files, or any existing native
serializer.

## Motivation

Agreement on an export's byte offset and serialized size is not enough
for an editor. Two parsers can agree that export 17 occupies a certain
range while disagreeing about **which native class/name/outer object
the range belongs to**. Building an actor property browser on that
unverified identity could mislabel an object even without rewriting it.

The checked-in DX2 reader is `map_exporter/dx2inspect.py::Package`.
The independently implemented Thief 3 reference is
`third_party/t3sdk_assets/upkg.py::Package`.
The strict synthetic-tested UE95 table auditor remains
`research/dx2/dx2_export_boundary_audit.py`.

## Added evidence checks

`research/dx2/thief3_export_concordance.py::compare_thief_reference`
continues to compare all three interpretations of **the exact same,
lowercase-SHA-256-pinned immutable bytes**. After the existing
source version/licensee, table count, header/table start and end,
and serialized export offsets/lengths checks, it now also compares:

- Every decoded original name entry, case-sensitively and in source order.
- Every import's class-package name, class name, outer/package reference
  and original object name.
- Every export's original object name, class reference, superclass
  reference, outer/package reference and object flags, in original
  export-table order.
- Integer and string runtime types for these fields, rejecting
  booleans misrepresented as integers and missing values rather than
  relying on Python truthiness.

The two readers use different names for some fields. The comparison
maps DX2 import `outer` to Thief3 `package`,
DX2 import `class` to Thief3 `class_name`,
DX2 export `super` to Thief3 `super_ref`,
and DX2 export `outer` to Thief3 `package`.
It preserves the previous zero-based Thief3 export-ID to one-based
DX2 export-ID check. No records are renamed or rewritten.

A successful report now includes `package_symbol_tables_concordant`
and numeric `matched_name_records`,
`matched_import_records` and
`matched_export_identity_records` totals. The original
decoded strings, asset names, byte offsets, export payloads and file
paths are **not** emitted in the report.

## Synthetic negative controls

Existing tests in
`native_editor/tests/test_dx2sdk_thief3_export_concordance.py`
now inject deliberate disagreements into both the DX2 and Thief3
in-memory table models: missing/wrong names, import classes/packages
and outers, export names/classes/superclasses/outers/flags, and
incorrectly typed boolean flags. These corruptions retain unchanged
serialized export ranges; the symbol checks must reject them
independently of the already-tested range/overlap checks.

Use the existing local-only opt-in
`research/dx2/thief3_export_concordance.py` diagnostic
with an independently calculated SHA-256 as described in
`docs/research/dx2-thief3-reader-concordance-v0-23.md`.
No proprietary game files are included in public tests or commits.

## Explicit limits

This is **interpretation concordance, not proof of independently verified
DX2 export ownership**. The two readers share reverse-engineered
Unreal/Ion Storm naming and reference conventions. The report still
explicitly sets:

- `export_envelopes_independently_verified: false`
- `native_bsp_leaf_zone_decoded: false`
- `runtime_game_verified: false`
- `writable: false`
- `source_original_modified: false`

No native BSP/zone/portal parser, Light/actor creation, collision rebuild,
retail playtest, T3ED cook stage or general GameSys editing is implied.
Until private original-package audits confirm candidate formats and
independent record boundaries, keep native geometry editing blocked.
