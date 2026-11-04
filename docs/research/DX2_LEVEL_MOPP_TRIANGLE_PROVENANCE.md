# DX2 native Level: MOPP triangle provenance to Flesh render sections

Read-only research on 19 user-owned original *Deus Ex: Invisible War* UE95 GMP maps (licensees 65/67/68/69), 2026-11-04. No retail geometry, map assets, mesh bytes, physics code, or material names are included in this repository.

## Confirmed serialized Level layout

Immediately **before** the independently validated PR #27 flattened Level-mesh header is a bounded per-triangle provenance array. All 19 maps have this source-observed sequence:

```text
12 bytes: three zero little-endian u32 words
 4 bytes: 0x6F000000 little-endian (observed marker, semantics unknown)
 4 bytes: 0x013E4312 little-endian (observed marker, semantics unknown)
 4 bytes: u32 equal to the PR #27 flattened triangle count
 8 * triangle_count bytes: u32 A, u32 B for each triangle
 4 bytes: length of following header's NUL-terminated source-name field
 ...     : existing PR #27 flattened mesh counts/header, source name, vertices and indices
 ...     : PR #28 MOPP code and zero trailer
```

**Each 8-byte pair aligns to the same triangle ordinal as the flattened global index array and the PR #28 MOPP terminal IDs.** Cross-reference against the independently parsed packed Flesh render blocks proves:

- **B** equals the triangle's 0-based render-block **section index** in all 43,154 records.
- **A** is constant for all triangles in a given validated render block, strictly increases between successive render blocks, and is unique per render block. Some indices are skipped; this **does not prove missing or corrupt geometry**. Its true engine member name and its relationship to any omitted native blocks remain unproven.
- Every pair resolves to exactly one render section and therefore to that section's **render material string**. The value is **not** independently verified as a Havok physics material, collision layer/filter, sound type, friction/restitution, or shape-property reference.
- The preceding triangle count equals the independently checked 32-bit global-index stream's triangle count; the source-name length/header boundary also agrees. Both source formats and the MOPP spatial structure remain read-only.

## Original retail 19-map evidence

| Test | Observation |
|---|---:|
| Original UE95 GMP maps checked | **19/19** |
| Packed Flesh render blocks | **3,002** |
| Triangle provenance pairs | **43,154 / 43,154** |
| Pairs whose B field matches render section ordinal | **43,154 / 43,154** |
| Monotone unique A IDs per represented render block | **3,002 / 3,002** |
| Distinct populated (A, B) section combinations | **7,240** |
| Total internal/leading gaps in per-map A ID domains | **104** |
| MOPP collision leaf triangles attributed to render sections | **43,152 / 43,152** |
| Missing MOPP leaves that are zero-area mesh triangles | **2 / 2** |
| Maps with matching framing and triangle-count fields | **19 / 19** |

The MOPP leaf set omits only the two previously proven degenerate triangles (one each in Seattle Hub Inclinator and MercDistrict Sák). Each still has a provenance pair. All **nondegenerate** collision leaves have a valid render-section attribution, and no material name is required to decode MOPP bytecode itself.

Across these retail maps, the packed render sections reference **212 distinct case-sensitive material-name strings**. Those strings are intentionally not included in the source-control report; a local `--include-materials` option can write counts by source render material to private JSON outside the game directory.

## Reproduce with private original maps

From the DX2SDK repo root:

```powershell
python research/dx2/inspect_level_mopp_triangle_provenance.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" --report "C:\DX2_Research_Reports\triangle_provenance.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_level_mopp_triangle_provenance.py" -v
```

The script refuses malformed marker/count framing, corrupted section references, inconsistent per-block labels, reordered/duplicate block IDs, bad MOPP trees, and output reports inside original map directories. Source packages are only read. Source-name/header semantics and skipped A IDs remain provisional; unknown variants refuse rather than guessing.

## What this enables, and what it does not

This exact relation permits a **collision triangle ID → Level provenance pair → packed Flesh render section → render material string** lookup, for audit/inspection without modifying geometry. It also provides an independent cross-check for any future geometry writer, where preserved triangle ordering will be critical.

It is **not** a native Havok shape/material decoder, physics material database, cooked collision compiler, DX2 BSP CSG surface table, runtime raycast, PVS implementation, game-tested writer, or proof that render materials map 1:1 to physical materials. An actual DX2 runtime trace or shape source is required before promoting these fields to Havok material semantics.