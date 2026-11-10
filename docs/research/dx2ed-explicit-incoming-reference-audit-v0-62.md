# DX2Ed v0.62: explicit incoming actor reference audit

**Checkpoint:** 2026-11-10. **Status:** read-only DX2 v95 GMP
analysis and conservative native unplace refusal. **Retail runtime remains
unverified**, and absence of known references is **not** proof of full safety.

## Problem addressed

The v0.59 unplace and v0.60 combined-change exporters could remove an
existing original StaticMeshActor from the Level actor list even if another
actor explicitly referenced it. The original export still exists on disk,
and this does not establish what the retail engine does with references,
object lifetime or collision.

v0.62 adds a source-only scan for **known, decoded positive UE2 export
references to the target object**, and refuses the native unplace when
any are found. It does not change any existing writer's allowed map
geometry or the source map, and does not delete the original actor export.

## What the read-only audit recognizes

For each other export, the checker identifies source actor, one-based
export ID, reference field and decoded reference kind when a **known
typed field** equals the selected original actor's one-based export ID:

- Export table class/super/outer references.
- Actor script-frame node/state_node pointers, where decoded.
- Decoded actor object-link compact-index entries.
- Tagged UE2 Object/Class properties, including nested decodable Struct
  property lists.
- Native GameSys object/class blocks and decoded GameSys struct property
  lists.

The original Level actor list is excluded from incoming-reference hits
because the unplace operation necessarily removes exactly that one
original Level membership; it is separately validated by the writer.
The target's own serialized export is not counted as an *external*
incoming reference.

## What it CANNOT prove

No known references means **only no references in those decoded explicit
fields**. The checker explicitly does not resolve:

- Unknown native class-specific tails, raw/untyped arrays and undeclared
  object encodings.
- IBD or TriggerScript resources, script bytecode, conversation/AI graph
  references, cross-map links, external GameSys packages or load/save state.
- Runtime-only relationships, initialization, collision or object spawning.

The JSON always keeps incoming_references_verified=false,
safe_to_unplace_claimed=false and runtime_game_verified=false. A reported
opaque/untyped count highlights incomplete coverage; zero opaque scopes
still does **not** establish IBD/runtime coverage.

## Read-only command

    python native_editor/package_writer/dx2_incoming_ref_audit.py "C:\DX2\Maps\M1_Example.gmp" --source-sha256 ORIGINAL_64_HEX --actor-export ORIGINAL_ONE_BASED_EXPORT --actor-name EXACT_ORIGINAL_ACTOR_NAME

The checker demands an exact original GMP SHA-256 and binary-identical
writer no-op baseline. It authenticates the target's decoded static mesh
class/name/Location and membership before reporting references.
It **never writes a candidate** or game data.

Possible reported status values:
- explicit-incoming-reference-found
- no-explicit-incoming-reference-found-coverage-incomplete
- refused (invalid source, identity or GMP)

The second status is **not a game safety certificate**. Even the first
status does not claim a runtime load/crash would necessarily occur; it is
an evidence-based refusal of the current narrowly defined writer.

## Integration

- Experimental original prop **Unplace Save As...** now invokes the
  incoming-reference checker before offering an isolated output.
- **Stage/Unstage original prop** in the v0.60 combined editor uses the
  stricter reference-aware unplace preflight rather than clone eligibility.
- Combined native Save As and JSON recipe export repeat that source
  preflight for each staged unplace. The Python combined writer separately
  rechecks all unplaced originals before writing in case the source or plan
  changed.
- v0.61 recipe import/rebuild relies on the same v0.60 Python compiler,
  so an incoming reference detection also blocks rebuilding an otherwise
  valid-looking recipe.

Read-only scanner plus exact-source writer checks complement, but do
**not** replace, byte-for-byte native binary verification and isolated
output destination rules.

## Automated evidence

Asset-free synthetic DX2 v95 fixtures demonstrate:
- Original unlinked candidate remains eligible without claiming full
  incoming-reference verification.
- A second actor with an explicit tagged Object reference to target is
  detected with a source export and field name, and both single and
  combined unplace writers refuse.
- An explicit GameSys object block reference is detected and blocks.
- An export-table outer reference to the target blocks.
- CLI audit returns machine-readable JSON, with no source writes.
- Bad target/export/SHA-256 is rejected.
- Godot 4.3 source compile and Windows bundled source import checks remain
  release gates.

## Next

The first highest-value user test is a controlled A/B test in a
disposable backed-up retail DX2 installation, on one map and one
non-essential static decoration. Verify fresh entry, object presence,
collision, re-entry, save/reload and original map restoration. Runtime
success is not established by this source-only audit.

Longer term, complete reference coverage requires reconstructing
typed array layouts, script/IBD linking and Level/actor ownership,
plus BSP/CSG, collision and resource cooking. Those are separate
capabilities on the road to T3Ed-like playable mission authoring.
