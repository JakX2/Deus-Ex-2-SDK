# DX2 map exporter integration review: consolidated performance stack

This branch is a **reviewable integration candidate based directly on `main`**,
combining the source-only work in draft PRs #171–#177 and an independent
GLB equivalence verifier. It does **not** merge or modify `main` and is
not a production DX2 SDK release. The original stacked PRs remain open for
review and history; merge **either** the consolidated integration PR **or**
the sequential individual PRs, not both as independent changes.

## What the integration contains

| Prior work | Capability | Default behavior |
| --- | --- | --- |
| #171 | BGRA/BGRX, DXT block decode and glTF vector optimization | Byte-compatible |
| #172 | External inspector/gallery HTML templates | Same generated pages |
| #173 | Complete map profiler, input hashes and cProfile output | Opt-in tooling |
| #174 | Main versus optimized pinned source A/B CI artifact | Source only |
| #175 | Bounded cached DXT1 endpoint palette and packed RGBA rows | Byte-compatible |
| #176 | DXT3 explicit-alpha packed RGBA rows | Byte-compatible |
| #177 | Optional PNG compression levels 1–9, GUI checkbox | Level 7 unchanged |
| This branch | GLB exact and decoded-PNG semantic comparator | Opt-in tooling |

No mandatory third-party Python package, native dependency, game DLL,
redistributed game data, GMP/IBD writer or engine BSP/collision compiler
has been introduced.

## New cross-map verification on original Seattle data

The game archives supplied privately by the project owner contain 19 Seattle
GMP and 19 mission IBD files. Exactly **six representative GMPs** were
exported with the original `main` revision
`7fb22999764dad958e5a8e95aa3b8e01df832fdf` and the final #177
candidate `1f79a4b0cf442290047f4bf1c73d06888e133ffc` using the same
input file set and the unchanged **default PNG level 7**.

One local timed run per map and revision (Python environment fixed, extracted
source files, output in disposable temporary directories):

| Seattle GMP | Main seconds | Candidate seconds | Missing static mesh actors | GLB & JSON report SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `M1_Seattle_Hub_Penthouse_Upper.gmp` | 7.250 | 4.624 | 16 | Both exactly identical |
| `M1_Seattle_Club.gmp` | 8.059 | 4.798 | 64 | Both exactly identical |
| `M1_Seattle_Corp_Campus_Interior.gmp` | 7.734 | 4.630 | 45 | Both exactly identical |
| `M1_Seattle_Hub_WTOterminal.gmp` | 6.880 | 4.587 | 10 | Both exactly identical |
| `M1_Seattle_MercDistrict_Hangar.gmp` | 4.323 | 2.960 | 30 | Both exactly identical |
| `M1_Seattle_Acorp_Lab.gmp` | 5.930 | 3.730 | 9 | Both exactly identical |

**Six of six defaults were byte-for-byte equivalent**, both GLB and
sidecar report. All **38 original source assets** were separately hashed
before and after the comparison: none changed.

These durations are **individual measurements**, not statistically stable
medians. The available archive does not contain the shared
`Kernel_GFXALL.ibd`, accounting for missing static meshes and incomplete
materials. No in-game runtime or native BSP/editor fidelity conclusion is
supported by these tests.

Fast PNG (level 1) was also exported for the first three maps, and its
larger GLB output is expected to differ from level 7. This branch adds
a standalone decoded-RGBA and glTF-geometry checker to audit that
difference. The verifier was additionally exercised locally on a
real Penthouse Upper pair: **74 embedded images** and **1,604 non-image
buffer views** matched exactly after decompressing both sets of PNGs
and ignoring only compressed PNG offsets and lengths.

## Verify a local pair of exports

From a repository checkout containing this branch, using existing exported
GLBs (the tool does not export or modify map files):

```powershell
# Baseline main versus optimized default (PNG level 7 in both):
python tools/verify_dx2_glb_equivalence.py D:\DX2Bench\main.glb D:\DX2Bench\optimized.glb

# Normal PNG7 versus optional fast PNG1, matching decoded image pixels:
python tools/verify_dx2_glb_equivalence.py D:\DX2Bench\normal.glb D:\DX2Bench\fast.glb --mode decoded-png
```

- `exact` (default) requires **identical bytes** and fails on any difference.
- `decoded-png` parses the GLB JSON/BIN chunks and validates PNG CRC,
  RGBA8 layout, bounds and decompressed scanline data. It compares all
  non-image buffer view bytes and glTF JSON after normalizing only
  changed BIN offsets, compressed embedded PNG lengths and BIN total size.
  Geometry, textures, materials, actor transforms, UVs and scene graph
  metadata must otherwise agree.
- The checker is **fail closed** for malformed headers, truncated GLB/PNG
  chunks, suspicious dimensions, changed pixels, changed geometry or
  altered metadata. It is specifically for current DX2 exporter GLBs
  using unfiltered embedded RGBA8 PNGs, not an arbitrary glTF viewer or
  a semantic proof of real DX2 game playability.
- The Python tool reads existing GLBs only and emits a JSON status line
  with SHA-256 fingerprints. It creates no output artifact or writes.

Asset-free tests:

```powershell
python -m unittest discover -s tests -p "test_exporter_glb_equivalence.py" -v
python -m unittest discover -s tests -p "test_exporter_hotpaths.py" -v
python -m unittest discover -s tests -p "test_exporter_png_preset.py" -v
python -m unittest discover -s tests -p "test_exporter_full_map_profile.py" -v
```

The first test runs on Linux and Windows/Python 3.10 and 3.12 in the
`exporter-hotpaths.yml` CI matrix. Proprietary GMP/IBD content is
**never** distributed through GitHub Actions.

## Landing and remaining engineering boundaries

This integration PR offers one coherent review surface against `main`.
Before landing, reviewers should check the code diff, exact-head CI,
the byte-equivalence evidence, the missing-shared-bundle limitation and
the opt-in default-off GUI option. If only individual PRs are landed,
preserve their original stacked base order (#171 first through #177).

After the exporter changes are integrated, the next project focus should
be DX2Ed's editor-side native *Invisible War* authoring parity: original
World BSP surface semantics, material/UV reconstruction and collision
format research. None of this performance work enables native GMP/IBD
World BSP/CSG writes, Havok/MOPP cooking or playable custom levels.
