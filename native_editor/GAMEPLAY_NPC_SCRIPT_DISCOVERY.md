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
