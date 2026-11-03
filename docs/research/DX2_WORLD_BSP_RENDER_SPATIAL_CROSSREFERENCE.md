# DX2 world BSP / Flesh render geometry cross-reference

Research date 2026-11-03. **Read-only audit** of 19 original user-owned *Deus Ex: Invisible War* GMPs (UE package 95, DX2 licensees 65/67/68/69). Builds on the [rooted world BSP topology](DX2_WORLD_BSP_TREE_TOPOLOGY.md).

## What the cross-check actually establishes

The large native world `Model` directly referenced by `Level` holds candidate BSP splitting planes and per-node bounding spheres. Separately, the `Level` holds packed Flesh render blocks containing world-space triangle XYZ positions.

For every nondegenerate rendered triangle:

1. Compute a normalized geometric triangle plane from its **actual three source XYZ positions**, rather than an actor transform or guessed surface normal.
2. Search for node planes with either matching or opposite normal orientation. Require Euclidean normal-vector difference ≤ **0.002**, and plane-W difference ≤ **0.15 source units**.
3. Check whether all three triangle vertices fit inside that node's source-observed bounding sphere, with **0.15 source-unit** margin.
4. Classify each triangle as **one spatial candidate**, **multiple ambiguous spatial candidates**, or **unmatched**. Never select an arbitrary owner.
5. Independently require that the 4-byte little-endian integer before each Flesh render block is the **exact block payload byte length**. Across this source corpus it is a length prefix, not established as a unique render-block ID.

There is **no authenticated game-native triangle-to-BSP-node index** in this tool. Geometry co-location is a strong clue, not a substitute for a serialized reference.

## Exact 19-map results

| Metric | Count |
|---|---:|
| Native compiled-world BSP nodes | **17,743** |
| Validated packed Flesh render blocks | **3,002** |
| Nondegenerate render triangles | **43,154** |
| Triangles sharing a node plane | **42,781** |
| Matching node plane + triangle centroid in sphere | **42,733** |
| Matching node plane + **all triangle corners in sphere** | **42,637 (98.80%)** |
| Full matches with **one** candidate | **37,433** |
| Full matches with **multiple** candidates | **5,204** |
| Unmatched after both checks | **517** |

The 5,204 ambiguous cases may represent coplanar/overlapping native nodes, as expected from the previously recovered third link field, but **this relationship is not proven**. The 517 unmatched cases are reported, not converted into false geometry links.

Examples:
- Seattle Hub: **1,281 nodes / 255 render blocks / 3,227 triangles**, of which **3,218** have plane+sphere matches, 2,897 unique and 321 ambiguous.
- Seattle Hub Inclinator: **1,077 nodes / 156 render blocks / 2,551 triangles**, of which **2,373** have plane+sphere matches. This is a useful challenging map for revisiting spatial and serialization hypotheses.

The very high agreement supports a shared spatial coordinate system between native node planes/spheres and Level render vertices. It does **not** establish actual engine render indexing, static collision behavior, visibility, Havok, zone or original world CSG semantics.

## Reproducible research tool

- `research/dx2/inspect_bsp_render_spatial_candidates.py` uses strict DX2SDK native Level/Model and Flesh render-block readers, standard-library Python, and a sparse 4D plane-candidate index.
- `native_editor/tests/test_dx2_bsp_render_spatial_candidates.py` checks orientation reversal, false plane matches, geometry outside spheres, ambiguity preservation, corrupt block prefixes, degenerate triangles and source-file nonmutation.
- A quantized bucket is **only for candidate discovery**. Every candidate is independently checked using the precise plane and bounding-sphere criteria.
- Add `--include-matches` to include per-triangle identifiers [render block index, material section index, triangle index] and candidate node indices. Default report contains aggregate counts and small examples. User-owned source paths are not embedded.

```powershell
python research/dx2/inspect_bsp_render_spatial_candidates.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" "C:\DX2\Content\DX2\Maps\M1_Seattle_Club.gmp" --report "C:\DX2_Research_Reports\bsp_render_crossref.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_bsp_render_spatial_candidates.py" -v
```

The original retail GMP files are never written to, installed or redistributed. Output JSON must be newly created outside the original game map directories.

## Compiler gate

Cross-referenced polygons can support a future **DX2Ed diagnostic overlay**, but need actual engine-level node, zone, leaf and render block links before becoming a writer schema. World CSG, source BSP surfaces, collision/Havok and map cooking remain separate, unverified tasks.

**No playable custom DX2 map or native BSP/collision compiler is claimed.**
