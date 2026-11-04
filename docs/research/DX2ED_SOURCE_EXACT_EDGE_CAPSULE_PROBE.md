# DX2Ed: source-exact shared-edge capsule crossing research probe

**Research PR #51**, stacked on #50's original Level v3 exact-welded edge-neighbor infrastructure. This adds an opt-in crossing *experiment*, not a walkability classifier, Havok player controller or writable collision.

## What it does

1. Open an **owner-supplied original GMP** and enable **Inspect source collision**, which authenticates original Level/Flesh/MOPP linkage, SHA-256 and exact-original Level coordinate welding.
2. Click an original collision triangle. Under **EXACT SOURCE EDGE LINKS**, select a source AB/BC/CA edge with **one unique original-welded neighbor**, two floor-like triangles under chosen geometric slope and hinge limits, and **opposite-side horizontal projections**.
3. Adjust the new controls: **Interior fraction** (default 0.2, from the shared edge midpoint toward each face's third vertex), **Up offset** (default 1.0 original Level unit), capsule **radius** (default 0.2 Level unit) and **half-axis length** (default 0.5 Level unit). These values are illustrative, not native DX2 player dimensions.
4. Select **Probe capsule across edge**. A new independent geometry module builds two points strictly inside the original neighboring triangle interiors and offsets them vertically in preview Up (original Level +Z). It requires that the resulting 3D straight chord **crosses the finite original shared edge in horizontal projection**, not merely the edge's infinite line.
5. The existing PR #48 read-only Python worker runs the *full original-map* capsule first-contact solver using the generated path, without manually entering XYZ or forging a mouse-ray hit.
6. The already validated PR #47 wireframe displays the swept capsule, earliest numerical source contact, original triangle ID and geometric contact normal if resolved. Empty results are shown as no geometric contact, not as an authenticated traversable path.

The positive geometric prerequisite (exact adjacency + low slopes + small hinge + opposite sides) only allows a **well-defined research crossing**. It **never** implies clearance. A straight chord above two sloped floors may drift vertically away from their piecewise surface through the edge, so the module records its crossing-height deviation from the source edge's locally interpolated elevation. The independent collision oracle, not the adjacency heuristic, determines contacts with other original triangles.

## Provenance and limitations

- Original neighboring triangle IDs originate from **source-exact welded float32 Level XYZ**, not Godot preview-coordinate proximity. No epsilon-weld adjacency is invented.
- Rejects open boundaries, non-manifold multiple neighbors, near-vertical projected edges, same-side/overlapping projected triangles, too-sharp hinges, steep planes, invalid parameters, degenerate paths and finite-edge misses.
- Preserves original source map hash and both original triangle IDs through the generated research path.
- Before an analytical chord enters the existing capsule worker, the panel **rebuilds the chord independently from the current authenticated source cache**, refusing altered endpoints or stale map SHA.
- The generated points are *analytical* samples, **not fake source mouse-ray picks**. Source-inspection reset, map change and worker lifecycle guards from #48 continue to apply.
- Python output is a **new private JSON outside original retail Maps**, then the existing first-contact overlay refuses mismatched source identifiers or invalid contact geometry. Original GMP/IBD are not written.
- The full source MOPP conservative candidate set and independent all-triangle capsule narrowphase check remain separate from geometric edge selection.
- A hit against a floor can be a normal supporting contact, not necessarily a *blocking* collision. A no-hit in this finite fixed-axis shape sweep does not prove Havok gameplay walkability, collision filters, dynamic blockers, player body type or native controller slide/step logic.

## Negative control proving exact edges are not enough

The synthetic Python geometry suite builds **two coplanar original floor triangles sharing one true edge**. A straight capsule sweep raised above them can show no floor contact. Adding a separate vertical wall across the same corridor causes the independent whole-map capsule oracle and first-contact solver to report the wall triangles, despite perfect adjacent floor geometry. Other controls vary capsule radius, vertical offset, initial ground contact and source triangle immutability.

This is evidence that the new probe must run against **full map geometry**, rather than blessing a pair of shared floor triangles as walkable.

## Files and tests

- `native_editor/godot_editor/source_edge_capsule_chord.gd`: source-exact validated crossing samples and finite projected edge intersection, no physics conclusions.
- `native_editor/godot_editor/source_edge_transition_panel.gd`: **Probe capsule across edge** and shape/path controls in the exact edge Inspector.
- `native_editor/godot_editor/capsule_sweep_picks.gd`: accept explicit source-validated analytical chords as a separate path kind, not fake ray clicks.
- `native_editor/godot_editor/capsule_sweep_panel.gd`: rebuild source chord from current v3 authenticated cache, then reuse the existing original-GMP read-only Python worker and validated PR #47 visualization.
- `native_editor/godot_editor/tests/smoke_source_edge_capsule_probe.gd`: synthetic headless Godot 4.3 fixture for crossing coordinates, original IDs, hinge/side checks, bad welds, hash changes, forged chord coordinates and UI integration.
- `native_editor/tests/test_dx2_edge_connected_capsule_clearance_controls.py`: **six** independent Python geometry tests for flat open chord vs unrelated blocking wall and height/radius variations.
- `.github/workflows/native-dx2ed.yml`: seventh Godot source-only smoke fixture.
- This research document.

All synthetic fixtures are independent of proprietary retail assets. **No full 19-map original GMP clearance audit has been performed for this new edge-path generator.** Actual Windows retail source testing and Havok runtime equivalence remain separate gates.

## Future work

Compare a finite number of original edge-crossing probes with authorized DX2 game runtime traces; distinguish dynamic colliders from original static Level geometry; recover actual character controller shape/step slope/filter behavior; expand from one fixed-height chord to a documented clearance profile over multiple elevations. Real geometry/collision rewriting and native MOPP cooking are not part of this PR.
