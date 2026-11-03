# DX2 Level → compiled-world Model reference: 19-map proof

**Research:** 2026-11-03. **Input:** 19 user-owned, original *Deus Ex: Invisible War* Seattle GMPs, UE package version 95, DX2 licensees 65, 67, 68 and 69. All operations are **read-only**; no retail assets or package dumps are committed.

## Resolving the "unreferenced Model" mystery

Previous [Brush/Volume ownership](DX2_NATIVE_BRUSH_MODEL_OWNERSHIP.md) and [convex volume reconstruction](DX2_NATIVE_MODEL_CONVEX_RECONSTRUCTION.md) found **exactly one large Model export per map that was not owned by a Level-listed actor's GameSys property 45**. That does **not** mean the Model is orphaned.

The **Level object itself** stores a **direct compact export reference** to the large Model, after its native actor list and URL. This reference is validated against the source package's real export table, not inferred from the Model's name or its payload length:

```text
UE95 Level export
    13-byte source-observed header
    u32 actor count; u32 repeated actor count
    array of actor compact export references
    FURL:
       FString protocol
       FString host
       FString map
       FString portal
       compact options count
       FString[options_count]
       u32 port
       u32 valid
    compact native Model export ref  <----- NEW, directly verified on DX2
    ... remaining Level data (not decoded by this tool)
```

The direct reference points to an export of class `Model` and **is not in the actor list**. The Model is distinct from the ordinary 63-byte Brush-owned Model exports and the face-bearing volume-owned Models.

The source-owned T3-Decomp reference document described a Level-to-Model reference after the URL. This investigation independently confirms the field and its target on **DX2's own retail map binaries**, including its exact Level-relative offset in each sample.

## Validated corpus

| Metric | Count |
|---|---:|
| DX2 GMPs examined | **19** |
| Direct Level refs targeting real Model exports | **19/19** |
| Direct target equals the sole large, invalid-box Model of its package | **19/19** |
| First candidate node plane begins after a valid compact count | **19/19** |
| First candidate normal is unit length (within 0.001) | **19/19** |
| Sum of candidate node counts | **17,743** |
| Smallest / largest source-observed count | **360 / 1,648** |

Package licensee distribution in sample: **65: 3 maps, 67: 3, 68: 12, 69: 1**.

Examples:

| Level | Direct Model export | Bytes | Compact count at Model offset 50 |
|---|---|---:|---:|
| `M1_Seattle_hub.gmp` | `Model__107`, export **693** | 148,674 | 1,281 |
| `M1_Seattle_Club.gmp` | `Model__77`, export **1595** | 111,425 | 961 |
| `M1_Seattle_Hub_WTOterminal.gmp` | `Model__44`, export **1233** | 66,078 | 576 |

In **all 19** of these source maps, the first 50 bytes of the direct Model have the observed invalid/empty box+bounding-sphere prefix. **At byte 50** is a **two-byte Unreal compact positive integer**, then four little-endian float32 values, with a unit-length first-three-component normal. This is consistent with the beginning of **serialized BSP node-like records**, but the actual node field identities, child links, zone masks, leaves and collision remain undecoded.

**Important:** The count is presently a **candidate node count**, not a source-code-authenticated `FBspNode` element count. Other map versions or serialization layouts must be independently validated.

## Reproducible read-only audit

Run from the SDK repo root, with **user-owned** original GMPs:

```powershell
python research/dx2/inspect_level_world_model.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" --report "C:\DX2Research\direct_world_model.json"
```

For each map the JSON stores source SHA-256, source package/licensee version, actor count, URL fields, Level-relative **exact offset** of the direct native Model reference, target export index/name, native Model payload hash/size, candidate node count/offset and first candidate plane. Reports must be **new files outside the source map directories**; the reader never modifies source GMPs.

Synthetic regression tests (no copyrighted game fixtures):

```powershell
python -m unittest discover -s native_editor/tests -p "test_dx2_world_model_root.py" -v
```

Tests cover original Level actor count consistency, FURL with optional strings, valid direct references, wrong target class, invalid actor references, direct Model listed as actor, malformed node counts, wrong package licensee, report output safety and source preservation.

## Next significant compiler milestone

Now that DX2 SDK can identify the **actual compiled world Model export**, the next task is decoding its **BSP node-array grammar**, not extrapolating from 63-byte Brush models or volume polygons. In particular:

1. Decode the variable-width node record structure, using node-like plane quartets and the 19-map corpus.
2. Recover child/leaf references and validate bounds, reference ranges, zone masks and tree connectivity.
3. Correlate tree data with Level's packed Flesh BSP render records, and determine what runtime collision requires.
4. Only after independent parse/round-trip tests, design isolated package writing and game-runtime verification.

**This PR does not produce or verify a new compiled DX2 map, collision, Havok, CSG or any native BSP writer.**
