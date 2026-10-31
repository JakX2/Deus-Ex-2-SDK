# DX2Ed 3D Actor Explorer 0.2 (experimental)

**Textured 3D level viewport plus read-only actor inspector, using original Invisible War maps.** Windows GUI; requires Python 3.9+ and a modern browser with WebGL2 (Chrome, Edge, Firefox).

The 3D GLB uses our existing DX2Ed map exporter. Each mesh node stores `DX2ExportIndex`, which this editor matches with a decoded actor from the GMP. Selecting a mesh gives you the name, class, position, rotation, game properties and linked scripts. This is **not** yet the Thief 3 Editor and **cannot save changes to a GMP map**.

## Windows use

1. Extract the ZIP anywhere. Keep the `dx2ed_3d` folder intact.
2. Double-click **`START_DX2ED_3D.bat`**. Python 3.9 or later must be installed.
3. Select an original `.gmp` in `Deus Ex Invisible War\Content\DX2\Maps`.
4. The exporter will attempt to detect its matching `.ibd` and shared graphics bundles. If detection fails, select the mission `.ibd` manually. The exported scene inherits the v0.2 map exporter's material fallbacks.
5. Choose the generated output folder, then click **Build and open 3D Actor Explorer**.
6. **Keep the launcher running** while using your browser. The local viewer is served at `127.0.0.1` on a randomly chosen port.
7. Left-drag orbits the map. Shift-drag or right-drag pans. Scroll to zoom. Click a 3D prop to select its actor. Double click or use **Focus selected** to center the camera. Filter actors by class or search the left panel. Use **Top view** to look down on the map.

The generated folder contains `scene.glb`, `actors.json`, `index.html`, and `scene.report.json`. These are *exports*. They must not be copied back into the game. The original `.gmp`/`.ibd` files remain unchanged.

### Avoid re-exporting large maps

If you already exported the *same* map with DX2Ed, supply that `.glb` in **Optional existing GLB**. DX2Ed verifies the GLB's recorded original map SHA-256 before reusing it. This saves time and preserves compatible export improvements, including Trier's materials.

### Command line

From the extracted `dx2ed_3d` directory:

```powershell
python dx2ed_3d.py build --map "C:\path\to\M1_Seattle_Hub_Penthouse_Upper.gmp" --output-dir "$env:USERPROFILE\Documents\DX2Ed3D\Upper"
python dx2ed_3d.py serve --folder "$env:USERPROFILE\Documents\DX2Ed3D\Upper"
```

If a map's `.ibd` cannot be detected, use `--bundle C:\path\to\mission.ibd`. The exporter also looks for shared graphics resources in the Maps directory. Optional `--system` adds a gameplay-property catalog, and `--logic-index` adds resolved TriggerScript names from prior research.

If `M1_Seattle_Hub_Penthouse_Upper.gmp` is present and you already have `Penthouse_Upper.glb`, you can use:

```powershell
python dx2ed_3d.py build --map "C:\path\to\M1_Seattle_Hub_Penthouse_Upper.gmp" --existing-glb "C:\path\to\Penthouse_Upper.glb" --output-dir "$env:USERPROFILE\Documents\DX2Ed3D\Upper"
```

## What's supported

- Textured BSP and placed static-mesh geometry as produced by the DX2Ed map exporter.
- Actor selection from the 3D viewport (approximate ray-versus-bounding-box picking) or searchable list.
- Engine and game property inspection, script references when supplied, focus selected actor, orbit/pan/zoom and layer toggles.
- Displays non-renderable entities in the inspector (and optionally as 2D markers), even if they lack a static mesh.
- Windows-friendly local browser launcher with no network/CDN dependency.

## Known limits

- **Read-only**. No transforms, script edits, new actor placement or game-compatible map saves.
- Renderer is experimental and was not visually verified under headless Chromium because the CI/container browser has no WebGL2. The actor inspector and generated GLB data were validated with original sample maps.
- Mesh hit testing uses world-space AABBs, not per-triangle ray tracing. Occlusion and small props may require list selection.
- Textures are approximated using the exporter's glTF materials. Some original DX2 effect shaders, normals, animations, and lighting remain unsupported.
- Skeletal characters and effects are not represented as fully rigged scene models.
- The WebGL2 canvas can be GPU-intensive on large scenes. The GUI export may take a while on big maps. If hardware acceleration is disabled, the browser will still show the actor inspector.
- The 3D viewer uses a **localhost HTTP server** because browsers commonly forbid fetching local `.glb` files from `file://` pages. It only listens on `127.0.0.1` and requires no internet connection.
- Bundled source-only parsers reflect our v0.2 DX2 map exporter and v0.1 actor explorer. No game assets distributed.

## Source and licensing

Research code; licensing/provenance audit is pending. Original game files remain proprietary. Retain source files in a private workspace until the source provenance audit is finished.