# DX2 compiled-world Model: native BSP node and zone-table boundaries

Research date: 2026-11-03. Read-only study of **19 user-owned Invisible War GMPs** (UE package version 95, DX2 licensees 65, 67, 68, 69). This extends the [direct Level-to-world Model reference audit](DX2_LEVEL_DIRECT_WORLD_MODEL_REFERENCE.md).

## New source-observed Model layout

The native world Model contains:
- 50-byte empty-bounds header
- Unreal compact positive integer: candidate BSP node count
- **109–116-byte variable-size node records**
- One u32 count of candidate zone records
- **69 bytes per candidate zone record**
- 8-byte zero trailer

**All 17,743 candidate nodes in all 19 original DX2 maps** can be partitioned unambiguously with the following independent checks:

1. Each node starts with a 16-byte, four-float candidate plane; the XYZ vector has unit length.
2. The next 32 bytes are mask-like, matching the 256-bit zone-mask expectation in the user's T3 decompilation reference. DX2 mask semantics are **not decoded**.
3. Each node's final 16 bytes consists of two little-endian signed i32 values within [-1, node_count−1], a zero u32 and an opaque u32.
4. For nonterminal nodes, exactly one length in the source-observed range leads to another valid normalized plane.
5. The last node has suffix i32 pair (-1, -1) and lands exactly on the counted 69-byte entry array; the final 8 bytes are all zero.

The i32 suffix pair is **not proven to be BSP child references**. Node zero frequently has (-1, -1) despite many additional nodes. Keep its semantics unclassified until the missing link fields are decoded.

## Widths and suffix patterns, entire corpus

| Node record bytes | Count |
|---:|---:|
| 109 | 37 |
| 110 | 567 |
| 111 | 3,257 |
| 112 | 5,011 |
| 113 | 3,031 |
| 114 | 3,096 |
| 115 | 2,068 |
| 116 | 676 |
| **Total** | **17,743** |

Trailing pair patterns:

| First i32 | Second i32 | Count |
|---|---|---:|
| -1 | -1 | 14,832 |
| -1 | nonnegative | 2,697 |
| nonnegative | -1 | 16 |
| nonnegative | nonnegative | 198 |

The 19 maps have **688 candidate zone records** (per map 18–73), each exactly 69 bytes. In each Model, the byte partition equation closes:

```text
model_length =
    50 + compact_index_width
    + sum(native node byte lengths)
    + 4 + (69 * candidate_zone_count) + 8
```

The candidate zone table interpretation is consistent with the user's Thief3-Decomp `tools/assets/t3bsp.py` and `docs/assets.md`, but the **meaning of fields inside the 69-byte records is not independently established in DX2**. This is byte framing and source cross-validation, not a decoded zone visibility system.

## Reproduce the read-only audit

Run from the DX2SDK repo root:

```powershell
python research/dx2/inspect_world_bsp_node_boundaries.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" --report "C:\DX2_Research_Reports\world_bsp_nodes.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_world_bsp_node_boundaries.py" -v
```

The optional `--include-nodes` switch outputs per-node source offsets, lengths, candidate planes and bounded suffix integers. This can generate a large JSON report. Reports must be new files outside the original game map directories; no input GMP is modified.

## Compiler research roadmap

1. Decode the compact node links and real BSP child/leaf topology from the variable middle segment (between mask and final 16-byte suffix).
2. Investigate the 69-byte candidate zone record grammar and cross-reference it against the node's 256-bit mask region.
3. Match BSP nodes to Level Flesh render-block IDs and other remaining geometry sections.
4. Determine and validate native DX2 collision/cooking dependencies and only then design a verifiable, isolated package writer.

The resulting parser **does not** implement native BSP rebuilding, collision, CSG, PVS, AI navigation, Havok, or any runtime-tested custom map.
