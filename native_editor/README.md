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


## Seattle Club geometry diagnosis (0.2.1)

A new **Copy mesh info** button records the original DX2 actor/mesh identity,
UE location and Pitch/Yaw/Roll, plus Godot world bounds. Click the geometry
that appears misplaced, then copy and share this report. When a click hits BSP
or otherwise unlinked render geometry, the inspector still reports the mesh
node. Selection now prioritizes real actor meshes over broad BSP bounding boxes.

See [Seattle Club findings](Seattle_Club_Transform_Findings.md).
The editor remains read-only; there is **no global geometry rotation fix** in
this release. Godot visual runtime tests remain to be done on Windows.

## Experimental 0.2.2: exact geometry picking (development branch)

The Seattle Club diagnostic picker now tests **rendered triangles** after a fast
ray/AABB broad-phase check. This prevents a large BSP box or a hollow mesh's
bounding box from stealing clicks on nearby props. The nearest surface wins;
an actor and BSP surface at effectively the same distance prefer the actor.
The original actor-name mapping and **Copy mesh info** feature remain in place.

The copied report now includes a "Pick method: rendered triangle" line, the
Godot-space hit position and distance. Vertex faces are cached by imported mesh
resource and discarded on map reload; all changes are in the read-only viewer.

This branch also fixes the diagnostic's mismatch with retail Actor Explorer
JSON, whose `mesh` field is a string, `mesh_bounds` is a separate field, and
`location` is an [x, y, z] array.

### Validation (requires Godot 4.3 or newer)

Run the asset-free headless smoke test from the **repository root**:

```powershell
godot --headless --path native_editor/godot_editor --script res://tests/smoke_triangle_picking.gd
```

The script checks solid triangle hits, rotated/scaled hits, an AABB false
positive, and the Actor Explorer JSON field layout. An output line beginning
`DX2Ed triangle picking smoke: PASS` is expected on success.

Then run the Python source/backend tests:

```powershell
python -m unittest discover -s native_editor/tests -v
```

Finally, open `M1_Seattle_Club.gmp` in the graphical viewer and click a
suspicious object. Use **Copy mesh info** to inspect its identity, transform,
world bounds, and exact surface hit. Compare prop selection against the same
spot on the retail map.

**Limits:** this is a source-level change awaiting the above Godot runtime and
Windows/Seattle Club checks. Meshes without readable triangle faces cannot be
picked by bounding box as a substitute; transparent visual effects and gameplay
visibility are not yet modeled. This does not modify any original GMP/IBD.
