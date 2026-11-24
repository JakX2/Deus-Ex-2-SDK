# Level spatial grids and VBSP v2

The entire span between the independently validated triangle/edge graph
and native render block count is framed on the 19 original Seattle maps.
It contains a u32 version 1, u32 cell count, 92-byte grid records (i32 XY,
f32 XYZ origin, u32 layer count 1, u32 byte count 64, 64 data bytes),
a counted array of 24-byte position/direction records, then VBSP v2.

The grid origin is map-relative XY on a 192-source-unit lattice; point
records align to a 24-unit lattice and contain one of four diagonal XY
unit directions. Multiple records may share XY, so the grid is not a
single flat array. Grid byte semantics remain unknown.

The VBSP span starts with one opaque u32 followed by 22 u32 header words.
Magic is VBSP and version 2. Saved 32-bit pointer differences independently
validate the array boundaries. Never dereference these values. Serialized
arrays in order: 36-byte node, 52-byte leaf, 16-byte plane, 24-byte portal,
12-byte portal vertex, final u32 candidate leaf IDs. Two zero counts and
three additional header words have unassigned semantics. The final leaf-ID array is preserved, not treated as a visibility set.
The leaf range fields are independently identified below.

A node's first word is (plane index << 2) | child flags. Child bit set
means leaf index; clear means node index; -1 is a solid sentinel. Root is
node 0; all nodes except root and all leaves have exactly one incoming
reference. The plane equation is dot(N, X) + D = 0, with nonnegative side
selecting child 0. A signed portal plane reference indexes the plane
directly when nonnegative, and uses bitwise complement when negative.
Every portal's vertices agree with that plane, and centroid probes at
+/-0.1 units along the normal classify to the two recorded leaf IDs.

Exploratory private corpus measurements:
19 maps, 2,775 grids (2,165 distinct per-map XY cells), 177,600 grid
bytes, 1,777 directional points; 10,010 VBSP nodes, 3,106 leaves,
5,087 planes, 2,626 portals, 11,520 portal vertices, 688 final leaf IDs.
All 9,991 node and 3,106 leaf child references are valid, with 6,923
solid sentinels. All 2,626 portal side-pair tests agree. Only 2,912 of
3,106 leaf AABB centers classify to their own leaf, which is not a
failure: a bounding box center need not lie within the convex leaf.

The new CLI verifies source framing, exact decode/encode and geometric
portal checks. Optional --delta translates the known graph vertices and
edge endpoints, grid origins, directional point XYZ, leaf bounds, portal
XYZ and plane D in memory. All indices, normals, grid payload, saved
addresses, and unassigned fields stay unchanged. The original Level
span is recovered by exact byte reversal. No GMP output or runtime
verification. The packaged corpus and translation tests are recorded below.

    python research/dx2/inspect_level_spatial_vbsp.py MAP.gmp
    python research/dx2/inspect_level_spatial_vbsp.py MAP.gmp --delta .125 0 0

Run with repository root, map_exporter and research/dx2 on PYTHONPATH.

## Packaged validation and native leaf ownership

The portable ZIP from 1c0afc836ae461826c713f85f4d3e2270b709298 passed
all 19 original-map spatial audits and +0.125 X prefix-only translations.
All 5,252 portal side probes retained their original leaf pairs. The
experiment patched 237,594 position/plane spans (302,576 changed bytes)
with exact original reversal and no source changes. The post-Model
prefix span is fully framed: 4,788,774 graph bytes plus 1,107,204 spatial
tail bytes, including 809,028 VBSP bytes. Opaque record fields remain.

Independent original-map crosswalks resolve both leaf ranges:
the first is a half-open range in the actual expanded polygon stream,
the second is a half-open range of portals with this leaf as first owner.
All 3,106 second ranges agree exactly with the independent portal table.
The first ranges partition all 16,789 expanded polygon ordinals once;
all 76,732 polygon vertices lie within the corresponding leaf AABB.
The 3,106 leaf ordinals are also the original native render block
ordinals. All 43,154 flattened render triangle provenance field A values
agree with their owning leaf, including all 3,002 nonempty render leaves
and 104 empty leaves. 16,787 of 16,789 +0.1 normal-offset polygon
centroid probes also classify to the expected leaf; the two exceptions
are retained as diagnostics, not discarded or treated as source ownership
failures. Source range and provenance identity are stronger evidence.

The integrated position dependency CLI now offers
--include-spatial-prefix to translate the decoded post-Model prefix
together with the other known world geometry. It verifies original and
candidate native leaf ownership and unchanged portal side associations.
No actor positions or pre-Model prefix fields are edited. Full combined corpus verification passed as documented below.

## Combined source-corpus validation

The actual source-only ZIP built from a6fa08dc6b55e8e74305d619dd5620a831030b57
passed the leaf/render ownership audit on all 19 original Seattle maps.
The combined position dependency experiment with --include-spatial-prefix
then passed on every map (18 with +0.125 X and one with +0.125 Y to preserve
original collision triangle degeneracy). Full package reversal, source
reparse, 16,789 polygon leaf associations, 5,252 portal side probes and
all 43,152 conservative MOPP centroid candidate sets remained valid.
No original or translated centroid misses or changed candidate sets.
Across the accepted experiments, 237,594 decoded prefix position spans
were patched, 302,045 prefix bytes and 948,392 total package bytes changed.
Original hashes were unchanged. The post-Model prefix is fully framed;
48,062 aggregate pre-Model prefix bytes and actor exports remain unmodified.
Unassigned flags and saved pointer words remain preserved; no runtime
visibility, navigation, collision engine or playable level is verified.
