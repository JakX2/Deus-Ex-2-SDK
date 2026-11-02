# DX2Ed: original NPC / TriggerScript discovery (read-only, v5 research)

## Why this is the next stage

User-requested next milestone after native static prop creation: NPCs and
scripts in playable DX2 maps. **StaticMeshActor duplication does not
justify blindly cloning active D_* gameplay actors.** These have native
state, game-property references, AI links and possibly mission scripts.
Original game scripts are compiled `.tsd` definitions, not ordinary
UnrealScript source files. Safe script-binding and spawning require
additional independent native package evidence and in-game testing.

This v5 addition is **an original-source browser, not yet a writer**.

## Original files studied

- The user's own original DX2 WTO Terminal GMP, source SHA-256
  `a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa`
  (retail source; no modified GMP redistributed).
- Original `Content/DX2/TriggerScript.zip`, 3,263 `.tsd` files:
  **2,645** active `Defs/*.tsd`, **618** `DeletedScripts/*.tsd`.
  Only active definitions are browsed.
- Named active examples: `GenericLightSwitch`, `AlarmDoorOpen`,
  `AlarmLightOn`. Their binary signatures include `1FFE2FST`
  and `0FFE2FST`; source strings include `kTCT_*` conditions and
  `kTAT_*` actions.
- Original WTO `actors.json`, generated directly from source GMP:
  **1,033** displayed actors, **14** have exact original GameSys editor
  property 82 (`name`) == `AI`, and **19** have a serialized
  TriggerScript property. Those 19 raw values contain integer index
  lists. **They cannot be equated to TS_ script IDs** until an
  independent mission logic-index binding is verified.
- AI-layer candidates include `D_527__0`, `D_2100__0`,
  `D_1216__0` and others. Their numeric D_* class names are
  insufficient to guarantee NPC type or safe spawnability.

## Editor workflow

1. Open the **original unchanged WTO Terminal GMP** in DX2Ed.
2. In the left actor category menu choose
   **Original AI layer (NPC candidates)**. This filters only by
   source-verified property 82 `AI`; it does not infer an NPC class.
3. Select an actor and press **F** to focus its source location,
   including actors with no GLB mesh. No new actor is created.
4. Open the new **Scripts** left-sidebar tab. Click
   **Open original TriggerScript.zip...** and choose the ZIP
   extracted from your own game files, not an arbitrary script.
5. Search script ID/title/condition/action, choose a result to
   inspect original symbol names and description.
6. With an original actor selected in the Hierarchy,
   click **Inspect selected actor script fields**. These are displayed
   as unresolved original integer indices, *not* invented connections
   to the separately browsed scripts.

The Python backend `dx2_gameplay_catalog.py` checks original map
SHA-256 against adjacent cache `actors.json` before reading the ZIP,
validates ZIP entry structure and source binary signatures, and writes
one private editor cache JSON under Godot's `user://` data folder.
It never writes into any game GMP or TriggerScript ZIP and does not
modify existing game files. Other ZIP members including
`DeletedScripts/` are ignored rather than executed or extracted.
The editor enforces read-only/no spawning/binding schema flags.

## Validation and limits

Tested on original private source files offline:
`2645 scripts / 14 AI-layer candidates / 19 actors with raw script
fields`. Asset-free regression tests cover malformed/unsafe ZIP
entries, invalid binary TSD headers, actor-cache SHA mismatch,
duplicate source exports, and CLI source-file preservation.

Pending: Windows Godot GUI user test, mapping raw script indices to
mission-scope definitions, identifying original NPC archetype
construction requirements and safe new-actor serialization. Do NOT
offer an unrestricted NPC spawn or TriggerScript writer yet.
Game/asset bytes and full script definitions are not committed to GitHub.

## Next experimental writer gates

1. Identify a single non-hostile, non-essential original D_* NPC
   source in a disposable map and its exact GameSys ancestor.
2. Independently decode its class, property 82 AI layer, actor
   references, AI points, script field references, native state
   frame and extra package resources.
3. Build a **read-only** source-bound object graph showing
   dependencies and warnings. Confirm exact script definition linkage.
4. Only then prototype a single isolated native NPC clone, with
   dependencies initialized, independent reparse, backups and an
   explicit in-game stability/collision/AI test. No retail map writes.


## Follow-up: Native placement directly from Assets list (v6 experiment, 2026-11-02)

T3Ed-style object placement can now begin with an existing `staticmesh`
resource in the DX2Ed Assets tab. This is **not** arbitrary new-resource
construction yet. The v6 command creates a valid draft by reusing a
**source-verified original StaticMeshActor already placed in the current
map** and referencing the selected IBD resource.

Use the Assets tab:
1. Select a static-mesh resource with `Native reuse source` listed
   in its details. The button **Place native copy (placed mesh)** is
   disabled for unused/unlinked meshes.
2. Click that button. The original source actor and original mesh must
   exist in the current source GMP and imported scene, with an exact
   source hash. The Python single-actor preflight rechecks that actor
   before any draft is created.
3. The new preview copy retains the source actor's mesh, skin,
   collision-reference-bearing original properties and orientation.
   It is placed at the editor's current camera target if within the
   existing native writer's 4096-UE-axis translation limit.
   Otherwise a safe one-metre offset from the source is used.
4. Move the draft as needed. For **exactly one** draft use
   `Experimental native Duplicate Save As...`. For **2–8**
   use `Experimental Multi Duplicate Save As...`. Both still
   require an isolated destination with the original GMP filename,
   preserve original map bytes, check native sources again, and
   generate an independent verification manifest.
5. Placing a resource not already instantiated in the map is still
   preview-only. No fake GameSys mesh references, new mesh imports,
   new collision hull references or native actor archetypes are made.

Source-only headless Godot tests assert that a known source IBD
resource selects the lowest valid original actor export, unused
resources are disabled for native placement, original actor
orientation is retained, and out-of-range/zero camera target offsets
fall back to a strictly supported one-metre translation.

**Status:** source and headless tests passed; this v6 UI workflow
has **not yet been tested in Windows retail DX2**. The underlying
single- and multi-copy native GMP mechanisms have previously
been confirmed to render and block the player in-game, but this
new UI entry path still requires a distinct runtime test.

Next format work: decode exactly how an original `StaticMeshActor`
references its mesh/material/physics hull from IBD resources,
including what name-index or resource key must be synthesized for
a mesh not already placed on the map. Do not enable native
placement for previously unused meshes until those package links
are independently reconstructed and runtime tested.
