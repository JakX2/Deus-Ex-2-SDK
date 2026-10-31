# Exporter tests

The source-only tests require no DX2 assets:

```powershell
python -m unittest discover -s tests -v
```

To run the optional full-content regression, set `DX2_TEST_MAPS` to your own `Content\DX2\Maps` folder holding original Penthouse maps, mission IBDs, and Kernel_GFXALL.ibd:

```powershell
$env:DX2_TEST_MAPS = "C:\Program Files (x86)\Steam\steamapps\common\Deus Ex Invisible War\Content\DX2\Maps"
python -m unittest discover -s tests -v
```

Validated against supplied Penthouse Upper and Lower original source files. Success does not imply all other maps are fully exportable.