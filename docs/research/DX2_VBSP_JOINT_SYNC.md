# Joint localized render, MOPP and candidate Model synchronization

Research-only in-memory experiment, no GMP output. A complete coupled
corner preview is required before any patch. First synchronize expanded
and packed positions/UVs, shadows and packed bounds. Then write matching
float32 flat coordinates and fixed-width MOPP spatial operands. Reparse
the actual joint package with the independent original source context
reader. Original package tables, polygon links, triangle provenance,
shadow associations and exact original byte reversal are mandatory.

For moved faces with bidirectionally unique geometric Model associations,
recalculate the node plane W using the original normal and projected
displacement, and bounding sphere from AABB midpoint and maximum vertex
distance times 1.001. Require the source sphere hypothesis, unchanged
candidate associations and original node tree topology. Check that
no previously conforming direct Model graph link becomes nonconforming.
Refuse any unresolved moved face or unupdated original plane alias.
These geometric checks do not establish native ownership semantics.

If the changed geometry violates the original MOPP root origin/scale
formula, recalculate the float32 origin and scale from changed flattened
geometry. Validate original paths with the old root, candidate paths
with the new root, preserving control flow and leaf IDs. Refit all
axis and experimental diagonal operands. If needed, try the bounded
single-byte local rescale fallback. Require exact code reversal,
original nondegenerate triangle coverage and independent point queries
for all changed triangles. Diagonal semantics remain runtime-unverified.

## Private 19-map, 38-offset experiment

| Result | +1 | -1 |
|---|---:|---:|
| Coupled geometry passed | 9 | 11 |
| Joint render/collision reparse passed | 9 | 11 |
| Additional Model hypothesis gate and reparse passed | 7 | 9 |
| Changed flat vertices | 109 | 141 |
| Changed collision triangles | 99 | 139 |
| Independent changed-triangle query samples (each mode) | 693 | 973 |
| Changed MOPP code bytes | 28 | 53 |
| Root quantization updated | 1 | 1 |
| Local rescale fallback used | 1 | 1 |
| Candidate Model records updated before Model gate | 45 | 63 |
| Moved faces without unique Model association | 2 | 2 |
| Unupdated plane aliases | 3 | 3 |

All 1,666 changed-triangle point queries pass each offline walker.
Both Inclinator signed candidates previously failed the root spatial
envelope check, but pass with root refitting. For the 20 complete
geometry candidates, 16 pass the extra Model gate. The campus entrance
has two unresolved moved faces per sign; WTO Terminal Lower has three
unupdated source plane aliases per sign. No new direct Model link
geometry violations or changed geometric association lists occurred.
The other 18 experiments fail coupled geometry before patching.
Four synthetic tests passed locally. Original files unchanged.

    python research/dx2/inspect_vbsp_joint_sync.py MAP.gmp --delta-d -1

Use root, map_exporter and research/dx2 on PYTHONPATH. Spatial prefix
(VBSP planes, portal polygons, leaf bounds, grids and navigation-like
graph) remains unchanged. This is NOT a complete native level editor,
a visibility/CSG compiler or a playable modified map. No private asset
bytes are committed or emitted.

## Complete root-requantization centroid sweep

Both Inclinator signed candidates contain 2,550 original leaf IDs. All
5,100 candidate centroid queries per offline interpreter recover their
intended triangle (zero original and candidate misses). Candidate lists
changed at 47 and 32 centroids in conservative mode, and at 61 and 49
in derived-diagonal mode, respectively. This is coverage evidence, not
proof of identical broadphase behavior or retail collision execution.

## Exact render-leaf AABB rule and synchronized bounds

Source audit of all 19 original Seattle GMPs shows all 3,002 nonempty
VBSP leaf boxes equal the AABB of their owned expanded polygon corners
exactly; all 104 empty leaves have all-zero bounds. Including the portal
vertices in the box would incorrectly change many original bounds.
The new module validates exact source boxes, reconstructs candidate
boxes from unchanged serialized polygon ranges, verifies original leaf
record bytes at the computed array span, and changes only 24-byte box
spans. Full joint package reparse verifies source leaf/triangle ownership,
unchanged splitter nodes, planes, portal records and portal side probes.

All 20 previously geometry-approved signed experiments passed this
additional gate, changing 25 leaf bounds (34 bytes) in aggregate.
All 16 previous joint Model candidates still pass, while the four
Model association/alias failures remain. Three synthetic tests pass.
The earlier statement that the entire spatial prefix is untouched is
superseded only for these leaf AABB records. Splitter plane D, portal
coordinates, navigation graph, grid semantics, visibility and actual
retail loading remain unresolved. No candidate GMP is emitted.

## Fixed-width splitter and coupled portal vertices

The next stage updates a selected splitter D and original portal corner
positions, retaining all vertex counts, loop order, plane references and
owner ranges. Exact coincident portal corners share one displacement.
Original incident portal support planes and leaf path contacts within
.002 units constrain that displacement. Coincident render corners must
already satisfy the same motion equations; otherwise refuse. Check all
original render polygons and portal loops for new per-path halfspace
violations, preserve original conforming render centroid classification,
require convexity and orientation of changed portal loops, and retain
ordered two-sided portal centroid classifications. These tests do not
prove visibility compiler or near-contact/T-junction semantics.

All 20 previous geometry-approved signed candidates passed the actual
in-memory package roundtrip after this stage (16 with the Model gate).
The source contact solver identified 16 active portal corner groups, all
with exact coincident render corner candidates. Across the 20 trials,
24 portals were affected and 40 original portal vertex occurrences moved.
75 splitter/portal bytes changed. No new path violations or owner/portal
probe regressions. Three synthetic tests pass locally, including refusal
of a stationary render contact. Navigation-like graph, grids, pre-Model
fields and runtime semantics remain unresolved. No candidate GMP emitted.

## Navigation-like graph and grid dependency audit

The read-only audit uses the original validated graph framing to sample
all triangle corners and centroids, edge endpoints and midpoints, grid
origins and directional positions. It compares the exact old and new
splitter decisions, traversing the original tree where the decision may
change; upward-offset probes are evaluated independently. It also finds
exact source-corner contact candidates and hypothetically tests their
motion without modifying any graph/grid bytes. This is not a navigation
compiler and these samples are not a proof of continuous free space.

All 20 geometry-approved signed trials passed the structural portal stage.
Record occurrences are counted, including repeated coordinates and both
signed trials.
The exact inventory is 77,721 graph triangle corners, 25,907 triangle
centroids, 111,716 edge endpoints, 55,858 edge midpoints, 3,031 grid origins
and 1,769 directional positions; 276,002 total original point occurrences,
plus the same number of upward probes. 22 triangle corner occurrences
have exact moved source contacts; hypothetical contact motion preserves
all their original point classifications. Unchanged positions produce
12 newly solid triangle corners, 2 centroids, 4 edge endpoints, 2 edge
midpoints and 1 grid origin; the upward probes find the same counts.
Eight trials have a dependency warning; twelve do not. Eight pass both
the Model and splitter/portal stages without a graph/grid sample warning.
Do not interpret that as permission to emit playable GMP files: unknown
graph/grid semantics, continuous collision and retail execution remain
unverified. Four synthetic tests pass locally. No graph/grid changes.
