# DX2 native Model: candidate convex hull reconstruction from face planes

Research date: 2026-11-03. This is a **DX2-only, read-only** sequel to [native face-record parsing](DX2_NATIVE_MODEL_FACE_RECORD_LAYOUT.md). Input corpus: **19 user-owned original Invisible War Seattle GMPs**, UE package v95, licensee 65, 67, 68 and 69. No retail map assets are committed.

## What has been recovered

The existing Model face-record decoder provides **unit normals, plane coefficients, candidate face points/radii and independently stored vertex counts**. We now solve intersections of three different plane equations:

```text
normal_i dot vertex = coefficient_i
normal_j dot vertex = coefficient_j
normal_k dot vertex = coefficient_k
```

A candidate vertex is retained only when it satisfies all source-observed halfspaces:

```text
normal_face dot vertex <= coefficient_face + tolerance
```

The faces are rebuilt from vertices on each source plane and sorted with outward winding. The result is accepted only if **all** of the following checks pass:

1. Every face's **number of derived corners** matches the native face record's stored vertex-slot count.
2. The maximum distance from the stored face point to a derived face corner, times **1.001**, reproduces the source face's bounding radius within 0.1 source units or 0.005% of the stored radius.
3. Every polygon has a positive signed area in its outward plane-normal orientation.
4. Every undirected polyhedron edge is shared by exactly **two faces**, with **opposite directed winding**.
5. The polyhedron satisfies Euler's V − E + F = 2.
6. No singular, malformed, mirrored, open or inconsistent plane set is silently converted into a supposed native brush.

**These are derived corner positions, not copied XYZ vertices from a native Model array.** Their coordinate space is the source face-plane frame, which need not equal the stored Model bounding box, and is **not** yet established against the actual retail game's actor transforms. The small-scale source coordinate tolerances are pragmatic and need wider corpus validation before writing data.

## 19-map results

| Check | Count |
|---|---:|
| Nonempty native Models with recognized face records | **309** |
| Models passing every convex hull check | **306** |
| Models failing/refused | **3** |
| Derived corner positions among accepted Models | **2,436** |
| Accepted candidate faces | **1,830** |
| Validated undirected edges | **3,654** |
| Native face vertex slots independently checked | **7,308** |

Since 2,436 − 3,654 + 1,830 = **612 = 306 × 2**, the accepted set also satisfies the expected combined convex-solid Euler result. Each accepted face agrees with its source record's corner count and candidate face radius.

Three specific Models are **excluded**, not fixed up or forced into a hull:

- `M1_Seattle_Club.gmp` → `Model__205`: mismatched source face radius/corner geometry for the simple convex-halfspace hypothesis
- `M1_Seattle_hub.gmp` → `Model__184`: mismatched source face radius/corner geometry for the simple convex-halfspace hypothesis
- `M1_Seattle_Hub_Penthouse.gmp` → `Model__106`: the unusual 19-face native Model with 110-byte records; no bounded candidate volume from the single-convex-halfspace assumption

The failure causes may involve nonconvex/compound solids, different coordinate conventions or additional record fields; **none is proven** yet.

## Reproduce the audit

Use original **user-owned** GMP files from your own installation, and write reports outside the game folder:

```powershell
python research/dx2/reconstruct_model_convex_candidates.py "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" --report "C:\DX2_Research_Reports\convex_hulls.json" --include-geometry
```

Default JSON output reports only summary information and failures. `--include-geometry` includes candidate corner coordinates and ordered polygon indices. Original GMPs are never modified.

### Optional offline OBJ geometry preview

For one specific source export, generate a **new untextured triangulated OBJ** outside the game installation:

```powershell
python research/dx2/reconstruct_model_convex_candidates.py "C:\DX2\Content\DX2\Maps\M1_Seattle_MercenaryDistrict.gmp" --preview-model-export 957 --preview-obj "C:\DX2_Research_Reports\Model60_candidate.obj" --report "C:\DX2_Research_Reports\Model60_audit.json"
```

In the examined source map, export **957 (Model__60)** produces a **10-corner, 7-face** candidate solid. It can be opened in Blender as a diagnostic mesh, but it has no imported materials, actor placement or native collision. Don't mistake this OBJ for a map export that Invisible War can load.

OBJ files are written with exclusive creation and can't overwrite source GMPs or existing previews. The CLI rejects unsupported models, corrupt plane data, and output paths inside the original game map directory.

Synthetic, game-asset-free regression tests:

```powershell
python -m unittest discover -s native_editor/tests -p "test_dx2_model_convex_reconstruction.py" -v
```

## Next engineering gates

- Explain the three refusing Models with additional source evidence (nonconvex / compound / transform / other record grammar).
- Check whether face data corresponds to brush-local, map-world or a third coordinate system by matching **actor locations, rotations and Model references** against the recovered candidate hulls.
- Independently recover the native **stored vertex representation and face index linkage**, if present, rather than only deriving intersections from planes.
- Investigate the large invalid-box Models containing compiled world data, and DX2-specific collision/CSG reconstruction.
- Attempt native Model/Level serialization only when all these source and runtime gates pass.

**Not implemented or demonstrated:** a native DX2 BSP compiler, native GMP geometry writer, real DX2 collision generation, NavMesh/PVS/Havok build, or modified-map gameplay in Invisible War.
