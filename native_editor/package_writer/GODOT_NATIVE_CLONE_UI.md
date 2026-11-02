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


## Debugged Windows refusal: source actor with active native state (2026-11-02)

The user attempted to clone original `StaticMeshActor__47`, export 1148,
by Unreal translation approximately `(0, -164.58046, 0)`. Their Windows
Godot screenshots show the preview was created and the confirm dialog
opened, but the Python GMP writer raised an uncaught traceback; no new GMP
appeared. The exact original retail WTO Terminal GMP was used to reproduce
the failure offline:

```
StaticMeshActor__47 (export 1148):
  node=-2; state_node=-2; probe_mask=0xffffffffffffffff
  latent_action=926359614; offset=-1
  links=[]; tail=00 00 00 00
  => conservative clone gate rejects nonzero latent_action
```

For comparison, the previously successful collision-tested high-tech
table `StaticMeshActor__611`, export 907, has the same quiet state
sentinels **but latent_action=0** and passes this gate.

The *repair* keeps the original gate unchanged (do not blindly clone
potentially stateful actors). The Python writer now has a read-only
`--check-actor` mode, performed automatically by the Godot editor
**before** the Save As file chooser. If the actor is ineligible, Godot
shows an explanatory refusal dialog instead of accepting a path and
crashing. All rejected CLI checks and exports return machine-readable
JSON with a `reason`, not a Python traceback. The UI also takes the last
exception line if an unforeseen Python import/runtime traceback occurs.
Only fully source-eligible actors are allowed to open Save As.

The new CLI operation example (no map writes):

```powershell
python native_editor/package_writer/dx2_actor_clone_probe.py "C:\\path\\to\\M1_Seattle_Hub_WTOterminal.gmp" --source-sha256 a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa --actor-export 907 --actor-name StaticMeshActor__611 --check-actor
```

These values apply only to the exact verified original map. Original
assets and derived candidate GMPs are not included in the repository.

**Remaining limits:** This does not enable arbitrary original props with
nonzero native state, nor multi-copy serialization. Future research may
test stateful decorations safely with extra checks and isolated runtime
evidence, but the general actor-state restriction remains for now.


## Broader static-prop source gate: experimental neutral clone frame (2026-11-02)

The user demonstrated another blocked source: `StaticMeshActor__316`
(export 814, an upholstered seat) with a screenshot of the correctly
working v2 preflight refusal. An independent audit of the original
`M1_Seattle_Hub_WTOterminal.gmp` showed **554 of 636** StaticMeshActor
exports contain nonzero values in the frame field decoded as
`latent_action`. Many of these four-byte words are recognizable filler,
such as `0xCCCCCCCC`, `0x00000001` or ASCII text fragments. In this
context treating *every* nonzero value as evidence of an active script
is much too restrictive. This does not prove the precise meaning of
every original value, and it does not justify editing source actor state.

### New isolated experimental clone operation

The writer now permits source actors only when **all** of the remaining
frame markers indicate the same neutral state as our previously working
table: `node=-2`, `state_node=-2`,
`probe_mask=0xffffffffffffffff`, `offset=-1`;
original Level membership exactly once; class exactly `StaticMeshActor`;
original authored Location; no object links, no unknown/nonzero native tail,
and no parse errors. Instead of copying the latent field verbatim,
it resets that **one four-byte value only in the newly appended actor**.
The original actor export is preserved byte-for-byte.

After building the candidate, the writer independently reparses both
source and output, confirms that the original exports are byte-identical
apart from Level's actor list, checks the newly appended actor has
latent value 0, and **reverses the new Location translation** to prove
the *entire appended actor payload* matches its original source
except for that precise four-byte reset.

Offline source/identity checks on the original WTO GMP:

- `StaticMeshActor__316`, export **814**, original
  latent value **943267902**; new copy neutralized to zero.
- `StaticMeshActor__47`, export **1148**, original
  latent value **926359614**; new copy neutralized to zero.
- `StaticMeshActor__611`, export **907**, original
  latent value **0**; stays zero and retains the known table clone path.

All three produced candidates that passed source-hash, package
table, Level list, independent parsers and exact new-clone provenance
checks. No source or game installation was changed during those checks.
A full original WTO source scan found **636/636 StaticMeshActor exports
pass the revised *preflight***; only three were used for the additional
end-to-end clone-generation tests. The count is not a runtime-success rate.

### Runtime gate

**This v3 normalization has NOT been tested in Invisible War.**
It is possible that a nonzero serialized field is meaningful for some
actors despite its garbage-like values, or that an otherwise structurally
valid clone can behave incorrectly in-game. Therefore keep this feature
experimental and opt-in. The next user test should duplicate
`StaticMeshActor__316` on a disposable backed-up WTO GMP, inspect
the seat in-game and test player collision, then exit and restore the
original. Do not enable NPCs, interactive archetypes, new mesh resources
or general actor cloning on this evidence alone. Do not redistribute
derived private GMPs or game binaries.


## User confirms v3 clone visually renders in WTO Terminal (2026-11-02)

After testing the v3 build, the user supplied a gameplay screenshot with
**"here it is"**. The image shows a large dark bench-like placed prop
in the right foreground near WTO Terminal fixtures, consistent with the
expanded static prop duplication test. The previous Godot screenshot
identified the attempted seat source as `StaticMeshActor__316`
(export 814); the latest screenshot itself does **not** independently
expose the active GMP SHA/export identity.

**Evidence update:** v3's wider cloning path now has a user-reported,
gameplay-screenshot-supported **visible placed object** in addition to
the earlier v1 high-tech table. This establishes a practical positive
runtime rendering result for a new clone after broadening the source
gate. Do not treat it as proof that all 636 candidate source actors are
safe, nor as proof of collision, physics interaction, save/load
persistence, map re-entry, correct object skin, or runtime state.
Those remain separate verification gates.

Next check on this precise clone: whether Alex is physically blocked by
the new prop, and whether it remains after a fresh level re-entry. Keep
the original game map verified and backed up; no game-derived GMP or
private user screenshot is part of this commit.


## Additional runtime check: v3 duplicated seat/bench blocks Alex (2026-11-02)

After the user supplied the in-game screenshot of the v3 duplicated
bench-like static mesh, they confirmed **"collision is alright / solid."**
This is user-reported **working player collision** for that v3 clone.
Combined with the image, the broader neutral-frame StaticMeshActor
duplication path now has both visual placement and physical blocking
observed in retail DX2. The precise active GMP checksum/export identity
was not captured in this particular report, so preserve that qualification.

This does **not** establish save/load persistence, level re-entry, correct
collision on every mesh, scripted behavior or safe cloning of interactive
archetypes. All 636 eligible original static actors passed source preflight,
not in-game validation. Keep PR draft, preserve original backups, and
prioritize a controlled multi-static-prop writer + Godot integration next.
