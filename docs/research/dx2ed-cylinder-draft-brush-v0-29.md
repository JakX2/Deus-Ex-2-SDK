# DX2Ed v0.29: cylinder preview brush

Adds **Cylinder** to the existing Godot Brush tab's primitive dropdown. The existing size controls set its X/Z diameters and Y height; the normal preview creation, hierarchy selection, inspector dimensions, duplication, undo and private draft save/load paths are reused. The generated mesh has 24 radial segments, closed top/bottom caps and side triangles (288 vertices). No native actor class or new binary writer is introduced.

The bundled orthographic authoring Godot smoke now validates the actual mesh builder's primitive count and rejects zero dimensions and non-unit non-stair step counts. All dimensions remain bounded by the existing brush validator. The editor-owned draft format continues to store a validated kind/size/steps record; source GMP/IBD files are never overwritten. A Cylinder is only a preview mesh, **not** a native Unreal brush, BSP leaf, collision solid, CSG result, UV/lightmap cook, or retail-compatible level edit.

CI should execute the bundled Windows Godot self-test and source/portable SDK workflows against this exact head before calling the feature validated. No proprietary game assets are required.
