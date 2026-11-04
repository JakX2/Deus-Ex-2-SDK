# DX2 Level: independent transverse segment crossings versus MOPP candidates

**Research PR #41**, stacked on PR #40's original Level point-geometry oracle. This is a read-only line-segment/triangle intersection study, NOT Havok raycasting, full MOPP ray traversal, a physics contact, or a game-compatible collision writer.

## How the independent geometry oracle works

The new module research/dx2/inspect_mopp_segment_geometry_oracle.py extends the geometry-only PR #40 BVH:

1. Accept a finite, nonzero-length segment in original Level XYZ, not Godot preview coordinates.
2. Traverse source triangle AABBs with a **finite segment slab test**.
3. For each nonparallel triangle, compute original geometric plane crossing and require its finite segment parameter t to lie within [0,1].
4. Verify the point with the independently implemented projected barycentric predicate from PR #40, preserving original source triangle IDs and winding.
5. Return every transverse hit in segment order, including multiple surfaces and reversed-winding duplicate faces at the same point.
6. Report parallel or near-parallel source faces separately. **Coplanar segment overlaps are not supported**, and are outside the zero-miss claim.
7. At each independently located hit, test both PR #38/#39 MOPP **POINT candidate** modes and require them to retain **every triangle geometrically containing that point**.

MOPP is NOT being asked to traverse a ray or line. It is queried for point candidates only at independently computed geometric crossings. The geometric plane tolerance is 1e-5 Level units, barycentric tolerance is 1e-8, and MOPP uses an empirical one-unit quantization comparison tolerance.

## Private owner-owned 19-map byte experiments (2026-11-04)

The original Seattle GMP archive was read immutably. Each source's SHA-256, flattened f32 geometry count, MOPP code length and omitted zero-area triangle count were checked against previously recorded independently verified PR #30 and PR #36 evidence. No commercial source bytes were committed.

For each of the 43,152 nondegenerate MOPP-linked source triangles, the audit constructs a finite segment along its unit geometric normal through the **asymmetric interior barycentric point (0.2, 0.3, 0.5)**.

| Per 19 original maps | Half-length 0.1 | Half-length 2.0 |
|---|---:|---:|
| Source triangle segments tested | 43,152 | 43,152 |
| Independently found transverse crossings | **43,423** | **44,719** |
| Segments encountering multiple triangle crossings | 181 | 1,244 |
| Conservative mode MOPP point comparisons | 43,423 | 44,719 |
| Experimental derived diagonal mode point comparisons | 43,423 | 44,719 |
| Candidate queries missing a geometrically valid source triangle ID | **0** | **0** |

**Totals: 86,304 finite segments, 88,142 transverse triangle crossing events, 176,284 candidate-set comparisons, zero observed missing geometric hits.**

These are geometry-derived finite segments, not arbitrary-world ray samples or swept shapes. The zero-miss statement covers transverse hit events only, not parallel/coplanar segments, runtime Havok contact or every point on those paths.

## Off-surface endpoint negative control

The original short-segment corpus also checked source geometry at both endpoints:

- 86,304 endpoints checked.
- **86,283** endpoints had no geometric triangle contact under the declared tolerances.
- Among these no-contact endpoints, the conservative MOPP point interpreter returned at least one candidate at **85,561** positions.
- The experimental derived-diagonal interpreter returned at least one candidate at **85,488** of the no-contact endpoints.

Thus a nonempty MOPP candidate list is plainly NOT a real collision contact. MOPP point candidate generation and exact geometric narrowphase remain separate tasks.

## Synthetic counterexamples, original-fixture tests and safeguards

Fourteen new geometry-only fixture tests cover two distinct planes, reversed direction, duplicate/reversed-winding overlapping triangles, shared edges, crossings hidden from endpoint-only tests, triangle endpoints, disjoint segments, intentionally unsupported coplanar overlap, invalid coordinates, source immutable geometry and an actually pruned overlapping triangle behind the synthetic PR #37 fixed X=128 split.

Eight further asset-free original Level/Flesh/MOPP fixture tests exercise read-only original-source triangle IDs, degenerate nonleaf omissions, the synthetic MOPP tree's spatial false negatives, source immutability, fixture striding, invalid input bounds and duplicate or missing GMP rejection.

**22 new tests passed locally** prior to the GitHub CI check. No retail data are included in CI. Tests do not claim a successful Havok runtime call or game-compatible MOPP regeneration.

Run:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_segment_geometry_oracle.py" -v
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_transverse_segment_audit.py" -v
~~~

Original owner-supplied retail map:

~~~powershell
python research/dx2/audit_mopp_transverse_segments.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --half-length 2.0 --report "C:\DX2Research\transverse_segments.json"
~~~

A fresh JSON report must be created outside original game Maps. The audit refuses overwrites and never writes back to source GMPs or IBDs.

## Next research gate

- Implement and test geometric coplanar segment overlap handling.
- Derive safe candidate sets for **entire** rays/segments and swept AABBs rather than querying individual intersection points known in advance.
- Compare these algorithms against a legally available compatible Havok query runtime.
- Only after that, investigate native shape/material serialization, geometry compiler and actual DX2 Level write support.

A source-verified geometry oracle is necessary test instrumentation; it is not a playable collision compiler.
