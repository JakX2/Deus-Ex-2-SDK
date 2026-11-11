# DX2Ed v0.75: original World BSP field-2 plane coherence

**Status:** strict read-only evidence collector, source-SHA-pinned, no native
geometry or collision writer.

## The next falsifiable question

Historical Unreal FBspNode structures suggest that the third compact integer
(column 2 of eight original DX2 Model node fields) might reference a shared
BSP surface record. That member name, actual source surface table, and its
consumer have **not** been recovered from the compiled Invisible War files.

The v0.74 diagnostic compared that raw number against original Level
triangle/provenance identifiers. This can help find coincidences and domain
mismatches, but depends on unverified **geometric** plane/sphere matches
between World Model nodes and Level render triangles.

v0.75 instead asks a narrower, **Model-only** question. If two original
BSP nodes share raw compact field 2, do their source plane equations define
the same infinite plane? Does the independently characterized field-5
coplanar reference link nodes whose raw field2 and planes agree?

This deliberately removes the cross-package geometry-matching heuristic.

## Model-only source evidence

The new dx2sdk.bsp_surface_plane_coherence inspector:

- Reads unchanged original DX2 UE95 source bytes through DX2Map, checks source
  SHA-256, original Level→World Model export identity, Model byte extent,
  independently validated BSP node framing, rooted graph and zone relations.
- Extracts each node's original float32 plane and the exact source-positioned
  eight-compact integer fields. Keeps original field2, field5 coplanar target,
  ordinal and serialized field2 offset. Original Level, materials and
  proprietary assets never leave the user's machine.
- Groups nodes by **nonnegative raw field2 value**. The -1 sentinel, if
  present, is counted separately and never treated as a surface group.
- Compares each reused field2 node's infinite plane against that group's
  first source node. Allows directly and oppositely oriented equivalents;
  counts conflicting normals or plane positions. Comparisons use explicit
  numerical tolerances of 0.002 in normal-vector difference and 0.15 source
  units in plane W, matching earlier geometric research tolerances.
- Cross-tabulates source field5 coplanar links for same/different field2
  numbers and same/different infinite planes. Disagreements remain visible.
- Reports counts and bounded conflicting original node ordinals plus exact
  compact field2 offsets **within the original Model export**. Does not
  guess missing native surface pointer targets or repair source records.

The grouping implementation is linear in node count, not quadratic across
same-field2 groups. Group coherence is explicitly **anchored to each group's
lowest-ordinal original node** rather than an all-pair or full-plane-cluster
proof. Differences would challenge a simple "one raw field2, one common
infinite plane" hypothesis, not automatically disprove any other surface
semantics. Plane agreement still cannot confirm a native iSurf field.

## Usage

~~~python
from dx2sdk import DX2Map

world = DX2Map.open(r"C:\DX2\Content\DX2\Maps\ORIGINAL.gmp")
out = world.inspect_bsp_surface_plane_coherence()
print(out["reused_field2_groups_containing_different_planes"])
print(out["candidate_coplanar_field5_link_evidence"])
~~~

The v0.74 source-SHA-pinned read-only CLI now offers a Model-only mode:

~~~powershell
python research/dx2/inspect_bsp_surface_provenance_hypotheses.py "C:\DX2\Content\DX2\Maps\ORIGINAL.gmp" --source-sha256 ORIGINAL_64_HEX_SHA256 --field2-plane-coherence --report "C:\DX2Research\bsp_field2_plane_coherence.json"
~~~

Use actual original source SHA-256, not the placeholder. The command
exclusively creates a fresh private JSON outside the original game Maps
directory. No GMP writes or native collision patches.

## Scope and next evidence gate

The prior documented private original corpus contains 17,743 World BSP
nodes across 19 Seattle maps, with source field2 showing a dense zero-based
numeric range in each map and 4,161 / 7,733 equality on raw field5 coplanar
links. These are **earlier observations**, not fresh v0.75 per-map
plane-coherence measurements. The new tests use synthetic original-format
records and independent validators. No fresh 19-map scan or retail game
runtime test is claimed.

Even a source-wide perfect same-plane result does not establish the actual
Model surface array. We still need to locate independent serialized surface
count/boundary/polygon data and show native field2 values indexing it.
BSP/CSG building, native stored vertex XYZ, Havok MOPP recooking, actor Region
construction, and playable retail mission export remain unsupported.

Everything here is read-only. The diagnostic is not an edited-Mission
compiler, does not write source files and does not export proprietary data.
