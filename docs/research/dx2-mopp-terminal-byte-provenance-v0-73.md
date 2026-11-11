# DX2Ed v0.73: original MOPP leaf instruction byte provenance

**Status: read-only, source-pinned original DX2 collision bytecode evidence.**
This increment builds on v0.72, which connected Level flattened-triangle
IDs to original MOPP terminal IDs but did not identify their instruction bytes.

## Exact source-backed relationship

For a selected original MOPP terminal triangle ID the new reader identifies:

1. The original Level export byte offset, size and SHA-256.
2. Original MOPP code start in Level, code length, SHA-256 and independent
   byte-identical source envelope reconstruction.
3. The exact terminal instruction position relative to MOPP code, Level
   payload and original GMP.
4. The source-observed terminal opcode role: 0x30..0x4f inline, or
   0x50..0x52 with big-endian 1/2/3-byte immediate triangle deltas.
5. The source output-base accumulated by the preceding MOPP control flow,
   with the original encoded terminal delta.
6. The original Level 8-byte triangle provenance pair (A, B), its source
   offsets, and the associated render block/section/local triangle locator.

A valid instruction byte location is a read-only reference to original
collision code, never authorization to patch it. Altering a leaf value might
change collision geometry, output bases or physics semantics. This code never
emits a mutation.

The index exhaustively walks original MOPP code and separately validates the
exact no-op instruction roundtrip and reachable leaf IDs. It refuses
duplicate, malformed and out-of-range terminal references. Every original
terminal is reconciled with the validated Level flattened mesh and render
provenance decoder. Original zero-area triangles without a MOPP terminal are
reported with no invented instruction location.

## Public API

~~~python
from dx2sdk import DX2Map

world = DX2Map.open(r"C:\DX2\Content\DX2\Maps\ORIGINAL.gmp")
leaf = world.inspect_original_mopp_terminal_bytes([1, 2, 3])
print(leaf["selected"][0]["mopp_opcode_absolute_offset_in_gmp"])

impact = world.inspect_bsp_plane_mopp_terminal_bytes(
    node=0, replacement=(0, 0, 1, 128))
~~~

The example node and plane are placeholders, not validated native edits.
The source-SHA-pinned read-only CLI from v0.72 accepts an optional
--with-original-mopp-opcodes switch:

~~~powershell
python research/dx2/inspect_bsp_mopp_plane_impact.py "C:\DX2\Content\DX2\Maps\ORIGINAL.gmp" --source-sha256 ORIGINAL_64_HEX_SHA256 --node 0 --plane 0 0 1 128 --with-original-mopp-opcodes --report "C:\DX2Research\bsp_mopp_opcode_offsets.json"
~~~

The CLI only creates a fresh private JSON outside original game Maps.
No proprietary GMP, MOPP bytecode, mesh or material bytes enter GitHub.

## Verification and limits

Synthetic fixtures cover source branch opcodes, inline terminals, big-endian
immediate terminals (1, 2, 3 bytes), output-base variants, explicit absence
for degenerate original triangles, source export/GMP offsets and hashes,
malformed bytecode, and source-locked BSP candidate joins. Source input bytes
remain unchanged.

Prior read-only original DX2 research across 19 private retail maps already
established complete MOPP code byte coverage and exact no-op reassembly.
This PR adds terminal-PC provenance using the observed grammar, not a new
independent 19-map empirical audit.

The native Model node ↔ render triangle relation remains a geometric
candidate, not an engine-authenticated surface ownership pointer. These
source addresses are not an engine-verified MOPP mutation recipe. Native
Model/Level surface references, collision compilation, BSP/CSG rebuilding,
Region assignment and actual retail runtime validation remain unresolved.
