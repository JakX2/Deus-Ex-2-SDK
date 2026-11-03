# DX2 world BSP: source-verified eight compact indices and rooted tree

Research dated 2026-11-03. This follows [the world-Model node framing audit](DX2_WORLD_BSP_NODE_ARRAY_BOUNDARIES.md), using **19 original user-owned Invisible War Seattle maps**, UE package version 95, DX2 licensee versions 65, 67, 68 and 69. **No retail assets are included.**

## Exact native serialization observation

Inside each already boundary-validated variable-size world-Model node, between its first 48 bytes (four-float candidate plane + 32-byte mask-like region) and its source-observed 16-byte sphere data, there are **exactly eight Unreal signed compact integers**. Their encoded byte widths vary, explaining the 109–116-byte node record lengths.

```text
Node:
    f32[4] candidate splitting plane
    32 bytes candidate zone mask
    compact integer field 0
    compact integer field 1
    compact integer field 2
    compact integer field 3  <-- link candidate A
    compact integer field 4  <-- link candidate B
    compact integer field 5  <-- link candidate C
    compact integer field 6
    compact integer field 7
    sphere-like center XYZ + radius
    remaining node flags / zone / leaf-like fields (not fully identified)
```

Fields **3, 4, 5** always contain **-1 or a valid node index** in all 17,743 sample nodes. Their combined references satisfy a much stronger invariant than merely being within range:

- **One unique root at node index 0** in every map
- **Exactly one incoming reference for every other node**
- **Exactly N−1 edges per map**, with no duplicate targets
- **Every node reachable from the root** using these three fields
- **No cycles**, as established by the full root traversal and unique-parent check

This is the first independently validated **native world BSP reference graph** across the 19-map source corpus.

## Statistics from the 19 retail maps

| Finding | Count |
|---|---:|
| Source maps | 19 |
| World BSP nodes / eight-compact records | **17,743** |
| Rooted graph edges | **17,724** |
| Links in compact field 3 | 2,875 |
| Links in compact field 4 | 7,116 |
| Links in compact field 5 | 7,733 |
| Largest root-to-node graph depth | **47** |
| Sum of all node link depths | **151,157** |

### Clues about the three link types

The candidate splitting-plane equation is treated as normal.xyz dot point = W. Using the **target node's saved bounding-sphere center**, the source data correlate strongly with side membership:

| Candidate field | Observed expected geometric relationship | Hits |
|---|---|---:|
| Compact #3 | Child center on **negative** side | **2,866 / 2,875** |
| Compact #4 | Child center on **positive** side | **7,087 / 7,116** |
| Compact #5 | Parent and target candidate planes equal or opposite within tolerance | **7,696 / 7,733** |

Breakdown for compact #5: 7,079 same-oriented planes, 617 opposite-oriented planes, and **37** exceptions which are retained as anomalies. The 38 source side-test misses for #3/#4 include points extremely near their parent planes; **do not** silently claim 100% spatial partition agreement or decode all gameplay BSP semantics from centers.

These relationships strongly suggest equivalent roles to Unreal's **back-side, front-side, coplanar-chain** links. The engine's exact C++ field names and traversal semantics are **still provisional**. An ordinary BSP tree would have two spatial branches with an auxiliary coplanar chain, which aligns with this evidence. We deliberately preserve the original field numbers (3/4/5) in the machine-readable audit.

### The remaining compact fields

- Compact field 0 takes only **0** or **5** in the examined corpus. Its exact role is unknown.
- Compact fields 1 and 2 have nonnegative values of very different ranges. They are *not* confidently mapped to native vertex pool / surface fields yet.
- Compact fields 6 and 7 may be -1 or nonnegative; field 6 sometimes **exceeds the total BSP node count**, so it must **not** be validated as another node child pointer.

No field names, collision information, leaves, zones, PVS or render-block mapping are invented for these values.

## Reproducing the read-only DX2 audit

Run from repository root, with the user's own map files:

```powershell
python research/dx2/inspect_world_bsp_tree_links.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" --report "C:\DX2_Research_Reports\world_bsp_tree_links.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_world_bsp_tree_links.py" -v
```

The optional `--include-edges` adds explicit parent/child indices to the report. This can produce large output, so the default report contains only graph and geometric-consistency summaries.

The reader reuses the verified native Level-to-world-Model pointer and the variable-sized BSP node-record validator, checks exact eight-compact index framing, rejects invalid or self-referential links, checks the full rooted graph and preserves plane-side exceptions. Reports must be new files outside original map directories. The original retail GMP is **never modified**.

## Engineering consequence

We now have a read-only native world BSP **topology** view, not just an unstructured list of planes. The next compiler-specific obstacles are:

1. Identify surface/polygon/vertex-pool links represented by the **other compact fields** and source node suffix.
2. Decode the candidate zone-record and mask interpretations; relate the BSP graph to the known Level Flesh render blocks.
3. Determine actual DX2 collision/physics serialization and the required geometry build stage.
4. Only then design a new native writer with independent byte-for-byte round-trip validation and a separate DX2 runtime playtest.

**Not completed:** native DX2 BSP compilation, map editing/export, collision generation, new actor/brush CSG, Havok/AI/PVS or runtime acceptance.
