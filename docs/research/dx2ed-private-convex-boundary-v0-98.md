# DX2Ed v0.98: source-private oriented convex boundary and segment queries

This is a **research-grade geometric input contract** for the Godot editor's validated, private, clipped `Brush::Box` solids. It is not the proprietary DX2 native BSP representation.

## New in-memory boundary representation

`dx2sdk.private_brush_boundary.build_private_box_boundary` independently runs the v0.92 3-plane-intersection validator and assembles:

- Globally indexed local vertices in Godot Y-up metres.
- Oriented convex polygon boundary loops with outward unit normals, `n·x <= d` halfspaces, face area and **source-private** face kind/slot.
- Every undirected perimeter edge with **exactly two opposite directed face uses**, explicit adjacent face indices, and per-face ordered neighbours.
- Complete finite positive volume, surface area, Euler characteristic `V - E + F = 2`, full convex plane containment, and independently checked bounds/census.
- A stable SHA-256 of the authored topology record, plus existing source-private spec and geometry SHA-256 values.

There are **no native source Model node IDs, BSP surface indices, CSG ownership, zones, actor records, materials, or Havok/MOPP collision artifacts** in this result. A face slot refers solely to an original private Box side or private authored clipping plane. This is useful for later compiler research without pretending the retail serialization is known.

## Read-only convex segment intersection

`query_private_box_segment` clips a finite bounded local line segment against every outward face halfspace, returning entry/exit positions, normalized segment parameters and **all** touched face IDs at a corner or edge. It distinguishes:
- `miss`
- `interior-interval`
- `boundary-only-interval`
- `tangent-point`
- `stationary-inside` or `stationary-boundary`

A surface-only glide does not falsely count as passing through the solid interior. This is a **mathematical private preview query**, not a source DX2 gameplay collision, native BSP zone query, swept character capsule, or Havok/MOPP physical contact result.

## CLI examples

```bash
python -m dx2sdk.private_brush_boundary private_box.json
python -m dx2sdk.private_brush_boundary private_box.json --start -2 0 0 --end 2 0 0
python -m dx2sdk.private_brush_boundary private_draft.json --copy DraftProp_98
python -m unittest native_editor.tests.test_dx2sdk_private_brush_boundary -v
```

All commands are read-only. They accept only a regular source-private `.json` (maximum 128 KiB); no native `.gmp`/`.ibd` input, no output-file option, no original game reads, no overwrites. Segments use local metre coordinates (each coordinate at most 1,000,000 units in magnitude), reject NaN, infinities, booleans and malformed vectors. Errors return status code 2.

The asset-free test suite verifies a half-Box (8 vertices, 12 perimeter edges, 6 faces, 4 m³ volume), eight-corner cut Box (24 vertices, 36 perimeter edges, 14 faces), reciprocal face adjacency and outward orientation, entry/exit through the clipped face, simultaneous corner hits, grazing/tangent/parallel and stationary cases, invalid sources and a byte-hashed synthetic original GMP sentinel.

The portable SDK source archive and Windows editor prototype include this utility and require it during package validation. **No retail engine World BSP/CSG or collision writer has been enabled, and T3Ed parity remains partial.**
