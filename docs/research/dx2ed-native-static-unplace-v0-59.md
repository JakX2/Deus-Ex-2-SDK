# DX2Ed v0.59: source-pinned original StaticMeshActor unplace

**Checkpoint:** 2026-11-10. **Status:** experimental binary authoring, native runtime NOT verified.

## What it does

DX2Ed now exposes **Experimental Unplace Original Prop Save As...** in the
Godot 4.3 editor. This is a first native-level removal operation for
Deus Ex: Invisible War, deliberately smaller than T3Ed's general Delete.

The isolated writer removes exactly one existing, verified
StaticMeshActor's one-based export index from the serialized **Level actor
reference list** in the original .gmp. It does **not** delete the export
record itself, modify any original actor payload, update collision,
rewrite GameSys, edit IBD resources, or clean up possible incoming links.
An absent Level reference is a hypothesis about runtime placement, not
proof that the actor will disappear in-game.

The source must have an identical DX2 v95/T3SDK no-op package round-trip.
The actor must have original neutral state sentinels, a decodable authored
Location, no outbound object links, no nonzero native tail, an exact source
name/export identity and exactly one unprotected Level membership.
**Other actors may still reference the target**; this is not decoded as a
complete incoming reference graph, and the tool explicitly reports
incoming_references_verified=false.

## Godot UI workflow

1. Open a user-owned, unchanged retail GMP with matching IBD resources.
2. Select exactly **one original** rendered StaticMeshActor in Scene or
   Hierarchy. Do not select a draft copy, a group, or an unlinked BSP mesh.
3. Keep the preview otherwise unchanged: no draft copies, private groups,
   moved originals, brush drafts, class templates or property overrides.
4. Choose **Experimental Unplace Original Prop Save As...**. The editor runs
   read-only Python --check-actor against the exact original GMP SHA
   *before* opening the file chooser.
5. Select a new, isolated output directory and retain the GMP basename.
   Confirm the displayed actor name and original export index.
6. The Python worker rebuilds the candidate from the original GMP, validates
   both UE95 parsers, validates the expected Level-list removal, confirms
   unchanged original actor exports and saves an adjacent
   .dx2ed-prop-unplace.json manifest.
7. A separate verifier regenerates the entire expected candidate from
   the original and compares every output byte. The original GMP and
   installed game files are never touched.

The editor continues displaying the original loaded source scene; the
native unplace does not silently change the private preview. Open the
candidate as a separate test in the original game only after a controlled
backup and path/hash check. Restore the original afterward.

## Command line

All examples require the locally owned original GMP and its exact SHA-256.

Read-only source eligibility:

    python native_editor/package_writer/dx2_actor_unplace_probe.py "C:\DX2\Maps\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256 --actor-export EXPORT_NUMBER --actor-name ORIGINAL_ACTOR_NAME --check-actor

In-memory native writer experiment, **no file written**:

    python native_editor/package_writer/dx2_actor_unplace_probe.py "C:\DX2\Maps\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256 --actor-export EXPORT_NUMBER --actor-name ORIGINAL_ACTOR_NAME

Only to create a new isolated test file, append:

    --output "C:\DX2EdResearch\M1_Example.gmp"

Independently verify that saved candidate without trusting its manifest
hash alone:

    python native_editor/package_writer/dx2_actor_unplace_probe.py "C:\DX2\Maps\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256 --output "C:\DX2EdResearch\M1_Example.gmp" --verify

All successful binary reports explicitly set runtime_game_verified=false
and native_actor_deleted=false. Failure is JSON with status=refused.

## Automated evidence

- Python creates an original, synthetic Ion Storm v95 GMP with one neutral,
  unlinked placed StaticMeshActor and a Level actor list.
- Removes one Level reference ([2,0,1] becomes [2,0] in the fixture),
  leaving the original export count and actor payload identical.
- Cross-checks T3SDK and the independent DX2 package reader, Save As,
  exact whole-file replay, rejection of forged re-hashed output bytes,
  malformed source actor identity, nonneutral state, source/path/hash drift
  and in-game directory targets.
- Godot headless smoke verifies the selected original actor source gate,
  and refusal to ignore draft copies, edited properties, grouped selections,
  changed source transforms or non-static actors.
- Windows prototype bundles both the new Python research worker and the
  GDScript smoke; the prototype doctor checks that the worker can import.
- No original game assets or edited retail GMP files are committed.

## In-game acceptance gates

1. Record exact original and candidate GMP SHA-256 and **active game install**
   path. Test only against a disposable backed-up game copy.
2. Enter the affected level fresh and compare before/after screenshots at
   the same viewpoint. Confirm only the targeted prop disappears.
3. Test player collision at the former location and other nearby props.
4. Leave the level, re-enter it, and independently test save/reload.
5. Restore original, verify its checksum, and confirm retail behavior returns.

Only after these are observed can **this specific actor/map test** be marked
runtime-verified. General deletion requires reverse engineering of incoming
refs, object ownership, gameplay links, collision and save-state semantics.
This patch does not establish any of those.

## Long-term objective

Reconstruct a DX2Ed authoring project comparable in player-facing capability
to T3Ed. A one-actor Level-list unplace is only a narrow first step toward
genuine in-game changes. Native object creation, actor/property editing,
BSP/CSG, collision, IBD cooking, triggers and custom mission packaging remain
independent milestones.
