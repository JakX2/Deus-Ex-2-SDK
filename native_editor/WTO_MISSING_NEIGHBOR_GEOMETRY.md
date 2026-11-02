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

## Original retail GMP/IBD verified (additional evidence, 2026-11-02)

The user subsequently supplied `wto.zip`, containing the **exact matching**
retail `M1_Seattle_Hub_WTOterminal.gmp` (SHA256
`a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa`)
and `m1_hub_wtoterminal.ibd`.

A byte-level scan of the original GMP's Level export shows:

| Metric | Actual source |
|---|---:|
| Level payload bytes | 649,640 |
| Packed 32-byte-vertex render header markers | **105** |
| Headers accepted by current DX2 BSP scanner | **105** |
| Independent supplied T3SDK `t3bsp.find_render_blocks` | **105** |
| Named render material sections | **226** |
| All BSP render triangles, including BF | **1,384** |
| BF-placeholder/no-draw triangles | **12** |
| BSP triangles exported by DX2Ed and cached report | **1,372** |
| BSP GLB nodes inferred | **104** (105 source blocks, one entirely BF-hidden) |

The **only fully BF-hidden block** has source bounds
`(3952, 1680, -160)` to `(4784, 2512, 400)` UE.
That is **far outside** the immediate wall area around actor
`StaticMeshActor__119`, located at `(-0.0009766, -272, 396)` UE.

The target actor is within a source BSP block with bounds
`(0, -480, 240)` to `(600, 160, 400)` UE containing
`M1WTO_intbathwall1` (4 triangles), `M1WTO_intwall1` (7 triangles)
and `M1WTO_intfloor1` (4 triangles). That block was decoded.

**Result:** we have no evidence that the current exporter skipped any
*recognized packed BSP render blocks* or any mesh-linked actors here.
There is no justification to generate a phantom wall, restore BF faces in
this room, or change the selected trim's 0° Roll.

Next investigate the original neighboring trims' texture-facing and
preview transforms, the retail renderer's visibility/shading conventions,
and the possibility of native geometry not included in the understood
packed BSP representation. BSP parser count parity **does not prove**
pixel-perfect display against the retail engine.

Reproduce a **read-only original-to-cache parity audit** with:

```powershell
python map_exporter/dx2_bsp_source_audit.py M1_Seattle_Hub_WTOterminal.gmp scene.report.json --target-ue 0 -272 396 --output wto_bsp_source_audit.json
```

Keep private GMP/IBD and reports out of the Git repository.

## Placed-mesh triangle parity and BSP/mesh isolation (2026-11-02)

The user's **original mission IBD** plus the two supplied shared bundles
(`Kernel_GFXALL.ibd`, `MainMenu_GFXALL.ibd`) independently account for
**123 unique mesh resources / 802 mesh-linked actors / 44,480 source triangles**
in WTO Terminal. This equals `placed_mesh_triangles` in the user's cached
report exactly, not merely the number of scene nodes.

The original T3SDK `t3mesh.py` source defines `BF` as a hidden material.
The existing DX2 BSP exporter already suppresses `BF` on BSP faces, but
the **static mesh** path incorrectly emitted these as opaque GLB faces.

- WTO has **134 source `BF` triangles across placed mesh instances**, mostly
  on coffee cups, tunnel lights, train gates/screens and WTO stairs.
- The four WTO stair instances account for **16 BF triangles**. Two are
  geometrically close to the selected trim region, though there is no
  proven direct occlusion of the wall in the retail screenshot.
- The importer now suppresses these BF static-mesh sections for the **GLB
  visualization only**, using each actor's effective selected skin.
  `placed_mesh_triangles` preserves the pre-existing source count,
  while `rendered_static_mesh_triangles` and
  `static_mesh_bf_hidden_triangles` distinguish actually rendered faces.
- Expected WTO visible source triangle totals become 44,346 placed static
  + 1,372 BSP = **45,718 preview triangles** (before any other display
  effects). This is a source-based prediction for the next import, not
  a runtime measurement of Godot's frame draw calls.

### Interactive diagnosis

The native editor now exposes two independent read-only checkboxes alongside
the original map import controls:

- **BSP**: hide/reveal all nodes named `BSP_...`.
- **Placed meshes**: hide/reveal placed actor meshes.

Use the running retail game screenshot as ground truth, then hide **Placed
meshes** to verify the structural WTO wall is present and continuous, and
hide **BSP** to see whether the horizontal trim/corner meshes line up by
themselves. Restoring both checkboxes restores the complete scene without
reimporting, modifying actor transforms, or writing any game files.

**Important:** this is a display/occlusion diagnostic. It does not yet
demonstrate that the missing appearance is corrected; if BSP-only and
mesh-only geometry both look correct separately but not together,
investigate surface depth/occlusion/material shading in the Godot preview.


### Cache regeneration after native BF fix

`dx2_native_backend.CACHE_VERSION` is now
`DX2Ed-Native-map-cache-v0.2.7-static-bf-v1`.
Opening the original WTO GMP or mission ZIP with this updated branch will
automatically export to a **new content-hashed cache folder** so the BF
rendering change is visible immediately. Existing 0.2.6 caches and saved
draft sidecars are **left untouched**, not deleted or migrated.

Verify the refreshed `scene.report.json` fields on WTO:

- `placed_mesh_triangles = 44480` (source, legacy field)
- `static_mesh_bf_hidden_triangles = 134`
- `rendered_static_mesh_triangles = 44346`
- `visible_bsp_triangles = 1372`
- `total_scene_triangles = 45718`

**Do not treat this as a confirmed correction of the pictured wall gap.**
The retail in-game image still needs comparison with the newly exported
editor image, BSP-only view and placed-mesh-only view.
