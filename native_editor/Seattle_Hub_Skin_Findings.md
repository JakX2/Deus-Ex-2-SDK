# Seattle Hub staircase skin audit (2026-11-01)

This research uses the user's privately supplied `shub.zip`, containing
`M1_Seattle_hub.gmp` (2,561,763 bytes) and `m1_hub.ibd` (27,848,704 bytes).
The archive passed ZIP CRC verification. **No retail assets, materials or images
are included in the public repository.**

## Verified input hashes

- GMP SHA-256: `57c8502db646db3f98448863fd8f0b4bd3a89dc6bb6738b2f8f5ad69ed9f58bd`.
- IBD SHA-256: `b7f044c2c6ff7260a848005fe26fc2dcf5c3dfb072e3990e1b90a38aa7c78d87`.

## Actor in the user's screenshot

This is **Seattle Hub**, not Seattle Club. The screenshot's actor matches the
retail GMP records exactly:

| Field | Decoded original value |
| --- | --- |
| Actor | `StaticMeshActor__130` |
| Export index | `1526` |
| Resource | `1Hub_city_stair1` |
| Position (Unreal units) | `[-224, 592, -1024]` |
| Rotation (Pitch, Yaw, Roll) | `[0, 16384, 0]` |
| Requested skin, Gamesys property 56 | `Tan Stones` |

The GMP contains 1,661 positioned actors, 1,080 of which reference static
meshes. All **12** placed instances referencing `1Hub_city_stair1` explicitly
request the same `Tan Stones` skin in Gamesys property 56.

## Original resource and material chain

The `1Hub_city_stair1` static mesh exists in `m1_hub.ibd` with
**four named skins**:

| Skin index | Skin name | First material | Second material |
| --- | --- | --- | --- |
| 0 | Default | `M1HUB-conc1` | `M1HUB-needleconc1dark` |
| 1 | GrayBrick | `M3_WallOLDbrick` | `M1HUB-needleconc1dark` |
| 2 | **Tan Stones** | **`M1HUB_wall`** | `M1HUB-needleconc1dark` |
| 3 | carpet | `M1WTO_intstair` | `M1HUB-needleconc1dark` |

Both Tan Stones material library records exist in the Hub mission IBD:

- `M1HUB_wall` has diffuse stage `wall`.
- `M1HUB-needleconc1dark` has diffuse stage `M1HUB-needleconc1`.

Both diffuse resources exist as 512 x 512 DXT1 textures in the same IBD and
decode to recognizable stone/concrete image patterns (not blank textures).
Conversely, the Default skin's `M1HUB-conc1` first material was not located
in the supplied Hub mission bundle or shared map bundles.

## Root cause and change

**Confirmed exporter bug:** Before DX2Ed 0.2.6, `Builder.mesh_data()` always
used `mesh.skins[0]` even when the placed actor requested `Tan Stones`.
Consequently, the 12 staircase actors could be rendered using the wrong
first-section material. This is a concrete explanation for the flat material
in the user's screenshot.

**Code fix already in development branch:** The exporter now resolves each
actor's requested skin (case-insensitive), produces a distinct GLB mesh per
skin selection, and records per-material texture resolution in the JSON
report and Godot inspector. Re-export is required; the map cache version was
bumped to prevent reuse of the earlier GLB.

**New convenience change:** The ZIP staging utility can autodetect a mission
ZIP containing exactly one GMP and one IBD, including `shub.zip`. It rejects
ambiguous archives. The Godot UI button is now **Open DX2 map ZIP...**.

## What remains unverified

The exact rendered Hub stair appearance after the exporter change still needs
Godot/Windows visual validation against the retail game. UVs, texture
samplers, game-specific lightmaps, and Ion Storm shader lighting are not
fully reproduced in the experimental renderer. Do not treat the original
asset chain as proof of perfect in-engine shading.

No source GMP or IBD was modified.
