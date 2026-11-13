# DX2Ed v0.95: export a private clipped Box OBJ from the Godot Inspector

**Scope:** export only an **editor-authored private** `Brush::Box` with a validated one-to-eight-plane convex clip stack. This is a source-independent Wavefront OBJ for external 3D inspection, **not** a retail DX2 World BSP/CSG write, collision bake, original map export or playable level.

## Editor workflow

1. Open the Godot 4.3 DX2Ed prototype and select exactly one **editor-created** `Brush::Box` preview copy with at least one valid 3D cut.
2. In the **3D Box plane clip (private preview only)** Inspector section, click **Export private Box OBJ...**.
3. Choose a new `.obj` path. Existing files cannot be overwritten. The editor binds the dialog to the selected private draft name at the moment the dialog opens and refuses the export if the selection changes meanwhile.
4. The private converter writes a local Y-up, metre-scaled, triangle-only OBJ with separated per-face normals and `private_cut_cap_XX` / `private_box_side_XX` polygon groups. Success includes triangle count and SHA-256 in the editor status bar.
5. Inspect the mesh externally in Blender or a compatible OBJ reader. The OBJ contains **no game materials, UVs, original DX2 surface identifiers, collision or gameplay data**.

## Reuse the independent Python exporter

The Godot helper `native_editor/godot_editor/private_box_obj_bridge.gd` validates its private clipped brush and saves *only the normalized brush spec*, never map, actor, source file or original game metadata, to an ephemeral `user://private_box_obj_stage` JSON document.

It runs the separately bundled, path-anchored `backend/dx2_private_obj_export_worker.py`, which resolves the repository/package root and imports the **already tested v0.93** `dx2sdk.private_brush_obj` Python exporter. The worker regenerates the independent v0.92 triple-plane convex topology and checks the exported OBJ's triangle orientation, counts and bounded output.

The worker is invoked without a shell and follows the same Python executable configuration/fallback as other Godot workers. The temporary private JSON is removed whether export succeeds or fails. User-facing success is reported only if the Python process returns zero, a valid success record is parsed, and the selected new file exists.

Input provenance is enforced twice: the Godot Inspector requires the actual selected private `Brush::Box` copy, and the Python path accepts only its normalized private Box schema. A click on an imported original actor, source BSP overlay, uncut Box, or a changed selection cannot use this export route. The Python converter also refuses symlinked or existing output files and invalid extensions, including `.gmp` and `.ibd`.

## Source-independent regression

`native_editor/godot_editor/tests/smoke_private_box_obj_export.gd` exercises the actual Editor signals and real Python process under Godot 4.3, without any original game assets:
- Build a synthetic 2×2×2m private clipped Box and verify the **Export private Box OBJ...** button and FileDialog are enabled.
- Emit the Inspector button and file-selected signals; assert that the exported OBJ has **8 vertices, 6 faces, 12 triangles**, the expected cap group and matching SHA-256.
- Confirm source-independent brush metadata and Undo history do not change, no private staging JSON remains, and a dummy `mock_original.gmp` byte hash stays identical.
- Attempt a second export to the same path and confirm it refuses overwrite.
- Change the selection to a synthetic imported StaticMeshActor while the dialog is open and confirm the original source cannot export.

The Godot native scene fixture CI compiles the bridge and runs the smoke. Portable Windows prototype package manifests and source-only preflight require the bridge, Python worker and test.

## Still missing

This does not change the original DX2 World Model, alter any native BSP vertex/surface/node ownership, write actor records or cook Havok/MOPP collision. A matching private OBJ is **not** an engine-compatible map, and retail runtime load/play tests have not established it as such. T3Ed import/export remains **partial**. Native World Model source-provenance research remains the larger task.
