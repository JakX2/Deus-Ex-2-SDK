# Export-only actor transforms (experimental)

DX2 Map Exporter v0.1.1 supports map-specific optional scale/mirror overrides for placed static mesh actors. These affect **only** generated GLB nodes, not the game installation.

The screenshots from Trier show that setting Blender object Y scale from +1 to -1 corrects two mirrored signs. To reproduce it automatically, copy `Trier_transform_example.json`, change its `map` field to the exact `.gmp` filename (from the Scan maps list), and remove entries for actors you do not want corrected. The example is **not** automatically applied.

Use the GUI's **Optional transform overrides JSON** field, or from PowerShell:

```powershell
python .\dx2_map_exporter.py export --game-root "$game" --map "M3_Germany_Trier.gmp" --output "$env:USERPROFILE\Desktop\Trier_fixed.glb" --transform-overrides ".\Trier_transform_example.json"
```

A JSON file must look like:

```json
{
  "schema": "DX2Ed-transform-overrides-v1",
  "map": "M3_Germany_Trier.gmp",
  "actors": {
    "StaticMeshActor__92": { "scale": [1, -1, 1] },
    "StaticMeshActor__146": { "scale": [1, -1, 1] }
  }
}
```

This is a workaround, **not yet a true decoding of native DX2 actor scale**. `scale` refers to the exported glTF object's **local** X/Y/Z. Mirrors change coordinate handedness. Negative scale may affect normals and polygon facing in some programs. Use care if an object's real in-game material has front/back sidedness.

Map filename mismatches, invalid scale values, unknown actor names and non-exportable mesh actor overrides abort without creating a GLB, except if later report errors occur. A generated `.report.json` includes `actor_transform_overrides_applied`.

For the real root-cause fix, please provide the Trier `.gmp`, its matching mission `.ibd`, and the `.report.json` from the unmodified export. Those retail files will not be committed to a public repository.

**Note**: The original GMP actor identifiers contain two underscores (e.g. `StaticMeshActor__92`); Blender may show a normalized object name. Overrides must use GMP actor identifiers.