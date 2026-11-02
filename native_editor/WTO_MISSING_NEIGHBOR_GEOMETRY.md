# WTO Terminal: neighboring geometry investigation

**Reference:** user's retail-game screenshot versus the Godot DX2Ed preview,
at `M1_Seattle_Hub_WTOterminal.gmp`, next to `StaticMeshActor__119`
(export `554`, mesh `1Hub_wto_term2-trim2-4ft`).

The selected trim renders with a matched diffuse texture and original
source mesh bounds. Its source rotator is `[0, 16384, 0]` (Yaw 90°, Roll 0°),
so Auto Roll has no effect. The visual discrepancy is **adjacent missing
surface/trim geometry**, not proof that this selected mesh was skipped.

## Verified cached WTO import (2026-11-02)

The user supplied both original **DX2Ed cache exports**, `actors.json` and
`scene.report.json`, for the same retail WTO Terminal map hash
`a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa`.

- **1,033 actors** decoded, including **623 StaticMeshActor** instances.
- Every one of the 623 StaticMeshActors has a resolved mesh name.
- Exactly **802/802 mesh-linked actors were rendered** and have placement
  diagnostic records. `missing_mesh_actors` is **empty**; this excludes a
  straightforward missing-IBD/static-mesh-actor cause for the screenshot.
- The generated GLB contains 906 scene nodes, so **104 BSP block nodes** are
  inferred from 906 - 802; 1,372 visible BSP triangles were reported.
- The three unresolved diffuse material names were monitor-screen effects
  (`Mon_screen1`, `Mon_screen4`, `Mon_screen7`), **not** the target trim.
- `StaticMeshActor__119` / export 554 has **matched** skin/diffuse,
  source rotator `[0,16384,0]`, and calculated world AABB
  X [-0.00005,0.51315], Y [4.64009,7.54380], Z [-6.40080,-5.18159] m.
- Among meshes nearest its transformed *AABB*, two intersect its AABB:
  `StaticMeshActor__567` (export 351, `GEN_TRIM5-16ft`) and
  `StaticMeshActor__599` (export 898,
  `1Hub_wto_term2-trim2-crnr1`). The world AABBs of
  `StaticMeshActor__450` (697), `__452` (691), and `__459` (722) are
  approximately 0.61 m away by conservative box-to-box distance. These three
  use `GEN_TRIM5-16ft` but have different source Pitch/Roll values.

**Conclusion:** the report does not support "DX2Ed silently dropped a
referenced static mesh". Target next: BSP render block/section recovery and
preview transforms of existing trim geometry. Box-to-box distance is
**not** triangle-to-triangle surface distance; no claim that an actual wall
opening is exactly 0.61m.

**Limitation:** these two cache JSONs do not contain the raw BSP render
payload, missing/filtered BSP section listing, or the source WTO GMP itself.
A fully independent extraction audit requires the matching original
`M1_Seattle_Hub_WTOterminal.gmp` and `m1_hub_wtoterminal.ibd`.
Existing cache reports predate the new `mesh_export_coverage` and
`bsp_export_coverage` fields and should not be interpreted as zeros.

## What the importer can now report

A freshly generated `scene.report.json` contains:

- `mesh_export_coverage`: total source `StaticMeshActor`s,
  unresolved GMP mesh references, referenced meshes missing from all
  selected IBD bundles, resource meshes with empty render sections,
  and any unexplained source-to-render gaps, listed by export ID.
- `bsp_export_coverage`: decoded BSP blocks, decoded sections, the
  number filtered by the current `BF` rule, and visible BSP triangle count.
  This is **not** a proof that the BSP parser recovered every surface.

Note: older private cached `scene.report.json` files predate the coverage
fields. They remain valid, and the neighbor audit can use their existing
`placement_actor_details` and `missing_mesh_actors` without modifying them.

## Audit nearby original actors

Run from the repository root, after importing the actual WTO map in DX2Ed:

```powershell
python map_exporter/dx2_missing_geometry_neighbors.py "C:\\DX2EdCache\\WTO_FOLDER\\actors.json" "C:\\DX2EdCache\\WTO_FOLDER\\scene.report.json" --actor StaticMeshActor__119 --radius 5 --output "C:\\DX2EdCache\\wto_missing_neighbors.json"
```

Replace both example cache paths with actual files in the same source-hashed
DX2Ed cache folder. The script does not modify either input.

The report lists neighboring source static mesh actors, their export IDs,
resource names and status: `rendered`, `missing_ibd_resource`,
`empty_render_sections`, `unresolved_gmp_mesh_reference`, or
`unverified_no_render_record`. The source location is preserved.

**Important:** This proximity check uses actor *origins*, not visible
triangle-to-triangle distances. Large meshes and pivot offsets can place
surfaces near the target even when their origins are farther away.
Missing BSP faces are not discoverable from actor IDs alone.

## What is still needed

The user's uploaded asset collection contains Seattle Club, but not the
original WTO Terminal GMP/mission IBD pair. With the user's WTO
`actors.json` and `scene.report.json`, we can narrow down missing static
mesh actors. To conclusively inspect dropped or misdecoded BSP surfaces,
we'll need the original WTO GMP and matching resource packages or a more
complete in-game geometry trace.

Do not change any source GMP rotations based solely on this report.
