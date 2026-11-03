# DX2 native Model: candidate face-plane coefficients (read-only)

Research dated 2026-11-03. Independent binary inspection of **19 user-owned Invisible War maps**, across Unreal package version 95, DX2 licensee versions **65, 67, 68, 69**. No proprietary data stored in the repository.

## Observations, not an invented native BSP schema

The [Model header / count corpus](DX2_MODEL_HEADER_AND_LENGTH_CORPUS.md) established:

- Offset 9: six bounding-box float32 values
- Offset 33: one-byte valid-box flag
- Offset 34: three float32 sphere-center values
- Offset 46: float32 radius
- Offset 50: count-correlated byte
- For 3,885/3,886 valid-box Models, total length = 63 + 109 * byte[50]

For **308** valid-box Models with a nonzero count and an **exactly matching** length, the following source-observed locations contain four readable float32 values:

```text
0x33 (decimal 51): candidate (normal x, normal y, normal z, coefficient)
next candidate: +109 bytes
next candidate: +109 bytes
...
count candidates: byte at offset 50
```

Across these Models, **all 1,857 candidate triples have unit length to within approximately 1.3e-7**. Examples include axis normals (`-1,0,0`), (`0,1,0`) and (`0,0,-1`) paired with signed plane coefficients.

That supports a **candidate plane-equation interpretation**. However, **the sign convention, coordinate space, polygon vertices and the remaining 93 bytes of each 109-byte span are not yet decoded**. In particular, **83/1,857** candidate coefficients fall outside the naive projection of the stored bounding box. This does **not** mean the source data is malformed: the bounds and plane values may be in different frames, or the fourth scalar may have different semantics. Do **not** force a world-space plane equation from this evidence.

The **one size-exception Model** (`M1_Seattle_Hub_Penthouse.gmp`, `Model__106`, 2,137 bytes, byte[50] = 19, 3 extra bytes) is intentionally **excluded**. The program never assumes a fixed 109-byte native face structure for that Model or silently guesses an alignment.

## Validation and use

The read-only script `research/dx2/inspect_model_plane_candidates.py` uses the previous native Model-header validator. It:

- Finds Model exports from user-owned DX2 GMPs.
- Checks the previously observed box header and exact length formula.
- For matching nonempty records, reads only candidate plane coefficient quartets, verifies finite values and unit-length normal, and reports original payload offsets.
- Records cases skipped because of invalid-box flags, unknown headers, count zero or nonconforming lengths.
- Never modifies source maps or writes a game package. Output is new JSON, outside game map directories.

```powershell
python research/dx2/inspect_model_plane_candidates.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" --report "C:\DX2_Research_Reports\candidate_planes.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_model_plane_candidates.py" -v
```

**Limits:** This is a **partial native surface-layout observation**, not a complete FPoly parser, CSG compiler, Level/Model link decoder, collision system, Havok/AI/PVS decoder or functional DX2 map writer.

## Next experiment

Compare the 93 unclassified bytes within each normal-plus-coefficient span across simple six-sided Models and find candidate polygon vertex counts/indices. Use both unrotated and rotated source brushes; test the exceptional 2,137-byte Model separately to identify whether the extra 3 bytes represent a compact index or variable-sized field. Only after reconstructing the record grammar should DX2SDK attempt a byte-preserving parse/serialize of those specific native Model sections.
