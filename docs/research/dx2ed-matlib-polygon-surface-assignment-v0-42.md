# DX2Ed v0.42: source-backed MatLib diffuse assignment to private Polygon surfaces

## User workflow

1. Select one editor-only Polygon brush.
2. Choose Top cap, Bottom cap or Side walls in the Inspector.
3. Open Materials and select a MatLib record with a resolved, verified diffuse preview.
4. Press **Apply diffuse to selected Polygon slot**.
5. Continue editing that slot's existing preset tint/roughness and U/V scale/offset, or clear the source diffuse to return to the procedural checker.

Only the selected private Polygon surface is changed. One assignment creates one existing editor history transaction, so Ctrl+Z/Ctrl+Y restores the exact before/after surface metadata and preview mesh.

## Source identity and cache verification

The assignment records:
- private catalog path and catalog SHA-256;
- catalog ID derived by the read-only catalog worker from its source-file identities;
- material name, source bundle, source label, version, flags, stage mask and category ID;
- resolved diffuse stage and texture name;
- texture source bundle, format, dimensions and usage;
- relative preview path and preview SHA-256.

The assignment validator accepts exactly the known metadata keys, bounds strings and numeric fields, requires a catalog under `user://dx2ed_material_cache`, and rejects absolute/traversing preview paths. The loader reopens the catalog, checks its digest and schema, matches the exact material and stage record, confines the preview beneath the catalog directory, checks its size and digest, then decodes the PNG.

A private project can still reopen if a cache is missing: its validated assignment metadata remains, while the surface renders the procedural checker. A changed catalog or thumbnail never silently substitutes a different texture. The Inspector reports the fallback state; **Clear source diffuse** removes the saved assignment.

The editor caches already-verified decoded textures during the current session so vertex dragging and geometry rebuilds do not repeatedly parse a potentially large MatLib catalog. A new process re-verifies the catalog and thumbnail during project reopen.

## Validation

The asset-free Godot smoke creates a synthetic IBD sentinel, one synthetic MatLib record and a generated 8×8 PNG. It exercises:
- Materials workspace search and resolved diffuse selection;
- application to only the selected side surface;
- source/catalog/thumbnail identity persistence;
- one-step Undo/Redo;
- private JSON Save and reopen with a reverified texture;
- tampered PNG rejection and procedural checker fallback;
- malformed assignment preflight preserving the current editor scene;
- byte-identical synthetic source sentinel after authoring.

The smoke is wired into Linux Godot 4.3 CI and the packaged Windows `START_DX2ED.cmd --self-test` suite. Python SDK remains v0.27.0.

## Scope and limits

This is a source-backed **Godot preview binding** for editor-created Polygon surfaces. The nine MatLib stage references remain metadata; DX2 shader effects/categories, blending, animated stages, environment maps, native surface indices and original BSP bindings are not interpreted or written. No original IBD/GMP bytes are modified. Native BSP/CSG/collision/lightmap cooking, GameSys/TriggerScript execution and retail game compatibility remain disabled/unverified.
