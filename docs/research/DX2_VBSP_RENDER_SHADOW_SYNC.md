# Localized coupled render and shadow synchronization

A separate in-memory package experiment consumes only a complete coupled
geometry preview. The original indexed polygon topology and material
section inventory must remain unchanged. Each source corner is rounded
to source float32; its expanded XYZ, packed XYZ, four expanded UV pairs
and packed primary UV are updated at the original byte locations. Whole
texture repeat offsets are preserved. The original tangent-like words
remain unchanged only if the old/new affine UV mapping and tangent
directions agree, and the packed vector is unit length and orthogonal to
the source plane within the empirical tolerances. This is not a native
tangent encoder.

For every shadow cap in each touched render block, its independently
validated original render triangle is joined to a unique permutation
of source XYZ corners. A moved corner carries its original shadow
offset, with a float32 residual check. Original shadow indices and
opaque packed fourth words remain intact. Render-block AABB, center and
radius are recomputed from the updated vertices. All patch spans are
fixed-width, disjoint and byte-exactly reversible.

The in-memory package is parsed independently again: package tables,
packed render block/material/index inventory, expanded polygon
crosswalk, and all shadow triangle associations must be unchanged.
The original collision tail and spatial prefix are explicitly preserved.
This is a render-only candidate; its collision, Model and spatial prefix
are intentionally NOT synchronized, and it must never be installed or
emitted as a playable map. Original source SHA-256 is rechecked.

## Private corpus audit

38 deterministic signed plane-offset experiments across 19 originals:
9 positive and 11 negative candidates passed the coupled geometry gate.
All 20 of those candidates also passed the stricter render-only
round trip; the other 18 were refused before patching.

| Count | +1 | -1 |
|---|---:|---:|
| Accepted faces | 47 | 65 |
| Candidate vertex records | 203 | 294 |
| Changed XYZ vertices | 109 | 141 |
| Changed UV vertices | 73 | 97 |
| Shadow caps checked in touched blocks | 192 | 286 |
| Shadow vertices moved | 162 | 180 |
| Render block bounds updated | 11 | 14 |
| Fixed-width spans | 816 | 1029 |
| Changed bytes | 1272 | 1777 |

The separate Model candidate inventory found 83 of 90 positive and
87 of 94 negative accepted partial-preview faces with unique geometric
associations in both directions. Among the 112 faces in the complete
geometry-approved experiments, 108 are uniquely associated. Both signed
experiments in the campus entrance have two unassociated/ambiguous faces.
A geometric association is not an authenticated native node ownership
field. No Model write, native collision update, spatial portal update,
navigation update or retail runtime check is claimed. Three synthetic
tests cover tangent preservation/refusal, shadow assignment/refusal and
nonfinite coordinates. No proprietary geometry or edited map committed.

    python research/dx2/inspect_vbsp_render_sync.py MAP.gmp --delta-d -1

Use root, map_exporter and research/dx2 on PYTHONPATH.
