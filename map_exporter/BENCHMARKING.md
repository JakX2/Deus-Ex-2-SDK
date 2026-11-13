# DX2 map exporter: whole-map performance profiling (research tool)

The existing `tools/benchmark_exporter_hotpaths.py` measures deterministic
**synthetic** texture and vertex workloads. Those speedups do **not** establish
that a complete retail level export is faster: package parsing, triangle
index assembly, mesh instancing, PNG compression, JSON generation and I/O
may dominate a real map.

`tools/profile_dx2_map_export.py` measures the **actual read-only map
export pipeline** using the user's **locally installed/extracted** original
Deus Ex: Invisible War data. It does not ship original game resources,
send files anywhere, or write into the game installation.

## Usage (PowerShell)

1. Supply an extracted `Content\DX2\Maps` directory containing the original
   `.gmp` and mission/shared `.ibd` files. A compressed `maps.zip` by itself
   is **not** a substitute for the extracted source assets. Keep an original
   copy of the game data.
2. Run an unprofiled repeated export plus **one separate cProfile pass**:

```powershell
python tools/profile_dx2_map_export.py `
  --maps "D:\Games\Deus Ex Invisible War\Content\DX2\Maps" `
  --map M1_Seattle_Hub_Penthouse_Upper.gmp `
  --repeats 3 --top 25 `
  --report "D:\DX2_Benchmark_Reports\penthouse_upper.json"
```

For a map with uncertain bundle autodetection, explicitly pass the matching
mission IBD as `--bundle "D:\...\m3_trier.ibd"`. Add further `--bundle`
arguments for required shared bundles in the intended precedence order.
The report path must have an unused `.json` name **outside the folders
holding source map/bundle files**. Parent directories must already exist.

For a wall-time-only trial:

```powershell
python tools/profile_dx2_map_export.py --maps "D:\Games\Deus Ex Invisible War\Content\DX2\Maps" --map M1_Seattle_Hub_Penthouse_Upper.gmp --repeats 5 --no-profile
```

The script produces every GLB and sidecar report in an automatically deleted
OS temporary directory. It hashes the original source GMP, selected IBD/ZIP
bundles and optional transform-override JSON before/after. It checks **byte
identical** GLB and sidecar report hashes across unprofiled and profiled
runs, and fails if any original input changed. If `TMP` or `TEMP` points
inside the source asset folder, the run is refused. A successful run writes
only the explicitly requested **new** JSON benchmark report.

## Reading the report

- `unprofiled_wall_ms`: wall-clock samples; **first sample may incur cold
  OS filesystem caches, Python imports, shader/PNG work and disk reads**.
- `median_unprofiled_ms`: within-machine central result. Record CPU,
  Python version, storage, bundle selection, caches and map name before
  comparing branches. Run several times before attributing small differences
  to code.
- `profile.wall_ms_including_profiler`: instrumentation-distorted, separate
  timing; **do not** interpret it as a directly comparable wall-time sample.
- `profile.hot_functions`: exporter functions sorted by **cumulative**
  cProfile time, with self time, call counts, module basename and source
  line. Inspect these before selecting a rewrite to NumPy, C++, or a native
  decoder. `cumulative_ms` includes callees and can double-count down the
  call tree. It is **not** a breakdown of disjoint fractions of total time.
- `output_glb_sha256`, `output_report_sha256`: exact output fingerprints,
  useful for detecting a change in the exporter's behavior, not absolute
  proof of correct game semantics.
- `original_assets_unchanged_sha256`: safety confirmation for the tested
  source inputs only.

The report intentionally excludes absolute paths and all source bytes. It
does not assess frame rates in Godot, native DX2 material fidelity, BSP/CSG
compilation, collision, or gameplay.

## Repeatable comparison

Use the **same local map, exact selected bundles, transform overrides,
Python version, CPU, OS, and filesystem/cache conditions**. For credible
baseline and candidate comparisons, run both checkouts independently and
alternate their order. Compare output fingerprints as well as medians.
A different SHA may indicate a functional change requiring investigation,
even if the export is faster. Never use a benchmark number as a CI speed
threshold: shared runners have unstable CPU and I/O load.

## No-asset automated tests

```powershell
python -m unittest discover -s tests -p "test_exporter_full_map_profile.py" -v
python tools/profile_dx2_map_export.py --help
```

Those tests use a synthetic exporter to verify temporary GLB cleanup, asset
hashing, deterministic output refusal, hot-function reporting and safe
report paths. They do not measure any retail map. Real map benchmarking is
an **optional, explicit local task**, not an implicit GitHub Actions job.

Current boundary: the exporter is inspection-only. A complete source map
profile is useful to decide where to optimize but does not make the DX2Ed
SDK a production-level editor or enable native game BSP/collision writes.
