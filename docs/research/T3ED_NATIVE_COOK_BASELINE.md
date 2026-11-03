# T3Ed native cook baseline: original Flesh source/compiled map comparison

**Status: read-only research. No editor executable was run, and no original
map was rebuilt or modified.**

The user supplied T3ED.7z on 2026-11-03 (SHA-256:
711bda8319ff115fd197a0ca3157123648f3594de865e639407445e2a58bb7d2).
The original proprietary archive is not included in this repository.

## Repeatable CLI

The new research/t3ed/compare_editor_cooked.py uses the **existing**
DX2SDK readers, dx2inspect.Package and dx2scene.find_bsp. It compares
already-existing v95 same-licensee and same-name source .unr/cooked .gmp
pairs, not newly compiled maps. Example (PowerShell):

~~~powershell
python research/t3ed/compare_editor_cooked.py pair "C:\T3ED\content\T3\Maps\Tutorial3.unr" "C:\T3ED\content\T3\Maps\Tutorial3.gmp"
python research/t3ed/compare_editor_cooked.py corpus "C:\T3ED\content\T3\Maps" --report "C:\DX2EdResearch\t3_tutorial_cook.json"
~~~

The report is a **new JSON** outside the map source directory. The
auditor refuses overwrite and does not include game binaries, geometry
arrays, material pixels or copyrighted map payloads. It records file
SHA-256, package version/licensee/GUID, names/imports/exports, class
counts, unique class+name payload hashes, ambiguities, and native
Flesh render-block SHA-256 digests.

The comparator deliberately matches only **unique (class, object name)**
keys because native export indices may be renumbered during cooking.
A changed payload can reflect reference/index rewrites rather than
changed gameplay or geometry. The BSP comparison uses a SHA-256 digest
of each entire validated Level-relative packed render block, including
its materials, with digest **multiplicity** preserved.

## Verified original T3Ed tutorial corpus

All four source/cooked pairs have UE package format 95 and licensee 133.
The original stock sample data produces:

| Source / cooked map | Source-only Polys exports | Brush count source/cooked | Model count source/cooked | Exact render blocks common | Level payloads changed |
|---|---:|---:|---:|---:|---:|
| Tutorial2.unr / tutorial2.gmp | 7 | 6 / 6 | 7 / 7 | 4 / 4 | 1 |
| Tutorial3.unr / Tutorial3.gmp | 8 | 6 / 6 | 8 / 8 | 4 / 4 | 1 |
| Tutorial4.unr / Tutorial4.gmp | 8 | 6 / 6 | 8 / 8 | 4 / 4 | 1 |
| Tutorial5.unr / Tutorial5.gmp | 8 | 6 / 6 | 8 / 8 | 4 / 4 | 1 |
| **Total** | **31** | **24 / 24** | **31 / 31** | **16 / 16** | **4** |

All 16 validated Flesh BSP render blocks are **byte-identical**
between these preexisting editable/cooked tutorial pairs.
Each tutorial Level payload changes, and all matched Brush and Model
payloads change bytewise even though their export counts are retained.
This is **not proof** of a new compiler run, nor does BSP render-data
equality establish spatial visibility/PVS, Havok physics, navigation,
lightmaps, runtime lighting or engine load compatibility.

Separate corroborating original packages:

- T3 Stonemarket1.unr: UE95 licensee 133, 319 Brush, 443 Model,
  443 Polys, and 616 validated Flesh BSP render blocks (7,060 triangles).
- DX2 M1_Seattle_hub.gmp: UE95 licensee 68, 241 Brush, 263 Model,
  no Polys, 255 validated render blocks (3,227 triangles).
- DX2 original System/Data/Entry.unr and Entry.gmp use **licensee 27**
  and similarly drop 3 source Polys in the cooked example. This is a
  related Unreal-package pattern, NOT DX2/T3 native compiler parity.
- The original DX2 Editor.d2u has EditorEngine, BrushBuilder,
  CubeBuilder and SheetBuilder classes.
- T3Ed.exe is a 32-bit PE with strings for Build Geometry And Unreal
  BSP, Build Flesh BSP, Illuminating BSP, and Havok world building.
  Those are binary clues, NOT executed or verified native APIs.

The compressed T3Ed archive lacks its configured .t3u packages; an
actual Windows launch may need files from the user's separately owned
Thief 3 installation.

## Next isolated T3Ed compiler experiment (not yet executed)

1. On Windows, copy a known original tutorial .unr to an isolated
   disposable working directory with its required stock T3 packages.
2. Run the **original unmodified** T3Ed to verify it starts and can
   open the stock tutorial. Preserve the original untouched.
3. On the isolated copy, make one minimal brush adjustment, perform
   Unreal BSP, Flesh BSP, Havok/physics, lighting and path-building
   steps only if the UI supports them, then save a new test file.
4. Use this audit on same-licensee, same-name staged source/cooked
   outputs before and after the rebuild. Record the exact binary
   hashes and native builder logs. Test a compiled T3 copy in T3
   separately, not as evidence of DX2 playability.
5. Only once stock T3 compiler behavior is understood attempt a
   **separate** DX2-class-aware authoring experiment. Do not patch
   DX2 package licensee bytes and assume that yields real compatibility.

Keep Godot as the DX2Ed frontend. Native map construction, BSP,
collision and lighting writing remain separate format/research gates.

## Tests and publication boundary

native_editor/tests/test_t3ed_cook_audit.py uses only synthetic
fixtures and tests digest multiset comparison, source-only Polys,
changed/unchanged payloads, ambiguous object identities, same-name
case-insensitive discovery, cross-licensee refusal, malformed headers,
no-level refusal, and exclusive report output outside original
map folders. CI requires no T3Ed executable or proprietary files.

**Never commit T3Ed.exe, original editable/cooked T3/DX2 levels,
retail game DLLs, or unlicensed assets to the public SDK.**
