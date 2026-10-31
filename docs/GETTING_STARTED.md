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

When additional research modules are integrated, their command-line `--help` options will document their inputs.

## Working with game data

Supply `.gmp`, `.ibd` and related game resources from your own installation. The project does not distribute them.

The two Penthouse research maps are `M1_Seattle_Hub_Penthouse.gmp` and `M1_Seattle_Hub_Penthouse_Upper.gmp`. Existing prototypes have been tested with particular retail builds; do not assume compatibility with other game versions.

Read [Safety](SAFETY.md) before testing any writer.
