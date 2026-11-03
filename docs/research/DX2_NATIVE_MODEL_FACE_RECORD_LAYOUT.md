# DX2 native Model: variable-width face record boundaries

Research date: 2026-11-03. Read-only original user-owned Invisible War GMPs, **19 Seattle maps**, UE package v95, DX2 licensees 65, 67, 68, 69. No retail game assets committed.

## Why the prior 109-byte size rule had one exception

Earlier Model work found 3,885 / 3,886 nonempty Models fit:

```text
Model payload bytes = 63 + (109 * byte[50])
```

The exception, `M1_Seattle_Hub_Penthouse.gmp` `Model__106`, is 2,137 bytes with count 19, three more than predicted. Its final three face records use **110 bytes**, while the first 16 use **109 bytes**. Thus exactly three extra bytes are accounted for by **three one-byte wider face records**.

The new dynamic decoder matches **every nonempty Model in the examined 19-map corpus**, not just Models following the simple length formula.

## Source-validated record landmarks

For record length N = 109 or 110 bytes, all listed offsets are **relative to the start of a candidate face record**.

| Offset | Bytes | Observation |
|---|---:|---|
| 0 | 12 | Three float32 candidate unit-normal components |
| 12 | 4 | Float32 candidate plane coefficient |
| 16 | 32 | All zero, meaning unclassified |
| 48 | 1 | Zero byte |
| 49 | 1 | Byte-sized running vertex-start offset |
| 50 onward | variable | Native fields not fully decoded; byte 50 is **not always a sequential polygon ID** |
| N − 53 | 12 | Three-float candidate point on the plane |
| N − 41 | 4 | Float32 candidate face bounding radius |
| N − 37 | 20 | Zero bytes |
| N − 17 | 1 | Candidate vertex count (3, 4, 5 observed) |
| N − 16 | 8 | Eight 0xFF bytes |
| N − 8 | 4 | Four zero bytes |
| N − 4 | 4 | Little-endian u32 running vertex start, matching byte at offset 49 |

Across all 1,876 records, both stored running vertex-start fields agree with the sum of **previous faces' vertex counts**. Candidate normals have length `1 (max error `1.3e-7), and the candidate plane coefficient equals the dot product of normal and plane point to within **0.004542 UE units**. These are strong internal consistency checks, not source-code confirmation of engine struct names.

The counts are **vertex indexing slots, not decoded XYZ vertex positions**. A usable brush, UV or collision model is not yet reconstructed.

## Empirical 19-map totals

| Metric | Result |
|---|---:|
| Model exports | 3,905 |
| Nonempty Model payloads fully recognized | **309 / 309** |
| Models with valid bounds and no candidate faces | 3,577 |
| Models with invalid bounds, intentionally skipped | 19 |
| Candidate face records | **1,876** |
| 109-byte records | 1,873 |
| 110-byte records | 3 |
| Triangles by candidate vertex count | 16 |
| Quads by candidate vertex count | 1,856 |
| Pentagons by candidate vertex count | 4 |
| Total candidate vertex-index slots | **7,492** |

The record width of 110 is an **observed exception**, not a universal limit. Future maps may contain different sizes and must be refused until characterized.

## Reproduce and verify

From the DX2SDK repository root, using copies of user-owned maps:

```powershell
python research/dx2/inspect_model_face_records.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Hub_Penthouse.gmp" --report "C:\DX2_Research_Reports\native_face_records.json" --include-faces
python -m unittest discover -s native_editor/tests -p "test_dx2_model_face_records.py" -v
```

The reader independently verifies a 32-byte zero section, two vertex starts, vertex count, normal unit length, point-plane equation, fixed suffix anchors and 12-byte tail. Corrupt/ambiguous input is reported as unsupported. It never modifies source GMPs; reports must be new and outside the input directories.

## Next real engineering gate

Find **polygon corner positions or their recoverable topology**. Validate the brush-space plane representation against original actor transforms and derived bounds, then pursue a conservative native Model round-trip. The 19 large invalid-box Model exports and DX2-specific collision/BSP build stages remain opaque.

**No native DX2 CSG compiler, BSP writer, new collision or runtime-verified map is produced by this audit.**
