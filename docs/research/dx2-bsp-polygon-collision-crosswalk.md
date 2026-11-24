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

## Private original-map audit, 2026-11-24

The source ZIP generated from f45466d08c2682e3abdd5c2cb5781952617bc7bc
was extracted and run against the 19 Seattle GMPs privately supplied
by the project owner. Both aggregate-only and opt-in detailed reports
completed with identical summary counts and original-file hash guards.
No original map or private report is committed.

| Metric | Count |
| --- | ---: |
| Native nodes | 17,743 |
| Original render triangles | 43,154 |
| Original reachable MOPP leaf IDs | 43,152 |
| Baseline strict polygons | 8,328 |
| Ambiguous triangle candidates | 5,204 |
| Ambiguity components | 1,192 |
| Unique complete covers | 124 |
| Multiple covers | 5 |
| No valid complete cover | 1,032 |
| Capped components | 31 |
| Newly assigned ambiguous triangles | 209 |
| Recovered strict polygons (including previously withheld unique triangles) | 245 |
| Total strict polygons | 8,573 |
| All-leaf strict polygons | 8,573 |
| Distinct assigned original MOPP leaves | 17,297 |
| MOPP leaves not yet assigned to strict polygon candidates | 25,855 |
| Original leaf triangles in recovered polygons | 505 |

Independent aggregation over the private detail report also found only
26 of 8,573 polygon candidates with raw Model compact field 2 equal to
every associated Level provenance A field. There were 6,097 per-map
field-2 groups, 1,565 reused groups, and only 267 reused groups whose
polygons all came from a single render section. 4,799 groups overall
had one render section; one individual polygon spanned two sections.
These counts argue against interpreting the compact field as a direct
render block/section ID. They do not decode the native surface table.

The crosswalk now records these surface-group aggregate diagnostics and
the recovered polygon collision coverage separately. Synthetic coverage
includes nonunique, unique, impossible and capped assignments; exact
source provenance, skipped block IDs, numeric field-2 counterexamples,
and partial/absent collision membership. Retail runtime and native BSP
serialization remain unverified.
