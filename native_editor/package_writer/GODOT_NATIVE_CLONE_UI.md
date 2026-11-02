# Experimental DX2Ed native Duplicate Save As in Godot

**Status:** development branch, draft PR #5. The one-actor standalone
`dx2_actor_clone_probe.py` previously created the user's first visible and
player-blocking extra table in WTO Terminal. This new UI connection passed
headless Godot and synthetic Python tests. **The integrated Godot → GMP
workflow has not yet been tested in Windows/game.**

## Use with the source-only editor test bundle

Requires Godot 4.3+ (standard edition), Python 3.11+, and your own retail DX2
game files. The bundle includes no proprietary GMPs, IBDs or game binaries.

1. Open `native_editor/godot_editor/project.godot` in Godot and press F5.
2. **Open DX2 map (.gmp)** and select an **unchanged original** GMP.
3. Click a rendered original static mesh, e.g. an existing table.
4. Press the ordinary **Duplicate** button (this creates a *preview draft*).
5. Select the new draft copy and move it using **Move W** / the transform
   gizmo. The new copy needs an actual position offset.
6. Press **Experimental native Duplicate Save As...**.
7. Choose an **empty, isolated research directory**, retaining exactly
   the original GMP filename. Confirm the actor/export and Unreal delta.
8. The Python worker independently checks the original hash, actor
   class/state, Level references and appended export. It creates a
   candidate GMP and `.dx2ed-prop-clone.json` manifest without touching
   the source or any `Content/DX2/Maps` installation directory.

The new action is **not** the older `Experimental GMP Save As...` button,
which remains strictly **existing-actor translation only**.

## Deliberate constraints for the first UI version

- Exactly ONE original `StaticMeshActor` preview copy.
- Source must have an original, existing serialized Location property.
- Translation only, no rotation, scaling, multiple copied actors, changed
  originals, edited GameSys properties, brush drafts or class-template
  placements. The UI refuses to silently omit other draft modifications.
- Godot metres are converted with `0.01905` metres per Unreal unit,
  swapping Godot Y/Z back to Unreal Z/Y.
- Source GMP SHA must match the cached original actor metadata.
- The underlying writer refuses active native/script actor state, linked
  actors, opaque native tails and unverified source object identity.
- The writer refuses output to a game Maps directory and any overwrite.
- This first implementation is **one duplicate per output GMP**, not
  multi-object editing, asset spawning, scripting or BSP rebuilding.

To play-test, first create a separate verified backup of the original
retail GMP. Install a candidate **only through an explicitly controlled
manual process** after the game's true map load path has been established.
Restore original after testing. If there is a failed/no-visible experiment,
confirm the selected disk SHA and actual file reads before changing code.

Do not publish proprietary modified GMPs as part of this SDK.
