# DX2SDK: numerical capsule first-contact time and geometric normals

**Research-only PR #46**, stacked on PR #45's independent translating capsule geometry. First source-Level capsule experiment computing a **normalized first-contact time bracket and geometric normal estimate**. Isolated from DX2Ed native Save As, game runtime, Havok shape writer and collision compiler. All original GMP files remain read-only.

## Numerical first-contact and geometry oracle

The new research module research/dx2/inspect_mopp_capsule_first_contact.py receives original Level-space triangles, a fixed-axis translating capsule, spherical radius and start/end centers. The source triangle ID domain is never renumbered.

Each candidate triangle is tested against the closest point on the capsule's **centerline segment at normalized time t**, using a new 3D closest-feature routine: segment/segment edge proximity, triangle vertices, edges and face crossing. This routine returns closest axis and triangle XYZ points and a distance. It derives no geometry truth from the MOPP opcode decoder.

For a convex, stationary source triangle versus a fixed-orientation linearly translating convex capsule centerline, the squared closest distance is convex along the normalized motion parameter. A bounded golden-section search obtains a minimum, then bisection brackets the **earliest entry into the distance-tolerance-expanded contact region**:

    segment_triangle_distance(t) <= capsule_radius + 1e-7 original Level units

The output includes t_last_outside and t_first_inside, with a maximum **1e-8 normalized time-parameter bracket width** for non-initial contacts. These are research **tolerance-expanded** first-entry bounds, not exact Havok runtime times. Near-tangent, numerical-only and initial-overlap conditions are flagged.

When a unique nonzero separation exists, the normal points **from the closest triangle point to the nearest capsule-axis point**. Zero separation returns an unresolved normal (None). The algorithm does not guess a polygon normal for deep penetration or invent an authoritative game response at a triangle corner. No contact manifold, surface physics, actor collision filtering, penetration resolution, friction or character controller is computed.

## Synthetic regression evidence

The PR adds **20 asset-free pure geometry unit tests** and **7 synthetic source-Level audit tests**. Key checked cases:

- A sphere falling from Z=2 to Z=-2 onto a Z=0 floor with radius 0.25 has time t approximately **0.4375**; a vertical capsule with axis half-length 0.5 first reaches that floor at t approximately **0.3125**.
- Upward versus downward motion reverses the outward geometric normal; edge and corner contacts produce different normals than triangle-face orientation.
- Two stacked horizontal surfaces produce two correctly ordered times; zero-area source triangle ID omissions and duplicate reversed-winding surfaces preserve original IDs.
- Stationary and initially penetrating capsules explicitly start at t=0. Exact coincident closest points return no invented contact normal.
- A grazing motion is flagged; zero-radius contact, invalid numbers and unmodified source vertices are checked.
- The new closest-point distance matches the PR #45 independent scalar segment/triangle distance for 400 deterministic random tests; an additional 3,000 random local checks also found zero discrepancies at tested tolerance.
- The synthetic audit deliberately includes a spatially invalid but instruction-valid MOPP tree and confirms that its missed collision is reported, not treated as a passing native shape query.

## Private owner-provided 19-map original-byte audit, 2026-11-04

All original Seattle GMP source hashes, Level triangle IDs and MOPP envelope relationships had been verified in the existing DX2SDK research sequence. This audit reads original bytes without modification. No proprietary mesh coordinates, collision bytecode, sample XYZ or contact locations are added to the PR.

A fixed vertical capsule with radius **0.2**, axis half-length **0.5** Level units was tested with 16 random expanded-bounds off-surface segments and 16 randomized triangle-aimed off-surface segments per map. Original GMP SHA-256 was mixed into random seed 20261104.

| Original-map metric | Measured |
|---|---:|
| Original GMP maps | **19** |
| Swept capsule paths | **608** |
| Earlier independent PR #45 full-sweep triangle-hit occurrences | **1,028** |
| New first-contact solver triangle-hit occurrences | **1,028** |
| Missing or extra geometry IDs | **0** |
| Sweeps with a resolved first geometric contact normal | **406** |
| Sweeps initially within contact threshold | **11** |

A smaller preceding 114-sweep original-data pass also matched all earlier geometric hits. These are **offline geometry consistency experiments**, not actual Havok runtime tests.

The committed owner-map audit CLI uses the validated Level SHA for its deterministic seed instead of the private driver using the whole-GMP SHA. Thus the sampling methodology is reproduced but individual random samples need not match. Each original Level audit independently tests the new solver against old PR #45 complete-sweep geometry and checks conservative and experimental MOPP envelope candidates.

## Run

Asset-free tests:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_capsule_first_contact*.py" -v
~~~

Owner-supplied original GMP, read-only, output must be **new JSON outside original Maps folder**:

~~~powershell
python research/dx2/audit_mopp_capsule_first_contact.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --bbox-random 16 --triangle-aimed 16 --radius 0.2 --axis-half-length 0.5 --seed 20261104 --report "C:\DX2Research\capsule_toi_audit.json"
~~~

The report contains aggregate counts, normalized first-hit t summaries, and original triangle ID-only counterexamples, **never private mesh XYZ or point-normal vectors**. The source GMP/IBD is never patched or rewritten.

## Open gates before gameplay or native collision writing

1. Independent near-tangent/grazing and float32 source-scale tolerance validation.
2. Authentic Havok shape, material, collision mask, coordinate transform and controller behavior.
3. Optional source-collision **research preview** in DX2Ed, carefully distinguished from working game physics.
4. Contact manifold, sliding, penetration response, stairs and dynamic actor interactions.
5. Native MOPP generation and original DX2 Level/BSP/CSG compilation with disposable in-game testing.

Neither runtime Havok collision compatibility nor a game-writable collision compiler is claimed here.
