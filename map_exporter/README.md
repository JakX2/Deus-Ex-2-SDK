# DX2 Map Exporter 0.2 (Trier compatibility update)

Read-only DX2 `.gmp` + `.ibd` to textured `.glb` exporter for Blender. Requires Python 3.9+, Windows GUI via `START_MAP_EXPORTER.bat`, or CLI.

Changes since 0.1:

- Creates **translucent cyan placeholders** for missing hologram materials or shader-only hologram stages, preserving source shader stages in `.report.json`. These are approximations, not original effect animations.
- Optionally previews missing skin material records from another *existing* skin of the same mesh, identifying substitutions in the report. Enabled by default; disable using the GUI checkbox or `--no-alternate-skins`.
- Reports each material's resolution, referenced mesh names, shader stages, and fallback provenance in `.report.json`.
- Ships `Trier_transform_example.json` with the **exact** actor IDs (`StaticMeshActor__92` and `StaticMeshActor__146`) from the original Trier GMP. These mirrors are **opt-in** and not guaranteed correct for all maps.
- Preserves all retail files, with no assets redistributed.

## GUI

Double-click `START_MAP_EXPORTER.bat`; select the game installation; click **Scan maps**, select a map, and export to GLB. Optionally choose `Trier_transform_example.json` under transform overrides when exporting `M3_Germany_Trier.gmp`.

## CLI

Run in the extracted directory:

```powershell
$root = 'C:\Program Files (x86)\Steam\steamapps\common\Deus Ex Invisible War'
python .\map_exporter\dx2_map_exporter.py list --game-root "$root"
python .\map_exporter\dx2_map_exporter.py export --game-root "$root" --map M3_Germany_Trier.gmp --output "$env:USERPROFILE\Desktop\Trier_v02.glb" --transform-overrides .\Trier_transform_example.json
```

The example file is only valid for the exact Trier map. The source game data is never modified. Inspect `Trier_Findings.md` and `TRANSFORM_CORRECTIONS.md` before relying on results.

## Optional faster PNG output

The exporter uses the original **zlib level 7** PNG encoding by default.
The new `--png-compression 1` flag makes large preview GLB exports faster
at the cost of larger files. It preserves decoded texture pixels and
geometry, but because PNG sizes and buffer offsets change, the resulting
GLB and `.report.json` SHA-256 will differ from the default output.

```powershell
python .\map_exporter\dx2_map_exporter.py export --game-root "$root" --map M1_Seattle_Hub_Penthouse_Upper.gmp --output "$env:USERPROFILE\Desktop\Penthouse_fast.glb" --png-compression 1
```

The GUI also provides a **Fast PNG compression** checkbox (off by
default). Use level 7 for exact historical output bytes. See
[`PNG_COMPRESSION.md`](PNG_COMPRESSION.md) for real-map timings, file
size tradeoffs, and decoded-image/mesh equivalence tests.

## HTML inspection/gallery templates

The inspector and texture gallery HTML pages are now maintained as separate
source files under `map_exporter/templates/`:

- `dx2inspect_viewer.html`: actor position plot shown by `dx2inspect.py viewer`
- `texture_gallery.html`: gallery page rendered by `dx2textures.py gallery`

**Keep the entire `map_exporter/` directory together** when copying or
packaging the scripts. Both CLI tools load these templates relative to their
own module location, not the current working directory, and fail if a required
template is missing. The generated HTML remains self-contained and usable
offline. The source game files remain read-only.

Run source-free template tests with:

```powershell
python -m unittest discover -s tests -p "test_exporter_html_templates.py" -v
```
