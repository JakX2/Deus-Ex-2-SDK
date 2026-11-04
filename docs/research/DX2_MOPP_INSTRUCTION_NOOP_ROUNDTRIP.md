# DX2 Level MOPP bytecode: 100% reachable instruction coverage and no-op reassembly

Research-only native collision serialization preflight, stacked after the DX2Ed source collision inspector work in PRs #27–35. The new inspector is read-only and does not build collision for modified geometry.

## Why this matters

PR #28 verified that a source-observed MOPP-compatible instruction stream resolves to each original non-degenerate triangle ID. This PR moves beyond a leaf-only decoder:

1. Enumerate every reachable (byte offset, output-base) instruction state.
2. Independently decode each reachable instruction's exact byte width and bounded operands, retaining unknown fields as opaque integer bytes.
3. Prove reachable instruction byte spans do not overlap.
4. Re-emit opcode and operands using their original big-endian widths, preserving any unreachable spans verbatim.
5. Compare the result to the entire original code stream. Rebuild the MOPP envelope's two little-endian byte-count fields while retaining original float32 spatial bits unchanged, then require exact byte identity to the original Level-export tail.
6. Independently check decoded leaf IDs and instruction-state counts against the existing PR #28 control-flow validator.

This yields an exact read-only no-op reference point. It is **not a MOPP compiler**. Re-emitting unchanged instructions does not establish that new geometry can be cooked, branch distances relocated, or Havok can load changed shapes.

## Private 19-map Seattle corpus

The original user-owned GMP files were loaded from the private maps.zip, and their exact bytes independently scanned for candidate MOPP envelopes. Validated code spans were cross-checked against PR #28 reachable-opcode decoding and original triangle counts. No original maps or collision bytecode are included in this PR.

| Verified measurement | 19 original GMPs |
|---|---:|
| Accepted code streams | 19 |
| Original MOPP instruction-stream bytes | **427,059** |
| Distinct reachable instruction offsets | **151,660** |
| Reachable instruction bytes | **427,059 / 427,059 (100%)** |
| Unvisited code bytes | **0** |
| Instruction-byte overlaps | **0** |
| Reassembled code byte differences | **0** |
| Reassembled native envelope byte differences | **0** |
| Unique source triangle leaves | **43,152** |

The Penthouse raw GMP contained **two envelope-shaped signatures**. One was rejected at the first child instruction; only the other matched the actual source control-flow grammar and expected triangle count. Envelope framing and root opcode alone are not proof of collision validity.

All selected streams showed complete instruction-byte coverage with no opaque gaps. The tool supports opaque gap preservation on synthetic data, but no private retail MOPP needed it. This 100%-coverage property is stronger than the prior unique-leaf result and offers a future **relocation/mutation preflight gate**.

## Reproduction

Fixture-only:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_mopp_bytecode_roundtrip.py" -v
~~~

Original game maps, supplied by their owner:

~~~powershell
python research/dx2/inspect_mopp_bytecode_roundtrip.py "C:\DX2\Maps\M1_Seattle_hub.gmp" --report "C:\DX2_Research\mopp_roundtrip.json"
~~~

Reports use exclusive creation and are refused inside source map directories. The original GMP remains unchanged. The CLI uses the existing strict DX2 UE95 package reader, packed Flesh render reader, Level flat geometry check and MOPP spatial/triangle validator before accepting the Level envelope.

Synthetic tests cover the original 14-byte fixture; omitted degenerate triangle; various operand widths; 8-, 16- and 32-bit output bases; conditional branches; unreachable opaque bytes; overlapping instruction rejection; invalid jumps; duplicate leaves; unknown opcodes; bad spatial parameters, lengths and footer; and source immutability.

## Not established

- How DX2/Havok generates a collision tree for changed triangle geometry.
- Runtime Havok query semantics, contact filtering, shape ownership or physics materials.
- Whether changed branch distances or altered mesh counts can be serialized into an executable game map.
- Native compiled-world BSP vertex/surface tables, CSG rebuilding, PVS cooking, or a native Level geometry writer.
- Any editable game-compatible collision/GMP serializer.

The next logical experiment is an entirely **synthetic-only restricted MOPP emitter** with independent validation, not a claim of runtime compatibility.
