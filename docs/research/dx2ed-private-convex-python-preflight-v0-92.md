# DX2Ed v0.92: independent source-private convex Box preflight

**Status:** standard-library Python verifier of private Godot-authored Box brushes, **not** a native Deus Ex: Invisible War BSP writer. It does not read original GMP, IBD, model exports, collision/MOPP, or retail content.

## Purpose

DX2Ed v0.80–v0.91 added authoring-local cutting planes and interactive face/corner editing. The editor mesh builder is not independent evidence of valid geometry. This module provides a second, separately implemented checker that reconstructs the private convex solid and reports a bounded, reproducible polygon/halfspace ledger before eventual research toward native BSP writing.

New module: dx2sdk/private_brush_preflight.py. Entry points: inspect_private_box_convex(raw) and inspect_private_draft_copy(document, copy_name).

## Accepted metadata

The private Box spec must have kind=Box, size=[x,y,z] (0.05–256m), steps=1 and exactly one of clip_plane (one cut) or clip_planes (2–8 cuts). Each cutting plane uses normal=[nx,ny,nz], signed distance and boolean keep_positive. Strict checks reject unnormalized/nonfinite planes, malformed shape/fields, invalid sizes, near-tangent cuts, empty or redundant intermediate cuts and nine-cut stacks.

A full saved DX2Ed-prop-draft-v1 JSON sidecar can also be inspected by selecting an exact DraftProp_N copy whose from_actor is Brush::Box and read_only_source is true. Neither its original map_cache nor game files are accessed.

## Independent topology algorithm

1. Begin with six outward box boundary halfspaces. Convert each new private cut into outward normal-dot-point <= offset (inverting when keep_positive).
2. Enumerate all triple boundary-plane intersections, filter finite points lying in all halfspaces and deduplicate within 2e-5m. This does not reuse Godot's polygon clipping implementation.
3. Collect coplanar vertices for each surviving face, angularly order its outward polygon and triangulate only nondegenerate fans.
4. Require every polygon and triangle edge to occur exactly twice with reversed direction, plus Euler V−E+F=2.
5. Require strictly shrinking finite signed volume after every authored cut and conservatively bound complexity to 14 faces / 44 triangles.

Outputs include private local face polygons, face/vertex/edge/triangle counts, enclosed volume, exact authored-cut order, private spec SHA-256 and a quantized geometric SHA-256. The latter is insensitive to clip-plane order when the final intersection is the same. Neither hash authenticates original retail content.

Every report explicitly records native_bsp_surface_indices_known=false, native_world_model_writer_enabled=false, collision_rebuild_verified=false, runtime_verified=false, original_gmp_or_ibd_modified=false.

## CLI

From the source checkout or extracted portable Python DX2SDK (Python 3.11+):

~~~powershell
python -m dx2sdk.private_brush_preflight C:\PrivateBrush\box.json
python -m dx2sdk.private_brush_preflight C:\PrivateDrafts\draft.json --copy DraftProp_12
~~~

Only regular, nonsymlink .json files up to 128 KiB can be read; the command prints a report to stdout. It will not read .gmp/.ibd or write any file, native map, or collision data. Invalid requests exit with status 2.

## Regression scope

The synthetic native_editor/tests/test_dx2sdk_private_brush_preflight.py tests a half-cube (6 faces, 8 vertices, 12 edges, 12 triangles, 4 m³), quarter-cube, reversed kept side, eight independent corner cuts with 14 faces/24 vertices/36 edges/44 triangles and expected volume 8−8×(3−√3×1.4)³/6, geometric fingerprint invariance under reordered cuts, redundant/empty/tangent refusal, malformed inputs, private draft actor authentication, and a byte-unchanged dummy GMP sentinel. No retail assets required.

## Native compatibility remains missing

This does not produce DX2's compiled World BSP node/zone records, point/polygon pools, native surface identities, material metadata, Havok/MOPP collision, or an engine-playable map. The original World Model v0.76 no-op and v0.77 provenance ledger remain separate, read-only research evidence. T3Ed native BSP and collision compilation are not implemented or verified.
