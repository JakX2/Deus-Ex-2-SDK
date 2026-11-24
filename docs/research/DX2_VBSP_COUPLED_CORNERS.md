# Coupled source-corner displacement research

This read-only prototype keeps original polygon corner identities and
triangle topology. All source-coincident XYZ occurrences are treated as
a single geometric candidate variable, not an authenticated native weld.
A selected VBSP plane offset imposes N dot displacement = -delta_D.
All unique incident face supports and actual path contacts (within .002
source units) impose their own plane equations. The stationary constraints
have zero right-hand side. An incremental rank-1/2/3 orthogonal solver
finds minimum displacement and refuses inconsistent or excessive movement.

Every affected face must retain convexity, orientation, its original
leaf halfspace constraints, support plane and source affine UV basis.
Original packed triangle locators are checked for nonzero signed area
and preserved winding. A complete affected stationary leaf-domain scan
checks newly violated unchanged faces. Shared-position diagnostics
compare both moved and stationary neighbors, including refused faces.
The private preview preserves original corner IDs and links affected
faces to original collision triangles; it does not rebuild collision.

The default selects a deterministic small plane experiment per map,
not the best result. Explicit --plane is accepted for one map. The
aggregate report is private-source-derived, but no geometry is printed.
Optional --include-preview-geometry requires one map and a fresh
--report JSON path outside the original directory.

    python research/dx2/inspect_vbsp_coupled_corners.py MAP.gmp --delta-d 1
    python research/dx2/inspect_vbsp_coupled_corners.py MAP.gmp --plane 0 --delta-d 1 --report PRIVATE.json --include-preview-geometry

Run with root, map_exporter and research/dx2 on PYTHONPATH.
No GMP output. A passed preview is not proof of watertightness:
T-junctions, noncoincident nearby corners, unrelated coincident faces,
portals, navigation and MOPP still require independent validation.
Corpus verification pending.

## Point-on-edge and near-coincident position checks

Independent exploratory measurement on 19 original Seattle maps found
722 interior corner/edge candidate pairs (627 within 1e-7 of their
supporting line, nine farther than 1e-4), and 24 distinct position pairs
within .002 source units. These are geometric relationships, not native
T-junction IDs. The portable solver now inventories them with a bounded
sorted-axis scan. After a proposed coupled displacement, every affected
relationship must retain its point-on-segment or near-position condition;
refused neighboring faces remain unresolved and fail the combined gate.
No original geometry is merged or split, and no native writer is enabled.
