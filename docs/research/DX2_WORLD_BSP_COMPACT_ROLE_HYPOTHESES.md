# DX2 compiled-world BSP: falsifiable hypotheses for compact fields 0/1/2/6/7

Research proposal, 2026-11-03. **Not yet validated on the retail 19-map corpus in this PR.** This follows the already confirmed rooted BSP graph and exact node/zone-mask relationships in [the zone audit](DX2_WORLD_BSP_ZONE_MASK_RELATIONS.md). The separate [older Unreal FBspNode member layout](https://wiki.beyondunreal.com/Legacy%3AStandard_Unreal_Object_Definition) supplies comparison names, **not** proof of DX2's native structure.

## Historical layout comparison, not decoded DX2 field names

| Source-observed DX2 compact field | Historical Unreal FBspNode role candidate | Current status |
|---|---|---|
| 0 | NodeFlags or another compact header flag | observed 0/5; **unproven** |
| 1 | iVertPool (first polygon vertex-pool slot) | **hypothesis** |
| 2 | iSurf (BSP surface index) | **hypothesis** |
| 3 | iBack / negative-child equivalent | independently supported by rooted geometry and masks |
| 4 | iFront / positive-child equivalent | independently supported by rooted geometry and masks |
| 5 | iPlane / coplanar chain | independently supported by rooted geometry and masks |
| 6 | iCollisionBound | **hypothesis**, may exceed node count |
| 7 | iRenderBound | **hypothesis** |

Candidate two-zone indices at native record-end -21/-19, polygon vertex count at -17 and suffix i32 pair remain independently observed, not authenticated legacy-member aliases. Original Unreal builds use different zone-mask widths and serialization details; **do not import their C++ binary layout directly into DX2**.

## Measurements in the new read-only diagnostic

research/dx2/inspect_world_bsp_compact_roles.py runs the existing strict node, rooted-tree and symmetric-zone validators before measuring:

1. Field **1 + candidate vertex count**: adjacent-serialized-node exact contiguity, negative starts, zero-based union coverage, overlaps and gaps. A dense progression from zero with a maximum end matching the previously observed **82,657** vertex slots would be powerful evidence for a first-vertex index, but **is not assumed**.
2. Field **2**: agreement/differences along **field-5 coplanar links**. A common value would support a shared surface index; disagreement is recorded explicitly rather than rejected.
3. Fields **6/7**: min/max, -1 sentinel frequency, unique values, values exceeding the BSP node count. These are **not** validated as node references.
4. Field **0**: numeric distribution and earlier 0/5 observation. It is **not** promoted to an enum or proven NodeFlags.

Run from repo root with original, user-supplied DX2 maps:

~~~powershell
python research/dx2/inspect_world_bsp_compact_roles.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" --report "C:\DX2_Research_Reports\bsp_compact_roles.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_world_bsp_compact_roles.py" -v
~~~

Optional --include-nodes includes all eight raw compact values per node (large JSON). Reports are exclusively created outside input map directories, with source hashes. No original map bytes are written, and no game assets are distributed.


## Independent 19-map original-corpus observation (2026-11-03)

The user's privately shared Maps ZIP was analyzed locally, without modifying or publishing the retail maps. A **separate bounded UE95 and World Model reader**, using the same previously observed framing, checked all 19 source maps. It independently reproduced the prior **17,743 nodes, 688 zone records, 82,657 polygon vertex-count slots**, rooted-parent constraints and exact zone-mask OR relationships. The numeric role measurements used the pure analyze_rows function from PR #26. This private read is **not** a run of the full repository CLI, and its results must not be treated as proof of native member names or geometry writing.

| New property | Original-map observation |
|---|---:|
| Field 1 values unique and nonnegative | 17,743 / 17,743 nodes; all 19 maps |
| Candidate field-1 spans overlapping | **0** |
| Field-1 spans touching in **sorted index order** | 11,415 / 17,724 adjacent interval pairs |
| Sorted field-1 intervals separated by positive gaps | 6,309 / 17,724 |
| Total summed internal gap slots across maps | 138,837 |
| Field-1 index/vertex ranges forming a complete zero-based dense pool | **0 / 19 maps** |
| Field 2 values covering each map's zero-based range with no missing integer | **19 / 19 maps** |
| Field 2 equality across field-5 coplanar links | **4,161 / 7,733** (53.8%) |
| Field 6 nonnegative indices | 6,923, all distinct per map; sparse |
| Field 6 values at least as large as that map's node count | 5,443 |
| Field 7 nonnegative indices | 7,398, all distinct per map |
| Field 7 covers zero through its maximum with **no missing values** | **19 / 19 maps** |

**Interpretation:** Field 1 is now a much stronger **first-vertex-start candidate**: unique ranges and zero overlaps are exactly what one expects of non-shared polygon vertex storage. However, many gaps rule out an unqualified claim that those 82,657 slots alone form the *entire* dense vertex pool. Field 2 behaves like an index into a smaller shared table (possibly BSP surfaces); differing values across coplanar chains are not unexpected for distinct surfaces, and must not be discarded. Fields 6 and 7 have distinct index-domain signatures, with field 7 looking like a compact zero-based per-record table and field 6 like an offset-bearing/sparse table. These could be collision/render bounds but **neither name is proven**.

The added profiler emits index_shapes (unique/dense/holes per field) and both original node-order and **sorted-span** gap counts. The two notions of adjacency are intentionally separated. An original map must not be rejected solely because its vertex ranges contain gaps or its coplanar links reference different candidate surfaces.

Next tests: find the actual native vertex-pool and surface-count fields; verify every field-1 range and every field-2 index against those independently serialized arrays. Then locate consumers/arrays for fields 6 and 7. Only independent bounds checks, references and actual vertex XYZ recovery could promote these hypotheses to a loader schema.

## Decision gates

- **Promote field 1 to likely iVertPool only** if native-corpus spans consistently behave as a plausible vertex pool, with exceptions explained. Polygon geometry still requires its actual indexed vertex XYZ array.
- **Promote field 2 to likely iSurf only** if coplanar links show very high surface-ID consistency **and** a separate native surface array is identified and bounded by its count.
- **Fields 6 and 7 remain opaque** until candidate bound arrays and actual collision/render consumers are located; a value beyond node_count is not an error.
- **Field 0 remains opaque** until byte-level or runtime semantics distinguish NodeFlags from other small enums.

The historical 69-byte zone record may also resemble Unreal's zone connectivity/visibility fields, but the second observed region is **32 bytes of literal 0x01**, not an all-bits-set 256-bit mask. It is explicitly **not** labeled a verified PVS or visibility matrix.

**No native writer, mapped vertex XYZ, surface table, Havok, collision compiler, PVS or DX2 runtime playtest is claimed here.**
