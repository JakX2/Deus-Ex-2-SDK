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
texture mapping still require a real CSG algorithm. No GMP or preview
geometry output is available; aggregate counts only.

    python research/dx2/inspect_vbsp_local_clip.py MAP.gmp
    python research/dx2/inspect_vbsp_local_clip.py MAP.gmp --plane 0 --delta-d 1

Run with root, map_exporter and research/dx2 on PYTHONPATH.
Integrated original-map results are pending. No collision rebuild,
visibility compilation, native source mutation or runtime testing.
