# DX2Ed v0.40: per-surface preview materials and UV authoring

## User-visible workflow

Select an editor-only custom **Polygon** brush. Its mesh is now split into three
independent Godot surfaces:

1. Top cap
2. Bottom cap
3. Side walls

The Polygon Inspector adds a surface-slot selector, preview preset selector,
U/V scale, U/V offset, and one **Apply surface style** action. The presets are
Neutral, Concrete, Metal, Ceramic and Hazard. They affect preview tint and
roughness/metallic response. A generated 64×64 checker texture makes the UV
transform visible without relying on original retail texture files.

Top and bottom UVs are derived from the normalized X/Z footprint. Side UV U
coordinates follow cumulative physical edge length around the perimeter and V
runs from the lower to upper extrusion plane. Each surface has its own material
resource and UV transform.

## Editing, history and persistence

- Each Apply validates the complete three-slot style and records one Undo item.
- Ctrl+Z/Ctrl+Y restore the previous/next preset and UV transform.
- BrushGeometry.validate accepts old Polygon drafts with no surface_style
  and supplies safe defaults.
- Present but malformed styles fail closed: unsupported presets, wrong array
  lengths, non-finite numbers, UV scale outside 0.05..64 or UV offset outside
  -64..64 are refused.
- The existing private JSON brush record stores the three style slots. The
  existing real Godot smoke exercises save, editor reload, style restoration
  and malicious UV metadata refusal before live edits are cleared.

## Why this stops short of original textures

The user-provided DX2 material explorer documents 225 MatLib records and nine
texture stages, while explicitly noting that shader effects and categories
are not yet interpreted. v0.40 therefore provides an honest procedural
checker/preset authoring surface rather than pretending a MatLib name is a
resolved, game-equivalent shader. Source texture extraction, shader-stage
semantics, original surface bindings and native BSP material indices remain
separate work.

## Verification boundary

The new surfaces and material overrides belong only to private Godot Polygon
preview brushes. No imported actor mesh, source GMP/IBD, native BSP surface,
zone, CSG, collision, lightmap, GameSys or TriggerScript is modified. No native
material writer or retail runtime compatibility claim is enabled. CI must
verify the Linux Godot geometry smoke, the bundled Windows Godot 4.3 executable
self-test, 910+ Python fixtures, portable SDK ZIP/CLI, source-only editor bundle
and fixture-free safety checks on the exact final commit.
