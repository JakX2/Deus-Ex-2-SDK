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
