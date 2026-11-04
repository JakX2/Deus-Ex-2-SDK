# DX2SDK: fixed-axis translating capsule geometry versus MOPP candidate envelopes

**Research-only PR #45**, stacked on swept-AABB PR #44. A capsule here is a finite centerline segment held at a fixed orientation, thickened by a sphere of radius r, and translated along a finite trajectory. We do not know whether real Deus Ex: Invisible War Havok uses this exact collision shape, dimensions or contact policy.

## Independent geometric capsule oracle

The new module research/dx2/inspect_mopp_swept_capsule.py derives the **whole swept capsule geometry**, not point-sampling the path. Its centerline traces a parallelogram when moving transversely, or a segment if stationary/parallel to its own axis. The entire swept volume is the swept axis patch plus a radius-r ball (a Minkowski sum).

For each original nonzero-area Level triangle, the independent source geometry BVH rejects distant candidates. A separate f64 closest-distance algorithm then computes the minimum 3D distance between the original triangle and the swept axis patch. Noncollapsed parallelograms are split into two geometric triangles; triangle/triangle distances include segment-to-face and edge-to-edge closest-point calculations, face crossings, overlapping triangles and vertex cases. Collapsed patches use segment-to-triangle distance. Original triangle IDs, winding and zero-area nonleaf gaps are preserved. A geometric contact is reported when this distance is no greater than **radius + 1e-7 original Level units**.

This oracle does NOT solve time-of-impact, contact normal, friction, penetration response, stairs or sliding. The geometric tolerance is a declared research parameter, not Havok policy.

## Separately inferred MOPP candidate envelope

Candidate generation uses only the source-verified original MOPP code and source MOPP origin/scale. The entire moving capsule is bounded by a moving AABB with axis-specific half extents:

    AABB_half_extent[k] = sphere_radius + capsule_axis_half_length * abs(axis_unit[k])

PR #44's MOPP swept-AABB interpreter follows every source-observed axis branch that could pass any point inside this moving envelope. The default conservatively visits both sides of unverified diagonal branches; the derived diagonal projections are opt-in research hypotheses; the unobserved opcode 0x1b is always visited both ways.

The candidate list is intentionally a superset, never claimed to be Havok's own swept capsule query. A synthetic test proves the structurally valid but spatially incorrect PR #37 MOPP can still miss a genuine capsule contact.

## Private 19-map source-byte experiment (November 4, 2026)

The owner-provided original Seattle GMPs were read immutably. Source GMP SHA-256 hashes, flattened Level vertices/triangle IDs and MOPP envelopes were cross-validated against earlier PR #30/#36 source research. No proprietary original geometry, Level data or game MOPP bytecode was committed.

Test shape: fixed vertical axis (0,0,1), spherical radius **0.2 Level units**, centerline half-length **0.5 Level units**. Each of 19 maps supplied 32 independent expanded-bounds off-surface random segments and 32 separately triangle-aimed positive off-surface segments:

| Original-source experiment | Measured |
|---|---:|
| Random endpoint-pair capsule sweeps | 608 |
| Random sweeps producing genuine triangle contact | 216 |
| Separate triangle-aimed capsule sweeps | 608 |
| Random source triangle-hit ID occurrences | 715 |
| Aimed source triangle-hit ID occurrences | 1,278 |
| **Total capsule sweeps** | **1,216** |
| **Total independent original triangle hit IDs** | **1,993** |
| **Full-envelope MOPP candidate comparisons (both modes)** | **2,432** |
| **Comparisons omitting any geometrically hit original triangle** | **0** |

Every independent capsule hit was additionally a hit of the separately computed PR #44 swept-AABB SAT oracle using the capsule-enclosing box. That is a consistency check, not a game-runtime confirmation.

Broadphase efficiency remains an open challenge: the 608 random capsule sweeps produced 138,204 conservative MOPP candidates but only 715 actual geometric hit IDs. Shape-triangle narrowphase is essential to avoid reporting false contacts.

The private experiment mixed random seed 20261104 with the **original GMP SHA-256**. The reproducible owner-GMP audit command uses the same distribution but mixes the seed with the independently validated **Level SHA-256**. The sample paths are therefore not guaranteed to match, although the source verification, algorithms and experiment design are the same.

## Source files and reproduction

- research/dx2/inspect_mopp_swept_capsule.py: independent capsule patch/triangle closest-distance oracle and source MOPP box enclosure
- research/dx2/audit_mopp_swept_capsule.py: owner-supplied GMP read-only audit and JSON report, with independent swept AABB geometric containment check
- native_editor/tests/test_dx2_mopp_swept_capsule.py: **25** synthetic geometry/MOPP regression tests
- native_editor/tests/test_dx2_mopp_swept_capsule_audit.py: **6** synthetic original Level/Flesh/MOPP source-validation tests

Run without retail assets:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_swept_capsule*.py" -v
~~~

Run a read-only source-original-map audit:

~~~powershell
python research/dx2/audit_mopp_swept_capsule.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --bbox-random 32 --triangle-aimed 32 --radius 0.2 --axis-half-length 0.5 --axis 0 0 1 --seed 20261104 --report "C:\DX2Research\capsule_audit.json"
~~~

The report is a NEW JSON outside original Maps. The input retail GMP is never modified. No original retail map content is shipped with tests.

## Runtime and native SDK limitations

Still unverified: native Havok shape type/size, exact integer/diagonal MOPP semantics, shape filters/materials, contact normals/time of impact/response, authentic DX2 runtime collision and spatial tree generation for changed meshes. The current fixed-axis capsule does not rotate, and its enclosing AABB deliberately over-retains triangle candidates.

Next useful gates: an independent capsule-distance oracle to challenge near-tangencies, alternate capsule axes/size scales on original sources, and a disposable authentic Havok runtime test. **Do not wire this into DX2Ed native Save As or label it a native collision compiler yet.**
