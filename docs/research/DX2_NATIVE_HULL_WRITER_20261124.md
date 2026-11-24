# Native convex hull serialization (2026-11-24)

## Original data evidence

The owner-provided Maps code.zip contains 42 type-5 resource records in
two physics bundles, comprising 518 point records. Every hull has four
parts of lengths 4, 1, 4, and 16 * point_count. Observed first dwords are
0, 2, 8 and 32; the one-byte second field is zero. Their exact semantics
are not established. The third part is the point count; each point is
three little-endian float32 coordinates followed by four zero bytes.

Original counts range from 8 to 26. All 518 points are finite and have
zero fourth words. An independent SciPy convex-hull calculation shows
all 42 point clouds are full-dimensional with every point an extreme
vertex. No face index table is present in these resources.

Forty records have a --number suffix whose base name corresponds to
39 distinct static mesh names. The other two records share the name
"character sphere". Name correspondence is not proof of actor binding
or engine registration. The render-to-hull extents often suggest a
factor near 0.1905, but differ on some axes and some resources. No
automatic conversion between render and physics coordinate frames is
implemented.

## Writer

tools/maps/dx2_hull_writer.py accepts only the observed type-5 layout
with preserved prefix fields and 4-64 explicit native physics points.
Float32-quantized points must be distinct, finite and full-dimensional.
Exact integer orientation predicates identify supporting planes and
verify that each point is an extreme vertex. Face-interior, edge-interior
and volume-interior points are refused. This mathematical test does not
model Havok's numeric tolerances or minimum shape requirements.

The original IBD must pass the integrity and canonical reconstruction
gates from #204. The new point count and payload are written as existing
resource parts. All unrelated resources, names, indices and opaque prefix
fields are preserved. Full reparse and exact inverse reconstruction are
mandatory. The disk CLI requires a SHA-256 source pin and a new isolated
candidate path with the original filename. It never installs a candidate.

Example geometry JSON, explicitly in native physics coordinates:

    {"min":[-1,-1,-1],"max":[1,1,1]}

Or:

    {"points":[[0,0,0],[1,0,0],[0,1,0],[0,0,1]]}

    python tools/maps/dx2_hull_writer.py inspect "C:\Owned\Kernel_PHYALL.ibd" --hull "ExistingHullName"

    python tools/maps/dx2_hull_writer.py replace "C:\Owned\Kernel_PHYALL.ibd" --hull "ExistingHullName" --geometry "C:\Work\hull.json" --source-sha256 ORIGINAL_HASH --output "C:\Trial\Kernel_PHYALL.ibd"

## Actual original validation

The exact CI source bundle from run 45334358509 passed 48 synthetic tests
locally. All 42 original hull records passed the strict new reader.
Every original hull was replaced with a newly generated four-point
tetrahedron and, independently, an expanded eight-point box. All 84
candidates passed full native integrity checks, point reparse and
byte-identical inverse reconstruction. The original ZIP SHA-256 was
unchanged. No retail runtime was launched. No modified or original
game files were committed.

## Render and physics coordination blocker

All 78 render records corresponding by name to the 39 distinct named
hull groups contain hardpoints and auxiliary shadow geometry. None of
these render records are in the narrow 32-record topology writer subset.
Thus the current tools must not be presented as a paired custom model
and collision importer.

A further read-only inspection of all 330 render records found 113
auxiliary meshes with 42,432 16-byte vertex records and 169,728 uint16
indices. All indices are within the corresponding shadow vertex ranges;
the shadow triangle count equals index count / 3. Each auxiliary
vertex's first three float32 values are finite. The fourth word is
nonzero and opaque, not a fourth float coordinate to rewrite.

All 1,288 hardpoint records contain three initial position floats
followed by nine values forming an orthonormal proper rotation matrix.
This supports investigating uniform scaling of positions while preserving
orientation and opaque shadow fields. It does not establish generation
of arbitrary hardpoints or shadow topology.

The next practical goal is a guarded coordinated uniform-scale trial
and eventual retail A/B verification. Mass/inertia, actor binding,
physics registry behavior, arbitrary shadow generation and BSP
compilation remain unresolved.
