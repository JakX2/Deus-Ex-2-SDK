# Source Level prefix triangle/edge graph

Immediately after the source-validated Level Model compact export reference,
19 Seattle maps contain a 30-byte zero header (one uses 31), a counted
triangle array, a counted edge array, one counted edge-reference list per
triangle, and one u32-pair owner record per edge. Remaining prefix bytes
before the native counted render block array are deliberately opaque.

Triangle record: u32 vertex count (3), nine f32 XYZ components, three
upward unit normal f32 components, one extra f32, one opaque byte (57 bytes).
Edge record: one opaque byte, six f32 endpoint components, eight opaque
bytes (33 bytes). The extra triangle float is commonly 146 or 160; it is
not the plane W coefficient and must not be translated as one.

Exploratory source verification across the 19 maps: 28,993 triangles,
86,979 triangle vertex records, 61,622 edges and 123,244 triangle edge
references. All edges have exactly two distinct triangle owners, and each
pair in the second owner table agrees exactly with the independent
triangle edge lists, at its original edge ordinal. All edge endpoints
are finite/bounded; 59,408 edges lie within .15 units of both owner planes
and 60,219 within .15 of at least one. Exact endpoint identity with triangle
corners is not required or generally observed. This is consistent with
a navigation-like graph with portal geometry, but runtime navigation
semantics are not yet authenticated. The remainder of the prefix and
the opaque fields are not decoded by this tool.

    python research/dx2/inspect_level_prefix_graph.py MAP.gmp

Use repository root, map_exporter, and research/dx2 on PYTHONPATH.
The parser is read-only, verifies byte-exact reassembly, rejects ambiguous
header width, and does not expose original graph coordinates in its
reports. No graph editing or regeneration, engine pathfinding, or
runtime geometry modification is claimed.
