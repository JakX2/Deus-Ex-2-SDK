# DX2Ed v0.72: source BSP candidate plane to original MOPP triangle IDs

**Status:** read-only, source-pinned diagnostic. No native BSP, collision, Havok, zone or actor writer.

## Why this matters

v0.71 identified render triangles whose geometric coplanarity and sphere association with one original BSP Model plane would change if the plane moved. The original DX2 Level contains a separately validated exact triangle-provenance chain:

1. The Level flattened render vertex/index arrays have a triangle ordinal T.
2. An 8-byte Level provenance pair at that ordinal has fields A and B. B is the render section index. A is a monotonically increasing per-render-block source reference with possible skipped IDs, not the render block array index.
3. Source MOPP bytecode terminal ID T refers to the same flattened triangle ordinal for nondegenerate original triangles. Exactly zero-area source triangles may have no terminal.

The existing research established these relationships across 19 original GMPs, with 43,154 provenance records and 43,152 reachable MOPP leaves. This module joins those exact IDs to the hypothetical BSP geometric candidate set from v0.71.

## Implementation

The new dx2sdk.bsp_mopp_plane_impact.compare_original_plane_mopp_impact:

- Requires an unchanged DX2SDK original UE95 GMP source and the existing independently checked Model node and Level render-block readers.
- Replays the before/after render triangle candidate comparison.
- Validates the entire original Level flattened mesh, provenance table and reachable MOPP leaf set, not merely affected triangles.
- Reconstructs each render locator in original flattening order, refusing reordered, duplicated or missing locators.
- Reports exact original flattened/MOPP triangle IDs, source provenance pair A/B and pair offsets within the original Level payload, with bounded examples of lost/gained candidate sets.
- Counts changed geometric candidate associations that correspond to original MOPP leaves, without claiming actual collision changes.

The public DX2Map method is inspect_bsp_plane_mopp_candidates(node=N, replacement=(a,b,c,w)).

Example source-pinned private report (replace original map path, SHA, node and plane):

~~~powershell
python research/dx2/inspect_bsp_mopp_plane_impact.py "C:\DX2\Content\DX2\Maps\M1_Example.gmp" --source-sha256 ORIGINAL_64_HEX_SHA256 --node 0 --plane 0 0 1 128 --report "C:\DX2EdResearch\bsp_mopp_impact.json"
~~~

The report must be a fresh private JSON outside source and retail map directories. No original map bytes, material names, textures, or proprietary geometry are included in repository fixtures.

## Interpretation and remaining gates

**Exact source relationship:** original Level flattened triangle ordinal, 8-byte provenance pair, and MOPP terminal ID for a nondegenerate triangle.

**Inferred relationship:** BSP Model node plane to render triangle. This is geometric coplanarity and full node-sphere containment, not an engine-authenticated ownership pointer. Candidate gained/lost does not mean that actual collision, native BSP surface, Havok shape, actor Region, portal or zone changed.

No collision bytecode, BSP Model bytes, Level render vertex, game installation or original GMP is modified. Synthetic tests cover two sections, skipped A IDs, degenerate non-leaf exceptions, corrupt tables, bad plane edits, deterministic counts and source checks.

Next gate: recover a native BSP node/surface/triangle ownership reference or validate a reversible no-op native Model/Level serialization boundary, then test isolated edits in a disposable retail installation. BSP/CSG and MOPP cooking remain unimplemented.
