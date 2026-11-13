# DX2Ed prototype P102: disposable Godot CSG geometry preview

**Scope:** This is an editor-private *visualization* of the previously tested P100 intersection and P101 multi-piece subtraction results. It does not create a native World BSP, game actor, Havok/MOPP collider, game-compatible material or modified retail package. There are no game source writes and no merge to main.

## Editor workflow

1. Use the existing private Godot Box authoring tools to create and clip **two** `Brush::Box` drafts. Both must have at least one validated cut plane.
2. Ctrl-select those **two** private drafts in the scene or hierarchy, not original BSP/source actors or imported meshes. A and B are assigned in **alphabetical draft name order** to avoid accidental reversal. The earlier-named draft is **A**, the later-named is **B**.
3. From the toolbar, click **Preview CSG A ∩ B** (transparent green) or **Preview CSG A - B** (transparent orange). A small read-only result in the status bar shows the source names, operation, piece count and volume in cubic metres. Zero-volume intersection/subtraction returns no rendered pieces.
4. Click **Clear CSG preview** to remove only the disposable colored overlay. The editor also discards stale CSG snapshots when brush geometry changes, a genuine editor change is recorded, Undo/Redo applies or a map is closed/reloaded.

## Implementation and source isolation

- `private_csg_preview_bridge.gd` validates both selected private brush specifications, serializes **only** those Box specs and each local-to-world preview pose into four unique `user://private_csg_preview_stage/csg_*.json` files, calls a path-anchored Python worker, reads its bounded JSON report and deletes all four staging files on both success and refusal. It never passes original GMP, IBD, BSP actors or source map paths.
- `backend/dx2_private_csg_preview_worker.py` invokes the existing `dx2sdk.private_brush_intersection` or `dx2sdk.private_brush_subtraction` source-private numerical backend, with no output-file destination.
- `private_csg_preview_mesh.gd` checks the operation-specific source-isolation and closed-shell flags, bounds vertex/face/triangle/piece counts and checks triangle orientation before emitting transient Godot `ArrayMesh` triangle geometry.
- Overlay `MeshInstance3D` objects are children of `DX2Ed_Private_CSG_Visual_Only`, **not** inserted into draft prop tables, original actor lists, source scene JSON, Undo snapshots, source pick lists, or native collision maps.
- The generated geometry is colored distinctly from the original editable drafts. It is a snapshot of two selected brushes, **not** a persistent new brush or live boolean modifier.

## Synthetic evidence

The headless Godot 4.3 fixture `tests/smoke_private_csg_preview.gd` exercises the actual toolbar events, Python worker and mesh builder using two authored clipped half-Boxes. It checks a translated subtraction and intersection that each yield a 2 m³ closed solid; a **48 m³ A minus 4 m³ internal B** case generating **six separate Godot mesh nodes** enclosing 44 m³ total; rejection of fractional JSON vertex indices; selection/name ordering, material mesh generation, no Undo changes, invalid source original actor refusal, brush-edit invalidation, no private temporary JSON leaks and an untouched synthetic original-GMP sentinel. Windows source prototype package manifests and the offline package doctor now require the bridge, worker and fixture.

## Important limitations

The preview uses the editor's private Y-up metres and **proper-rigid** transform basis. Reflections, scaling, malformed/degenerate meshes, over-capacity or near-tangent results are refused by the underlying geometry backends. This does not reconstruct retail engine World BSP/CSG, material UVs, zones/portals, IBD actor data, native GameSys references, Havok/MOPP collision or a playable custom mission. It is a visible geometric foundation for subsequent research, not T3Ed parity or a production 1.0 release.
