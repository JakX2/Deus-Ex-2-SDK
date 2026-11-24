# Position dependency audit and rigid translation experiment

A preliminary private analysis of 19 Seattle GMPs finds:
* All 76,732 flattened vertices (230,196 XYZ components) match the exact
  float32 rule f32(render_component * f32(0.1905)), not merely a tolerance.
* All 3,002 packed block boxes and centers match their render vertices.
  Radius agrees with the AABB half diagonal within .002 source units.
* 2,478 shadow-bearing blocks contain 158,088 16-byte shadow vertices and
  632,352 u16 indices. Every three vertices form one indexed cap, with a
  fixed 12-index cap/side pattern and bounded side references.
* Every one of 52,696 caps has a unique render XYZ triangle when all corner
  candidates within .301 units are considered. Nearest-only matching fails
  for 50 caps. This is a geometric match, not an engine ownership field.
* All 17,743 Model nodes have zero bytes in the 16-byte spatial reserved
  region after the candidate sphere.

The new CLI checks those dependencies. With --delta it also constructs an
in-memory fixed-width candidate package translating expanded/packed XYZ,
packed boxes and centers, shadow XYZ, flattened vertices, Model plane W
and sphere centers, and the MOPP origin. Original UVs, normals, indices,
radius, quantization scale, MOPP code, actor data and opaque Level prefix
remain unchanged. Full package reparse, source crosswalk invariance and
exact byte restoration are mandatory. Sampled axis-only MOPP centroid
queries compare before/after candidate sets; unknown diagonal behavior is
not proven. The original map is never modified, and no candidate GMP
output is offered. Rounding may invalidate a translation; refusal is
expected if any independent gate fails.

    python research/dx2/inspect_world_position_dependencies.py MAP.gmp
    python research/dx2/inspect_world_position_dependencies.py MAP.gmp --delta .125 0 0

Run with root, map_exporter and research/dx2 on PYTHONPATH. Corpus
results are recorded below.
This is not a native BSP compiler, actor relocation or playable level
translation. The large opaque Level prefix remains an important blocker.

## Integrated 19-map corpus results

The source-only portable ZIP built from 4c0b961090f77b336baca87b67e70708d36a9609
passed the dependency audit on all 19 maps. In addition to the initial
counts above, every one of 52,696 shadow cap candidates resolves to a
unique original render triangle index locator. 358 shadow vertices have
multiple nearby XYZ candidates; a cap-level intersection resolves these.
The maximum nearest-render shadow vertex distance is 0.3001012671.

A fixed translation of +0.125 source units on X passed all structural,
reparse and reversal gates on 18 maps. One map was correctly rejected
because a previously degenerate collision triangle became nonzero-area
after float32 conversion. Its +0.125 Y and Z translations passed instead;
several X offsets were independently refused. No validation gate was relaxed.

One accepted experiment per map (18 X, one Y) then compared every original
reachable MOPP leaf triangle centroid, not just the default sample.
All 43,152 centroid candidate sets remained identical under the existing
conservative axis-only interpreter; no new centroid misses were observed.
MOPP bytecode and original leaf IDs remained identical. This does not
prove Havok runtime equivalence or correctness at every possible query
position. The original maps were not modified, and the in-memory
candidates were not saved or launched.

The 5,944,040 bytes of unchanged Level prefix (including actor list and
other header fields) are a blocker for whole-level translation. Follow-up
research identifies a navigation-like triangle/edge graph within that
prefix (see DX2_LEVEL_PREFIX_TRIANGLE_EDGE_GRAPH.md). This is why the
experiment does not produce a playable edited GMP.
