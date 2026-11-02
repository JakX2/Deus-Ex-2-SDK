# DX2Ed: native StaticMeshActor duplication (experimental)

**Status:** source-only prototype on draft PR #5. Synthetic asset-free
package tests have passed. A newly appended retail DX2 actor has NOT yet
been verified in-game. The code deliberately does not write into game
installations, does not redistribute GMPs, and does not enable the Godot
visual duplication button as a native writer yet.

## What this does

Clone one existing, locally authored `StaticMeshActor` of the current GMP:
- verifies source SHA-256, original actor name and one-based export index;
- requires the actor to be present exactly once in the Level actor list
  beyond the first two protected entries;
- refuses state-active actors, object link lists, opaque native tails,
  missing tagged Location, unsupported class and abnormal coordinates;
- copies the existing export's original data and class identity;
- appends one uniquely named export and adds it once to the Level actor list;
- edits only the clone's existing tagged FVector Location, in **Unreal units**;
- independently reparses resulting GMP and checks every pre-existing export
  except the Level is byte-identical, plus T3SDK package integrity checks;
- writes only to a separate output directory with same GMP filename,
  exclusive creation, and a SHA-256 manifest.

This does **not** build BSP, modify collision, update navmeshes, write IBD
resources, create new mesh definitions, or guarantee saved-game persistence.
Keep the real retail GMP original intact.

## First use

Extract the source-only archive while preserving its folders, or run from
the full repository checkout. Requires Python 3.11+. Original retail file
is supplied by the owner and is NOT bundled.

From the unpacked bundle's root, first list conservative candidate props:

```powershell
python native_editor/package_writer/dx2_actor_clone_probe.py "C:\GOG Games\Deus Ex - Invisible War\Content\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --source-sha256 a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa --list
```

Pick an `actor` and `export` from the returned read-only candidate list.
The following is a **template** only; replace placeholders with the
literal export number and name emitted by `--list`:

```powershell
python native_editor/package_writer/dx2_actor_clone_probe.py "C:\GOG Games\Deus Ex - Invisible War\Content\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --source-sha256 a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa --actor-export EXPORT_NUMBER --actor-name ACTOR_NAME --dx 100 --dy 0 --dz 0
```

That second command is **in-memory only**; verify the reported
`new_export_count` and `level_actor_count_after`. Then, only when the
report passes, append e.g.
`--output "C:\DX2EdResearch\M1_Seattle_Hub_WTOterminal.gmp"`.
The output directory must not be inside any Content/DX2/Maps game directory;
the output file and manifest must not already exist.

To test in-game later, manually back up the original GMP and confirm with
Process Monitor that DX2 actually **reads the modified map** in the intended
installation. Test from a fresh level entry and restore original afterward.
The prior test-build incident showed that an EXE's install path alone does
not prove which map it loads.

**Do not merge** this research prototype merely because synthetic CI passes.
Before integrating the Godot Duplicate button, verify a single copied static
prop at the correct position in the game, its collision, saved-game behavior,
and clean original-map restoration. Cloning actors that reference specific
object links or scripts is still explicitly blocked.
