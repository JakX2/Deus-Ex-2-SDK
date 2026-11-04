# DX2Ed original Level surface slope, edge and sampled step-height diagnostics

**Research PR #49, stacked on PR #48.** This adds read-only geometric diagnostics to the existing original source-hash-authenticated Level/Flesh/MOPP collision picker. No Havok contact, actor, physics shape, editable BSP, or native GMP writer is changed.

## Read-only inspection

Enable **Inspect source collision**, click a triangle, and view the new **SOURCE SLOPE + STEP DIAGNOSTICS | RESEARCH** panel.

- **Unsigned plane slope:** angle between the original triangle plane and horizontal Godot XZ, computed with acos(abs(geometric_normal dot Up)). Flat is 0 degrees; vertical wall is 90 degrees. Up in preview space maps to original Level +Z. Triangle winding does not establish floor versus ceiling.
- **Original source edge classes AB/BC/CA:** interior shared edge, open boundary, render-material seam, or non-manifold. Existing independently validated source edge metadata is used. Render materials **are not Havok physical materials**.
- **Per-edge rise/incline:** absolute endpoint elevation change in original Level units and the angle of that edge relative to horizontal.
- **Nearest edge:** geometric 3D point-to-edge distance in original Level units.
- **Custom slope threshold:** default 45 degrees, for geometric screening, not actual game walkability.

The inspector requires the source picker to be ready; refuses nonfinite points, unrecognized original Level triangle IDs, points outside the selected triangle and points off its plane. Point containment uses a 1e-4 Godot-unit plane tolerance and a 2e-4 barycentric tolerance, **not** native Havok margins.

## Compare two surfaces

1. Click an original collision surface in the Godot viewport.
2. Click **Pin surface reference** in the new Inspector panel.
3. Click another original collision surface, and inspect the signed height difference and horizontal separation.
4. Set your **Step limit** (default 0.5 original Level units), **Max planar gap** (default 1.0) and **Slope limit** (default 45 degrees). These are user-selected probes, not recovered DX2 player settings.

The panel draws disposable editor-only cyan horizontal and amber vertical measurement lines between nearby sampled points. Clear the reference or exit source collision mode to delete the line overlay. Nothing is added to native map/actor data.

**Scientific guardrails:** If the two samples are distant in the XZ plane, the panel refuses a local-step inference. If both points are on the same original triangle, the height difference is *surface rise*, not a step. If either plane is too steep under the user setting, the pair is flagged. Only two distinct nearby floor-like source triangles with measurable height difference produce a **vertical-discontinuity proxy**, labeled **NOT verified traversable step**. Two stacked stories can share an XZ footprint without a physically walkable connection; no edge link, collision filter, clearance, shape or real step-up is inferred.

Only actual source ray picks can be pinned; section navigation centroids show slope but are not eligible step reference samples. Source map SHA mismatch clears or rejects comparisons. Original triangle IDs are preserved, including original Level ID gaps.

## Coordinate handling

Existing source-authoritative Level XYZ is shown as Godot XYZ = (Level X/10, Level Z/10, Level Y/10). Measurements are converted back to original Level lengths by multiplying Godot lengths by 10; normal orientations remain source winding-dependent.

This is Godot local source geometry analysis and generates no proprietary report or retail bytes.

## Aggregate original-map slope histogram (private cache, not raw GMP)

The additional Python research command reads DX2Ed's **existing validated original-source collision cache-v2**, not raw GMP bytes. It requires the caller to supply the original GMP SHA-256, rejects wrong source/hash, contradictory original topology and invalid original triangle IDs, and computes only anonymous counts of source MOPP-leaf triangle slopes (0-5, 5-30, 30-45, 45-75 and 75-90 degrees), face winding signs and existing edge classes.

From the full SDK checkout, after activating Inspect source collision for an original map:

~~~powershell
python research/dx2/audit_source_surface_slope_cache.py --cache "C:\DX2EdPrivateCache\source_collision_selection_v2.json" --expected-sha256 "INSERT_ORIGINAL_GMP_SHA256" --report "C:\DX2Research\source_slope_counts.json"
~~~

Use your real DX2Ed cache path and the original GMP hash. The report must be NEW and outside the private cache directory. It contains no vertices, triangle IDs, or contact XYZ. Cache JSON is private and must not be published. The output is a **geometric distribution**, not a validated game walkability threshold or physics response. SHA binding prevents accidental cross-map analysis but does not cryptographically sign a manually edited cache.

This PR includes **nine new fixture-only Python audit tests**. We have **not** executed this new cache histogram against the full owner-provided 19 original maps in public CI; real-map histogram counts are not claimed here.

## Implementation and verification

- native_editor/godot_editor/source_surface_diagnostics.gd: slope, nearest edge, exact source edge classes, per-edge rise/incline and constrained two-sample height comparison
- native_editor/godot_editor/source_surface_panel.gd: interactive read-only Inspector measurements and disposable viewport comparison line
- native_editor/godot_editor/main.gd: minimal source collision activation, hit selection, and reset integration, no Save As changes
- native_editor/godot_editor/tests/smoke_source_surface_step_diagnostics.gd: fixtures covering flat floor, analytic 26.565-degree ramp, 90-degree wall, source edge classification, sign of height delta, threshold changes, too-distant points, same triangle, untrusted points, source hash change, marker lifecycle and integration parse
- .github/workflows/native-dx2ed.yml: new fifth Godot 4.3 source-only smoke test

CI fixtures contain **no original game assets**. Owner-GMP interactive Windows testing and independent Havok runtime verification remain necessary.

Next research: matched-location edge connectivity and character controller clearance, independently tested against authorized actual Havok queries. No native collision cooking or gameplay collision Save As is claimed.
