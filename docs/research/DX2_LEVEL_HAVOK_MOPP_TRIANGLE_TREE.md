# DX2 Level collision-acceleration: Havok-MOPP-compatible bytecode

**Status:** read-only decoder and source-observed cross-reference. **Not** a runtime-validated or writable Havok shape/compiler. Research date: 2026-11-03.

## Discovery and byte layout

After the flattened Level mesh independently identified by the previous PR (#27), all 19 examined user-owned original DX2 UE95 GMPs have a length-delimited native tail:

| Relative bytes from end of flattened u32 triangle indices | Meaning supported by 19-map tests |
|---|---|
| `+0..+3` | little-endian u32 outer length = `MOPP_byte_count + 20` |
| `+4..+19` | little-endian f32[4], consistent with Havok MOPP `CodeInfo` XYZ origin and quantization scale |
| `+20..+23` | little-endian u32 MOPP bytecode length |
| `+24..+24+N-1` | N bytes of Havok-MOPP-compatible spatial-tree bytecode |
| final 12 bytes | exactly zero in every audited map, purpose otherwise opaque |

The native tail length is therefore **N + 36**, with two independently checked length fields. The bytecode starts with axis-filter opcodes `0x26`, `0x27`, or `0x28`, and traverses using Havok's known MOPP instruction format. **Bytecode operands are big-endian**, whereas the Level's outer length fields are little-endian.

The f32[4] has an independent numerical relationship with the **flattened geometry from PR #27**, not merely a coincidental header match:

- `origin.xyz = mesh_min_xyz - (0.05, 0.05, 0.05)`.
- `origin.w = (254 * 65536) / (max(mesh_max_xyz - mesh_min_xyz) + 0.1)`.
- Across all 19 original maps, maximum **component origin error** is about `0.00001221`; maximum **relative scale error** is about `1.09e-7`, consistent with float32 rounding.

The 0.05/0.1 padding is an observed DX2-specific parameter; do not substitute other games' collision tolerances. The scale expression and opcodes independently match documentation of Havok's `hkpMoppCode` and established MOPP bytecode grammar.

## Exact collision-triangle leaf coverage

The decoder symbolically traverses **both branches** of every reachable conditional MOPP instruction. It propagates output-base changes, resolves big-endian jump offsets, and obtains unique triangle indices from terminal opcodes. It is **not** a raycast, physics simulation, or statement that both branches could satisfy the same spatial query.

| Private original-source test | Total |
|---|---:|
| Maps | **19 / 19** |
| Flattened vertices already checked against packed Flesh geometry | **76,732** |
| Flattened triangles | **43,154** |
| MOPP bytes across maps | **427,059** |
| Reachable instruction states `(code offset, output base)` | **151,660** |
| Unique, in-range terminal triangle IDs | **43,152** |
| Triangle IDs without a terminal leaf | **2** |
| Exactly zero-area triangles in flattened mesh | **2** |
| Missing terminal IDs that are not zero-area triangles | **0** |
| Duplicate terminal IDs | **0** |
| Unsupported reachable opcodes / out-of-bounds branch targets | **0 / 0** |
| Maps satisfying `leaf_IDs == all_triangle_IDs - zero_area_IDs` | **19 / 19** |

Only two triangles are omitted. Both are geometrically **collinear** despite using three distinct vertex indices:

- `M1_Seattle_Hub_Inclinator.gmp`: triangle **875**.
- `M1_Seattle_MercDistrict_Sak.gmp`: triangle **781**.

This is a direct, falsifiable mapping between the recovered flattened geometry and MOPP-compatible collision acceleration. It is the strongest DX2 collision-serialization identification in this series so far, but still **does not establish a working Havok collision runtime integration**.

## Verification

```powershell
python research/dx2/inspect_level_mopp_triangle_tree.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" --report "C:\DX2_Research_Reports\mopp_hub.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_level_mopp_triangle_tree.py" -v
```

The read-only CLI reuses the *actual existing DX2SDK* UE95 package parser and packed Flesh render-block extractor, then the PR #27 flattened-geometry validator, before interpreting the code. Output reports may only be created **outside source GMP folders** with exclusive creation, so original files are not replaced. Unsupported file layouts or absent/duplicate streams fail closed. The separate private 19-map run executed the same PR #28 **core verifier**, supplied by independent existing private GMP/render-block extraction rather than by the full repository CLI. Synthetic regression tests cover valid and corrupted MOPP lengths, bad spatial fields, invalid jumps, unknown instructions, zero-area omission, duplicate/out-of-range triangle leaves and read-only behavior.

## What remains unknown

- Whether and how DX2's runtime constructs the exact Havok shape tree and material/filter data from these bytes; no game executable was run or patched.
- Numerical traversal of spatial query volumes, contact generation, welding, and other physics-specific semantics.
- Safe regeneration or cooking of a new **native DX2** MOPP; a *decoder* is not a *compiler*.
- Other Level serialization data, compiled-world Model vertex pool, native BSP CSG surfaces, physics materials, zone/visibility reconstruction and cooked output dependencies.

**No retail geometry, MOPP code, original GMP, IBD assets, Havok binaries, or game source are committed.** Reports contain only aggregate measurements, source hashes, instruction statistics and triangle IDs.

### Comparative external format references (not DX2 engine authentication)

- Havok MOPP `hkpMoppCode::CodeInfo` has an `hkVector4 m_offset` and its fourth component is exposed as the scale: <https://codeviewer.zeldamods.org/uking/uking/lib/hkStubs/Havok/Physics2012/Internal/Collide/Mopp/Code/hkpMoppCode.h.html>.
- MOPP bytecode, axis filters, split/jump and output-base/terminal opcode ranges: <https://github.com/BadDogSkyrim/PyNifly/blob/main/docs/mopp_format.md>.
- Historical MOPP quantization and origin padding explanations: <https://github.com/niftools/nifxml/wiki/Havok-MOPP-Data-format>.
