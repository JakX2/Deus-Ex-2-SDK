# VBSP portal reconstruction and localized clipping

A portal can be reconstructed geometrically by intersecting its source
plane with the oriented splitting halfspaces of both source owner leaf
paths. Seed with a large square in a stable plane basis, then clip with
the halfspaces. A loop touching the seed boundary is refused as unbounded.
This is not proof of the complete original portal compiler.

An exploratory private test across 19 Seattle maps found 2,265 of 2,626
portal boundaries within .15 source units by bidirectional vertex-to-edge
distance, 88 empty results, and significant differences for other portals.
Adding leaf AABB clipping makes the result worse (1,789 matches), so
leaf boxes are not assumed to be the portal clipping domain. There are
11,520 original portal edges; 10,836 have one geometric oriented
owner-path supporting plane, 322 have multiple, and 362 have none.
Only 2,112 portals have unique source path candidates for all edges.
These are hypotheses about geometry, not explicit serialized edge IDs.

The new source-only CLI audits all portals and material polygon patches.
It requires original portal boundary/area agreement, convexity, no
significant source halfspace violation and unique candidate edge planes
before permitting a hypothetical reconstructed portal preview. It then
checks the new centroid probes against the modified tree. The same
offset can translate supporting material faces and clip existing material
patches against changed leaf halfspaces. A nonmatching original face,
ambiguous support, or invalid candidate is reported, not repaired.
Existing material patches are not extended, so exposed surfaces and
texture mapping still require a real CSG algorithm. No GMP output is available. An opt-in private preview geometry report
is described below; ordinary output remains aggregate counts only.

    python research/dx2/inspect_vbsp_local_clip.py MAP.gmp
    python research/dx2/inspect_vbsp_local_clip.py MAP.gmp --plane 0 --delta-d 1

Run with root, map_exporter and research/dx2 on PYTHONPATH.
Integrated original-map results are recorded below. No collision rebuild,
visibility compilation, native source mutation or runtime testing.

## Integrated private corpus results

The source-only SDK built from f2487f41e48b3732a380f8de8d854280dcc8541b
passed all 19 original maps and all four CI workflows. It found 2,265
matching portal boundaries/areas, 273 different and 88 empty results.
1,995 portals meet all conservative reconstruction gates. 2,576 source
portal loops satisfy the strict convex test; 18 have a path violation.
Of 16,789 source material patches, 16,124 pass the planar/convex test,
15,972 match the original after clipping, 126 clip to empty, 26 differ
and 665 are excluded as nonconvex/nonplanar.

One plane per map was selected deterministically among unique-support
planes with portal dependencies and fewer than 200 face dependencies
(where possible): minimize face + portal dependency count, then maximize
support count, then choose lowest original plane ordinal. A +1 D offset
affected 62 material patches and 40 portals. All 62 face previews passed
(20 supporting-face translations, 4 area reductions, 1 vertex count
change). 28 portal previews passed; 12 were refused by the original
source gate. No original maps or runtime data were changed.

## Private textured geometry previews

With a fresh local --report path, --include-preview-geometry and exactly
one hypothetical plane offset, the CLI includes accepted face and portal
loops and synthetic convex triangulations. The face output retains the
source polygon ordinal, owning leaf, material, normal, and primary UV.
Surviving corners keep original UVs; new clipping vertices use a
source-verified affine projection with residual <=1e-4 and plane error
<=.15. Texture mapping follows the translated material patch. A failed
texture/triangulation gate excludes that face from the textured preview.
No native tangent or lightmap encoder, collision writer, CSG surface
expansion, or game-ready map is supplied. Private geometry is never
printed on stdout or included in public CI artifacts.

    python research/dx2/inspect_vbsp_local_clip.py MAP.gmp --plane 0 --delta-d 1 --include-preview-geometry --report PRIVATE.json

The primary UV basis and packed tangent evidence are separately audited by
inspect_level_polygon_uv_basis.py. Packaged validation of the preview and UV audit is recorded below.

## Original UV and textured-preview validation

The portable source ZIP from 69ff6c12eebc4c9d21ca4d75db2ff45cdb8b38f7
reproduced the 19-map primary UV basis audit. On the same 19 deterministic
plane offsets, all 62 affected face previews passed the texture and
triangulation gate, and all 28 previously accepted portal previews were
exportable. The first preview implementation projected surviving corners
back onto a face basis; this could classify a surviving nonplanar source
corner as an interpolated UV. The follow-up uses source projected corner
identity and preserves original XYZ plus only the requested translation,
and original UV verbatim. Newly clipped points retain the affine gate.

## Exact-position seam and original triangle diagnostics

Every original material corner and undirected boundary edge is grouped by
exact source XYZ, without assuming a native vertex weld or topological
connection between coincident geometry. The exploratory 19-map inventory
has 22,388 distinct positions, 22,140 shared by multiple polygons and
12,935 crossing source leaves. 76,484 of 76,732 corner occurrences belong
to shared groups. 40,026 distinct boundary edges include 36,685 shared
groups, 36,673 with two occurrences and 12 with more than two. 13,270
edge groups cross leaf boundaries.

The private report now compares surviving source corners to stationary
neighbor polygons and other accepted previews. A separation beyond .002
source units, a refused neighbor, or removed source corner with surviving
neighbors is recorded. These are conservative seam warnings, not proof
of a crack or complete watertightness; T-junctions and coincident unrelated
surfaces remain unresolved. Every affected face (including refused ones)
is also linked to exact original flat render triangle and reachable MOPP
IDs. The link is source provenance, not a regenerated collision mesh.
No native write or runtime execution. Follow-up integrated corpus results are recorded below.

## Integrated seam/provenance verification

The source-only ZIP from 1e46bd539b00575b5f9b766a6d7aa79c02f2c0be
passed all 19 original-map baseline audits and reproduced every source
corner/edge inventory count above. The same 19 deterministic plane offsets
passed 62 textured face previews (20 support translations, 4 reduced-area
patches, 1 changed vertex count) and 28 portal previews, with 12 portals
refused by the original reconstruction gate. Exactly 32 preview vertices
used the affine UV projection; surviving source vertices kept their XYZ
(up to the requested translation) and UV associations.

The affected faces link to 125 original flat triangles, all original MOPP
leaf IDs. Of 139 affected shared source XYZ groups, 53 fully agree, 60
have separated surviving positions and 28 have removed original corners
alongside surviving neighbors. Warning categories can overlap. These are
geometric dependency diagnostics, not authenticated native welds or proof
of cracks. No watertightness, collision rebuild, native writer or retail
execution is claimed. Independent face clipping cannot be promoted to a
native geometry writer: a coupled corner/edge constraint solver, T-junction
handling, newly exposed surfaces and synchronized collision cooking remain
required. Original maps were not modified; private geometry was not committed.
