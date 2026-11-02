# DX2Ed T3Ed-style native Assets placement: WTO source evidence

As of 2026-11-02, user wanted a workflow akin to T3Ed: select a mesh
from the Assets browser, place it, save one map. This document records
the exact *first* implementation boundary and native source structure.
Game data remains private and is not committed.

## Original WTO Terminal inventory

Independently enumerated original `M1_Seattle_Hub_WTOterminal.gmp`
(SHA-256 `a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa`)
and the original mission `m1_hub_wtoterminal.ibd` using
`dx2_actor_explorer.actor_records` and
`dx2_asset_catalog.catalog_from_paths`.

- Mission IBD contains **134** `staticmesh` resource records.
- Source-level scene lists **623 placed StaticMeshActor records** with
  decoded mesh properties, comprising **57 unique mesh names**.
- All 57 are represented in the mission IBD, giving **57 native reuse
  candidates** through the new Assets button, subject to each source
  passing the original actor-clone eligibility check.
- **77** mission IBD static-mesh records have no original placed
  `StaticMeshActor` in this map. These remain preview-only.
- The count is a map-specific inventory, not a count of all base-game
  resources: shared IBDs, other levels and System data can contribute
  additional assets.

## How the original native mesh link works

From the original map's actor GameSys block `id=43`:
- `StaticMeshActor__611`, source export 907,
  mesh `FO_table_hitech3`, id-43 object reference
  `+742` -> map export `StaticMesh__499`.
- `StaticMeshActor__47`, source export 1148,
  mesh `1Hub_wto_term-deska`, id-43 reference
  `+1383` -> `StaticMesh__141`.
- `StaticMeshActor__578`, source export 889,
  mesh `1Hub_wto_term-detail1-j`, id-43 reference
  `+1093` -> `StaticMesh__159`.

The actor's `game_properties` block 43 is not a string name.
It is an **object reference to a serialized map-local StaticMesh
export**. That export itself points to the original mission IBD mesh
name and has extra metadata such as bounds and mesh/skin details.
This is why replacing that reference with an arbitrary resource
name or index would be unsafe. A future fully general native
asset spawner must construct (or reuse) a verified matching
StaticMesh export, maintain package name/index tables and resource
metadata, and verify existing collision/hull semantics.

## Implemented v6 editor behavior

An additional `Place native copy (placed mesh)` button appears
in the **Assets** tab, separate from `Place preview mesh`.

- Native source discovery matches the selected IBD resource name to
  source actors' exact decoded mesh names, case-insensitively, and
  restricts to original `StaticMeshActor` classes with valid
  render instances. The earliest source export wins deterministically.
- The UI displays the exact actor export used. The button stays
  disabled if the resource has no valid placed static actor.
- Clicking native placement validates the source GMP SHA and
  runs the existing independent Python actor preflight. An invalid,
  stale, or changed source map cannot create a native draft.
- A new `DraftProp_n` instance reuses the actual source actor's
  original mesh, materials, basis and native actor source identity;
  it does not create or rebind property 43.
- The draft initially uses the editor camera target when the
  displacement is within the existing 4096 Unreal-unit per-axis
  translation gate. Otherwise it is offset a safe one metre
  from the original source, retaining the exact original basis.
- From there, the existing one- or multi-prop Save As writer
  continues to enforce strict source eligibility, no rotation or
  scale, independent package reparse, original export preservation,
  and an isolated output GMP plus manifest.

This is more convenient source-verified placement, **not** native
mesh-actor instantiation from previously unused IBD mesh data.
No proprietary asset, GMP, GLB or IBD data is distributed.

## Next milestone

Research precisely the binary layout and source references of the
map-local `StaticMesh` exports before generating any new one.
The first safe experiment should be a **read-only** analyzer that
compares source exports for two different original mesh resources,
then tests an isolated *in-memory* new-export construction with
independent DX2/T3SDK parsing. Runtime testing would follow only
after all index, IBD resolution and collision checks pass.
