# DX2Ed v0.60: combined native static-prop authoring plan

**Checkpoint:** 2026-11-10. **Evidence:** asset-free binary and Godot 4.3 smoke tests. **Retail runtime:** not yet independently tested for the combined operation.

## Player-facing objective

DX2Ed aims to become an Invisible War mission editor with feature parity to
T3Ed where the original game format permits it. Player-visible, playable
modified levels are the acceptance standard. A 3D preview alone is not a mod.

Earlier native research paths wrote one translated original, one/multiple
clones or one unplaced StaticMeshActor into separate experimental GMPs. v0.60
creates ONE candidate GMP combining up to 8 translations, 8 duplicate
exports and 8 original Level-list unplacements (maximum 16 edits in total).
At least two distinct change kinds are required at this research stage.

This is a narrow, source-verified StaticMeshActor operation, not a general
"Save Map" button. Rotations, scales, animation, new mesh resources, object
links, NPCs, scripts, environmental lighting, GameSys, geometry, BSP, MOPP,
IBD, actor export deletion and collision baking are NOT implemented here.

## Godot workflow

1. Open a user-owned, unchanged retail GMP through **Open DX2 map** and
   import the matching IBD resources as usual.
2. Move original rendered **StaticMeshActor** objects, without rotating
   or scaling them. Ordinary preview transforms still remain private until
   export.
3. Make new preview copies using **Duplicate**, then move each copy.
   The clone will receive a new native export with a neutralized latent
   field. All original actor exports remain source-authenticated.
4. Optionally select an original, unchanged decorative StaticMeshActor
   and choose **Stage/Unstage original prop**. Staged removals stay
   **visible in the editor**; the stage is a temporary Level-list intent,
   NOT an actual object deletion or collision preview. Select the object
   again and click the same button to unstage, or use
   **Clear unplace stages** to clear all temporary staging.
5. Choose **Experimental Combined Save As...** after creating at least
   two kinds of the above edits. This workflow refuses non-static sources,
   draft groups, unsupported transforms, pending actor property edits,
   draft brushes, class templates or over-limit plans rather than
   silently excluding them.
6. The editor checks the exact original GMP SHA-256 and authenticates
   the native source class/name/export using a read-only preflight
   before opening the Save As chooser.
7. Choose a **new isolated directory**, retaining the same GMP basename.
   The confirmation dialog lists exact moved, copied and unplaced
   counts. Confirm to serialize the validated plan into a private
   temporary JSON file and run the Python worker.
8. The worker verifies the source, writes the isolated GMP and manifest,
   reconstructs the entire expected candidate from the unchanged source
   and confirms that **every output byte** matches the original-pinned
   edit plan. The original game installation is never modified.

Successful Save As clears temporary unplace stages but does **not**
silently alter the imported preview scene. The original GMP remains the
source of truth until a separate game/test copy is opened.

## Standalone Python research writer

Use native_editor/package_writer/dx2_native_prop_plan.py with Python
3.11+. All input maps must be user-owned original DX2 v95 GMP files.

The exact JSON plan schema is:

    {
      "schema": "DX2Ed-experimental-native-prop-change-plan-v1",
      "moves": [
        {"actor": "StaticMeshActor__1", "export": 1,
         "delta": [50.0, 0.0, 0.0]}
      ],
      "copies": [
        {"actor": "StaticMeshActor__2", "export": 12,
         "delta": [0.0, 100.0, 0.0]}
      ],
      "unplaces": [
        {"actor": "StaticMeshActor__3", "export": 15}
      ]
    }

This is only a shape example. Actor names and one-based native export
numbers must come from the actual unchanged source and must pass the
eligibility gate. Coordinates use original Unreal X/Y/Z units. Duplicate
sources may be original actors that are also moved or unplaced, but
moving and unplacing the same source actor in one transaction is refused.
Clones derive from the source actor's ORIGINAL native payload, not from a
moved preview.

In-memory experiment only, with no GMP output:

    python native_editor/package_writer/dx2_native_prop_plan.py "C:\DX2\Maps\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256 --plan-json "C:\DX2EdResearch\change-plan.json"

Generate an isolated test candidate:

    python native_editor/package_writer/dx2_native_prop_plan.py "C:\DX2\Maps\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256 --plan-json "C:\DX2EdResearch\change-plan.json" --output "C:\DX2EdResearch\Output\M1_Example.gmp"

Independent re-read and whole-file replay:

    python native_editor/package_writer/dx2_native_prop_plan.py "C:\DX2\Maps\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256 --verify --output "C:\DX2EdResearch\Output\M1_Example.gmp"

The saved manifest is located beside the candidate:
M1_Example.dx2ed-native-prop-plan.json.

## Independent verification boundaries

The new writer requires:
- exact source SHA, version and DX2/T3SDK byte-identical original no-op;
- source actor class exactly StaticMeshActor, original authored Location,
  original Level membership exactly once and permitted native frame;
- no outbound object links or unknown nonzero actor native tail;
- unique source name/index, valid finite nonzero translation <=4096
  Unreal units per component, and new coordinate inside safe bounds;
- exclusively changed existing actor Location payloads (reverse to
  original bytes for exact proof), new neutral-clone payloads and the
  original Level list membership;
- unchanged source actor exports otherwise, stable GUID and import
  tables, expected name/export counts, and strict output path isolation;
- whole-file **byte-for-byte** replay from the original GMP during
  independent post-save verification. Updating a forged output hash alone
  cannot bypass this check.

Native original actor unplacement removes **only the Level reference**.
The original export remains serialized. The checker does NOT prove
there are no incoming script/object references or that the actor
vanishes, loses collision, or remains absent after a loaded save game.
Every report sets runtime_game_verified=false,
incoming_references_verified=false and
native_actor_exports_deleted=false. No code installs or distributes
retail game assets.

## Next acceptance tests

Using a disposable backed-up installation and recorded original/candidate
SHA-256 values:

1. Apply one harmless moved static prop + one clone in the same map,
   confirm both render and have expected player collision.
2. Apply one clone + one unplacement, then confirm the target original
   disappears and the clone remains.
3. Repeat at fresh level re-entry, save/reload and after returning from
   another map. Confirm unrelated original props remain unchanged.
4. Restore the original GMP, confirm original SHA-256 and original
   runtime appearance.
5. Only then mark specific tested operation/map combinations as
   retail-runtime validated, and consider increasing scope.

The long-term work remains IBD resource reconstruction, safe native
object class creation, references/links/scripts and BSP/collision baking
for player-authored levels.
