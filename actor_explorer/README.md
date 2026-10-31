# DX2Ed Actor Explorer 0.1

Read-only, offline actor browser for original Deus Ex: Invisible War `.gmp` maps, inspired by UnrealEd's actor inspector.

Requires Python 3.9+ with no third-party packages. The actor parser reuses `map_exporter/dx2inspect.py`, `map_exporter/dx2scene.py`, and `map_exporter/dx2bundles.py`. No retail data is distributed.

## Windows

Run `START_ACTOR_EXPLORER.bat` from this folder (in the repository checkout). Select the `.gmp` inside your own `Content\\DX2\\Maps` directory, choose an output HTML path, and click **Create and open Actor Explorer**.

The resulting HTML is fully offline: search actor names/meshes, filter by class, select actors on an X/Y overview, and inspect engine and gameplay properties.

Optionally supply the game's installed `System` directory or a `System.zip` to resolve gameplay property names. The tool only reads your original files. Supplying a locally generated research `DX2_Logic_Index.json` can resolve TriggerScript IDs and titles for supported actor links.

## CLI

```powershell
python .\actor_explorer\dx2_actor_explorer.py --map "C:\Games\DX2\Content\DX2\Maps\M3_Germany_Trier.gmp" --output Trier_Actors.html
```

Optional flags: `--system System.zip`, `--logic-index DX2_Logic_Index.json`, `--json Trier_Actors.json`.

## Limits

This is **not a 3D level editor** and does not write changes back into the game. The X/Y map is a spatial overview. Script names are linked only when a compatible, locally generated mission-logic index is supplied. The numeric `TriggerScripts` serialized property must not be interpreted as direct script IDs.

Source-only project. Do not commit generated HTML containing extracted map data, original `.gmp`/`.ibd` files or game assets.
