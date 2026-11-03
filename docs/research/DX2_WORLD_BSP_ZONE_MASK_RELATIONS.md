# DX2 world BSP zones: exact node-mask recurrence and 256-bit relation graph

Research date: 2026-11-03. **Read-only** analysis of **19 user-owned retail Deus Ex: Invisible War GMPs**, Unreal package v95, DX2 licensee revisions 65, 67, 68, 69. This builds on [the rooted BSP node links](DX2_WORLD_BSP_TREE_TOPOLOGY.md) and [variable-length world Model records](DX2_WORLD_BSP_NODE_ARRAY_BOUNDARIES.md).

## Critical discovery: BSP node zone masks are exact subtree summaries

Each of the **17,743 compiled-world Model BSP node records** carries:

| Relative to node | Bytes | Directly observed |
|---|---:|---|
| +16 | 32 | A 256-bit little-endian zone-membership mask |
| end − 21 | 2 | Candidate zone index A, little-endian unsigned 16-bit |
| end − 19 | 2 | Candidate zone index B, little-endian unsigned 16-bit |
| end − 17 | 1 | Candidate polygon vertex count, observed values **3–15** |
| compact fields 3/4/5 | variable | The previously validated rooted BSP graph's child/chain node indices |

For **every** node in the 19-map sample, the following equality holds **bit-for-bit**:

```text
node.zone_mask =
      (1 << zone_a if zone_a > 0 else 0)
    | (1 << zone_b if zone_b > 0 else 0)
    | node[compact_3].zone_mask   (if child index != -1)
    | node[compact_4].zone_mask   (if child index != -1)
    | node[compact_5].zone_mask   (if child index != -1)
```

The resulting **17,743/17,743 exact equalities** independently verify that the 256-bit masks summarize zone membership across the **complete rooted native BSP reference tree**, rather than just containing random sparse bits. All **17,724/17,724** parent→child links satisfy the mask-subset property. No node mask sets a zone index beyond its map's counted zone table; mask bit 0 is absent in all sampled nodes. Excluding zone index 0 from *own-node* bits is source-observed, **not yet proven to be an engine enum or outside-world constant**.

Each node's two zone indices fall within the associated zone-table count. The first index is nonzero on 1,068 nodes; the second is nonzero on 17,739. The candidate vertex-count byte totals **82,657** slots across 17,743 nodes; these counts are not recovered native polygon vertex XYZ positions.

## Second discovery: the 69-byte records carry a symmetric zone relationship

Immediately after the BSP node array, the [previously established zone table](DX2_WORLD_BSP_NODE_ARRAY_BOUNDARIES.md) contains **688 total records** across 19 maps.

Each 69-byte record, in the examined corpus:

| Offset | Bytes | Observed data |
|---|---:|---|
| 0 | 1 | Unknown byte (zero in **669** records, nonzero in **19**) |
| 1 | 32 | **256-bit little-endian zone-relation bitset** |
| 33 | 32 | All bytes `0x01` in every sampled record, meaning unknown |
| 65 | 4 | All zeros, meaning unknown |

Interpreting bit N in zone record Z's first 32-byte mask as the existence of a relation between zone Z and zone N produces an **exact symmetric, reflexive and range-bounded matrix** in every map:

- **688 / 688** zone rows have their own self-bit set.
- **0** bits point outside that map's counted zone records.
- **0** asymmetric links, across every pair of zone rows.
- **786** distinct undirected connections between different zones (1,572 off-diagonal directed bits), plus 688 self-bits, for **2,260 total set bits**.
- **53** connected components across the 19 independent map-specific relation graphs.

The graph is **connectivity-like**, and may model portal/zone relationships, but the exact engine semantics are **not established**. It must **not** automatically be named PVS, actual runtime visibility, acoustic connectivity or a portal graph.

### Cross-check between the two independently serialized representations

For **all 1,064 nodes with both zone indices nonzero**, the corresponding pair appears as a set relation bit in the 69-byte zone table, **1,064 / 1,064**. This is an important independent check that the native node tail and the native zone table reference the **same zone-index namespace**.

That conclusion is stronger than a mere correlation of geometric locations or a guess based on a string name.

## Reproduce the read-only validation

Run from the DX2SDK repository root using **your own original DX2 maps**:

```powershell
python research/dx2/inspect_world_bsp_zone_relations.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" --report "C:\DX2_Research_Reports\bsp_zones.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_world_bsp_zone_relations.py" -v
```

Optional `--include-zones` produces each zone's candidate relation list; `--include-node-zones` includes full per-node zone indices and mask membership lists and may create very large reports.

The audit fails closed on corrupt or unfamiliar zone-record framing, missing self-links, asymmetric or out-of-range relation bits, out-of-range node zones, altered vertex counts, malformed BSP links, and violations of the exact subtree-mask OR equation. Source GMPs are **never modified** and reports must be newly created outside the source game-map directories.

## Next engineering priority

This establishes the native **BSP tree's exact zone-mask algebra and a highly structured relation matrix**, but the game still needs a compiler to construct BSP nodes, render blocks, collision and gameplay dependencies from authored geometry.

Investigate native Model compact fields **1, 2, 6 and 7**, node surface and vertex-pool identifiers, direct links to the Level's remaining polygon/zone data, and the true cooking pipeline. Build-time zone relation generation and PVS/physics semantics remain unverified.

**No native map writer, Havok/collision rebuild, PVS decoder or runtime-playable custom DX2 level is claimed.**
