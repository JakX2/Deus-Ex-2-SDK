# DX2SDK read-only Level MOPP triangle debug mesh (PR #30)

## Purpose

Export **verified Level flattened geometry** and its **MOPP-terminal triangle IDs** as an editable-in-external-tools **OBJ debug visualization**, accompanied by per-triangle provenance JSON. This is a research/debug bridge toward inspecting surfaces in Blender and eventually DX2Ed. It is **not** a DX2 runtime collision compiler, Havok shape builder, BSP writer or proof of any physics-material flags.

This builds directly on PRs #27 (exact packed-render ↔ flattened Level geometry), #28 (MOPP-compatible bytecode ↔ triangle leaves), and #29 (triangle ID ↔ original render block/section). No original game files or binary assets are included in the repository.

## Binary relationships preserved

- Each original Level flattened vertex is a **16-byte record** containing f32 XYZ plus zero u32. OBJ vertices are emitted in **exact original order**, with the OBJ's 1-based vertex index corresponding to the Level's 0-based flattened index plus one.
- Flattened triangle indices are 32-bit little-endian; OBJ preserves their winding and order, except for an explicitly omitted zero-area triangle when using default settings.
- Each source triangle has an 8-byte `(render block ID, render section ID)` provenance pair. The original source render section supplies a **render material name**. No Havok physics-material ID or gameplay-surface property is implied.
- The MOPP bytecode supplies the exact set of terminal triangle IDs, after strict full-chain validation. Only triangles with MOPP leaves are exported to OBJ by default. **All** triangles remain in JSON; zero-area exceptions have `mopp_terminal_leaf=false`.
- The optional `--include-zero-area` includes the omitted degenerate faces for research, without manufacturing a missing MOPP leaf.

### Output files

| Output | Contents |
|---|---|
| `collision_triangles.obj` | Original flattened vertices, material-labelled OBJ triangles and comments with original Level triangle IDs and provenance block IDs |
| `collision_triangles.mtl` | Stable **synthetic debug colors**, not original textures or Havok material parameters |
| `triangle_provenance.json` | Original map SHA-256, exported geometry counts, complete per-triangle IDs and vertex index triplets, block/section ordinals, MOPP-leaf flags and render material strings |

`triangle_provenance.json -> export.obj_face_to_level_triangle_id` lists the Level's zero-based triangle ID for each OBJ face in face order. This is important when the OBJ omits a degenerate triangle and OBJ face count no longer equals source Level triangle ID plus one. Materials are identified inside the file by `debug_0000` etc., and the JSON material table maps each debug name back to its original render material string.

Coordinates are original **Level flattened XYZ**. Their physical units / world transformation are **not** claimed to be metres or Havok collision runtime coordinates. OBJ supports importing into Blender, MeshLab, and other conventional viewers; editing the OBJ will **not** update a game `.gmp`.

## Private retail 19-map audit

All 19 original retail Seattle maps (UE95 DX2 licensees 65, 67, 68, 69) passed `audit_map`, `inspect_mesh` and `render_obj` with no malformed source indices, mismatched MOPP IDs or provenance table failures.

| Validated quantity | 19-map original corpus |
|---|---:|
| Maps passing | **19 / 19** |
| Original source flattened Level vertices | **76,732** |
| Source flattened triangles | **43,154** |
| MOPP-leaf-linked OBJ faces, default | **43,152** |
| Zero-area triangles omitted from default OBJ | **2** |
| Original render-block/section references | **7,240** |
| Synthetic source/output bytes written to game map files | **0** |

For an end-to-end original-map smoke check, the actual new CLI exported `M1_Seattle_hub.gmp`: **5,783 vertices, 3,227 faces, 17 distinct render material names**. The source GMP remained unchanged. All complete original maps remain private.

## Command-line usage

From the repository root on Windows PowerShell, using **your own** retail DX2 `.gmp`:

```powershell
python research/dx2/export_level_mopp_triangle_debug_mesh.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" --outdir "C:\DX2_Research_Reports\M1_Seattle_hub_MOPP_Debug"
```

To expose the two degenerate triangles present elsewhere in the retail corpus, add `--include-zero-area` (with a **fresh** output directory).

In Blender, choose **File > Import > Wavefront (.obj)** and select `collision_triangles.obj`. Preserve the adjacent MTL file to see the debug palette. All generated geometry is a private derivative of your own GMP input. The user may export or edit it, but there is no supported path to re-import it into DX2.

The script requires Python 3.9+ and the existing `map_exporter` / `research/dx2` code, no third-party libraries. Output is restricted to an **entirely new** folder outside the original maps directory. It refuses existing output folders, malformed original file/version, corrupt triangle data or MOPP code, bad scaling and invalid source section mapping. It does not execute the game or edit GMP bytes.

## Next decisions

1. Determine whether the recovered Level MOPP-mesh is used as Havok triangle-soup shape in the retail game, or only as a cooked query precomputation; test via actual runtime instrumentation or independently decompiled/identified shape consumers.
2. Distinguish the render section's named material from native physical material, friction, restitution and footstep categories. Do not invent surface flags from the name string.
3. Locate the compiled-world BSP Model's separate vertex/surface pools and native fields 1/2, independently of the Level flattened mesh.
4. Reconstruct native Level collision block writer only after shape records, MOPP generation, engine reload and game-acceptance tests are independently verified.