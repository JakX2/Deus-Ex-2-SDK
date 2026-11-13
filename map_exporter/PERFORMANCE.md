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

## Limitations and follow-up

- The DXT optimizations remain Python-based. Large-scale asset processing
  may benefit further from a trusted native BC1/BC2/BC3 decoder or an
  **optional**, measured NumPy implementation. Do not make third-party
  packages mandatory without compatibility, packaging and security tests.
- A pure-Python texture decoder can still be slow on very large textures,
  especially DXT5. Profile rather than assume the next bottleneck.
- The embedded HTML in `dx2inspect.py` and texture gallery is a
  **maintainability concern, not this measured hot path**. Moving it to
  package-relative HTML templates should be handled in a separate
  compatibility-tested refactor, not mixed with binary texture changes.
- No original GMP/IBD writing or native game collision compilation is
  introduced by this performance work.
