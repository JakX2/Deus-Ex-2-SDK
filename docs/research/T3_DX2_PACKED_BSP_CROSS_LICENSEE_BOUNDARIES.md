# Thief 3 vs. Invisible War: shared packed BSP render-record boundaries

Research dated 2026-11-03. **Read-only, user-owned asset comparison**: one newly edited, exported *Thief: Deadly Shadows* game-ready GMP and two original *Deus Ex: Invisible War* Seattle GMPs.

This audit is the next step after verifying that T3Ed generated a new brush, compiled new Flesh BSP geometry, exported a native GMP, and successfully loaded it in **Thief 3 with player collision**. It does **not** imply T3's map compiler can build native DX2 mission maps.

## What is actually shared

| Metric | T3 test GMP | DX2 Seattle Hub | DX2 Seattle Club |
|---|---:|---:|---:|
| Package version | 95 | 95 | 95 |
| Licensee version | **133** | **68** | **68** |
| Package bytes | 68,118 | 2,561,763 | 2,296,630 |
| Export count | 37 | 3,173 | 3,168 |
| Editable Polys exports | 0 | 0 | 0 |
| Validated packed Flesh render records | **8** | **255** | **183** |
| Render vertices | 172 | 5,783 | 4,363 |
| Render triangles | 94 | 3,227 | 2,423 |
| Render payload bytes (excludes length words) | 21,024 | 468,104 | 437,540 |
| Level bytes before first render record | 7,300 | 537,038 | 543,166 |
| Level bytes after final render record | 23,951 | 817,146 | 617,362 |

Across **all 446 validated render records** in these samples:

1. The packed render block header begins with the same validated **80-byte header layout** and marker at header offset `0x44`.
2. The packed vertex data uses **32-byte vertex records** (the existing DX2SDK parser validates vertex positions, normals and UVs).
3. A **4-byte unsigned little-endian integer immediately before the render block header equals the exact following render block payload byte length**. This equality holds **446/446** for the three user-owned inputs.
4. The byte gap between two adjacent decoded render-block payloads is exactly **4 bytes in all 443 inter-block gaps** across the samples. That gap contains the next block's length prefix.

The record boundary supported by this sample is therefore:

```text
[u32 little-endian render_payload_byte_count]
[80-byte validated packed render header]
[vertex records, additional sections, indices, material records ...]
[next u32 render_payload_byte_count]
[next packed render payload]
```

The per-block size prefix is a concrete binary serialization invariant to reuse in read-only validation and, eventually, in a carefully bounded native writer. It does **not** reveal how the surrounding Level serialization, collision, AI, Havok, PVS or baked lighting works.

## Unknown Level data remains large

The *entire* T3 Level payload is 52,303 bytes, including 21,024 bytes of validated render payloads and 32 bytes of associated length prefixes. **31,247 bytes are not classified by this render-block tool.**

For Seattle Hub the Level payload is 1,823,304 bytes, including 468,104 packed render payload bytes and 1,020 associated length-prefix bytes. **1,354,180 bytes are not classified by this tool.**

For Seattle Club the Level payload is 1,598,796 bytes, including 437,540 packed render payload bytes and 732 associated length-prefix bytes. **1,160,524 bytes are not classified by this tool.**

These other bytes need not all be “native engine features”; many kinds of Level object records or tables may be present. Treat them as **unclassified**, not automatically as collision/PVS/Havok.

The comparison uses different maps of different sizes, so the differing counts do not isolate the licensee-version delta. Do not compute schema-compatibility conclusions by subtracting Seattle Hub counts from Tutorial3 counts.

## Reproducible audit

The new `research/t3ed/compare_t3_dx2_boundaries.py` script reuses the existing UE95 package and Flesh render-block validator. It checks the record-length DWORD independently of marker recognition.

```powershell
python research/t3ed/compare_t3_dx2_boundaries.py --t3 "C:\T3Research\DX2SDK_Geo_Test.gmp" --dx2 "C:\DX2Research\M1_Seattle_hub.gmp" --report "C:\Audits\t3-vs-dx2.json"
```

The JSON report records source-file hashes, licensee revisions, shared header/length-prefix grammar, class-name overlaps, Level byte-region partitions and explicit negative claims about native writer interchangeability.

Input GMPs remain untouched; report output must be **a new file outside both input map directories**.

Asset-free synthetic tests:
```powershell
python -m unittest discover -s native_editor/tests -p "test_t3_dx2_render_boundaries.py" -v
```

## Next DX2-specific engineering gates

1. Locate a small DX2 UE95/licensee 68 map and develop an independent, read-only decoder for the **non-render Level fields immediately surrounding one known render record**, with bounds checks and corpus validation.
2. Identify original DX2 Brush/Model/Level serialization and object references. A render-block writer alone cannot create valid native CSG actors or collision.
3. Only once those schemas have falsifiable fixture tests, attempt **isolated Save As of a copy** with before/after identity checks. No implicit writes to retail installations.
4. Validate custom DX2 map load and collision **in Invisible War itself**. T3 runtime results are informative but cannot satisfy this gate.

The report is about shared record boundaries, not a DX2 native compiler or working full BSP authoring.
