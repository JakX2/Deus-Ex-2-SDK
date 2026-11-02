# DX2Ed v8: original native Light dependencies and visual-only preview

Source verification date: 2026-11-02. This stage **does not** enable
native Light creation. It adds evidence and a safe, explicitly non-native
visual experimentation path, informed by the real original retail DX2 map.

## Original WTO Terminal evidence

Original GMP:
`M1_Seattle_Hub_WTOterminal.gmp`,
SHA-256 `a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa`.

- **25 original placed `Light` actors**, spread over **12 distinct**
  `Region.ZoneNumberLow` values: 3, 4, 5, 7, 8, 9, 10,
  12, 13, 14, 15 and 17.
- Every original Light references **`DefaultPhysicsVolume__6`**
  from the native tagged `PhysicsVolume` property (map export **3**).
- Every original Light references **`LevelInfo__0`** from
  tagged `Level` and the `Zone` within tagged
  `Region` (map export **2**).
- All 25 have a tagged `Region` struct with numeric
  `iLeaf` and `ZoneNumberLow`. The values vary across actors
  and must not be inferred from the original Light name, nearby
  mesh, or GameSys light radius.
- All 25 have native state frame `node = -8`,
  `state_node = -8`, `offset = -1`,
  `probe_mask = 0xffffffffffffffff`.
  There are **17 different** original `latent_action` values
  among these sources, including large nonzero values.
- All 25 have a four-byte zero native tail, no native
  object link list, and tagged `bDynamicLight = true`
  and `bSentSpawnNotification = true`.
- **23** have the tagged keys `Location`, `PhysicsVolume`,
  `bDynamicLight`, `bSentSpawnNotification`,
  `Region`, `Level`; **2** additionally have `Rotation`.

**Implication:** Existing static-prop cloning normalizes a very
specific *different* source actor state frame with `node = -2`
and `state_node = -2`, and permits translation without
region recalculation. That policy **cannot be generalized** to
`Light` actors, which have `-8/-8` native frames and
location-dependent BSP leaf/zone metadata.

Cloning a light to a new position while blindly retaining
`Region.iLeaf` and `ZoneNumberLow` risks an invalid renderer
or runtime spatial/lighting state, even if the result is a
well-formed GMP package.

## New independent read-only backend

`native_editor/package_writer/dx2_light_dependency_audit.py`

Example, with a user's own original map:

```powershell
python native_editor/package_writer/dx2_light_dependency_audit.py "C:\\Research\\M1_Seattle_Hub_WTOterminal.gmp" --source-sha256 a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa
```

Optional `--actor-export 132` limits the report to the original
`Light__3`. Optional `--output "C:\\Research\\light-audit.json"`
writes a new JSON report but refuses an existing output and refuses
writing into `Content/DX2/Maps`.

The backend checks an exact SHA-256 of the *original GMP*, a
byte-identical no-op writer roundtrip, two independent original
package readers, actual `Light` export/class identity,
single original Level membership, state frame, finite coordinates,
existing map-local `LevelInfo` and `DefaultPhysicsVolume`
references, and explicit BSP leaf/zone fields. It checks the
source hash again before completing. It **cannot** reconstruct a
new position's BSP leaf/zone or prove new actor state safety.

All results always declare:
`native_light_spawn_enabled=false`,
`region_for_new_position_verified=false`, and
`state_frame_clone_verified=false`.

A source-free synthetic fixture unit test constructs its own Ion
Storm v95 package, adds valid `PointRegion`, `Level`, and
`PhysicsVolume` tagged references, and checks the report and
strict failure gates. Proprietary map bytes are excluded from GitHub.

## New Godot Environment tab controls

1. Select a source `Light` in Environment.
2. Its details now expose original `PhysicsVolume`,
   `Region` (zone, leaf and zone number), `Level`,
   `bDynamicLight` and `bSentSpawnNotification`.
3. **Audit original Light dependencies** launches the SHA-pinned
   source-only scanner on a background thread, verifies the selected
   original export, and presents native frame/region evidence.
4. **Preview selected Light at camera target** places an
   **editor-only Godot `OmniLight3D`** node *outside*
   the imported GLB, native actor list and native draft-state
   dictionary. Brightness, hue, saturation, and range are
   **approximate visualization mappings only** and are not
   validated against DX2's lighting engine.
5. **Clear temporary Light previews** removes the extras; opening
   another map automatically clears them. At most eight can coexist.

These preview-only lights are **never serialized to a GMP**,
never modify original Light actors and never make the native
`StaticMeshActor` exporter accept an invalid class.

## Validation and next gate

- Synthetic Python source-only tests check positive and invalid
  Light dependency maps, read-only output, source SHA pinning and
  unsafe field rejection.
- Godot headless smoke checks temporary `OmniLight3D` instance,
  parent relationship, location, source-provenance metadata,
  draft isolation and cleanup.
- Next crucial research task: reconstruct *BSP point-to-leaf*
  lookup from actual DX2 model nodes, then independently
  validate it against all 25 original Light positions and
  their stored `Region.iLeaf` /`ZoneNumberLow`.
  **Even after solving BSP**, frame initialization and retail
  runtime testing remain separate requirements.
- Other pending milestones: new positional sound emitters
  (distinct from `Emitter` particle actors and
  `ZoneProperties` ambient sound fields); BSP brush compilation.

Do not commit the user's original GMP, native reports containing
proprietary source payloads, or third-party EXEs to GitHub.
