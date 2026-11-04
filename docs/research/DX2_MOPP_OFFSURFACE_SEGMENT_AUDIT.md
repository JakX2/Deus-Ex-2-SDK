# DX2SDK: randomized off-surface segment coverage against original MOPP interval candidates

Research-only follow-up to PR #42. The question is now whether source-verified MOPP interval candidates retain *every independently computed triangle intersection* for segments whose endpoints do not lie on known triangles. This is a stricter distributional test than the source-normal and coplanar edge probes in PRs #40–42.

No native Havok runtime, genuine MOPP raycast or sweep, physical-material query, collision mesh compiler, native geometry writer or GMP modification is implemented.

## Two statistically distinct probe strata

1. **Unconditioned expanded-bounds segments**: choose two random points independently from the original triangle geometry AABB, expanded by 10 percent of its diagonal in every direction. Reject endpoints that the independent point geometry oracle identifies as lying on a source triangle. These lines are *not aimed at a chosen source face* and include a meaningful number of genuine no-contact cases.
2. **Randomized triangle-aimed off-surface segments**: choose a random original nondegenerate MOPP-linked triangle, a random interior barycentric target, and a randomized 3D direction that is transverse (normal incidence at least 0.3). Place both endpoints an equal, bounded distance outside its plane. This provides a collision-positive control even when the map has sparse geometry, but is **not** described as an entirely source-independent random ray.

The random number generator is deterministic, explicitly seeded and mixed with the authenticated source hash. Both endpoints are independently verified off source surfaces. The two strata are reported separately, including the number of no-contact cases. Private source Level XYZ is never written to result JSON.

## Geometry truth and candidate comparison

- Strict original DX2 GMP/Level/Flesh/MOPP provenance is validated before probing any original source map.
- The independent BVH in PR #40 provides all original triangle IDs geometrically hit at each point.
- PR #41 finds transverse crossings anywhere along a finite segment, including multi-surface events.
- PR #42 adds continuous coplanar overlap intervals. Results are combined with the full geometric set at each crossing or overlap.
- The source-authenticated interval interpreter from PR #42 computes candidates for the **whole segment without being supplied the hit positions**. Both conservative and opt-in experimentally derived diagonal modes are checked.
- Every candidate ID missing from the independent geometric truth is reported as a falsifiable failure, never counted as a success. The audit also tracks broadphase false positives and source-AABB parallel candidates.
- The geometry oracle's plane and barycentric tolerances, one-unit MOPP quantization margin and unknown near-parallel cases are research parameters, not game-authenticated Havok contact policy.

## Full 19-map owner-provided retail audit (2026-11-04)

The original privately supplied maps.zip was checked against existing SHA-256 and Level/MOPP byte-span evidence from the earlier source audits. The experiment produced:

| Per 19 original maps | Count |
|---|---:|
| Unconditioned expanded-bounds segments | **9,728** |
| Random-bounds segments intersecting one or more source triangles | **3,503** |
| Random-bounds segments with no geometric triangle intersection | **6,225** |
| Separate randomized triangle-aimed segments | **9,728** |
| Aimed segments geometrically intersecting their target | **9,728** |
| **Total finite off-surface segments** | **19,456** |
| All independently found geometric source triangle ID occurrences | **24,240** |
| Conservative plus opt-in derived MOPP interval comparisons | **38,912** |
| **Comparisons omitting one or more geometric original triangle IDs** | **0** |

Sampling used 512 unconditioned segments and 512 aimed segments per map, with original byte source hashes, PR #30/36 source-geometry/MOPP validation and deterministic seeded sampling. It was run locally against privately supplied original bytes, **not** inside public GitHub Actions. User-supplied proprietary original map streams remain uncommitted. The branch contains fixture tests only.

Long cross-map bounds segments return many false-positive broadphase candidates; nonempty candidate sets are not geometry contacts. The audit's two modes have *zero observed* omissions for this finite set, **not** proof of soundness for arbitrary origins, infinitely long rays, exact original Havok integer arithmetic, shape sweeps, or runtime contact response.

## Reproduction

No proprietary assets required for tests:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_offsurface_segment_audit.py" -v
~~~

Owner-supplied original DX2 GMP:

~~~powershell
python research/dx2/audit_mopp_offsurface_segments.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --bbox-random 512 --triangle-aimed 512 --seed 20261104 --report "C:\DX2Research\offsurface_audit.json"
~~~

The CLI uses full original-source validation, refuses duplicate GMP input, bounds the number of trials, rejects existing output and writes only a **new JSON outside the source Maps directories**. Original game assets are never modified. The program mixes the seed with the original Level hash; the separately executed private packed-byte corpus driver used the full original GMP hash when seeding its samples, so individual sample sequences differ despite the same public seed value. Both distributions and verification logic are identical.

## Synthetic counterexamples and remaining work

The **12 new fixture tests** distinguish random versus aimed sampling, assert all endpoints are off surfaces, check seeded determinism, detect multi-plane crossings and coincident/reversed-winding faces, prove a structurally valid but spatially wrong synthetic MOPP tree omits a real geometric hit, and refuse malformed inputs and duplicate source paths.

Remaining gates: independent native Havok query results, ray/segment integer quantization, near-parallel and tangent contact policies, swept AABB/capsule extent handling and ultimately geometry-derived MOPP tree construction. Keep this experiment out of production editor Save As and retail level-writing code.
