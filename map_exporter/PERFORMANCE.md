# Map exporter hot-path profiling and compatibility

The map exporter remains a **read-only**, standard-library-only tool. This
performance pass changes only image decode and GLB vector packing logic. It
does not claim to make native DX2 World BSP/CSG editing possible.

## What changed

- **BGRA8 / BGRX8**: Replace the old Python per-pixel channel shuffle with
  four bulk strided `bytearray` assignments. BGRX alpha is still forced to
  255. Input mip byte counts are checked before decoding.
- **DXT1 / DXT3 / DXT5**: Keep the observed legacy palette, interpolation,
  transparency and alpha math. Process one compressed block-row in one buffer
  slice assignment instead of four individual pixel writes. Clip odd sizes
  at their original image boundary.
- **DXT1 palette/row decoder (real-map-guided)**: A dedicated BC1/DXT1
  path memoizes at most 32,768 immutable RGB565 endpoint palettes and
  concatenates four prepacked RGBA colors per full block scanline, with a
  precise edge-block fallback. The three-color transparent DXT1 mode,
  cubemap faces and original mip bytes are unchanged. DXT3/DXT5 continue
  through the proven generic block-row decoder. The cache is capacity-bounded
  and has no third-party dependencies.
- **glTF POSITION/NORMAL/UV arrays**: Validate and pack float32 vector
  components and collect POSITION bounds in one pass, rather than a separate
  validation pass, packing pass, then six min/max passes. Original numeric
  extrema types are preserved for glTF JSON.
- Both changes have **byte-for-byte regression tests** against frozen legacy
  implementations. Synthetic cubemaps, partial compressed blocks, alpha
  interpolation, PNG contact sheets and original DDS mip bytes are covered.
  No retail game files are included.

## Reproduce the benchmark

From the repository root, on Python 3.9 or newer:

```bash
python -m unittest discover -s tests -p "test_exporter_hotpaths.py" -v
python tools/benchmark_exporter_hotpaths.py --size 512 --vectors 30000 --repeats 5
```

The benchmark emits machine-readable JSON: Python/OS version, texture formats,
source-size, legacy median milliseconds, optimized median milliseconds,
speedup ratio, and exact-output checks. Every input is a deterministic,
generated memory buffer. It does **not** open game maps or original texture
packages and has no timing-based CI threshold, since CPU, interpreter and
thermal throttling affect measurements. Benchmarks are **not** evidence of
actual full mission export speedups.

For a real-data whole-export measurement on an installation you own, set
`DX2_TEST_MAPS` to the original game Maps folder and run the existing
optional map regression from `map_exporter/TESTING.md` before and after
this change. Record wall-clock time, Python and CPU versions, map name,
number of textures, and final GLB/report output hashes. The optional tests
assert scene/actor/image counts and that the original source maps remain
unchanged. Because PNG/GLB output must be identical for supported numeric
inputs, compare actual output hashes where possible, using the same source
and invocation.

## Actual retail-map A/B measurements (13 November 2026)

The project owner supplied the *Seattle maps.zip* archive through the
project's Google Drive. The original extracted GMP and mission IBD data
were used **locally only**. No copyrighted assets have been uploaded to
GitHub, embedded in CI, or committed. The archive lacked shared
`Kernel_GFXALL.ibd`, and the exports therefore report missing models
(**16** in Penthouse Upper and **64** in Seattle Club). These are
**limited-content** but identical-input comparisons, not complete
retail-material fidelity assessments.

Source revisions and environment:
- Original `main` commit: `7fb22999764dad958e5a8e95aa3b8e01df832fdf`.
- Prior optimized exporter (before DXT1 palette cache):
  `3a8e027305f9b3a3c3e222462a322d2c8ff61ca5`.
- Dedicated DXT1 palette/row implementation introduced in:
  `965a610cbbc700182af795f0b2ea5d2fb8a41022`.
- Linux, CPython 3.13, same machine, extracted original mission bundles,
  temporary GLB/report output directories, without changing source maps.
  The first two columns each use **two controlled alternating runs**
  per map; new DXT1 figures are medians of **three** independent runs.
  No CPU timing threshold is enforced in GitHub Actions.

| Map | Original main, median | First fast path, median | DXT1 cached path, median | Main to DXT1 reduction |
| --- | ---: | ---: | ---: | ---: |
| `M1_Seattle_Hub_Penthouse_Upper.gmp` | 6.636 s | 5.510 s | 3.769 s | 43.2% |
| `M1_Seattle_Club.gmp` | 6.785 s | 5.567 s | 3.885 s | 42.7% |

**Exact output verification:** all three exporter versions produced the
same GLB and JSON sidecar SHA-256 *within each map*:

| Map | GLB SHA-256 | JSON report SHA-256 |
| --- | --- | --- |
| Penthouse Upper | `f01603df714d6e5543c6d84bee5e0cb715eb738cf1b1f5d004c0969c3e0eeac0` | `08b58019d4977282b50fe5d63d41f98d971501e8ef1586565746e70fe481bc30` |
| Seattle Club | `f8cf964318d33ccfa5068a74445cceffbdb68d98696cb24869a95ef1e4c7b5f7` | `63244d0314b5a681100774b03517665df70414e2e72e11b00fa9efd0c043a914` |

The core bottleneck was measured rather than inferred: the original
Penthouse Upper `cProfile` trace showed 490,880 calls to
`dx2textures._palette`, with `rgba_pixels` dominating the exporter.
The tested mission bundle contained 166 DXT1, 14 DXT3 and 1 BGRA8
texture resources. A separate 25-texture DXT1 microbenchmark containing
409,600 compressed blocks reduced RGBA decoding from ~2.7 s to
~1.2–1.3 s with identical decoded bytes.

Caveats: timing medians reflect a small local sample, cold/warm cache
effects and Python-version details. cProfile adds instrumentation and
must not be mixed into unprofiled wall-time comparisons. Byte-identical
outputs show the optimization preserved **the previous exporter output**,
not that every original game visual has been faithfully reconstructed.
For reproducible user-owned game-data measurements, see
[`BENCHMARKING.md`](BENCHMARKING.md).

## Limitations and follow-up

- The DXT optimizations remain Python-based. Large-scale asset processing
  may benefit further from a trusted native BC1/BC2/BC3 decoder or an
  **optional**, measured NumPy implementation. Do not make third-party
  packages mandatory without compatibility, packaging and security tests.
- A pure-Python texture decoder can still be slow on very large textures,
  especially DXT5. Profile rather than assume the next bottleneck.
- The inspector and texture gallery HTML templates were refactored
  separately in PR #172, not as part of the binary texture decoder.
- No original GMP/IBD writing or native game collision compilation is
  introduced by this performance work.
