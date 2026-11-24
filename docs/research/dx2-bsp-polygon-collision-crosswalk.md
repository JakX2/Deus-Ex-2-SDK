# BSP polygon ambiguity and original collision crosswalk

Follow-up to the strict render-derived polygon candidate audit. The default
audit remains unchanged apart from explicit method metadata on private
preview rows. Two opt-in research flags are available:

    python research/dx2/inspect_bsp_polygon_candidates.py MAP.gmp --recover-ambiguous --include-mopp-crosswalk

Run with repository root, map_exporter and research/dx2 on PYTHONPATH when
using the source tree. To obtain per-polygon geometry and source leaf IDs,
also specify --include-preview-polygons and --report with a fresh private
JSON path outside the source map directory. Keep source maps and private
reports out of git and public CI.

Ambiguous triangles form connected components through their candidate nodes.
A component is accepted only if one exhaustive complete cover satisfies
the strict existing boundary, area, convexity, source vertex count and
bounding sphere checks. Unique spatial candidates are required; nodes with
no required triangles may be unused. Every ambiguous triangle must be
assigned exactly once. A second solution, a missing solution, or a search
cap refuses recovery for the whole component. This is a hypothesis, not an
engine ownership proof; source render geometry may not satisfy this model.

The MOPP option independently validates the entire Level provenance and
MOPP leaf set using the existing source decoder, joins by exact render
locator and flat ordinal, and reports all/partial/no-leaf polygon counts.
A candidate's collision membership does not identify a native surface
array or authorize writes. No geometry, source MOPP code, or GMP is changed.

Original-map measurements for these new options remain pending until a
private map corpus run. Synthetic coverage includes nonunique, unique,
impossible and capped assignments; exact source provenance, skipped block
IDs, and partial/absent collision membership.
