# DX2 Map Exporter 0.1 (DX2Ed)

**Experimental, read-only, standalone map exporter for Deus Ex: Invisible War.**

Turns existing `.gmp` game levels plus `.ibd` resource bundles into **textured, self-contained `.glb` files** suitable for Blender or another glTF 2.0 importer. Uses only the Python standard library; no game executable modification, no original game assets bundled.

## Windows: GUI (recommended)

1. Install **Python 3.9+** from python.org and ensure `python`/`py` is available from PowerShell (Tkinter normally included).
2. Extract the release ZIP and double-click **`START_MAP_EXPORTER.bat`**.
3. Choose your **Deus Ex Invisible War** Steam installation directory, or its `Content\DX2\Maps` folder. For Steam, a typical location is `C:\Program Files (x86)\Steam\steamapps\common\Deus Ex Invisible War`.
4. Click **Scan maps**, select a map, choose an export folder, then **Export selected map to GLB**.
5. In Blender, use **File > Import > glTF 2.0 (.glb/.gltf)**. The `.report.json` next to the GLB lists mesh coverage, triangle counts, texture statistics, and warnings.

### PowerShell / CLI

From the `map_exporter` subfolder:

```powershell
$game = "C:\Program Files (x86)\Steam\steamapps\common\Deus Ex Invisible War"
python .\dx2_map_exporter.py list --game-root "$game"
python .\dx2_map_exporter.py export --game-root "$game" --map M1_Seattle_Hub_Penthouse_Upper.gmp --output "$env:USERPROFILE\Desktop\Penthouse_Upper.glb"
```

For unusual installations where a mission `.ibd` is not detected, manually supply bundle paths in priority order:

```powershell
python .\dx2_map_exporter.py export --game-root "$game" --map M1_Seattle_Hub_Penthouse_Upper.gmp --bundle "$game\Content\DX2\Maps\m1_hub_penthouse_upper.ibd" --output "$env:USERPROFILE\Desktop\Penthouse_Upper.glb"
```

The `--bundle` override is intended for rare custom layouts. The exporter also discovers the shared `Kernel_GFXALL.ibd` and `MainMenu_GFXALL.ibd` automatically in `Maps`. If your resources are in a user-created `Maps.zip` instead, pass that as an extra `--bundle`.

## What it exports

- Existing placed **static mesh actors**, their approximate transforms and mesh data.
- Visible **BSP render geometry**.
- Embedded diffuse textures approximated as standard glTF PBR materials.
- Actor names and DX2 export indices in glTF extras for inspection.
- JSON report with resource coverage and current limitations.

**Not supported:** skeletal meshes/NPCs, gameplay scripting, lights and lightmaps, collision, sounds, animations, exact DX2 shaders, full alpha/translucency, editing game levels or GLB-to-GMP reimport. Actor rotations and pivots remain **provisional**, and results can vary by map and installed game version. The game file is never modified. Read-only map export does not imply import/rebuild support.

## Validation

The original research pipeline successfully exported **Penthouse Upper** with 471 static mesh actors, **Penthouse Lower** with 1,000, plus visible BSP geometry and PNG diffuse textures. This standalone wrapper is regression-tested with the original user-owned maps and bundles. Other maps may have unsupported resource layouts or missing mesh references; check each generated report before assuming completeness.

## Source and licensing

Do not publish original retail `.gmp`, `.ibd`, map exports containing protected game artwork, or proprietary game binaries without permission. Source licensing and third-party provenance review are ongoing. This unofficial project is not affiliated with Ion Storm, Eidos or Square Enix.
