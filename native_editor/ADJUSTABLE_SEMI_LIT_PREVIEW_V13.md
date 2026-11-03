# DX2Ed v13: configurable lighting preview and source diagnostics

**Status: Godot preview controls, not native DX2 lighting export.** This
extends v11 semi-lit mode and v10 per-Light visual Inspector settings.
Do not conflate Godot `OmniLight3D` nodes with DX2's baked, visibility-
capped, shadowed or runtime light sources.

## Why

The user tested v12 on original `M1_Seattle_hub.gmp`. Their screenshot's
toolbar showed `32/41 source lights (approx.)`. The **32** was
DX2Ed v11's editor-imposed nearest-to-camera cap; the 41 were source
Light actor candidates with readable LightColor/LightShape and original
positions. That counter alone cannot establish why a given game wall is
dark. GL Compatibility per-object local light limits, attenuation,
source radius conversions, materials, baked lighting and zone/portal
occlusion are independent factors.

## New user controls

1. Open an original GMP with matching original IBD resources in the
   Godot DX2Ed project.
2. Check **Semi-lit (map lights)** and select **Lighting...** in the
   map toolbar.
3. Choose a **Preset**:
   - **Editor (fully lit)**: original preview key 1.6 / ambient 1.1;
     releases all semi-lit OmniLight3D nodes.
   - **Semi-lit (v11)**: 32 nearest lights, ambient 0.38,
     radius x1.0, brightness x1.0 (same as original v11).
   - **Brighter**: All valid lights (safety cap 256),
     ambient 0.60, radius x1.50, brightness x1.20.
   - **Dark**: 32 nearest lights, ambient 0.15, radius x0.85,
     brightness x0.85.
   - **Custom**: manual sliders/spinboxes retain settings.
4. Adjust **Source light nodes** between 8, 16, 32, 64 or
   **All (safety max 256)**. The default is 32 to preserve v11
   performance. All is limited to 256 for editor stability, so
   a map with more than 256 valid lights will still have exclusions.
5. Adjust **Ambient energy** (0..2), **Source radius multiplier**
   (0.25..4), and **Source brightness multiplier** (0.1..4).
   Settings are Godot values; they do not rewrite the `LightColor`
   or `LightShape` GameSys properties.
6. Inspect source diagnostics for original Light count, eligible
   candidates, active Godot nodes, capped candidates, explicitly OFF
   `bLightOn=false` and missing/invalid source data.
7. The source list labels each Light **ACTIVE**, **LIMITED**, **OFF**,
   or **INVALID**. Double-click a source to focus the original
   editor actor. Only the first 500 eligible IDs are displayed if
   unusually large map data would exceed that count.

## Semantics, limitations and safety

- Light source names and locations come from unmodified `actors.json`
  bound to an original GMP. Only actors with readable source LightColor
  (GameSys 116) and LightShape (118), original markers and valid
  positions enter the scene-wide preview.
- An explicitly-authored `bLightOn=false` is excluded; absent
  `bLightOn` remains UNKNOWN and is not treated as proof of native-on.
- For budgets smaller than the eligible source count, the nearest
  positions to the editor camera are ranked, with stable actor-name
  tie breaking. The algorithm does not reproduce native visibility,
  linked-flicker logic, shadow casting, per-zone illumination or
  lights through walls.
- Selected per-Light preview color/radius/brightness and position
  offsets still affect its active scene-wide Godot light. Global
  radius/brightness multipliers apply afterward and are bounded.
  While in semi-lit mode, selected Light wire-radius sphere reflects
  the global radius multiplier.
- Godot's Compatibility renderer may restrict how many local lights
  actually shade each mesh; an ACTIVE entry means the editor node
  exists, **not** that it illuminated every triangle.
- Toggling Semi-lit OFF or selecting **Editor (fully lit)** frees all
  scene-wide source light nodes and restores baseline key/ambient.
- This panel never changes `actors`, original `game_properties`,
  exported GLB materials, `draft_prop_copies`,
  `property_overrides`, GMP serialization, IBD data or retail files.
- Settings are session-only and intentionally not written into a
  persistent game/map draft.

## Validation

The Godot 4.3 headless smoke creates 41 synthetic eligible original
Lights plus one explicitly OFF and one invalid source. It confirms:
- Default mode 32/41, with exactly nine LIMITED source IDs.
- All mode creates 41 editor-only lights, zero LIMITED,
  while respecting source data and performance max of 256.
- Ambient/radius/brightness changes alter Godot values only.
- Dark and Editor presets reset counts/illumination correctly.
- UI labels OFF/INVALID source IDs and source GameSys data and
  all native draft state remain unchanged.

Windows visual validation against the user's real Seattle Hub is
still required. A more accurate DX2 lighting reconstruction remains
a separate, significantly larger research task.
