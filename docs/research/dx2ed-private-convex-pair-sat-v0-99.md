# DX2Ed v0.99: source-private convex pair SAT preflight

**Scope:** compare two separately validated, editor-authored clipped `Brush::Box` solids under two **proper rigid** local-to-preview transforms. This is a read-only geometry research feature for later CSG input planning. No native DX2 BSP node, surface, zone, actor, material or collision identity is inferred.

## Why this matters

A single closed convex boundary (v0.98) is not enough to reason about multiple authored brushes. The separating axis theorem (SAT) can classify their relative placement before any boolean/CSG step or collision rebuild is attempted.

`dx2sdk.private_brush_pair_sat.inspect_private_box_pair(a, b, transform_a=..., transform_b=...)`:

- Uses the independent preflight and v0.98 closed boundary topology for **both** private solids.
- Transforms local vertices by 3×3 proper orthonormal rotation plus translation into a common Godot-preview Y-up metre frame. Rejects reflections, shear, scaling, nonfinite coordinates and out-of-bounds origins.
- Tests normals of every face from both solids **plus cross products of all distinct boundary edge directions**. Edge-cross axes are necessary: rotated boxes may overlap on every face-normal projection but remain separated.
- Reports `disjoint`, `boundary-contact` or `interior-overlap` within an explicit **1e-7m numerical contact tolerance**, with a supporting witness axis, source-private face/edge indices, projected axis intervals and unique-axis census.
- Returns private geometry, topology and transform SHA-256 fingerprints; reports native BSP, Havok/MOPP, original source files and retail gameplay as unsupported or untouched.

The reported axis gap is **a projected separation on the chosen axis**, not exact minimum Euclidean shape distance. The minimum tested overlap is **an axis interval overlap**, not a verified penetration depth or contact manifold. No triangle-mesh collision engine, physics simulation or game-native geometry writer is involved.

## CLI usage

```bash
python -m dx2sdk.private_brush_pair_sat first_box.json second_box.json
python -m dx2sdk.private_brush_pair_sat first_box.json second_box.json --transform-b second_transform.json
python -m dx2sdk.private_brush_pair_sat my_draft.json my_draft.json --copy-a DraftProp_7 --copy-b DraftProp_8
python -m unittest native_editor.tests.test_dx2sdk_private_brush_pair_sat -v
```

An optional private transform JSON has **only** `basis` (three row-major coordinate triples) and `origin` (one triple). For example:

```json
{"basis":[[1,0,0],[0,1,0],[0,0,1]],"origin":[3,0,0]}
```

Input files are regular non-symlink `.json` up to 128 KiB, using the existing private Box/draft parser; the CLI never accepts source `.gmp`/`.ibd`. It writes **nothing** and returns status code 2 for unsupported input. Original game data is not read.

## Asset-free evidence

`native_editor/tests/test_dx2sdk_private_brush_pair_sat.py` covers deterministic exact repeat results, identical private solid overlap, separated/touching/overlapping placements, face/edge/point contacts, proper rotations, reflected/scaled/sheared transform refusal, malformed numeric inputs, private draft selection and a byte-unchanged original-GMP sentinel.

The diagonal rotated disjoint fixture is a deliberate edge-edge test: the original and rotated face-normal projections overlap, but an edge-cross axis separates the two solids. SDK and Windows prototype package manifests require the new source module. T3Ed BSP/CSG parity remains **partial**.

## Explicit limitations

This only checks two source-private **convex** solids. It does not perform a boolean union, intersection or subtraction; it does not output a new brush, build visibility/zone portals, serialize DX2 World BSP, assign original BSP surfaces, generate native GameSys/actors, bake materials, cook Havok/MOPP collision or establish retail walkability and gameplay behavior. Those tasks need separately established engine-native specifications and tests.
