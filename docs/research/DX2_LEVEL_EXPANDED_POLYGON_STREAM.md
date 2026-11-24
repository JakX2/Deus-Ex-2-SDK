# Original Level expanded polygon stream

A source-observed polygon stream starts immediately after the final validated
packed Flesh render block. Each record is a little-endian u16 vertex count,
that many 92-byte vertices (23 f32 words), then a little-endian u32 material
name byte count and a printable ASCII NUL-terminated material name. XYZ is at
vertex +0, normal at +12, and primary UV at +24; later words remain preserved
but not assigned engine semantics. A zero-only region follows the stream,
ending at the independently validated 24-byte provenance header.

The record count is bounded by the independently decoded packed vertex
inventory. An exact decode/encode no-op and a complete one-to-one ordered
XYZ/material match with contiguous indexed triangle disks are required.
The indexed boundary must follow source vertex order; alternate
triangulations are preserved. Packed UVs may differ by a constant whole
texture-repeat offset per polygon; two f32 subtraction exceptions require
a tolerance of 1e-6. Quantized packed normals agree within 2/127.

Exploratory private measurements across the 19 Seattle maps:
16,789 polygon records, 76,732 vertices, 43,154 triangles, all exact ordered
XYZ/material associations and oriented indexed disks. 16,274 polygons have
exact primary UV agreement; all 16,789 have constant integer-repeat
agreement within tolerance. 15,043 use first-vertex fan triangle sets;
the others have a different valid indexed triangulation. The Model
node count is 17,743. Geometric count/center/radius/plane matching finds
14,857 polygons with one candidate node, 7 with multiple, 1,925 without
a candidate, and 14,849 bidirectionally unique associations. This is
not proof of native Model index ownership.

Run with the repository root, map_exporter and research/dx2 on PYTHONPATH:

    python research/dx2/inspect_level_expanded_polygons.py MAP.gmp

Use --include-private-polygons --report PRIVATE.json only for local source
research. No original map, geometry report, or retail assets belong in git.
Native Model vertex/surface arrays, BSP tree rebuild, Havok MOPP cooking
and retail runtime validity are still separate unsolved problems.

## Packaged corpus verification and counted block framing

The source-only SDK ZIP built from eaf6f11c8a72ee098a54aed660a6b278e277c8cc
passed the complete 19-map audit. The expanded records occupy 7,459,923
bytes and are followed by 900,019 zero bytes in aggregate. All 43,152
reachable original MOPP terminal triangles are attributed to an expanded
polygon; two original triangles are nonleaves. 16,787 polygons have all
of their triangles represented by MOPP leaves.

A separate framing probe showed that provenance field A indexes a native
u32-counted array of u32-length-prefixed render blocks. Empty entries are
exactly zero-length records, including leading and internal gaps. Across
the 19 maps, 3,106 native entries contain 3,002 nonempty blocks and 104
empty entries. All nonempty spans match the independent packed parser
exactly, and the array ends precisely at the expanded polygon stream.
The decoder now checks this counted framing as an additional source gate.
