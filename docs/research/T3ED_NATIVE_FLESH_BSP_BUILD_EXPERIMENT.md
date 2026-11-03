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

## T3 runtime test: custom geometry and collision confirmed by user

On 2026-11-03, the user reported **DX2SDK_Geo_Test** successfully loaded inside *Thief: Deadly Shadows* when launched through T3Ed **Build > Play Level with Game Exe (Ctrl+B)**. They subsequently tested the added cube and confirmed it **blocked Garrett's movement**. This is a first successful **user-observed runtime geometry and collision test** of the native T3Ed-edited map, not a tool-instrumented collision or Havok payload decode.

The standard command-line `T3.exe DX2SDK_Geo_Test` initially failed with a Microsoft Visual C++ 'abnormal program termination' on the loading screen, **and the unmodified stock Tutorial3 GMP crashed the same way**. The user's `User.ini` contained `LoadFromResourceBlockFiles=True` while `System/Default.ini` contained `False`. Commenting the user override did not resolve command-line loading. Switching to **Build > Play Level with Game Exe** succeeded. Do not infer that the original failed launch was caused by the rebuilt map, or that standalone command-line launching is fixed.

The [original editor release instructions](https://worthplaying.com/article/2005/2/23/news/22704-thief-deadly-shadows-game-editor-available-now/) distinguish editable `.unr`, game-ready *uncooked* `.gmp`, and cooked `.ibt` resource blocks. The test proves successful T3 runtime use of an exported custom map via the editor-integrated patched launch path, with user-observed physical blocking by newly authored geometry. **It does not show** how collision is serialized, demonstrate accurate PVS/AI/Havok for larger levels, validate IBT cooking, or establish DX2 licensee 68 compatibility.

Preserve the two UNR build snapshots and the generated GMP as private research fixtures; never commit proprietary assets. Next priority: document a DX2-specific compiler/writer design from validated shared primitives while testing the different game serializer boundaries on user-owned DX2 maps.

## Follow-up: first user-generated GMP export

On 2026-11-03, user exported `DX2SDK_Geo_Test.gmp` using **File > Export Map For Game** from the 78,727-byte After_Flesh_BSP source map.

- Exported GMP: **68,118 bytes**, SHA-256 `6b205d1cc09a299e82cf6863bf3968dd4d19e5a4977c50790b4e6c40b666eba3`.
- Source UNR: SHA-256 `289a16523e2e20c6096bcaf77e1d99d9af3d889f8419e23a0ea4d52b0544d0b9`.
- Both valid UE95 / T3 licensee133. Names/imports/exports **129/16/46 → 114/10/37**.
- Editable Polys exports **9 → 0**, Brush **7 → 7**, Model **9 → 9**.
- **All eight validated Flesh BSP render blocks survive byte-for-byte in identical order**, preserving **172 vertices**, **94 triangles** and **21,024 packed render-block bytes**.
- Level payload **46,785 → 52,303 bytes** (+5,518); its additional nonrender bytes remain uninterpreted.

**Concluded:** The native T3Ed source-to-uncooked-GMP exporter preserves newly built render geometry. **T3 game load and cube collision were subsequently confirmed by the user through T3Ed's Ctrl+B launch**; PVS, Havok data serialization, IBT generation and DX2 licensee68 writing compatibility remain unproven. No copyrighted map data is committed.

Use `research/t3ed/compare_editor_cooked.py pair` to reproduce this kind of same-name `.unr`/`.gmp` comparison; use `compare_editor_stages.py` for the two source `.unr` build stages.
