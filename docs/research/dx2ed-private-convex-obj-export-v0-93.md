# DX2Ed v0.93: deterministic Wavefront OBJ export for private Box geometry

**Status:** source-only Godot-private geometry interchange, not a Deus Ex: Invisible War compiled World BSP/CSG writer, collision/Havok/MOPP cooker or retail gameplay capability.

## Goal

The v0.92 independent Python halfspace preflight reconstructs polygon geometry for private Godot-authored clipped Boxes. v0.93 exports that same validated polygon topology as ordinary OBJ triangles suitable for inspection in Blender or equivalent tools. The exporter deliberately accepts no imported original DX2 geometry, proprietary assets, native BSP IDs, source material names or textures.

## Command line

With Python 3.11+ and the source checkout or portable DX2SDK ZIP:

    python -m dx2sdk.private_brush_obj C:\PrivateBrush\box.json C:\Exports\box_preview.obj
    python -m dx2sdk.private_brush_obj C:\PrivateDrafts\draft.json C:\Exports\box_preview.obj --copy DraftProp_12

Input: only regular nonsymlink JSON up to 128KiB, containing a private Box brush specification or a DX2Ed-prop-draft-v1 sidecar with read_only_source=true. Full sidecars require an exact Brush::Box DraftProp_N selection. Output: only a NEW .obj path, using exclusive creation; an existing output is never overwritten. Original .gmp and .ibd are rejected as inputs and outputs. Success prints a JSON summary with the mesh and output SHA256 hashes; failure returns code 2.

The Python API render_private_box_obj(raw, copy_name=None) produces an entirely in-memory pair (obj_bytes, summary). The export_private_box_obj(raw, destination, copy_name=None) API writes a new file only.

## OBJ contract

Output contains o DX2Ed_Private_Box and s off, followed by one deduplicated v record per solid vertex, one outward vn record per planar face, and triangle f vertex//normal indices. Each face has its own group, private_box_side_XX or private_cut_cap_XX, where XX is a local authored face/cut ordinal, never a native BSP identifier.

Coordinates are **Godot-local metres, Y-up**, not DX2 world-engine coordinates. The exporter intentionally omits UVs, materials, game shaders, original actor identities and collision. For every exported triangle, cross-product orientation must agree with the independent outward face normal. The preflight separately verifies reciprocal oriented mesh edges, finite enclosed volume and Euler V−E+F=2.

Repeated export of the same private brush produces identical OBJ bytes. Different authored cut orders may serialize face groups differently while producing the same quantized geometric SHA when the final intersection is equivalent. Matching private geometry fingerprints are not evidence of retail-game interoperability.

## Test and packaging coverage

The source-only Python test native_editor/tests/test_dx2sdk_private_brush_obj.py constructs invented geometry and checks:

- Half-Box: six faces, eight vertices, twelve triangles and volume 4m³.
- Eight disjoint corner cuts: fourteen faces, 24 vertices, 44 triangles and analytic truncated-cube volume.
- An independently parsed OBJ: valid triangle indices, outward normals, reciprocal shared edges and positive signed enclosed volume.
- Determinism, authored plane reorder differences, and geometry hash equivalence.
- Strict original actor rejection, malformed source-private data refusal, unchanged original synthetic GAME.gmp sentinel, exclusive creation, refusal of overwrite/symlinks, and CLI use of an exact private draft copy.
- Presence of the new module in the portable Python SDK and Windows prototype source manifests, preflight and package tests.

No original game files or proprietary content are used in CI.

## Native-format blockers

OBJ is an external interchange format, not an Invisible War native level. Source-authenticated Model point/polygon pools, BSP surface ownership, visibility and zone compiler, material representation, collision/Havok/MOPP regeneration and retail-game load/play checks remain absent.

The original native World Model byte-exact no-op (v0.76), source span ledger (v0.77), and private convex Python topology report (v0.92) are separate research artifacts. This exporter does not claim to join them into an engine-valid modified Model. T3Ed feature parity remains **partial**.
