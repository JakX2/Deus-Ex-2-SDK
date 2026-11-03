# DX2Ed native Environment research: lights, sound zones and particles

**2026-11-02.** This is a source-backed experimental feature for the
user's own Deus Ex: Invisible War files. It does not redistribute assets
or claim that a sound or light entity has been spawned in retail DX2.

## Source files and verifiable layout

The original WTO Terminal map
`M1_Seattle_Hub_WTOterminal.gmp` had SHA-256
`a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa`.
Original DX2 `System.zip` provides native UnrealScript declarations in
`Engine.d2u` and `DX2Gamesys.d2u`. Independently rebuilt
`dx2catalog.build_catalog` discovers **1,130** GameSys property IDs
across 2,822 source text buffers, with zero conflicting names.
This is game-file evidence, not a guess based on Thief's editor.

Source map actor inventory:
- **25** placed class `Light` actors.
- **20** placed class `ZoneProperties` actors (21 exports in package
  enumeration; one is not in the read-only scene-actor list).
- **4** placed class `Emitter` actors. They are particle emitters,
  **not** audio/sound entities.
- Additional `D_*` gameplay actors may have other audio behavior;
  this audit does not claim all sound sources are ZoneProperties.

Confirmed original GameSys names:
- 116 `LightColor` (struct with `LightBrightness`,
  `LightHue`, `LightSaturation`).
- 118 `LightShape` (struct with `LightRadius`,
  `LightPeriod`, `LightCone`).
- 1586 `EmissiveScale` (float).
- 1487 `bLightOn` (bool; when explicitly serialized).
- 1287 `StreamSchema1` (string on `Engine.ZoneProperties`).
- 1286 `StreamSchema2` (string on `Engine.ZoneProperties`).
- 1467 `NonStreamSchema1` (string on `Engine.ZoneProperties`).

Representative original WTO `ZoneProperties__3` export 144:
`StreamSchema1 = SeattleWTOTerminal`,
`StreamSchema2 = HubWTO_SmallRooms`,
`NonStreamSchema1 = (Silence)`.
Other zones use `HubWTO_LargeRooms`,
`HubWTO_RandomInAdj`, `HubWTO_FlybyInside` and variants.
These are genuine source string fields, but the contents still
depend on the engine's audio schema lookup and runtime zone activation.

Original `System/Default.ini` recognizes
`SoundSchemas=sch|Sounds*`,
`SoundSchemaMetafiles=csc|Sounds`,
and `WaveSound=ogg;wav|Sounds*`.
This confirms that the separately supplied `csc-tool` can serve
as a reference for DX2 sound formats in addition to Thief 3.
We have not executed that third-party EXE or published it.

## New Godot Environment tab (v7)

The **Environment** tab presents native original actor instances:
`Light`, `ZoneProperties` and `Emitter` are explicitly distinct.
Clicking an actor displays its original source export, Unreal XYZ and
GameSys fields, and the actor is selected in the normal Inspector.
Press **F** to focus its source position even though it may have no
GLB render mesh. These controls never create a light or sound actor.

### Experimental existing-zone sound editing

The new selector appears only for original `ZoneProperties` actors
with a source-authored string field having **at least one different,
already present value for the same property ID in that map**.
The UI cannot invent a script name. It offers an
**Experimental Zone Sound Save As...** button:

1. Open your original, hash-matched GMP (and its imported metadata).
2. Choose **Environment** tab and select an original
   `ZoneProperties` actor.
3. Select a stream/nonstream field and another source-observed
   schema name from its dropdown.
4. Click **Experimental Zone Sound Save As...** and choose a fresh,
   isolated research folder, retaining the exact original GMP basename.
5. Confirm. This calls `dx2_zone_sound_probe.py` and writes a new
   GMP plus `.dx2ed-sound-zone.json` manifest. Original game files
   are never written or installed automatically.

Writer revalidates the exact original source SHA-256, source
actor/export/class, Level membership, only one non-runtime original
string block, current expected field value, and the replacement's
presence in another original zone **using the same property ID**.
It then rewrites one source actor through the MIT T3SDK serializer,
reparses through independent DX2 and T3SDK readers, verifies that
all other export payloads, GUID, package tables and Level references
remain unchanged, and **reverses the edit** to check exact original
actor bytes. It refuses overwriting any existing result or writing
inside the game's `Content/DX2/Maps` installation folder.

The source-bound experiment on the original WTO GMP successfully
replaced the **StreamSchema2** field from `HubWTO_SmallRooms` to
`HubWTO_LargeRooms` *in memory*, then restored/verifed actor
binary provenance. An alternative `NonStreamSchema1` test also
passed its package verification. No gameplay changes were
installed during these checks.

**Runtime limits:** Newly creating a light, building a sound point
emitter, changing stream schemas to names absent from the original
map, and compiling new `.csc` sound blocks are **not implemented**.
New light creation must account for original
`PhysicsVolume`/`Region` and possibly zone-specific state. A
ZoneProperties string edit is NOT proof that the replacement schema
will audibly play at runtime. Test in a backed-up game copy and
re-enter the map freshly before considering any change validated.

## Automated checks

Source-only Python regression uses synthetic v95 maps with two
ZoneProperties actors containing alternate string field values.
It verifies exact payload reversal, unrelated export preservation,
independent reparse, strict refusal of new/unrecognized schema
names, source SHA pinning, no in-place writes, output exclusivity and
manifest hash.

Godot headless smoke verifies three original environment actor
classifications, original light properties, zone schema string
inspection, audio picker refusal on particle emitters, and read-only
actor location focus. The editor's older experimental StaticMesh
Save As paths remain unchanged.

## Next research priorities

1. Identify a *safe original light source* and the exact required
   zone/Region and PhysicsVolume data when placing it elsewhere.
2. Build **in-memory only** light actor duplication and independent
   original package verification; first runtime candidate only after
   native state and zone references are proven.
3. Extract source sound-schema identifiers from the user's locally
   owned `.csc` data with safe independent parsers, cross-check
   the third-party tool's known syntax and file descriptions, and
   identify DX2 point-sound actor conventions.
4. Only after runtime proof, add *new light* and *sound emitter*
   entries to DX2Ed's general Add Entity browser, with isolated
   GMP writes and schema/zone validation.
