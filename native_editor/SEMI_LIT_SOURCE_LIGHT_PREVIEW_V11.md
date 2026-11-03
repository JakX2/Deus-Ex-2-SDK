# DX2Ed v11: semi-lit source Light map preview

Status: experimental editor-only rendering mode, **not** original DX2 baked/static lighting.

## How to use

1. Launch the Godot 4.3+ native editor and open a DX2 map with
   source-matched `actors.json` containing original `Light` instances
   and readable GameSys LightColor/LightShape fields.
2. Check **Semi-lit (map lights)** in the toolbar (next to Auto Roll).
3. The editor lowers the bright preview sun/ambient lights and places up
   to 32 non-shadowing Godot `OmniLight3D` proxies, selected by distance
   to the camera from valid source Light actors. Moving the camera more
   than 3 m periodically refreshes the selection.
4. View the count indicator: `N/total source lights (approx.)`. If
   actors do not provide usable original light fields, semi-lit is
   unavailable rather than guessing generic values.
5. The v10 Environment Light color/radius/brightness controls modify
   the corresponding in-viewport proxy, if active. W-position preview
   moves that proxy too. The v10 single live preview node is suppressed
   in this mode so it does not double the lighting.
6. Uncheck Semi-lit to restore default scene lighting and remove every
   global preview proxy. Map changes reset mode and nodes.

## Actual rendering versus approximation

- Positions come from the same original source Light actors used for
  clickable v9 markers.
- Source `LightColor` and `LightShape` yield approximate Godot color,
  brightness and radius. They are **not** the DX2 renderer's calibrated
  attenuation, baking or shadow algorithms.
- An explicitly authored `bLightOn = false` is skipped. Missing
  `bLightOn` is not interpreted as proof of engine state.
- Semi-lit changes baseline Godot directional-light energy 1.6 -> 0.18
  and ambient energy 1.1 -> 0.38, retaining enough visibility to edit.
- Selected nearby lights run without shadows. All map-wide nodes live
  under `DX2Ed_SemiLit_Source_Approximation_EDITOR_ONLY`, separate from
  imported scene GLB and all actor/export drafts.
- GL Compatibility rendering can apply per-mesh light limits even
  when 32 Godot light nodes exist. That is not an exact renderer parity
  claim. Some imported materials may react differently, especially
  emissive and alpha-blended surfaces.

## Non-goals

No GMP/IBD writes, Light actor creation, authored LightColor edits,
BSP/zone rebuild, lightmap reconstruction, baked shadows, light
occlusion through walls or engine-equivalent attenuation. Retail
Windows visual testing is outstanding.

## Tests

Godot 4.3 headless smoke checks original actor properties remain
untouched, separated proxy nodes, correct read-only positions,
source-derived light values, enabled/disabled global brightness,
color/range/energy overrides, preview moves and cleanup. Python
backend fixtures stay unchanged.
