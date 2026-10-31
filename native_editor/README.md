# DX2Ed Native 3D Viewer v0.1 (Godot proof of concept)

**This prototype uses a real game engine instead of our experimental browser/WebGL renderer.** It loads the same `scene.glb` and `actors.json` our current map exporter and 3D Actor Explorer produce. Its purpose is to validate the rendering/editor architecture, not to replace the game or modify maps.

This is a **Godot project, not a compiled Windows application**. Godot is **not bundled**. GPU rendering and selection have not been tested on the user's Windows machine. This code was checked structurally and its *original synthetic GLB* was validated; **Godot was not installed in the build environment, so GDScript has not yet been executed through Godot**.

## How to test on Windows

1. Download and extract a Godot 4.3+ Standard build from https://godotengine.org/download/windows/. No .NET edition is needed.
2. Run Godot Project Manager -> **Import** -> select `godot_editor/project.godot` from this ZIP -> **Run** (F5).
3. Click **Load demo cubes**. You should see two yellow 3D cubes. Select a cube either from the actor list or by clicking it.
4. If the demo works, click **Open exported GLB** and choose an existing DX2Ed generated `scene.glb`. The tool automatically loads `actors.json` from the same directory. For example, use the `M1_Seattle_Hub_Penthouse_Upper` folder created by Actor Explorer v0.2.x.
5. Orbit: left drag; pan: right drag; zoom: wheel. **Frame scene** centers the entire map; **Focus actor** centers a selected placed mesh. Search for an actor name, class or mesh in the left pane.

**Important:** Selecting the exported `scene.glb` from the old browser viewer folder is preferable to selecting a random GLB. Actor linkage relies on DX2Ed actor names such as `StaticMeshActor__709`. This format is already preserved in our exported glTF.

## Architecture

- Godot 4 runtime `GLTFDocument.append_from_file()` + `generate_scene()` loads the textured GLB as native 3D nodes.
- The application uses a `SubViewportContainer`, native `Camera3D` and Godot's built-in **Compatibility renderer** (OpenGL) rather than hand-written graphics shaders.
- Meshes are linked to the original `.gmp` actor metadata by their exported scene-node names, using actor name keys in `actors.json`.
- Screen-space picking tests rays against mesh world-space bounds. This is a first approximation, not triangle-perfect picking.
- The actor panel shows the entire original tagged/game-property JSON, and can select actors that have no 3D model.
- All controls are deliberately **read-only**; no game files are changed, and no save operation writes to `.gmp` or `.ibd`.

## Build tests

`python -m unittest discover -s tests -v` checks GLB structure, metadata links, and absence of game resource files. To rebuild the demo scene: `python tests/make_demo_scene.py`.

## Known limitations

- Godot engine installation required separately. No EXE installer yet.
- Untested on your GPU and in a native Godot runtime in the build environment. We need a Windows screenshot showing the demo cubes before declaring viewport rendering fixed.
- Materials follow the GLB exporter's limitations; DX2 advanced holograms, UV transformations and skeletal meshes need more research.
- Some imported glTF node names may be adjusted by the Godot importer; this can affect actor linking and should be checked on the first real map.
- `scene.glb` is often 10–15 MB. Importing large maps can take time and consume VRAM.
- Runtime mesh picking uses AABBs, not collision triangles, so overlapping objects may sometimes select the wrong actor.
- The browser viewer remains available for users who prefer it, but native Godot is the direction for future 3D editor features.
- The prototype is not a full level editor and cannot write new meshes/actors back to the DX2 binary formats.

## Licensing

Tool source is research code with provenance/licensing review in progress. Godot itself is open-source under the MIT license; this project does not redistribute any Godot binaries or game assets.

For GitHub checkouts: run `python native_editor/tests/make_demo_scene.py` once before using the **Load demo cubes** button. The downloadable ZIP already includes the generated demo GLB.
