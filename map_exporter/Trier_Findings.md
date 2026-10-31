# Trier retail bundle diagnostics (DX2 Map Exporter 0.2)

Examined locally supplied `M3_Germany_Trier.gmp` and `m3_trier.ibd` plus the existing `Maps.zip` shared resource archive. **Do not upload these copyrighted resources to a public repository.**

| Actor in original GMP | Mesh | Finding | Preview | Confidence |
|---|---|---|---|---|
| `StaticMeshActor__92` | `M3_sign_9worlds` | `M3_sign_tavern9` and its diffuse texture `M3GTavern_sign9worlds` both present | Optional local Y mirror | Mirror effect visually user-tested in Blender, game transform decoding pending |
| `StaticMeshActor__146` | `M3_QueeQueg_sign` | `M3_queequeg-emissive` / `M3_QueeQueg` present | Optional local Y mirror | Same |
| `StaticMeshActor__380` | `1Apipe` | Default skin references `0_pipes-brownrust` and `0_pipes-brownrustdark`, neither present in supplied bundles | Alternate `OrangeRust` skin resolves `0_pipes-orange` -> `gen_pipes5`; this is NOT the original rusty look | Resource lookup verified |
| `StaticMeshActor__29` | `M3Trier_hands_stat` | `GEN_MEMBRANE-holocyan` material record missing | Untextured translucent cyan | Approximate |
| `D_2968__0` | `GO_globe-pubterm` | Globe second slot `GO_globe-holo` has empty diffuse, references `globe_N` and `anim_12_holocyan_1` in shader stages | Untextured translucent cyan | Approximate |

The actor IDs in the original GMP have **two underscores**. They may display differently after an import.

**Important:** This does not establish that global Y mirrors are a correct native transform interpretation. Do not apply them indiscriminately to all actors. No DX2 shader/animation reconstruction is claimed.