# DX2Ed Native Editor 0.2: direct GMP loading (experimental)

**A Godot 4 based, read-only 3D map and actor viewer for Deus Ex: Invisible War.** This project uses the original map files from your own game installation, not bundled retail data.

## What's new since 0.1

The new **Open DX2 map (.gmp)** button automatically finds the corresponding mission .ibd and shared bundles, runs the existing DX2Ed parser/exporter, and loads both the textured scene and actor metadata. You no longer need to export a GLB and actors.json manually. Conversion runs in a Python worker thread and creates a content-hashed cache outside the game installation.

The previous **Open exported GLB**, **Load actors.json**, and **Load demo cubes** features remain available. The left-side actor list and read-only property inspector are retained.

## Install and test (Windows)

1. Install **Godot 4.3 or newer, Standard edition** and **Python 3.9 or newer**. Ensure the `python` or `py -3` command is available.
2. Import `native_editor/godot_editor/project.godot` in the Godot Project Manager, then press **F5**.
3. Press **Open DX2 map (.gmp)** and select a map in `Deus Ex Invisible War/Content/DX2/Maps`, such as `M3_Germany_Trier.gmp`.
4. DX2Ed locates the matching IBD, builds a private GLB cache, and generates actors.json internally. On first load this may take some time.
5. Once the viewport appears, select actors in the list or click the meshes; use **Frame scene** and **Focus actor** to navigate.
6. Open the map again to verify **cached** appears in the status line. Changing the map or its resource bundles invalidates the cache.

If automatic resource lookup fails, select **IBD override...** first, then choose your map.

## Command-line diagnostics

```powershell
cd native_editor\godot_editor
python .\backend\dx2_native_backend.py --map "C:\path\to\Maps\M3_Germany_Trier.gmp" --output-root "$env:LOCALAPPDATA\DX2EdCache" --inspect
python .\backend\dx2_native_backend.py --map "C:\path\to\Maps\M3_Germany_Trier.gmp" --output-root "$env:LOCALAPPDATA\DX2EdCache"
```

The backend uses only the Python standard library. Run fixture-free tests with `python -m unittest discover -s native_editor/tests -v` from repository root.

## Validation

The Python backend passed tests covering cache invalidation, safe output paths, regeneration, and automatic map/bundle lookup. A real Penthouse Upper load produced **705 actor records** and **455 static meshes** in an isolated environment without shared graphics bundles, reporting 16 missing mesh resources. Full installations should provide shared bundles, but material coverage varies by level.

The previous Godot v0.1 viewer was confirmed rendering a real Trier GLB on Windows; **the direct-GMP load button added in v0.2 has not yet been Windows-tested**.

## Important limits

- This is an **experimental viewer, not a complete map editor**.
- **Read-only:** never patches or replaces your .gmp/.ibd originals.
- GLB is a visualization cache, not a reversible game map format.
- Gameplay script editing and safe GMP writing are still separate research utilities.
- Missing DX2 materials and effects may be approximated or left unresolved.
- No game assets, proprietary binaries or copyrighted editor executables are distributed.

See [Architecture](ARCHITECTURE.md) for the native file-loading pipeline.
