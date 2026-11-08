# DX2Ed v0.35: T3Ed-inspired draft face editing and real project round-trip

**Scope:** source-only Godot 4.3 editor geometry drafts. No native DX2 CSG,
BSP leaf/zone, MOPP collision, GMP/IBD or runtime exports are written.

## New usable face editing

Select an authored, editor-only Box, Wall or Floor brush in the Godot
Inspector. A **Face** selector exposes the six local faces
(`-X/+X/-Y/+Y/-Z/+Z`). **In** contracts the chosen face by the
current Grid m increment; **Out** expands it. The opposite plane
does not move. On a rotated or scaled brush, the center displacement is
transformed through the existing Godot basis so the local opposite face
remains fixed in world coordinates.

The primitive builder validates the class, finite delta, dimension
bounds (0.05–256 Godot meters), and face index before changing any
preview. Unsupported draft shapes (cylinders, cones, ellipsoids,
ramps, stairs), imported original actors, source BSP meshes, Light
and collision proxies cannot receive a face resize.

Each operation uses the existing DX2Ed edit history (Ctrl+Z,
Ctrl+Y), 3D preview/orthographic views and Save draft/Load draft.
The result stays a private JSON brush spec and editor transform,
never a cooked Unreal brush or script.

## End-to-end test added

`native_editor/godot_editor/tests/smoke_t3ed_face_edit_roundtrip.gd`
runs in the actual bundled Godot 4.3 editor, entirely from invented
source-only data. It verifies the six-face toolbar, opposite-plane
anchoring for a 90-degree rotated box, bounds/unsupported-class
refusal, Undo/Redo, a moved synthetic imported actor, private
scene Save, workspace state, a changed intermediate scene,
and reloading that saved project, including the anchored face and
unchanged original fake source bytes.

`prototype/START_DX2ED.cmd --self-test` invokes the added smoke.
The Windows ZIP build and offline prototype doctor both require it;
the manifest flags the preview face editor while expressly disabling
any native BSP face writer.

## Next actual T3Ed parity steps

- Editable face selection directly in the viewport, UV/pan/rotate
  authoring, triangulated draft polygon manipulation, and
  potentially authoring-only CSG previews.
- Portable DX2Ed project scenes that preserve surface/material
  assignments across reopening and template source assets.
- Independently prove original DX2 cooked BSP/zone ownership,
  collision rebuild and source-engine runtime before writer/cooker
  permission. Current validation is **synthetic only**.

See the draft PR's exact CI results for Godot/Windows evidence.
