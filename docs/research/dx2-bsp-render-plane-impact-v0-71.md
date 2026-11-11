# v0.71: BSP plane versus original render triangle impact

The new `dx2sdk.bsp_render_plane_impact.compare_original_plane_render_impact`
reads the unchanged original GMP, validates the World Model via the existing
source-checked node/zone parser, extracts the original Model node sphere and
plane, and reads Level render blocks through `dx2scene.find_bsp`.

For a hypothetical float32 plane change, it compares original render
triangles that satisfy **both** candidate plane coplanarity and complete
node-sphere containment, before and after the change. Counts and up to
16 triangle locators per direction are returned. No retail triangle
coordinates or proprietary bytes are embedded in reports.

The spatial candidate algorithm already exists in
`research/dx2/inspect_bsp_render_spatial_candidates.py`. This feature
reuses its tested tolerances and original source geometry instead of
introducing another unvalidated geometric association.

**Interpretation:** a lost render triangle candidate is a concrete
geometry consistency warning for a future native BSP plane edit, **not**
proof of an engine-owned node-to-triangle reference. The plane and source
render triangles are independently serialized and the latter are not
automatically updated by changing the plane. Collision, Havok/MOPP, Region,
zone and runtime reconstruction remain unsupported.

Synthetic tests use three invented triangles and a shifted plane to show
one lost and one gained geometric candidate, refusal of invalid float32
edits, deterministic behavior, and unchanged input arrays. No retail data
is committed or modified.

Next: correlate the affected render triangle locators with the existing
source Level MOPP terminal-triangle provenance before considering a
strict isolated writer experiment.
