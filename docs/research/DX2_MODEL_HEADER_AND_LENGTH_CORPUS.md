# Source-observed native DX2 Model header and length patterns

**Research date:** 2026-11-03. Original user-owned *Deus Ex: Invisible War* maps, 19 Seattle GMPs. All UE95, DX2 licensee **65, 67, 68, or 69**. No game data is distributed.

This extends the [Level → GameSys45 → Model ownership audit](DX2_NATIVE_BRUSH_MODEL_OWNERSHIP.md), examining the serialized Model export itself. It does **not** decode the BSP tree or collision.

## Measured header layout, all 3,905 Model exports

| Offset | Bytes | Source-observed interpretation |
|---|---:|---|
| 0 | 9 | Zero prefix in all Model payloads; meaning unknown |
| 9 | 24 | Six little-endian float32: box min XYZ and max XYZ |
| 33 | 1 | Box-valid byte (1 in 3,886, 0 in 19) |
| 34 | 12 | Three float32 bounding-sphere center coordinates |
| 46 | 4 | Float32 bounding-sphere radius |
| 50 | 1 | Byte statistically correlated with Model payload size, unknown actual type |
| 51 onward | variable | Not yet decoded as planes, polygons, BSP nodes or collision |

This is consistent with a serialized bounding box and sphere. The user's *Thief3-Decomp* snapshot has an in-memory `FBox` definition (six FVector floats and validity byte with three pad bytes), which is a useful **independent hint**, but **not source-code proof of DX2 serialization**.

## Broad corpus findings

| Licensee | Models | Valid box byte | Invalid box byte | Radius exceptions |
|---|---:|---:|---:|---:|
| 65 | 373 | 370 | 3 | 1 |
| 67 | 739 | 736 | 3 | 8 |
| 68 | 2,442 | 2,430 | 12 | 31 |
| 69 | 351 | 350 | 1 | 5 |
| **Total** | **3,905** | **3,886** | **19** | **45** |

Every one of the 3,886 valid-box Model centers matches the source bounding-box midpoint to within 0.001 Unreal units (maximum observed absolute error `0.000244).

For 3,841 of those 3,886 Models, the saved sphere radius matches **1.001 × bounding-box half-diagonal** within a source-observed float32 tolerance. **45 do not.** These exceptions must be retained rather than silently fixed.

All 19 invalid-box Models have zero min/max/center/radius values, with substantial other native payload content. Each map has exactly one. These may be compiled world Models; the ownership/BSP relationship is **not yet proven**.

### Byte-50 length correlation

For **3,885 of 3,886** valid-box Models, serialized payload byte length obeys:

```text
payload_bytes = 63 + (109 * byte_at_offset_50)
```

| Payload bytes | Models | Byte 50 |
|---:|---:|---:|
| 63 | 3,577 | 0 |
| 608 | 8 | 5 |
| 717 | 296 | 6 |
| 826 | 2 | 7 |
| 1,371 | 1 | 12 |
| 1,698 | 1 | 15 |
| 2,137 | 1 | 19 |

**Exception:** `M1_Seattle_Hub_Penthouse.gmp`, `Model__106`, export 1172, has byte 50 = 19. The formula predicts 2,134 bytes; the actual payload is **2,137 bytes (+3)**.

Thus **109 is not established as a fixed per-polygon record stride**. It is a statistical relationship, possibly affected by variable-size indices, vertices, or another as-yet unknown layout field. Do not derive native writers from this formula.

### Wider Brush reference caveat

Across the same 19 maps, 3,392 of 3,408 original Brush actors have a unique valid GameSys45 object reference to Model. **16 Brushes** in `M1_Seattle_Acorp_Lab_Upper.gmp` (licensee 67) lack that property. The ownership auditor must continue reporting these exceptions rather than inventing missing references.

## Reproduce the read-only audit

From the DX2SDK repo root:

```powershell
python research/dx2/inspect_model_serialization.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" --report "C:\DX2_Research_Reports\model_header_audit.json"
```

Use `--summary-only` to omit individual Model rows. The program hashes its source inputs, refuses output in original map directories, never overwrites reports and never mutates a GMP.

Run synthetic tests:

```powershell
python -m unittest discover -s native_editor/tests -p "test_dx2_model_serialization.py" -v
```

**Not supported:** writing Models, native polygon/BSP parsing, collision compilation, Havok, AI, CSG semantics or running a modified map in DX2.

## Next gate

Decode the variable region from offset 51 against examples with count bytes 0, 5, 6, 7, 12, 15 and 19, including the **three-byte size exception**. Then investigate the large invalid-box Model payloads and their Level relationship. Only progress toward a DX2 BSP writer after independent, falsifiable read/roundtrip tests.
