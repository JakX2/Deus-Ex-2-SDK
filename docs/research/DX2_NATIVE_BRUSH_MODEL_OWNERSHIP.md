# DX2 Brush/Volume → native Model ownership (read-only)

Research dated 2026-11-03, based on **three user-owned retail DX2 Seattle maps**, all Unreal package version 95, licensee version 68. This is a DX2-specific investigation, not evidence that T3Ed's licensee-133 compiler works in Invisible War.

## Discovered serialized reference chain

1. The `Level` export begins with a source-observed actor list at Level-relative byte **13**: two equal `u32` actor counts, then compact Unreal export references. Both `Brush` and volume actors appear in this list.
2. Each examined `Brush` actor has exactly one Ion Storm **GameSys property 45** of type `object`, pointing directly to a valid `Model` export. Other volume actors use the same property ID.
3. **All 515 Brush references are unique and valid.** Additional Model owners are `NavMeshSubtractionVolume`, `AITaggedVolume`, `DatalinkVolume`, and `Volume`.
4. After accounting for 580 actor-owned Models, exactly one Model export per map remains without a Level-listed actor's property-45 link. These large exports are plausible combined-world-model candidates, but their relationship to Level is **not fully decoded**.
5. All 583 Model payloads start with nine zero bytes, then six little-endian finite ordered `f32` values at offset 9, compatible with a candidate bounding-box field. **Local/world coordinate convention and collision meaning are unverified.**

Do not interpret raw numeric `CsgOper` tagged values `1` and `2` as proven CSG semantics yet.

## Corpus findings

| Metric | Seattle Hub | Seattle Club | WTO Terminal | Total |
|---|---:|---:|---:|---:|
| Brush exports / Level-listed brushes | 241 | 183 | 91 | **515** |
| Brush GameSys45 → valid distinct Model | 241 | 183 | 91 | **515** |
| Model exports | 263 | 216 | 104 | **583** |
| Actor-owned distinct Models | 262 | 215 | 103 | **580** |
| Unowned by actor GameSys45 | 1 | 1 | 1 | **3** |
| Multiply owned Models | 0 | 0 | 0 | **0** |
| Models with plausible six-f32 bounds header | 263 | 216 | 104 | **583** |

Additional Model ownership: `NavMeshSubtractionVolume` **47**, `AITaggedVolume` **6**, `DatalinkVolume` **7**, `Volume` **5**.

Three large unowned Model candidates: `Model__107` (Seattle Hub, 148,674 bytes), `Model__77` (Seattle Club, 111,425 bytes), and `Model__44` (WTO Terminal, 66,078 bytes). "Unowned" means unowned **by this property 45 link**, not unreferenced anywhere in the package.

## Reproduce the audit with user-owned DX2 map data

Run from repository root:

```powershell
python research/dx2/inspect_brush_model_links.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" --report "C:\DX2_Research_Reports\seattle_brush_model.json"
```

The tool uses the existing UE95 package and GameSys decoders, checks the Level actor list, derives explicit Model export targets and flags duplicates/missing or malformed links. It emits JSON with source SHA-256, counts, source actor/model names, candidate header bounds and *research caveats*. The original GMP is never edited. Output must be new and outside the game map directory.

Asset-free tests:

```powershell
python -m unittest discover -s native_editor/tests -p "test_dx2_brush_model_links.py" -v
```

## What remains before a native DX2 geometry writer

- Decode the complete Model-native payload and the three large world-model candidates. The plausible bounding header is only a first structural field.
- Establish what the original native CSG and Level data do with Model references; document, then test, actual `CsgOper` semantics.
- Understand DX2-specific BSP rebuild, collision, PVS and resource-block dependencies, rather than importing conclusions from Thief 3.
- Only then implement isolated GMP output with independent whole-package verification, and test the result in **Invisible War** itself.

**No playable DX2 level, new collision data or native brush writer is claimed by this work.**
