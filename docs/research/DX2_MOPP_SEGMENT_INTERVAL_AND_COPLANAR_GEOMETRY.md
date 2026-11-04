# DX2SDK: whole-segment MOPP interval candidates and coplanar geometry

Research-only PR #42, stacked on #41. This feature asks which original MOPP leaf triangles remain possible at ANY location along a finite segment, without precomputing where that segment hits geometry.

This is not Havok raycasting, contact generation, physics-material filtering, a collision compiler, or a native GMP writer.

## Two independent components

**Geometry-only coplanar overlap** traverses the source Level triangle BVH, checks both endpoints against the triangle plane (1e-5 source Level unit tolerance), projects to the triangle's dominant 2D plane and clips a continuous segment using barycentric inequalities (1e-8). It returns all source triangle IDs, entry/exit parameters and overlap spans, including shared edges, reversed-winding coincident faces, vertex tangencies and original ID gaps. Near-parallel off-plane contacts remain outside the confirmed contract.

**Whole-segment MOPP candidate traversal** transports the two endpoints together through each source-observed filter, rescale, split, jump and leaf instruction. It explores a branch whenever ANY point along the line could meet that branch's quantized coordinate condition. Branch intervals are deliberately not narrowed after traversal decisions, so extra source candidates are expected. This is an overapproximation under the tested opcode hypotheses, not an engine-authenticated Havok segment query.

The conservative default explores every diagonal split both ways. An explicit derived_diagonals research mode uses the PR #39 fitted DX2 diagonal projections at both endpoints, while never guessing the unobserved 0x1b opcode. Original MOPP code, source triangle IDs, f32 envelope and quantization margin are preserved through the existing independent validators.

**Negative control:** Both endpoint point queries can return no candidates while a segment passes through a filtered interior; the new interval query correctly retains that source leaf. Another test shows the structurally valid but spatially incorrect synthetic PR #37 tree can still omit a geometrically overlapping triangle. Source grammar validation alone cannot prove working collision.

## Private 19-map source-byte experiment

Every one of 43,152 original nondegenerate MOPP-linked triangles in 19 owner-provided Seattle GMP maps was sampled with two separate finite segments:

| Source segment | Segments | Independent geometric intersections | Missing source triangle queries in either candidate mode |
|---|---:|---:|---:|
| Coplanar along AB edge, extending 20 percent beyond both endpoints | 43,152 | 280,392 triangle-overlap events | **0** |
| Short source-normal transverse segment through asymmetric interior | 43,152 | 43,423 triangle crossing events | **0** |
| **Total** | **86,304** | **323,815** | **0** |

There were **172,608 full-segment MOPP candidate comparisons**, two modes per segment. Candidate volume demonstrates expected conservative overapproximation: 882,245 conservative and 763,381 experimental candidate IDs over the coplanar queries; 121,124 conservative and 94,280 experimental over transverse queries.

The geometric hits were found without using the MOPP interpreter. The finite segments were built from original source coordinates. Original source file SHA-256, vertex/triangle counts and MOPP code lengths matched earlier original-map research; the source GMPs were never written or committed.

These source-consistency results are not evidence of runtime Havok behavior, collision response, swept shapes, arbitrary world query correctness, new MOPP generation or game compatibility.

## Source and reproduction

- Research: research/dx2/inspect_mopp_segment_interval_candidates.py
- Read-only GMP audit: research/dx2/audit_mopp_segment_interval_coverage.py
- 20 source-free geometry/interval tests: native_editor/tests/test_dx2_mopp_segment_interval_candidates.py
- 7 source-free original-Level integration tests: native_editor/tests/test_dx2_mopp_segment_interval_coverage_audit.py

Run tests:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_segment_interval*.py" -v
~~~

Audit owner-provided DX2 map without modifying it:

~~~powershell
python research/dx2/audit_mopp_segment_interval_coverage.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --report "C:\DX2Research\segment_interval_audit.json"
~~~

Optional --stride 10 reduces samples, and --max-samples N caps them per map. Reports must be new JSON outside source Maps directories; inputs remain read-only.

## Unresolved

- Runtime-verified axis and diagonal branch arithmetic, quantization rounding and real Havok query extents
- Arbitrary-world segment and swept-volume coverage outside the finite sampled original geometry
- Near-parallel noncoplanar contact resolution, actual runtime collision response and physics materials
- Spatially correct MOPP cooking for changed meshes, native compiled BSP/CSG and writable native DX2 Level structures

This is strong geometric research instrumentation, NOT a gameplay-ready collision compiler.
