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
three additional header words have unassigned semantics. Leaf range
fields and the final leaf-ID array are preserved, not treated as visibility
sets.

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
verification. Integrated packaged corpus and translation tests pending.

    python research/dx2/inspect_level_spatial_vbsp.py MAP.gmp
    python research/dx2/inspect_level_spatial_vbsp.py MAP.gmp --delta .125 0 0

Run with repository root, map_exporter and research/dx2 on PYTHONPATH.
