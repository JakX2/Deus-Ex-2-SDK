# Getting started

This repository is an experimental source tree, **not yet a full DX2Ed desktop application**.

## Requirements

- Python 3.9+ on Windows, Linux, or macOS for the research utilities.
- Your own legitimate DX2 installation for tests involving game resources.
- Blender (optional) for examining exported glTF models.

In a terminal at the repository root:

```powershell
python --version
python tools/check_source.py
```

## First usable commands

Inspect your own game resource bundles without changing them:

```powershell
python .\\tools\\maps\\dx2bundles.py stats "C:\\path\\to\\m1_hub_penthouse_upper.ibd"
python .\\tools\\maps\\dx2bundles.py list "C:\\path\\to\\m1_hub_penthouse_upper.ibd" --type staticmesh
python .\\tools\\scripts\\dx2_script_bundle_probe.py --game-root "C:\\path\\to\\Content\\DX2"
```

See [bundle/mesh instructions](IBD_MESH.md) and [script-bundle instructions](IBD_PROBE.md).

Run asset-free tests with:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The full v0.28 script editor and textured-map exporter require additional research modules not yet migrated into this repository. Those components remain available in the separately prepared source-only starter archive.

## Working with game data

Supply `.gmp`, `.ibd` and related game resources from your own installation. The project does not distribute them.

The two Penthouse research maps are `M1_Seattle_Hub_Penthouse.gmp` and `M1_Seattle_Hub_Penthouse_Upper.gmp`. Existing prototypes have been tested with particular retail builds; do not assume compatibility with other game versions.

Read [Safety](SAFETY.md) before testing any writer.
