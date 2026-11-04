# DX2SDK: restricted synthetic MOPP control-flow emitter

Research-only follow-up stacked on PR #36. This is the **first synthesized MOPP-compatible opcode graph** in DX2SDK, independently checked against the source-observed decoder. No DX2 game files, GMP packages or Havok runtime libraries are read or modified.

## What the tool actually builds

The module research/dx2/emit_synthetic_mopp_fixture.py accepts a tiny synthetic f32 triangle mesh, excludes triangles whose f32 geometric cross product is exactly zero, and builds a deterministic balanced graph over the surviving original triangle IDs. It emits:

- Root opcode 0x28 and two **opaque, fixed** bytes 00 ff. Their observed opcode grammar and width are corroborated by the original source corpus; exact runtime spatial behavior is not established.
- A small two-child split 0x20 with fixed 0x80 opaque threshold and an automatically relocated forward **8-bit** displacement if the first child fits.
- A longer two-child split 0x23 with two fixed 0x80 opaque thresholds, a zero first-child **16-bit** displacement, and relocated 16-bit second-child displacement for larger subtrees.
- Source-observed terminal leaves: inline 0x30..0x4f for triangle IDs 0..31, immediate 0x50 for IDs 32..255, 0x51 for IDs 256..65535, and 0x52 for higher 24-bit IDs.
- Native-envelope-shaped bytes: little-endian code_length+20, four float32 spatial parameters, little-endian code_length, the generated stream, and twelve zero trailer bytes. Spatial parameters match original source-observed formula: origin=min(xyz)-0.05; scale=254*65536/(max_xyz_extent+0.1).

**A valid symbolic opcode graph does NOT imply working Havok collision.** The fixed filter/threshold operands do not have confirmed spatial semantics. No material/filter/shape serializer, live Havok calls, compiled BSP, native GMP writer or playable level is included.

## Independent validation

The prior PR #28 and #36 decoders MUST accept every generated graph and independently verify:

1. Exactly the intended original triangle leaves, without repeats, after omitting zero-area triangles.
2. Every 8/16-bit branch displacement and instruction pointer stays in bounds.
3. Reachable instructions do not overlap, and cover **100% of emitted code bytes**.
4. Decoded instruction operands reassemble byte for byte.
5. Spatial float32 values and native-envelope framing agree with the synthetic geometry.
6. The separate fake Level export payload used for tests passes the existing flattened Level mesh cross-reference and MOPP consistency check. The fake Level is **not** a valid complete UE95 game package.

A 16-test source-free suite exercises one-, two-, four-, six- and 260-triangle graphs; short/wide relocation; 8/16/24-bit leaf IDs including high sparse IDs; exactly omitted degenerates; float32 envelope consistency; deterministic outputs; corrupt branch displacements; malformed input; and exclusive output safety.

## Run

Asset-free tests:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_synthetic_mopp_fixture_emitter.py" -v
~~~

Print a synthetic report:

~~~bash
python research/dx2/emit_synthetic_mopp_fixture.py --triangles 4
~~~

Create fresh synthetic-only binary and JSON outside original Maps/System folders:

~~~powershell
python research/dx2/emit_synthetic_mopp_fixture.py --triangles 4 --output-prefix C:\DX2Research\demo
~~~

This produces demo.synthetic-mopp.bin, **not a GMP**, plus demo.synthetic-mopp.json. The CLI refuses output inside Maps/System, native game-file extensions, and overwriting existing synthetic outputs. It NEVER reads game assets.

## What this proves and does not prove

PR #36 previously proved an exact **no-op** original-byte reconstruction over 19 retail maps: 427,059 instruction bytes and 151,660 distinct instruction offsets. This PR emits a **new synthetic graph** using that observed instruction grammar. Neither result establishes runtime Havok spatial-query correctness or a valid new game collision shape.

Next gate: reverse the original MOPP spatial branch tests or obtain a legally available Havok query implementation, then test against known original DX2 collision geometry and a disposable runtime scenario. Until then, the tool stays isolated from native Save As and game maps.
