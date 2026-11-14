# DX2Ed Prototype P105: original native World BSP node dossier in Godot

## Purpose

The existing native research recovered the original **50-byte Model header,
variable-length 109–116-byte BSP records, 69-byte zone records, and exact
byte-for-byte original Model reassembly**. P105 exposes that verified source
structure inside DX2Ed's Godot Inspector. It does NOT build native BSP,
deduce polygon ownership, identify original materials/UVs or convert source
planes into editable brushes.

## Workflow

1. Open an original owner-supplied GMP through DX2Ed. The already imported
   actors.json metadata must identify the **same GMP basename and SHA-256**.
2. In the Inspector, select **ORIGINAL WORLD BSP | SOURCE BYTES ONLY** and
   enter a native node ordinal (0 is the first). Press **Inspect BSP node**.
3. The independent Python SDK worker rereads the original GMP with its
   pinned SHA, validates the Level→World Model identity, original BSP rooted
   graph/zone masks, full Model no-op reassembly and complete byte-span ledger.
4. Only then does the inspector present the original node's float32 plane,
   eight source-order compact field values and individual byte positions and
   widths, candidate u16 zone pair, polygon vertex slot count, and Model-
   relative and GMP-absolute byte offsets.
5. Wrong map, changed file SHA, unsupported source grammar, invalid fields
   or an unexpected native writer claim is REFUSED, with no stale report.

A source Model plane is an *infinite mathematical plane*, NOT a native
editable surface polygon. Raw compact field 2 remains an unauthenticated
surface ID hypothesis, not an engine-confirmed material/UV binding.

## Direct SDK read-only API

~~~python
from dx2sdk import DX2Map

source = DX2Map.open(r"C:\DX2\Content\DX2\Maps\ORIGINAL.gmp")
dossier = source.inspect_original_bsp_node_dossier(0)
assert dossier["original_model_full_span_ledger_verified"]
assert dossier["native_BSP_or_Havok_collision_writer_enabled"] is False
~~~

The source SHA-pinned CLI emits bounded original-node JSON to stdout only
and does not accept any output path:

~~~powershell
python research/dx2/inspect_bsp_node_dossier.py --gmp "C:\DX2\Content\DX2\Maps\ORIGINAL.gmp" --source-sha256 ORIGINAL_64_HEX_SHA256 --node 0
~~~

## Automated validation

- Python synthetic Model/GMP tests check byte-exact planes, all 19 source
  spans, compact noncanonical widths, original offsets, source hash,
  mutated/unsupported nodes, out-of-range ordinals and CLI refusal.
- Godot 4.3 synthetic Inspector checks the visible source provenance,
  mismatched SHA, changed original sentinel, tampered spans/planes and
  explicit source-private-only flag boundaries; a fake GMP must be refused
  by the real Python worker.
- Source-only Windows/editor ZIP and standalone Python package require
  the new modules. CI compiles main.gd and the new Inspector separately.

**Native BSP/CSG rebuilding, vertex XYZ recovery, surface/material/UV
mapping, zone/PVS rebuilding, Havok/MOPP collision, original map writes and
retail runtime proof remain unsupported.** Future research should identify
independently serialized surfaces and vertices and cross-validate compact
field 2 against those source array bounds before enabling native authoring.

P105 is prototype milestone numbering, not product 1.0.
