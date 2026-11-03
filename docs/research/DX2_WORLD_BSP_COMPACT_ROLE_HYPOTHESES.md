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

## Decision gates

- **Promote field 1 to likely iVertPool only** if native-corpus spans consistently behave as a plausible vertex pool, with exceptions explained. Polygon geometry still requires its actual indexed vertex XYZ array.
- **Promote field 2 to likely iSurf only** if coplanar links show very high surface-ID consistency **and** a separate native surface array is identified and bounded by its count.
- **Fields 6 and 7 remain opaque** until candidate bound arrays and actual collision/render consumers are located; a value beyond node_count is not an error.
- **Field 0 remains opaque** until byte-level or runtime semantics distinguish NodeFlags from other small enums.

The historical 69-byte zone record may also resemble Unreal's zone connectivity/visibility fields, but the second observed region is **32 bytes of literal 0x01**, not an all-bits-set 256-bit mask. It is explicitly **not** labeled a verified PVS or visibility matrix.

**No native writer, mapped vertex XYZ, surface table, Havok, collision compiler, PVS or DX2 runtime playtest is claimed here.**
