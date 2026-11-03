# DX2Ed v10: Light preview Inspector (source-only)

This work builds on the v9 selectable original DX2 Light markers and
three-axis **editor-only** move gizmo. It is NOT a native Light writer.

## Workflow

1. Open a legitimate original DX2 GMP through the normal DX2Ed flow, then
   select **Environment**. The tab is scrollable on smaller displays.
2. Click a yellow source Light marker, or select a native `Light` actor in
   the Environment list. The existing yellow radius wire sphere and W move
   gizmo should appear.
3. Change **Preview color**, **Radius (preview m)** or
   **Brightness (preview)**. The sphere immediately follows preview radius.
4. Check **Live lighting at selected source marker** to create one Godot
   `OmniLight3D` visualization at the current editor-only marker position.
   It follows W movement and changes to the Inspector's preview values.
5. Use **Reset selected Light preview appearance** to discard that actor's
   temporary appearance overrides. Use the existing **Reset selected Light
   gizmo preview** to restore its original position.
6. Uncheck Live to remove the transient light. Switching to a non-Light
   entity automatically removes the live light. Map reload clears all
   visual overrides and temporary light nodes.

## Data and boundaries

- Original `LightColor` (GameSys 116) and `LightShape` (118) values are
  read as source evidence. Missing or invalid source fields disable the
  editable preview controls.
- Source hue/saturation bytes are converted to a Godot color. Source
  brightness and radius are approximated as respectively
  `clamp(brightness / 64, 0.05, 2.5)` and
  `clamp(radius * 0.12, 0.5, 16)`. These ARE NOT verified retail engine
  equivalents. UI values operate in Godot preview units only.
- Temporary appearance settings live in
  `environment_light_visual_settings` and never in
  `actors`, `game_properties`, `property_overrides`,
  `draft_prop_copies` or GMP writer plans. The live light is
  marked `editor_only`, parented outside imported GLB, never exported.
- No DX2 BSP leaf/zone recalculation, baking, runtime lighting,
  new Light actor creation, or native GMP LightColor/LightShape edit is
  enabled. Do not claim game lighting edits from visual preview behavior.
- Current design previews one selected live source light at a time and
  keeps the older "Preview selected Light at camera target" feature
  separate, with its existing eight-node maximum.

## Validation

`native_editor/godot_editor/tests/smoke_triangle_picking.gd` exercises
selection, live node provenance, preview color/radius/energy, finite/bounds
gates, W-proxy following, reset behavior, original GameSys immutability and
no accidental prop/native draft state. The repo CI also runs Python source
fixture tests. Windows UI appearance and actual retail runtime behavior
require user verification after CI.

The original DX2 GMP, original retail assets and third-party executable
tools remain private and are not included in this branch.
