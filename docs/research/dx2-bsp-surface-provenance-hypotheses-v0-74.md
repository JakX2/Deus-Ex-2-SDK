# DX2Ed v0.74: original Model compact field 2 versus Level collision provenance

**Status:** reproducible read-only hypothesis audit, not a decoded native BSP
surface owner or a game-compatible writer.

## Why field 2 is the next format question

The original compiled-world Model has a fully framed BSP node array whose
eight compact integer fields have independently source-checked positions.
Columns 3, 4 and 5 are supported by the rooted tree/zone-link evidence.
Column **2** remains a candidate surface-table index, not an authenticated
DX2 engine member named iSurf.

Existing original-map research observed **17,743** world BSP nodes across
19 owner-original UE95 maps, and a zero-based dense value range for
column 2 in every map. Its equality across field-5 coplanar references was
**4,161 / 7,733**, rather than universal. Those facts make field 2
interesting, but they do not identify a native surface array.

Separately, the Level flattened-triangle/MOPP provenance work proves that
each original triangle ordinal maps to a serialized pair of native Level
u32 fields (A, B). Here B equals the render section ordinal and A is an
original monotone, occasionally gapped, per-render-block label.
Neither is established as the Model's candidate surface index.

## New cross-source measurement

The new read-only dx2sdk.bsp_surface_correlation module:

1. Validates the original UE95 GMP, the Level-to-World-Model link, the
   rooted BSP node/zone structure, every original Model record, and the
   exact source byte position of its third compact field (index 2).
2. Independently validates original Flesh Level render blocks, flattened
   triangle order, all provenance A/B pairs and MOPP terminal IDs.
3. Uses the existing geometric plane/sphere matching logic to associate
   Level triangles to **candidate** BSP Model nodes.
4. Allows only triangles with **exactly one** node candidate into the
   numeric equality analysis. Ambiguous/missing/degenerate cases remain
   separate. This prevents arbitrary owner selection.
5. Counts four independent integer equalities on those candidates:
   Model node field2 == native Level provenance A, 0-based render block
   ordinal, render section ordinal, and global flattened-triangle ID.
6. Groups unique candidate matches by field2 and reports whether each raw
   value is associated with one/multiple source provenance A labels,
   render blocks or render sections. A mismatch is evidence against
   direct numeric identity, **not source-file corruption**.
7. Emits up to 12 bounded examples with original node ordinal, exact
   field-2 byte position within the Model payload, triangle locator,
   collision terminal membership and Level A/B values. No original
   geometry or material bytes appear in the report.

These equality counts are intentionally a **falsification tool**, not
proof of ownership even if many source values happen to be equal.
The exact value-domain match, source array bounds and actual pointer
consumer must be independently demonstrated before promoting field 2
to an editable BSP surface reference.

## Running against private original maps

The DX2Map public read-only method is:

~~~python
from dx2sdk import DX2Map

world = DX2Map.open(r"C:\DX2\Content\DX2\Maps\ORIGINAL.gmp")
audit = world.inspect_bsp_surface_provenance_hypotheses()
print(audit["numeric_equality_only"])
~~~

The optional source-SHA-locked CLI writes only fresh private JSON outside
original game/map directories:

~~~powershell
python research/dx2/inspect_bsp_surface_provenance_hypotheses.py "C:\DX2\Content\DX2\Maps\ORIGINAL.gmp" --source-sha256 ORIGINAL_64_HEX_SHA256 --report "C:\DX2Research\surface_hypotheses.json"
~~~

The public DX2Map API currently supports original v95 licensee **68/69**
GMP files; source-research parsers cover additional observed 65/67 cases.
The CLI does **not** claim to audit all 19 private original maps. Run only
on owner-supplied maps accepted by the conservative source reader.

Synthetic fixture tests cover two sections, skipped Level A labels, source
geometric ambiguity, node-sphere refusal, degenerate triangles, corrupted
render/provenance order and original Model compact-field byte locations.
No retail data is distributed or modified.

## Unresolved engineering gates

Find the actual serialized Model surface array and its count, and
demonstrate field-2 references into that array. Independently recover
world BSP vertex XYZ or surface polygon indices. Then establish the
Level render triangle mapping without geometrical heuristics. Only after
these steps should isolated native BSP/CSG and Havok collision compilers
be developed and tested in the original game.

No original GMP writes, engine-authenticated geometry ownership,
collision regeneration, runtime testing or playable map compilation are
claimed by this research audit.
