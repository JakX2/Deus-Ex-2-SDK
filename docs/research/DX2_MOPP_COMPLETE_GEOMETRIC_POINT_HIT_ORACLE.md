# DX2SDK: complete geometric point-hit oracle for original MOPP triangles

**Research PR #40**, stacked on PR #39. The old point-candidate checks asked only whether MOPP kept the *single source triangle that supplied the point*. This new independent geometric test instead asks **whether every triangle at that same point is among the candidate IDs**.

## Independent geometry truth

The module research/dx2/inspect_mopp_point_triangle_oracle.py constructs a deterministic CPU AABB BVH over original f32 Level triangles. Its geometry-only predicate:

- Verifies plane distance in original Level XYZ (declared 0.00001 source-coordinate-unit tolerance).
- Projects each nonzero-area triangle onto the two coordinates perpendicular to its dominant geometric normal.
- Uses orientation-based double-precision barycentric weights (declared 0.00000001 unitless tolerance), preserving original triangle winding and vertex indices.
- Returns ALL original triangle IDs at a point, including exact overlap, reversed-winding duplicates, crossing triangles, shared edges and vertices.
- Excludes only known zero-area, non-MOPP-leaf triangles and refuses unaccounted-for source IDs or degenerate MOPP leaf faces.
- Does not use or derive its truth from MOPP opcode/branch traversal, a Havok library or the editor's GLB picking geometry.

The audit tool research/dx2/audit_mopp_all_point_hits.py reads user-owned GMPs through the existing strictly validated DX2 Level/Flesh/MOPP chain, compares all geometric hits with candidate IDs from BOTH the conservative and opt-in derived diagonal modes, and reports missing original IDs. It does not embed source vertex positions in recorded counterexamples and does not write game assets.

## Positive synthetic counterexample

The PR #37 synthetic graph emitter can serialize a valid, source-grammar-compatible two-leaf tree behind a fixed X=128 split even if both distinct source triangles overlap entirely at X near zero. A point on the overlapping surface geometrically hits **original triangles 0 and 1**. That program returns only triangle 0, omitting triangle 1.

The new oracle correctly reports that omission and refuses to treat the valid opcode graph as working collision. This is an explicit regression test, not a retail-map problem, and it proves that self-triangle-only centroid checks were an incomplete oracle.

## Private raw-byte 19-map experiment (2026-11-04)

All 19 user-owned Seattle original GMPs were independently read as immutable bytes from the user-provided maps.zip. Native MOPP code/envelopes were located and cross-checked against prior PR #36 code lengths; f32 Level vertex records, globally indexed faces, zero padding and original source hashes were verified against PR #30 source counts/hashes. Nonzero-area leaf counts match the previously independent 19-map source audit, including the two zero-area omissions.

The original source bytes and their map files were never changed or uploaded into GitHub.

### First set of probes

| Point sampled in every relevant triangle | Point queries | Any geometrically valid triangle missing (both modes) |
|---|---:|---:|
| Centroid, every nondegenerate triangle | 43,152 | 0 |
| AB edge midpoint, every triangle | 43,152 | 0 |
| Vertex A, every tenth triangle | 4,326 | 0 |
| Vertex B, every tenth triangle | 4,326 | 0 |
| Vertex C, every tenth triangle | 4,326 | 0 |
| **Subtotal** | **99,282** | **0** |

### Additional holdout surface probes

| Point sampled in every source triangle | Point queries | Any geometrically valid triangle missing (both modes) |
|---|---:|---:|
| BC edge midpoint | 43,152 | 0 |
| CA edge midpoint | 43,152 | 0 |
| Interior barycentric position 0.23/0.37/0.40 | 43,152 | 0 |
| **Subtotal** | **129,456** | **0** |

**Total:** **228,738** geometrically tested points, **457,476** MOPP candidate-set comparisons (two diagonal modes per point), **0 observed queries that omitted a triangle geometrically containing the point**. The geometric oracle independently found many multiple-hit queries, including **143 source centroids and 42,759 AB-edge midpoint probes** contained in at least two original triangles. A total of 141,190 points across both audit runs had more than one geometric triangle hit. Keeping only the originating triangle would not have tested this property.

The two candidate-query modes remain source-correlated hypotheses, not actual Havok runtime output. A zero-miss finite sample does not establish correct treatment of arbitrary world points, swept shapes, ray paths, exact integer rounding, collision response or unobserved opcodes.

## Reproduce safely

Asset-free tests:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_point_triangle_oracle.py" -v
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_all_point_hit_audit.py" -v
~~~

Original user-owned GMP (not included in the repository):

~~~powershell
python research/dx2/audit_mopp_all_point_hits.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --report "C:\DX2Research\all_hit_audit.json"
~~~

The command checks every MOPP-linked triangle centroid and AB-edge midpoint, plus the three vertices of every tenth triangle. It validates both conservative and derived diagonal point walkers and refuses existing report paths or new JSON within the original game Maps folder. The input source is never modified.

## Remaining validity limits

- The predicate tests triangles *at point positions on the original source surface*. This is not an arbitrary-point or swept-shape completeness proof.
- The plane/barycentric tolerances are explicit geometric research tolerances, not verified native Havok contact thresholds.
- Real Havok MOPP queries may expand search extents or transform coordinates differently, and the observed empirical one-unit quantization tolerance is not necessarily a Havok runtime setting.
- Intersection truth is purely geometric and independent of collision response, material/filter ownership and the native BSP/world-model object domain.
- No full native collision compiler, physically correct source MOPP tree emitter, original world CSG compiler or in-game writable Level integration exists yet.

**Next validation gate:** independent off-triangle point/segment and swept-AABB tests, then contact-level comparison against a legally available compatible Havok implementation before any game-compatible writer claim.
