# Native T3Ed Flesh BSP build: controlled stage-pair experiment

Research date: 2026-11-03. Goal: use the native *Thief: Deadly Shadows* (T3) editor as a research reference for DX2SDK, **not** assume that T3 licensee 133 maps work in *Deus Ex: Invisible War* (licensee 68).

## Inputs and provenance

A Windows experiment added a BSP brush to a copy of Tutorial3.unr, saved After_Unreal_BSP/DX2SDK_Geo_Test.unr following Rebuild Geometry and Unreal BSP, and saved a second DX2SDK_Geo_Test.unr after the user reported running Build Flesh BSP. The tool did not directly observe either editor command, so attribution is based on the stated sequence. Binary maps remain user-owned and are **not committed**.

- After_Unreal_BSP: 66,131 bytes; SHA256 1b68fd4a6be01dba0f6ab330b839407ae3798509b184bb7557fb962a1b3ab3c2
- After_Flesh_BSP: 78,727 bytes; SHA256 289a16523e2e20c6096bcaf77e1d99d9af3d889f8419e23a0ea4d52b0544d0b9
- Both packages: Unreal 95, T3 licensee 133, 46 exports, 7 Brush / 9 Model / 9 Polys.

## Read-only findings

| Measurement | After Unreal BSP | After Flesh BSP | Delta |
|---|---:|---:|---:|
| Package bytes | 66,131 | 78,727 | +12,596 |
| Level payload bytes | 34,179 | 46,785 | +12,606 |
| Validated packed BSP render blocks | 4 | 8 | +4 |
| Render vertices | 120 | 172 | +52 |
| Render triangles | 66 | 94 | +28 |
| Render index entries | 198 | 282 | +84 |
| Packed render-block bytes | 14,536 | 21,024 | +6,488 |

Three original blocks survive **byte-identically** (source indices 1–3, target indices 5–7). The first source block becomes unmatched while five target blocks appear in the same broad region. That is consistent with new spatial partitioning/re-tessellation, but exact one-to-many lineage is not established by the hashes.

Material triangle counts: DOCfloorB_D (38 to 52), GENCeilingA_D (14 to 26), GENgoodnessIRON_D (14 to 16). The 6,118-byte increase outside validated render blocks is opaque. No collision, Havok, PVS, AI or lighting semantics may be inferred from that size change.

## Reproducible audit

Run with Python from the DX2SDK repository root, passing two same-named .unr paths in the correct order:

    python research/t3ed/compare_editor_stages.py C:\Snapshots\After_Unreal_BSP\DX2SDK_Geo_Test.unr C:\Snapshots\After_Flesh_BSP\DX2SDK_Geo_Test.unr --report C:\Snapshots\Reports\stage.json

The report is JSON-only and must be written to a **new path outside the input map directories**. It records the two SHA-256 identities, class/export changes, per-block bounds, vertices, triangles, materials and exact one-to-one byte matches. Unmatched blocks are not treated as proven actor lineage. Input snapshots are never changed.

Synthetic, game-asset-free tests:

    python -m unittest discover -s native_editor/tests -p test_t3ed_flesh_stage_audit.py -v

## Next gate: run the new geometry in Thief 3

The [original Ion Storm editor release instructions](https://worthplaying.com/article/2005/2/23/news/22704-thief-deadly-shadows-game-editor-available-now/) distinguish editable .unr, game-ready **uncooked** .gmp, and cooked resource blocks .ibt. Test only in a separate game/editor installation:

1. Export DX2SDK_Geo_Test.gmp from the editor's **Export .gmp file** command.
2. In that test installation's user.ini, comment out LoadFromResourceBlockFiles=true (prefix the line with a semicolon) to enable GMP loading.
3. Close the editor and run **T3.exe DX2SDK_Geo_Test** from System.
4. Confirm whether the map loads; walk into the cube, check collision and rendering; collect the exported GMP and logs.

The editor toolbar Play Map requires the **debug-only T3MainOptVersion.exe** replacing a backed-up T3Main.exe in a test installation, per the original release instructions. Do not replace a retail executable merely to run this test.

T3 runtime verification remains pending, and T3 compatibility **does not** prove DX2 runtime compatibility.
