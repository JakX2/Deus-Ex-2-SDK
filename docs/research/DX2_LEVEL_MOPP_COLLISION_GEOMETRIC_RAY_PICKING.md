# DX2SDK Level MOPP-linked geometric ray picking (PR #32)

This research feature adds **read-only triangle selection** to the DX2SDK collision-debug pipeline. It works with original user-owned Unreal v95 *Deus Ex: Invisible War* GMP maps and the verified chain from earlier PRs:

`Flesh packed render blocks → flattened Level XYZ/u32 triangles → Havok MOPP leaf IDs → triangle-to-render-section provenance → exact-position topology audit → independent CPU ray picker`.

**This does not invoke Havok or reproduce its runtime collision queries.** The CPU picker builds an ordinary AABB-based binary BVH over the already verified MOPP-linked triangle soup. The BVH is **not** a decode or rebuild of MOPP's proprietary optimization tree, and hits are geometric ray/triangle intersections, not engine collision contacts.

## Original retail corpus verification (19 privately held GMP maps)

| Read-only check | Result |
|---|---:|
| Original DX2 GMPs decoded and indexed | **19/19** |
| Original flattened triangle entries | **43,154** |
| Reachable MOPP terminal triangles eligible for picking | **43,152** |
| Source zero-area, non-MOPP triangles excluded | **2** |
| New CPU BVH nodes across all maps | **14,047** |
| Deterministic rays targeted at first, median and last MOPP leaf of each map | **57/57** |
| Target original Level triangle IDs found | **57/57** |
| Total source-triangle intersection candidates evaluated by BVH for these rays | **1,227** |
| AABB nodes traversed for these rays | **1,775** |
| Local fixture-only regression tests, PRs #27–32 together | **76 passed** |

For each test ray, we selected a known nonzero-area MOPP leaf, computed its exact triangle centroid and source winding normal, placed the origin 0.05 Level-coordinate units on the winding-normal side, and cast toward the centroid with maximum range 0.06. Each map returned its intended original triangle ID and a hit distance within `0.0001` of `0.05`. Other coplanar or nearby triangles may also intersect the ray. These **57 sample rays** are not exhaustive proof that all possible queries or native Havok runtime behavior match.

The original retail archives, their vertex coordinates, collision code streams, and output debug geometry are **not committed**. The test fixtures are completely synthetic. The original 19 GMPs were used unchanged.

## Ray query semantics

- Input: Level-flattened XYZ ray origin, finite nonzero direction, maximum distance in **source Level coordinate units** (physical units not established), hit limit, and optional backface culling.
- Direction is normalized; reported `distance_in_level_coordinate_units` is a geometric distance measured in that original coordinate frame.
- A deterministic median-split AABB hierarchy prunes candidate triangles. Its leaf groups contain at most eight source triangles; repeated source XYZ positions are **not welded or altered** for ray intersection. It ignores only the two zero-area triangles already absent from the verified MOPP leaf set.
- Möller–Trumbore intersections return barycentric weights, source winding normal, hit position, distance, winding front/back, original Level triangle ID, original vertex IDs, render-block ID, source render-section ordinal, and render-material **name string**.
- Results are sorted by increasing geometric distance, then original triangle ID. Coincident and edge-touching faces can produce multiple hits. A ray begins hitting only after `1e-7` coordinate units to avoid self-intersection at the origin. Numerical tolerances are explicit, not promises of exact Havok behavior.
- `render_material_is_physics_material` is **always false**. No friction, bounce, filter information, physical surface type, Havok `hkpMeshMaterial`, gameplay footstep type, or game native collision shape is inferred from a render-material name.

## CLI example

On Windows PowerShell, from the DX2SDK repository root, with your own retail `.gmp`:

```powershell
python research/dx2/inspect_level_mopp_collision_raypick.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" --origin 0 0 100 --direction 0 0 -1 --max-distance 200 --max-hits 8 --report "C:\DX2_Research_Reports\seattle_hub_ray_pick.json"
```

The coordinates in the example are only illustrative; this query **may legitimately miss**. To find a known intersection, use your viewer camera's Level-coordinate origin and direction or a source triangle's centroid/normal.

The JSON output path must be outside the input map directory and must not already exist. The input GMP is never changed. With no `--report`, the JSON result is printed to stdout.

Run the standalone synthetic tests:

```powershell
python -m unittest discover -s native_editor/tests -p "test_dx2_level_mopp_collision_raypick.py" -v
```

## Remaining engine integration work

1. Wire these deterministic triangle-picking results into the SDK's **read-only 3D selection/UI layer**, preserving original triangle IDs and source render-section names.
2. Identify the actual game's Havok shape/material filtering, contact generation and triangle welding rules. External Havok versions may allow separate material-index arrays; **no DX2-specific physical-material mapping is confirmed** from the existing Level fields.
3. Verify the native BSP Model's still-unknown polygon vertex pool and surface table instead of substituting Level render vertices.
4. A native MOPP compiler, DX2 BSP rebuild, Havok shape writer and verified playable level still **do not exist**. Do not modify retail maps with this tool.
