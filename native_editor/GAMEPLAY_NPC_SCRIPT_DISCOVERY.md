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


## Follow-up: independent GameSys 92 name-table slot evidence (v8, 2026-11-05)

After the original TSD-to-IBD resource comparison in PR #60, DX2Ed now
also verifies the **original actor's cooked GameSys property 92** against
the owner-original GMP's native actor binary. The new
`backend/dx2_actor_script_name_candidates.py` reopens the original
DX2 Unreal v95 package, checks every original actor export/name/class,
re-decodes the GameSys property, and requires it to match the source-hash-
authenticated cached actor property exactly.

For compact-integer arrays only, the research panel compares each raw
numeric value against the **name in the original GMP package name table
at the same numeric position**. If present, the inspector also displays:

- whether that name matches an original `Defs/*.tsd` script ID in the
  owner's unchanged TriggerScript ZIP;
- whether the name matches a kind-21 script resource in the owner's
  selected original IBD;
- whether the standalone TSD payload and IBD payload are exactly equal,
  different, or the resource is absent from that IBD.

This creates a useful three-source candidate trail:
**original actor GameSys 92 value → original GMP name-table slot →
original TSD/IBD resource evidence**. However, the first arrow is
explicitly **hypothetical**. The generic compact-index array decoder
does **not** prove that this particular GameSys field stores Unreal
`FName` indices rather than some other game-defined integer references.
A coincidental triple match is therefore **not proof that the actor
executes the named TriggerScript**. The output schema retains
`name_table_indices_semantics_verified=false` and
`actor_to_script_binding_verified=false`, even for byte-exact matches.

The probe is best-effort: if an original actor cannot be independently
decoded or its source cache disagrees with the GMP, that actor's
candidate list is empty and the already-verified standalone TSD/IBD
resource results remain available. Report files are private user-data
JSON and are never input to the experimental native GMP Save As writer.

**Manual owner-map acceptance:** open a source-unmodified DX2 GMP,
its original TriggerScript ZIP, and one or more matching original IBDs.
Choose an actor with source GameSys property 92, use **Scripts →
Inspect selected actor script fields**, and record the per-index
candidate evidence. To claim a genuine runtime link, the numeric
reference mechanism must still be independently demonstrated by
additional native package/script evidence and a disposable retail
game test. Do not mark script compilation, NPC spawning, or dialogue
serialization as supported until separately validated.


## Follow-up: map-wide native TriggerScripts numeric index hypotheses (v9, 2026-11-05)

The previous original-actor GameSys property 92 inspector exposed only
single-actor name-table coincidences. DX2Ed now aggregates all original actors
with independently re-decoded native compact-integer arrays and compares five
small numeric adjustments (`raw - 2`, `raw - 1`, `raw`, `raw + 1`,
`raw + 2`) against the **same owner-original GMP name table**.

Choose **Scripts → Show map-wide script index audit** after comparing your
unchanged original `TriggerScript.zip` to one original mission/kernel IBD.
The source-pinned report records, for each exploratory shift:

- total raw numeric values and how many positions reference a nonempty
  original GMP name-table entry;
- how many positions name an original active `Defs/*.tsd` definition,
  including the number of **distinct** script names;
- how many name hits also have an exact, byte-identical original IBD kind-21
  payload, how many have different payloads, and the numbers of actors with
  any candidate match;
- how many repeated candidate-name occurrences could inflate the raw hit
  totals.

Actors whose source export, class, name, and **exact native GameSys 92
serialized property** could not be independently verified remain excluded and
are counted separately. Opaque or string-interpreted arrays are not coerced
into name indices. The view refuses source-unsupported boolean declarations
of native writer support, validated actor-runtime links or a preferred offset.

This is a **discrimination experiment**, not a recovered serialization
contract. Shifted offsets are not necessarily independent statistical control
groups, and a higher name/TSD/IBD match count is **not** proof that any of
these offsets is the true runtime interpretation. Even the zero-shift row
is only a name-table coincidence unless original game behavior or another
independent native reference table establishes the mapping. The script
writer, dialogue compiler and actor binding exporter remain disabled.

The implementation is `backend/dx2_script_index_hypothesis_audit.py` plus
`script_index_audit_view.gd`. The source-only test suite exercises valid
positive matches, deliberately misleading shifted matches, forged match
claims, ambiguous script identities, malformed numeric array elements,
partially decoded original actors, no original package, and GDScript view
fail-closed behavior. Only aggregate counts are displayed; no original game
bytes are included in CI or in the user-facing report.

**Suggested real-game research:** compare two **different** owner-original
GMP maps with their own source-matched actors and IBD resources; examine
whether the same proposed offset produces coherent candidate trends across
maps and whether exact-match counts are consistent with source script
presence. Do not infer a native binding from aggregate trends alone. Before
enabling script assignment, independently validate GameSys 92 element type
and mission-scope resource index resolution with retail runtime evidence.


## Follow-up: mission IBD versus original Kernel_TSDALL binary profiles (v10, November 5, 2026)

User-side Seattle Club evidence already showed **37/37** original actors with
native GameSys property 92 successfully decoded and **103/103** raw
compact integers landing on original GMP name-table entries whose names
match active standalone TriggerScript IDs at offset zero. Shift controls
(-2, -1, +1, +2) yielded only 29–30 such name matches each. In the
**selected Club IBD**, the actor-name-slot candidate occurrences were
**17 exact and 71 different** relative to original standalone TSD
payloads (with 15 occurrences not in either classification).
These are **actor candidate *occurrences***, not necessarily unique
script definitions or evidence of runtime execution.

The v10 native read-only differential builds on that observation. The
**Scripts → Compare mission IBD against Kernel_TSDALL...** command
requires the same source-authenticated GMP, original actors.json,
TriggerScript ZIP, and a previously verified **mission-specific** IBD
selected via **Verify script resources in original IBD...**. It
requires a *different* user-owned original IBD named
`Kernel_TSDALL.ibd`.

The new `dx2_mission_kernel_script_diff.py` independently compares
three distinct source payload relationships per named script:

1. The mission-specific kind-21 IBD resource versus the original
   standalone `Defs/*.tsd` bytes after the known 12-byte TSD header.
2. The same script in the original `Kernel_TSDALL.ibd` versus that
   standalone TSD payload.
3. If both IBDs contain the script, mission IBD versus Kernel IBD
   *directly*, independently of any standalone TSD definition.

Result categories preserve exact matches, differing bytes, a script
missing from one IBD, and a name found in an IBD but not in the active
source ZIP. For each comparable pair, the private local JSON contains
only SHA/provenance metadata, sizes, first different payload byte
offset, common prefix/suffix lengths, overlapping different-byte count
and changed-byte-run count. **Original script bytes are never copied
into the report or published by DX2Ed**.

The Godot UI presents a **sanitized aggregate** of total unique IBD
resources, shared/mission-only/kernel-only IDs, exact versus different
copies, and the **five most common first differing offsets** in each
of the three comparisons. This can distinguish common structural
divergences from scattered byte changes but **cannot establish their
cause** without deeper native format research. A user can inspect
byte-offset metadata for an individual selected original script locally.
The **Copy sanitized mission / Kernel summary** button deliberately
excludes source filenames, paths, actor/script names, hashes and binary
content. Original actor name-table candidate occurrences are tracked
separately from unique IBD resources to avoid misreporting earlier
17/71 reference-weighted counts as unique script counts.

These source-derived results do not prove an actor's runtime script
binding, executable modifications, native bytecode compilation,
mission-script link installation, or dialogue serialization. The
existing native GMP Save As and IBD writers are **not** connected to
this research. Original game input files remain unchanged; only a new
private JSON report is generated outside the game directories.

This PR includes source-only Python tests with synthetic IBD resource
tables and differing-length/equal-length binary payloads, original GMP
cache SHA mismatch, invalid kernel selection and corrupted IBD refusal,
private report non-overwrite/path protection, and deliberate redaction of
owner-local CLI output. A dedicated Godot fixture tests first-byte
offset clustering, privacy-safe summaries, detailed script metadata,
and refusal of forged native runtime flags.
