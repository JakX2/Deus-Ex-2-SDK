# DX2SDK: translating AABB versus original Level triangles and MOPP candidates

**Research-only follow-up to PR #43.** This adds independent continuous swept-axis-aligned-box intersection testing to original source-authenticated Level triangles. It also adds source-MOPP *point-branch candidate overapproximation* expanded by the box extents. This is **not a Havok shape sweep, DX2 collision compiler, or native GMP writer**.

## Independent continuous collision-geometry oracle

Source module: research/dx2/inspect_mopp_swept_aabb.py.

A translating, nonrotating AABB versus an original Level triangle is tested with continuous separating-axis geometry. The test intersects normalized time intervals in [0,1] for all **13 axis families**:

- Three original world-space AABB axes
- One original triangle geometric normal
- Nine triangle-edge cross world-axis products

The moving center's projection varies linearly in time; the projected box radius is the sum of half-extents times absolute axis components. A collision requires overlap across *all* axes at a common time. Original triangle IDs and repeated/reversed-winding surfaces remain distinct. Degenerate nonleaf triangles stay omitted. A box-expanded geometry BVH reduces triangle testing, but the SAT predicate independently filters bounding-box false positives.

The experiment uses f64 geometric computation with an explicit 1e-7 original-Level-coordinate-unit projection tolerance. This is **not** an authenticated Havok collision margin. Stationary boxes and initially overlapping boxes can be tested. No box rotation, capsule, dynamic convex hull or contact response is implemented.

## MOPP branch candidates for the full moving box

A separate source-bytecode walker derives candidate original triangle IDs without consulting the geometric SAT results:

1. Convert both moving-box center endpoints and nonnegative XYZ half-extents into original MOPP quantized space.
2. Propagate center coordinates and box extents through observed MOPP rescale instructions.
3. Explore an axis branch if any interpolated point in the whole moving AABB could satisfy its condition.
4. Default mode stays **conservative** and explores all unknown diagonal branches both ways.
5. Experimental derived-diagonal mode checks the PR #39 projection hypothesis at eight AABB corners at *each* endpoint. Unknown opcode 0x1b still takes both branches.
6. Validate each resulting triangle ID against the independently traced source MOPP leaf set.

This produces a deliberately enlarged broadphase candidate list under current source-MOPP opcode hypotheses. **It is not the game's shape query**. The synthetic negative control proves that a structurally valid PR #37 tree can still omit a real moving-box intersection when its spatial split is wrong.

## Private original 19-map audit, 2026-11-04

All owner-provided original Seattle GMP source bytes were read without modification and their SHA-256, original Level geometry and MOPP bytecode spans checked against prior PR #30/#36 private source research. No original map bytes or vertex coordinates are included in GitHub.

The test box's XYZ half-extents were **(0.2, 0.2, 0.3)** in original Level coordinates. Each map contributed 128 independent off-surface random-bounds finite segments plus 128 independently randomized triangle-aimed segments. Fixed seed 20261104 was mixed with the full original GMP SHA for the private audit. The committed CLI mixes the same seed with the authenticated Level SHA, so it reproduces the methodology, though not identical random endpoints.

| Original source experiment | Total |
|---|---:|
| Random-bounds moving-box sweeps | **2,432** |
| Separate triangle-aimed moving-box sweeps | **2,432** |
| Random sweeps with a genuine geometric triangle contact | **846** |
| Aimed sweeps with a geometric triangle contact | **2,432** |
| Source-triangle hit occurrences, random + aimed | **2,665 + 4,913 = 7,578** |
| Full-swept-box MOPP candidate-set comparisons, both modes | **9,728** |
| MOPP candidate queries omitting a geometrically hit source triangle | **0** |

The broadphase returns numerous extra candidates. Across random sweeps, conservative mode yielded 509,274 candidate triangle IDs and the experimental mode 362,260, versus 2,665 geometric triangle IDs. Exact narrowphase is essential.

This is a finite empirical source-consistency experiment. It **does not prove soundness for all sweeps, Havok runtime compatibility, exact Havok integer rounding or game acceptance of generated MOPP data**.

## Tests and reproduction

Files:
- research/dx2/inspect_mopp_swept_aabb.py: independent 13-axis geometry and MOPP moving-box branch expansion
- research/dx2/audit_mopp_swept_aabb.py: read-only user-GMP source audit and exclusive sanitized JSON report
- native_editor/tests/test_dx2_mopp_swept_aabb.py: **19** new synthetic geometry and MOPP tests
- native_editor/tests/test_dx2_mopp_swept_aabb_audit.py: **6** source-Level fixture integration tests

Fixture-only tests:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_swept_aabb*.py" -v
~~~

Owner-supplied original GMP (report must be a *new file* outside the source Maps folder):

~~~powershell
python research/dx2/audit_mopp_swept_aabb.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --bbox-random 128 --triangle-aimed 128 --half-extents 0.2 0.2 0.3 --seed 20261104 --report "C:\DX2Research\swept_aabb.json"
~~~

The CLI never overwrites source GMP/IBD or an existing JSON report.

## Additional box-scale sensitivity checks

Two smaller read-only owner-map audits used the same deterministic sampler but **64 independent-bounds and 64 aimed segments per map**, rather than 128+128 in the baseline. The fixed random seed and original-GMP-SHA mixing were held constant. The first 64 samples are a prefix of the baseline 128 for each stratum, so the three experiments are **not statistically independent samples**; only the moving shape dimensions differ.

| Moving AABB half-extents in original Level XYZ | Sweeps across 19 maps | Independently hit source triangle IDs | MOPP candidate comparisons (both modes) | Missed geometry comparisons |
|---|---:|---:|---:|---:|
| Tiny: (0.02, 0.02, 0.02) | 2,432 | 2,930 | 4,864 | 0 |
| Baseline: (0.2, 0.2, 0.3) | 4,864 | 7,578 | 9,728 | 0 |
| Large: (1.0, 1.0, 1.5) | 2,432 | 7,334 | 4,864 | 0 |
| **Aggregate test invocations** | **9,728** | **17,842** | **19,456** | **0** |

The larger AABB naturally hits more geometry per path. This checks that the box-extent expansion survives changes of scale, not that the box sizes reflect an actual DX2 player or NPC collision body. A future validation should vary sweep direction, scale, offset, tangent configurations, and seed independently.

## Unresolved gates

- Repeat with different size scales, long paths, grazing/tangent cases and independent randomized SAT oracles.
- Verify the Havok runtime's actual shape types, transforms, broadphase expansions, surface filtering and contact threshold.
- Derive exact integer quantization/diagonal behavior rather than rely on the documented research hypotheses.
- Extend geometry-only testing to capsules and/or other convex shapes; do not confuse their shape parameters with AABB extents.
- Build a disposable MOPP/shape runtime test before claiming any native collision compilation or DX2 game-compatible writer.

Research stays completely isolated from DX2Ed native Save As.
