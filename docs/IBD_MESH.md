# Inspecting DX2 bundles and exporting individual static meshes

The original [`dx2bundles.py`](../tools/maps/dx2bundles.py) reads the tested Ion Storm `.ibd` container format and exports a single **untextured** GLB static mesh for inspection in Blender.

It uses only the Python standard library. Retail game files are not included.

From the repository root:

```powershell
python .\\tools\\maps\\dx2bundles.py stats "C:\\path\\to\\m1_hub_penthouse_upper.ibd"
python .\\tools\\maps\\dx2bundles.py list "C:\\path\\to\\m1_hub_penthouse_upper.ibd" --type staticmesh
python .\\tools\\maps\\dx2bundles.py mesh-info "C:\\path\\to\\Maps.zip" GO_basketball
python .\\tools\\maps\\dx2bundles.py mesh-glb "C:\\path\\to\\Maps.zip" GO_basketball -o basketball.glb
```

The input `Maps.zip` here is a **user-created local ZIP of their own IBD bundles**, not an SDK-supplied file. Use paths that exist in your installation.

An internal test against a provided Penthouse Upper retail bundle returned 856 resources, including 139 static meshes and 63 TriggerScript definitions. Other versions and maps require separate verification.

The exported GLB is a static-mesh *inspection* model. It is not a valid level re-import format, and this module does not reconstruct original DX2 shaders. It writes only the explicitly requested output GLB; the input bundles remain read-only.

[Fixture-free tests](../tests/test_ibd_mesh.py) exercise bundle reading, invalid layout rejection and the GLB output header.
