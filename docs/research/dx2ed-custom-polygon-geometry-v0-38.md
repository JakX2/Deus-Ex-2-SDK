# DX2Ed v0.38: editable custom concave polygon geometry (editor drafts)

## New genuinely user-authored geometry

DX2Ed now has a **Polygon** brush type in the existing Brush tab.
Unlike the eight preset primitives, its planar X/Z footprint can have
**3 to 32 vertices** arranged in a simple (including concave) polygon.
Starting from a six-vertex L shape, users choose a vertex in the Inspector,
move its X/Z coordinate (local normalized -1..+1), insert a new corner
slightly inward from an existing edge, or delete a corner. The existing
Size X, Y, Z controls scale the footprint width, extrusion height, and
depth. Translate, rotate and duplicate using the existing T3Ed-inspired
view/gizmos and selection hierarchy.

Top and bottom caps use `Geometry2D.triangulate_polygon`; every edge
generates a bounded two-triangle side wall. The result is a closed,
triangulated **Godot preview mesh** that can produce irregular corridors,
platforms, niches and walls, not merely standard cuboids. Original
`Box/Wall/Floor/Stairs/Cylinder/Cone/Sphere/Ramp` tools are unchanged.

## Safety, determinism and save/load

The geometry helper at `native_editor/godot_editor/custom_polygon_geometry.gd`
rejects duplicate/near-zero edges, self-intersections, non-finite data,
out-of-range coordinates, polygons with negligible area, missing valid
triangulation or more than 32 points. It accepts clockwise and
counterclockwise outlines with consistent top/bottom and side winding.

All authoring goes through the existing `BrushGeometry.validate` and
`_set_brush_spec` paths before a preview mesh is replaced. Brush outline
coordinates are stored explicitly in the existing editor-private draft
`copies[].brush.outline`, alongside its `size`, `kind` and `steps`.
Duplicating a custom brush deep-copies that outline. Undo/Redo replays
its spec and rebuilds the preview. Loading a malformed custom shape
fails **before** replacing current editor geometry, retaining the strict
preflight established in prior milestones. No new retail DX2 map writer
or user-original file changes are authorized.

## Real Godot integration test

`smoke_custom_polygon_geometry.gd` in the packaged Godot 4.3 Windows
self-test checks construction of a concave closed L-shaped extrusion,
reverse winding, top/bottom/side vertex counts and scene dimensions,
invalid or self-intersecting polygon refusal, real Inspector controls,
vertex move/insert/delete, Undo/Redo, private project Save, source-sha
preservation, full saved-shape/editor-state restore and refusal of a
synthetic malicious JSON draft before mutating live scene edits.

The Windows release builder/doctor requires both the helper and smoke
file, and the source-only release manifest explicitly marks preview
custom polygon authoring while declaring native CSG cooking disabled.

## Limitations and next features

This is a true **custom 2D polygon footprint extruded vertically**, not
arbitrary nonplanar topology. It does not yet have direct viewport
corner handles, multiple holes in one footprint, CSG subtractive
brushes, per-face UV/material editing or nonvertical 3D vertex movement.
These are viable next editor features.

Retail DX2 native BSP leaf/zone, portal, collision/lightmap rebuilding,
engine cooker, original actor class spawning and actual game acceptance
remain **unverified**. No claim that a Godot draft polygon becomes a
playable cooked DX2 mission. No proprietary game bytes are checked in.
