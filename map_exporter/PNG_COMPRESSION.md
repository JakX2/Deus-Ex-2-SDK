# Opt-in fast PNG encoding for DX2 GLB previews

The original DX2 map exporter embeds zlib-compressed RGBA PNG files in GLB
previews. The default PNG compression is **level 7** and is unchanged in
this implementation, retaining exactly the legacy PNG/GLB bytes.

**Faster export is opt-in** via zlib level 1. It produces larger, still
lossless embedded PNGs. It does not change decoded RGBA pixels, texture
alpha, geometry, glTF materials or map parsing. Because compressed PNG
sizes change, GLB byte offsets and total file sizes also change; **GLB
and JSON report SHA-256 hashes are not expected to match across levels**.
Do not use a raw GLB byte comparison to claim a rendering regression for
this particular option.

## Using the option

```powershell
python map_exporter/dx2_map_exporter.py export `
  --game-root "D:\Games\Deus Ex Invisible War" `
  --map M1_Seattle_Hub_Penthouse_Upper.gmp `
  --output "D:\DX2_Exports\Penthouse_fast.glb" `
  --png-compression 1
```

Choose any integer from **1 through 9**. The CLI defaults to **7**.
The Windows GUI has a checkbox labeled **Fast PNG compression (larger
GLB, same pixels)**. Leave the box unchecked for the original output.
The low-level `dx2level.py` CLI and Python `run_export` API also support
`png_compression_level`.

No original `.gmp`, `.ibd`, DX2 World BSP, Havok/MOPP or GameSys data
is written or converted by this change.

## Read-only measurements (Linux, Python 3.13.5)

Locally extracted, user-supplied Seattle GMP and mission IBD data,
tested on the same machine with **ABBA ordering: 7, 1, 1, 7**.
Each level has **two independent full-map runs**. These timings are
indicative, not a broad speed guarantee or automated CI assertion.

| Mission | PNG 7 median | PNG 1 median | Export time saved | GLB growth |
| --- | ---: | ---: | ---: | ---: |
| Corporate Campus Interior | 3.827 s | 2.122 s | 44.5% | 18.5% |
| Penthouse Upper | 3.525 s | 1.954 s | 44.6% | 19.7% |

File sizes and embedded texture counts:

| Mission | PNG 7 GLB | PNG 1 GLB | Embedded textures |
| --- | ---: | ---: | ---: |
| Corporate Campus Interior | 9,871,916 bytes | 11,699,572 bytes | 78 |
| Penthouse Upper | 8,764,508 bytes | 10,492,608 bytes | 74 |

Correctness checks were stronger than comparing PNG bytes:

- For **every embedded PNG**, validated PNG chunk CRCs, RGBA8 IHDR
  properties, filter-zero scanlines and decompressed RGBA image bytes
  at both compression settings.
- Compared every **non-image glTF binary buffer view**, byte-for-byte;
  texture and geometry source data were otherwise identical.
- Compared the complete glTF JSON after normalizing changed buffer
  offsets, image compressed lengths and the overall BIN length.
- Compared the original sidecar JSON reports except for the expected
  `output_glb_bytes` field.
- Confirmed **deterministic GLB/report hashes within each setting**, and
  unchanged source map/bundle SHA-256 fingerprints.

This archive still lacks `Kernel_GFXALL.ibd`, so **45 static mesh
actors** are missing from the Campus Interior export and **16** from
Penthouse Upper. These are partial-content preview export benchmarks.
They do **not** prove complete retail material fidelity, native BSP
writing, collision reconstruction, or playability.

## Source-only regression and CI

```powershell
python -m unittest discover -s tests -p "test_exporter_png_preset.py" -v
```

The asset-free regression tests lossless RGBA identity at levels
1, 2, 3, 7 and 9; original level-7 bytes; malformed level refusal;
cropped textures; cubemap contact sheets; and simulated GLB geometry
buffers surrounding a changed PNG. It runs in the exporter hot-path
GitHub Actions workflow across Python 3.10 and 3.12 on Windows/Linux.
Performance thresholds are deliberately **not** CI tests.

Next profiling candidates: remaining DXT5, material expansion and
original shared-graphics resource discovery. They should be measured
on representative assets before a native rewrite is considered.
