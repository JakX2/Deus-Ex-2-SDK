# WTO Terminal: neighboring geometry investigation

**Reference:** user's retail-game screenshot versus the Godot DX2Ed preview,
at `M1_Seattle_Hub_WTOterminal.gmp`, next to `StaticMeshActor__119`
(export `554`, mesh `1Hub_wto_term2-trim2-4ft`).

The selected trim renders with a matched diffuse texture and original
source mesh bounds. Its source rotator is `[0, 16384, 0]` (Yaw 90°, Roll 0°),
so Auto Roll has no effect. The visual discrepancy is **adjacent missing
surface/trim geometry**, not proof that this selected mesh was skipped.

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
