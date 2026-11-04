# DX2SDK: diagonal MOPP projection hypotheses inferred from original triangle paths

**Research only: corpus-supported hypotheses, NOT verified Havok runtime semantics.** Stacked on PR #38. The default point walker continues exploring both children of every diagonal split. Experimental pruning is strictly opt-in through --diagonal-mode derived_diagonals.

## Falsification before fitting

The community references at https://github.com/niftools/nifxml/wiki/Havok-MOPP-Data-format and https://github.com/BadDogSkyrim/PyNifly/blob/main/docs/mopp_format.md provide candidate diagonal expressions for Bethesda NIF Havok. Copying these unmodified into DX2 produces false negatives. For 1,805 centroid probes sampled every tenth triangle from the first six original GMPs, the one-unit tolerance results were:

| Branch policy | Missed intended original triangle | Mean candidate count |
|---|---:|---:|
| PR #38 always explore both diagonal children | 0 / 1,805 | 2.765 |
| Apply published 0x13-0x19 equations; explore 0x1a-0x1c both | **531 / 1,805** | 1.668 |
| Apply all published/guessed 0x13-0x1c equations | **609 / 1,805** | 1.538 |

Pruning more triangles while losing the correct target is a failure, not a speedup.

## Derivation from original paths

For each every-tenth original nondegenerate source triangle, the conservative PR #38 interpreter reaches its uniquely identified leaf. Every diagonal on that successful path imposes a one-sided inequality on the projection: for the left branch, projection < BB + 1; for the right branch, projection >= AA - 1. This yielded **15,197 constraints** from **4,326** original centroids in the complete private 19-map corpus.

| Opcode | Path constraints | Contradictions with starting published guess | Contradictions with inferred formula |
|---|---:|---:|---:|
| 0x14 | 2,169 | **1,382** | **0** |
| 0x1c | 486 | **185** | **0** |

The two different **empirical DX2 formulas** are:

- Opcode 0x14: 127 + (Y - Z)/2, rather than the published 127 + (Z - Y)/2.
- Opcode 0x1c: (508 + X - Y - Z)/3, rather than the prior guess (254 - X + Y + Z)/3.

X/Y/Z here denote the CURRENT quantized and rescaled query state, not raw DX2 map positions.

Other observed source-supported hypotheses, zero contradictions on these sampled paths within one-unit tolerance:

| Opcode | Projection hypothesis |
|---|---|
| 0x13 | (Y+Z)/2 |
| 0x15 | (X+Z)/2 |
| 0x16 | 127+(X-Z)/2 |
| 0x17 | (X+Y)/2 |
| 0x18 | 127+(X-Y)/2 |
| 0x19 | (X+Y+Z)/3 |
| 0x1a | (254+X+Y-Z)/3 |

Opcode **0x1b was not observed** on the original source target paths and is deliberately explored on both branches in the experimental mode. No formula for 0x1b is asserted.

## Holdout and interior/vertex probes

The formulas were derived on approximately 10% of the triangles (every tenth one). The next audit tested ALL nondegenerate original source triangle centroids across 19 maps, including the other 38,826 held-out centroids. Additional predetermined points tested interior barycentric positions and source-triangle corners:

| Original-source probe | Queries | Intended source triangle absent |
|---|---:|---:|
| All nondegenerate centroids | **43,152** | **0** |
| Every tenth triangle, (0.3/0.2/0.5) interior barycentric | **4,326** | **0** |
| Every twentieth triangle, vertex A | **2,168** | **0** |
| Every twentieth triangle, vertex B | **2,168** | **0** |
| Every twentieth triangle, vertex C | **2,168** | **0** |
| **Total** | **53,982** | **0** |

Mean centroid candidates fell from 2.7556 (conservative, both diagonals) to **2.2081** (experimental formulas), about a 20% reduction. Zero observed omissions for target triangles does NOT prove arbitrary-point, overlapping-triangle, swept-volume, ray or runtime Havok correctness. Vertex queries often return more candidates due to shared geometry.

## Implementation and safety

Research file research/dx2/inspect_mopp_axis_point_candidates.py adds a tested, separate projection function and opt-in diagonal_mode parameter; default remains conservative. The source-audit CLI gains --diagonal-mode. Results explicitly state that projected diagonal arithmetic is NOT Havok runtime-verified and that 0x1b continues its both-branch fallback.

Use fixture-only tests with no proprietary game data:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_diagonal_projection_hypotheses.py" -v
~~~

Run read-only audit against a user-owned map, writing a fresh JSON outside its Maps folder:

~~~powershell
python research/dx2/inspect_mopp_axis_point_candidates.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --diagonal-mode derived_diagonals --report "C:\DX2Research\diagonal_audit.json"
~~~

Neither mode edits game assets. No engine-verified contact generation, physical materials, original collision writer, or new spatial MOPP compiler exists yet.

## Remaining verification

Independent Havok spatial-query outputs; exact integer rounding and overflow rules; 0x1b handling; intersections at arbitrary points rather than known triangle probes; full shape/sweep queries; correct geometry-derived split thresholds. Keep derived diagonal pruning isolated from DX2Ed's native save and runtime integrations until those questions are answered.
