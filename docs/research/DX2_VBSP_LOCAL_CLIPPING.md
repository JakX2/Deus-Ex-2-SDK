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
inspect_level_polygon_uv_basis.py. Packaged validation of the new preview
export and UV audit is pending.
