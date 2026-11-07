# v0.21: experimental DX2 package export table boundary audit

This is a **read-only, source-only research utility**, not an enabled BSP/zone decoder or a native editor writer. It adds `research/dx2/dx2_export_boundary_audit.py` alongside the existing caller-declared opaque span observer in draft PR #87.

## Concrete progression

`audit_dx2_export_boundaries(source: bytes, source_sha256=...)` performs a fail-closed structural pass over the known **candidate** UE package v95, Ion Storm licensee 68/69 table layout. It pins the exact immutable source bytes to lowercase SHA-256 before parsing. It checks:

- Package magic, version/licensee and one specific DX2-style header layout (including generation count and the name-table starting boundary).
- Bounded names, imports, exports and generation counts; bounded ANSI/UTF-16 serialized strings and canonical signed compact indices.
- Import name indexes, export name indexes and native object references against the header's table counts.
- Export offsets/lengths, including negative sizes, overflows, truncated payloads and zero-sized export exclusion.
- **Pairwise non-overlap** between header, name table, import table, export table and every nonempty candidate export payload. Candidate export rows are deterministic by original one-based export ID.

The returned `candidate_export_envelopes` is shaped like the optional `export_envelopes` input in `opaque_source_spans.py`, but that existing observer deliberately treats all such input as **unverified caller declarations**. Passing these candidates to it must **not** set `export_envelopes_independently_verified: true` or grant byte-writing permissions.

## Trust and compatibility boundary

The report explicitly sets `export_envelopes_independently_verified: false`, `native_bsp_leaf_zone_decoded: false`, `runtime_game_verified: false`, `writable: false`, and `source_original_modified: false`. Passing synthetic checks only confirms that the *hypothesized* export table is internally self-consistent under the strict layout. There is **no claim** that the restricted header layout accepts every retail map, that fields are BSP leaves/zone records, that a successful parse proves genuine export provenance, or that any data may be recooked.

Synthetic tests (`native_editor/tests/test_dx2sdk_export_boundary_audit.py`) cover valid invented data, source SHA drift, invalid package tags, version/licensee mismatch, name indexes, object references, table collisions, export overlap, truncated bytes, malformed compact indexes, name termination and zero-sized exports. The helper is not wired into the public SDK, packaged editor, original GMP writer or game loader. It writes **no** files and contains **no** proprietary assets.

## Next evidence gate

Cross-check against *private, user-owned* DX2 package headers and export bytes in a local-only read process, without committing the bytes or full reports. Compare the independent table model to the existing `map_exporter/dx2inspect.py::Package` output and Thief 3 reader behavior. Any parse rejection or mismatched table span must remain a hard stop. Only after that can we consider upgrading export evidence, and only after an independent native record format is established can a BSP/zone observer label records as leaves or zones. No edits or retail compatibility claims at this stage.

## Follow-up hardening: empty name records

The experimental name-table reader now rejects a zero compact-index name length before consuming flags or advancing to subsequent records. A zero-byte name is not a valid terminated ANSI or UTF-16 name under this restricted candidate layout; accepting it would make table interpretation ambiguous. A synthetic fixture mutates the first name-length byte to zero and asserts fail-closed rejection. This remains a structural negative control, not proof of DX2 retail-format compatibility or independently authenticated export ownership.
