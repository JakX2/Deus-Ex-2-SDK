# DX2 Level flattened mesh: exact triangle indices and scaled XYZ

Read-only original retail investigation, 2026-11-03. The 19 user-owned Deus Ex: Invisible War GMP maps use UE95 licensees 65/67/68/69. No original map data, geometry arrays or game resources are committed.

## Confirmed Level serialization cross-reference

The Level export contains a second flattened representation corresponding to the previously decoded **packed Flesh render blocks**. Immediately before the arrays, a nearby native header has independently observed little-endian u32 vertex and triangle counts. Other surrounding Level fields and map-name strings remain undecoded.

- **16 bytes per flattened vertex:** f32 XYZ followed by a zero u32.
- **12 bytes per triangle:** three global little-endian u32 indices.
- The flattened sequence of triangle indices matches every packed Flesh block's u16 section indices after adding cumulative vertex offsets per block. This is **full exact sequence equality**, not shared plane candidates.
- Flattened XYZ in the same vertex order is packed-render XYZ multiplied by **0.1905**, within a conservative **0.0002** absolute per-component tolerance. Maximum observed discrepancy was approximately **0.000061** from float32 rounding. Coordinate bytes are not identical.

| Independent cross-check | Original 19-map corpus |
|---|---:|
| Maps | **19** |
| Source packed render blocks | **3,002** |
| Flattened and packed vertices | **76,732** |
| Triangles | **43,154** |
| Matching global triangle indices | **129,462 / 129,462** |
| Matching scaled float components | **230,196 / 230,196** |
| Unique full index-stream match per Level | **19 / 19** |
| Unique nearby native u32 vertex/triangle count pair | **19 / 19** |
| Nonzero fourth vertex words | **0** |

The factor 0.1905 is verified numerically. Its physical unit-system meaning is not yet established.

## Important: not the compiled-world BSP Model vertex pool

The previously decoded native world Model has separate compact field 1 and candidate polygon-vertex counts. In **all 19 maps**, the maximum field-1-plus-polygon-count endpoint exceeds the number of flattened Level vertices. Therefore, field 1 **cannot directly index this particular Level array** using its observed values. A different native vertex pool or distinct field semantics must be recovered.

This second Level array is **not yet proven to be** actual physics/Havok collision, engine-owned runtime render storage, PVS, the Model's vertex-pool array, or a complete cooked native level. Historical Unreal field names are informative but insufficient.

## Reproduction

From the DX2SDK repo root, with user's own original GMPs:

~~~powershell
python research/dx2/inspect_level_flattened_mesh_crossref.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" --report "C:\DX2_Research_Reports\level_flattened_mesh.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_level_flattened_mesh_crossref.py" -v
~~~

The script reuses the existing strict UE95 package parser and packed Flesh render-block reader. It rejects absent/duplicated full index sequences, malformed index ranges or vertex arrays, mismatched XYZ scaling, nonzero fourth words, bad count pairs, unsupported licensees and source-directory report outputs. GMPs remain unchanged. Reports are exclusively created as new JSON files outside source game directories.

## Next native compiler gates

1. Identify actual engine consumers of the flattened Level arrays; **do not label them collision** without evidence.
2. Locate the distinct compiled-world Model vertex pool and surface-table bounds; test field-1 and field-2 references against their real arrays.
3. Recover the rest of the Level-native header/footer records, associated collision/zone/visibility dependencies and resource cooking stages.
4. Only after round-trip invariants are proven should a separate writer target disposable copies and native DX2 runtime tests.

**No game-compatible DX2 geometry writer, Havok rebuild, PVS decoder, collision renderer, T3 editor interchange or playable new level is claimed.**
