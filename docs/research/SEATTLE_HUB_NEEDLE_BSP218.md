# Seattle Hub / Needle BSP_218 investigation

Verified on 2026-11-03 against the original user-provided
`maps.zip` → `M1_Seattle_hub.gmp`, SHA-256
`57c8502db646db3f98448863fd8f0b4bd3a89dc6bb6738b2f8f5ad69ed9f58bd`.
The original map binary remains private and is **not** committed.

## Confirmed source geometry

The screenshot of the Needle selected `BSP_218` and showed material
`M1WTO_hangerfloor1` on a very large vertical rectangle.

An independent raw GMP signature scan using the same validated packed
BSP header/vertex/index/section structure as `find_bsp` found exactly
255 validated render blocks in the original map. Original block index
218 matches the screenshot:

- Serialized block ID: **264**.
- **4 source vertices and 2 non-degenerate triangles** in one section.
- Material: **`M1WTO_hangerfloor1`**.
- Source coordinates: Unreal X ranges **-3072..-2016**; Y is
  **constant -1152**; Z ranges **512..1664**.
- All four packed normals point along negative Unreal Y.
- Original coordinate-space rectangle size: 1056 × 1152 UE units,
  or approximately 20.12 × 21.95 Godot metres at the viewer's
  existing 0.01905 conversion ratio.
- The source material appears on **46 sections elsewhere in this map**
  and is used in multiple orientations. Its name alone therefore does
  not establish that the surface ought to be horizontal.

**Conclusion:** This is a real, coherent, pre-existing vertical
BSP quad inside the original GMP, **not a floor accidentally
rotated by the Godot X/Z axis conversion**. All material indices,
vertex coordinates and triangle normals agree on that interpretation.

## Why it is visible in DX2Ed

The current exporter (`map_exporter/dx2scene.py:find_bsp` and
`map_exporter/dx2level.py:Builder.bsp_block`) accepts the source
BSP render block and sends all material sections except special
`bf` sections to the Godot scene. It does **not** reproduce the
retail engine's native BSP region/visibility or camera-based
portal/occlusion logic.

This is a strong explanation for why an otherwise unused/occluded
surface may become visible while freely flying outside the playable
world. However, **we have not demonstrated that the retail engine
actually suppresses this specific block** or determined whether the
author placed it deliberately. Do not change the source game map or
silently remove it from all exports yet.

## Tools added

1. `map_exporter/dx2_bsp_anomaly_audit.py`: source read-only
   block material, source/viewport bounds, normals, triangle area,
   geometry degeneracy and neighboring-block report. By default
   inspects block 218. It refuses to overwrite an existing report.
2. Godot Inspector: **Hide selected BSP (preview)** / **Restore hidden BSP**,
   working on a currently selected `BSP_*` mesh. This is a
   reversible **visibility-only** operation, never a native edit or
   modification of the original imported mesh asset. The current
   scene reload restores visibility.
3. Synthetic Python and Godot tests enforce data/preview isolation.

## Reproduce locally

From the SDK repository root:

```powershell
python map_exporter/dx2_bsp_anomaly_audit.py "C:\Games\Deus Ex Invisible War\Content\DX2\Maps\M1_Seattle_hub.gmp" --index 218 --output "$env:USERPROFILE\Desktop\needle_bsp218_report.json"
```

The exact source filename path is illustrative; use the user's local
legitimate installation. Never run an editor/native GMP write just to
inspect this issue.

## Next research gate

Compare the same camera position inside retail DX2 if reachable,
or reconstruct BSP sector/PVS and block visibility metadata. If the
game truly never renders this surface, add a narrowly targeted,
explicitly **preview-only** optional visibility rule, rather than
editing native geometry or guessing material-wide exclusions.
