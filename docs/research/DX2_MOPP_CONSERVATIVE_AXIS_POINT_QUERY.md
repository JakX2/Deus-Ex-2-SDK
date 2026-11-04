# DX2SDK: conservative MOPP point candidates from source geometry

**Status:** experimental, read-only, incomplete Havok spatial semantics. Stacked on synthetic opcode graph PR #37 and original byte-exact disassembler PR #36.

This is the first DX2SDK prototype to apply spatial point coordinates to original MOPP bytecode rather than following both paths of every condition. It returns candidate triangle IDs for possible geometric narrowphase work. It is **not** Havok physics, an actual DX2 collision contact, a DX2 ray caster, or a functional Havok MOPP compiler.

## Independent research references

- Niftools [Havok MOPP data format](https://github.com/niftools/nifxml/wiki/Havok-MOPP-Data-format) documents filter/split opcodes, rescale and 24-bit integer coordinates with caveats about diagonal arithmetic and game-specific behavior.
- PyNifly [MOPP bytecode format](https://github.com/BadDogSkyrim/PyNifly/blob/main/docs/mopp_format.md) describes axis-aligned split/filter groups and original compiler research for Bethesda NIF collision.
- DX2-specific offsets, triangle IDs and spatial scale formula were recovered separately from 19 original user-owned maps in PRs #27, #28 and #36. The external descriptions give us a **testable hypothesis**, not proof of identical DX2 runtime query behavior.

## Experimental point-query behavior

1. Verify the original Level flattened geometry, MOPP envelope, triangle-leaf ownership and bytecode control flow using existing independent source-observed checks.
2. Quantize a source Level-space point: coordinate = (point - source_origin) * source_scale / 65536.
3. Apply source-observed axis filter opcodes 0x26..0x28 and interpret 0x29..0x2b as the documented 24-bit filters.
4. Evaluate axis splits 0x10..0x12, 0x20..0x22 and 0x23..0x25, preserving overlapping branch behavior.
5. Apply rescale opcodes 0x01..0x04 as coordinate = (coordinate - byte_operand) * (2 ** opcode).
6. Maintain output base across 0x09..0x0b and return only independently validated original triangle IDs from leaves 0x30..0x52.
7. **Do not guess diagonal projections:** every 0x13..0x1c split visits **both** child branches, a conservative superset relative to either unknown decision.
8. Allow an explicit **one quantization-unit tolerance** around comparisons, selected empirically. It is not a documented official Havok parameter or a guarantee for arbitrary queries.

Every query returns source triangle candidate IDs and diagnostics for opaque diagonal decisions, rescale operations, visited states and tolerance. No triangle intersection or physics response is computed.

## Private 19-map empirical audit

The implementation was first tested independently against the original user-owned Seattle GMPs, reading MOPP code, flattened f32 vertices and global triangle IDs from authenticated raw byte ranges. No original map changes or assets were committed.

**All nondegenerate original source triangle centroids:**

| Metric | Measured |
|---|---:|
| Maps | 19 |
| MOPP-linked nondegenerate triangles | 43,152 |
| Original triangle centroid queries | **43,152** |
| Queries omitting their own source triangle ID | **0** |
| Average returned candidate triangle IDs per query | **2.7556** |
| Omitted zero-area nonleaf triangles | 2 |

All maps had zero centroid misses at one-unit tolerance. This does **not** establish zero false negatives for arbitrary points, rays, swept shapes or actual Havok contacts.

A second independently sampled audit across all 19 maps found:

| Probe | Trials | Missing intended source triangle IDs |
|---|---:|---:|
| Centroid, zero tolerance | 4,326 | **378** |
| Centroid, one-unit tolerance | 4,326 | **0** |
| Barycentric interior point (0.3/0.2/0.5), one-unit | 4,326 | **0** |
| Sampled source-triangle corners, one-unit | 6,504 | **0** |

A zero-tolerance query is demonstrably too strict even for centroids, likely because of quantization and threshold rounding differences. The audit does not establish the exact source of these discrepancies.

**Negative control:** the synthetic opcode emitter from PR #37 is not a spatial builder. Two distant triangles along Z with both small X coordinates are assigned separate leaves behind a fixed X=128 split. The original symbolic graph decoder accepts their unique IDs, but the spatial prototype necessarily misses the second triangle. Synthetic tests codify this counterexample so future work cannot silently confuse opcode-graph validity with collision correctness.

## Run

Synthetic tests, no retail assets needed:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_conservative_axis_point_query.py" -v
~~~

Read-only retail audit, with a user-owned GMP:

~~~powershell
python research/dx2/inspect_mopp_axis_point_candidates.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --report "C:\DX2_Research\mopp_axis_centroids.json"
~~~

Zero --max-centroids means every source nondegenerate centroid; positive values limit probes in original triangle order. Use --tolerance-units 0 for strict-rule counterexamples. New reports are written exclusively outside original Maps folders; no GMP/IBD modifications.

## Blockers before functional native collision

- Confirm 24-bit filter and quantization rounding against a suitable Havok runtime or independent compatible implementation.
- Decode diagonal projections and integer overflow/shift behavior for all 0x13..0x1c branches; currently all diagonals are unpruned.
- Compare candidate sets with authentic Havok query outputs, not only self-triangle IDs at sampled centroids.
- Establish whether game collision queries use points, volumes or swept shapes, with proper broadphase expansion.
- Implement geometry-derived spatial branch thresholds. Fixed synthetic thresholds can demonstrably produce false negatives.
- Reconstruct native Havok shape serialization, physical materials, compiled BSP, CSG and game loading.

**No runtime Havok execution, playable collision data, game-file writes or physics-material schema is included.**
