# DX2Ed v0.28: T3Ed-style orthographic authoring views

Status: **Godot 4.3 editor preview only**. This is a user-facing authoring workspace improvement stacked on DX2SDK v0.27 (draft PR #94), not a UE95/GMP/BSP/zone serialization discovery.

## Scope and T3Ed relationship

The 2005 T3Ed editor resources and the DX2Ed parity plan document brush, vertex, face, polygon and geometric authoring modes. DX2Ed lacked top/front/side orthographic previews with planar alignment, a core workflow when placing original meshes and editor-only draft brush primitives. T3Ed's editable Unreal source .unr and DX2 retail cooked .gmp cannot be equated; this change makes the viewport more useful without claiming game-native CSG/BSP support.

## Editor functionality

The existing Godot toolbar now offers Perspective (1), Top XZ (2), Front XY (3), and Side ZY (4). Shortcuts work when the pointer is inside the viewport and fly-look mode is not active. Fixed-axis views use orthographic camera projection; perspective camera yaw and pitch are preserved when returning to 3D. The existing middle-mouse pan, scroll zoom, and F focus are supported; Alt-left mouse pans in planar mode and orbits in perspective.

The separate Ortho grid checkbox shows a semi-transparent, editor-only plane aligned to the active camera. Grid m controls 0.25–64 Godot-meter grid pitch and synchronizes the existing Ctrl-drag move snapping and preview nudge increment. The grid is capped at 64 half-lines (default 24), validated against nonfinite inputs, and rebuilt only when its snapped camera center, projection or pitch changes. The grid is a separate editor-only non-actor mesh outside imported GLB scene geometry, never present in native output or draft actor lists.

## Implementation and test

- native_editor/godot_editor/orthographic_authoring_guides.gd: pure camera and bounded planar grid math.
- native_editor/godot_editor/main.gd: view mode UI, viewport projection transitions, grid toggle, target-aligned guide generation, shortcuts and pan/zoom behavior.
- native_editor/godot_editor/tests/smoke_orthographic_authoring_views.gd: synthetic Godot tests for camera normals, grid planes, invalid inputs and actual main editor toolbar/view mode interactions.
- prototype/START_DX2ED.cmd --self-test: invokes the new Godot script on the packaged Windows runtime. ZIP builder and offline doctor require both the helper and smoke.
- native_editor/t3ed_parity.json: updates only partial-scene-navigation evidence, without marking native geometry as verified.

## Explicit non-goals

A four-pane synchronized camera layout, face/vertex/UV/brush CSG editor, verified DX2 native BSP leaf/zone or collision rebuild, game-compatible lightmap cooking, or original-GMP writer are NOT delivered. Grid spacing is a Godot editor preview unit, not a proven DX2 authoring-unit scheme. No original retail files are opened or modified by synthetic CI. Continue preserving source hash, isolated output and non-retail-compatibility guards.

CI and Windows artifact links are to be added to the PR only after the actual CI run has passed.
