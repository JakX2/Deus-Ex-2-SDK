# DX2Ed P107: read-only original door/vending candidate discovery

**Scope:** source-grounded investigation only. Not an interactive actor editor,
new-actor spawner, door compiler, script linker, or gameplay-runtime proof.

## What this adds

The original GMP actor decoder already reads placed source actors, their
Source/StaticMesh identity, tagged properties and original GameSys fields.
This command scans **that original parsed actor inventory** for conservative
name/mesh/class matches related to doors and vending machines.

It reports original native export numbers, actor class, original mesh name,
original map positions, matching substrings and decoded GameSys property
**IDs/names**. It also lists at most five original actors within 512 Unreal
units as **spatial clues only**, not decoded links, ownership, activation
targets or interactions. An unresolved serialized TriggerScript field is
indicated but is **never** interpreted as a verified script binding.

The report is source-hash-bound. Original GMP is re-hashed after parsing,
mismatched parser source identity is refused, unknown identities are not
invented, and no game assets are redistributed. The tool does not create or
patch actors, GMPs, IBDs, TSDs, collision, scripts, or GameSys data.

## Using it on Windows

From the root of the complete repository or the bundled source-only
Windows prototype (requires its bundled Python dependency setup):

~~~powershell
py -3.11 .\native_editor\godot_editor\backend\dx2_interactive_actor_candidates.py --map "D:\DX2\Content\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --kind both
~~~

To label more source GameSys fields when a compatible original System
directory or ZIP is available:

~~~powershell
py -3.11 .\native_editor\godot_editor\backend\dx2_interactive_actor_candidates.py --map "D:\DX2\Content\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --system "D:\DX2\System" --kind door --limit 50 --output "D:\DX2EdPrivate\wto-door-candidates.json"
~~~

The parent directory of a private JSON output must already exist and be
**outside the retail Maps directory**; existing output is never overwritten.
Omit --output to print JSON to the terminal without writing any report.

The command allows category values **door**, **vending**, or **both**.
Its English token heuristics may fail to identify actors whose source
class/name/mesh has only an opaque numeric name. Missing a candidate
does not establish that a map has no interactive object.

## Evidence gates before creating working gameplay objects

1. **Identify** a source actor, original export ID and exact map SHA.
2. **Decode** its authoritative class/parent and native state, script,
   GameSys and object-link encoding (not just its mesh or nearby actors).
3. **Compare** original paired interactive objects to determine what
   changes when the game sets an open/closed or purchase/idle state.
4. **Validate** an isolated native clone only if the full dependency
   closure, package writer and runtime behavior are independently tested.

The existing StaticMeshActor table duplication and reported player
collision cannot be generalized to doors, vending machines, AI or other
interactive actors. The source-specific candidate report always declares
native_interactive_clone_supported=false and game_runtime_verified=false.

## Asset-free regression

~~~powershell
py -3.11 -m unittest native_editor.tests.test_dx2_interactive_actor_candidates -v
~~~

Tests verify classification, original field provenance, proximity as
non-links, strict source hash rechecking, output isolation, non-overwrite,
limit handling, malformed data refusal, and no original-map mutation. All
test maps/actors are fabricated.
