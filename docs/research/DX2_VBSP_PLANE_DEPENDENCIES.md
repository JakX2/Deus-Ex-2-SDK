# VBSP localized plane dependency preflight

The direct leaf polygon ownership crosswalk lets us inspect all oriented
halfspace constraints along each original VBSP leaf path. A geometric
supporting-plane candidate requires every polygon vertex within .15 of
the plane and the original vertex normal within .002 of its oriented
normal. This is not a new serialized Model surface-index claim.

Exploratory private corpus: 33,095 leaf path constraints, 175,929
polygon-path tests, three path violations beyond .15, 16,784 unique
supporting-plane polygon candidates out of 16,789, five unmatched, zero
multiple. Across 4,287 used source planes, 2,559 support multiple
polygons (15,056 polygons total), 1,727 are reused by multiple node
records, 2,904 appear on multiple leaf paths, and 281 are referenced
by a portal. The exceptional polygons remain visible in counts.

The preflight can report hypothetical changes to a single plane's D
coefficient while holding all polygons stationary, including affected
leaf paths, source polygon candidates and direct portal references.
It flags newly violated unchanged polygon constraints; it does not
rebuild or clip any geometry. Never treat the absence of violations
as permission to patch a plane: other native structures may still need
recompilation.

    python research/dx2/inspect_vbsp_plane_dependencies.py MAP.gmp
    python research/dx2/inspect_vbsp_plane_dependencies.py MAP.gmp --plane 0 --delta-d 1

Run with root, map_exporter and research/dx2 on PYTHONPATH.
Source-only corpus and hypothetical tests are read-only; no proprietary
geometry or map files are emitted or committed.
