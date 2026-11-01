# DX2Ed Native Editor 0.2: direct GMP loading (experimental)

**A Godot 4 based, read-only 3D map and actor viewer for Deus Ex: Invisible War.** This project uses the original map files from your own game installation, not bundled retail data.

## What's new since 0.1

The new **Open DX2 map (.gmp)** button automatically finds the corresponding mission .ibd and shared bundles, runs the existing DX2Ed parser/exporter, and loads both the textured scene and actor metadata. You no longer need to export a GLB and actors.json manually. Conversion runs in a Python worker thread and creates a content-hashed cache outside the game installation.

The previous **Open exported GLB**, **Load actors.json**, and **Load demo cubes** features remain available. The left-side actor list and read-only property inspector are retained.

## Install and test (Windows)

1. Install **Godot 4.3 or newer, Standard edition** and **Python 3.9 or newer**. Ensure the `python` or `py -3` command is available.
2. Import `native_editor/godot_editor/project.godot` in the Godot Project Manager, then press **F5**.
3. Press **Open DX2 map (.gmp)** and select a map in `Deus Ex Invisible War/Content/DX2/Maps`, such as `M3_Germany_Trier.gmp`.
4. DX2Ed locates the matching IBD, builds a private GLB cache, and generates actors.json internally. On first load this may take some time.
5. Once the viewport appears, select actors in the list or click the meshes; use **Frame scene** and **Focus actor** to navigate.
6. Open the map again to verify **cached** appears in the status line. Changing the map or its resource bundles invalidates the cache.

If automatic resource lookup fails, select **IBD override...** first, then choose your map.

## Command-line diagnostics

```powershell
cd native_editor\godot_editor
python .\backend\dx2_native_backend.py --map "C:\path\to\Maps\M3_Germany_Trier.gmp" --output-root "$env:LOCALAPPDATA\DX2EdCache" --inspect
python .\backend\dx2_native_backend.py --map "C:\path\to\Maps\M3_Germany_Trier.gmp" --output-root "$env:LOCALAPPDATA\DX2EdCache"
```

The backend uses only the Python standard library. Run fixture-free tests with `python -m unittest discover -s native_editor/tests -v` from repository root.

## Validation

The Python backend passed tests covering cache invalidation, safe output paths, regeneration, and automatic map/bundle lookup. A real Penthouse Upper load produced **705 actor records** and **455 static meshes** in an isolated environment without shared graphics bundles, reporting 16 missing mesh resources. Full installations should provide shared bundles, but material coverage varies by level.

The previous Godot v0.1 viewer was confirmed rendering a real Trier GLB on Windows; **the direct-GMP load button added in v0.2 has not yet been Windows-tested**.

## Important limits

- This is an **experimental viewer, not a complete map editor**.
- **Read-only:** never patches or replaces your .gmp/.ibd originals.
- GLB is a visualization cache, not a reversible game map format.
- Gameplay script editing and safe GMP writing are still separate research utilities.
- Missing DX2 materials and effects may be approximated or left unresolved.
- No game assets, proprietary binaries or copyrighted editor executables are distributed.

See [Architecture](ARCHITECTURE.md) for the native file-loading pipeline.


## Seattle Club geometry diagnosis (0.2.1)

A new **Copy mesh info** button records the original DX2 actor/mesh identity,
UE location and Pitch/Yaw/Roll, plus Godot world bounds. Click the geometry
that appears misplaced, then copy and share this report. When a click hits BSP
or otherwise unlinked render geometry, the inspector still reports the mesh
node. Selection now prioritizes real actor meshes over broad BSP bounding boxes.

See [Seattle Club findings](Seattle_Club_Transform_Findings.md).
The editor remains read-only; there is **no global geometry rotation fix** in
this release. Godot visual runtime tests remain to be done on Windows.

## Experimental 0.2.2: exact geometry picking (development branch)

The Seattle Club diagnostic picker now tests **rendered triangles** after a fast
ray/AABB broad-phase check. This prevents a large BSP box or a hollow mesh's
bounding box from stealing clicks on nearby props. The nearest surface wins;
an actor and BSP surface at effectively the same distance prefer the actor.
The original actor-name mapping and **Copy mesh info** feature remain in place.

The copied report now includes a "Pick method: rendered triangle" line, the
Godot-space hit position and distance. Vertex faces are cached by imported mesh
resource and discarded on map reload; all changes are in the read-only viewer.

This branch also fixes the diagnostic's mismatch with retail Actor Explorer
JSON, whose `mesh` field is a string, `mesh_bounds` is a separate field, and
`location` is an [x, y, z] array.

### Validation (requires Godot 4.3 or newer)

Run the asset-free headless smoke test from the **repository root**:

```powershell
godot --headless --path native_editor/godot_editor --script res://tests/smoke_triangle_picking.gd
```

The script checks solid triangle hits, rotated/scaled hits, an AABB false
positive, and the Actor Explorer JSON field layout. An output line beginning
`DX2Ed triangle picking smoke: PASS` is expected on success.

Then run the Python source/backend tests:

```powershell
python -m unittest discover -s native_editor/tests -v
```

Finally, open `M1_Seattle_Club.gmp` in the graphical viewer and click a
suspicious object. Use **Copy mesh info** to inspect its identity, transform,
world bounds, and exact surface hit. Compare prop selection against the same
spot on the retail map.

**Limits:** this is a source-level change awaiting the above Godot runtime and
Windows/Seattle Club checks. Meshes without readable triangle faces cannot be
picked by bounding box as a substitute; transparent visual effects and gameplay
visibility are not yet modeled. This does not modify any original GMP/IBD.


## Experimental 0.2.3: open original Seattle Club ZIPs directly

The development branch now includes a read-only staging workflow for the three
user-owned ZIPs: club, shared map resources, and optional System packages.
Only GMP/IBD files from the first two ZIPs and D2U/INI/INT files from System
are copied into a private, content-hashed cache under Godot's user data folder.
EXE, DLL, shader bytecode, and other unrelated files are **not** extracted.
The game ZIPs and installed game remain untouched.

In the Godot viewer, use the second toolbar row in this order:

1. **Shared ZIP...**: select the archive containing Kernel_GFXALL.ibd and MainMenu_GFXALL.ibd
2. **System ZIP... (optional)**: select the retail System archive for richer actor metadata
3. **Open DX2 map ZIP...**: select a mission archive containing exactly one .gmp and one .ibd, such as club(1).zip or shub.zip

The viewer stages these resources with Python, then invokes its existing
direct-GMP importer. It does not upload game assets or write to the source ZIPs.
System metadata is passed to the backend with --system when supplied.

To run the ZIP staging utility independently from the repository root:

~~~powershell
python native_editor/godot_editor/backend/dx2_zip_stage.py --club "C:\path\to\club(1).zip" --maps "C:\path\to\maps(1).zip" --system "C:\path\to\System(2).zip" --output-root "$env:LOCALAPPDATA\DX2EdStaging"
~~~

The output is JSON with the staged map and System paths; pass them to
dx2_native_backend.py using --map, --system, and --output-root. Without the
optional System ZIP, omit --system.

**Validation:** source/backend unit tests run on GitHub Actions with synthetic
fixtures. Source ZIP path traversal, symlinks, duplicate paths, missing required
shared bundles, oversized entries and cache tampering are rejected. Initial
archive layout checks used the user's actual Seattle Club/Maps/System ZIPs,
but the full native Godot GUI workflow still requires Windows runtime testing.
The imported actor rotations, original shaders and gameplay behaviors remain
provisional, not corrected by ZIP staging.


## Experimental 0.2.5: reversible stair comparison and prop drafts

The editor now defaults to the **uncorrected original map transform preview**.
Enable **Experimental stair Roll** in the ZIP toolbar to rebuild Seattle Club
using the evidence-based, map-specific stair rotation hypothesis. Disable it
to compare against the baseline. The preview modes have distinct content cache
keys; neither modifies any GMP/IBD files. This is NOT a confirmed engine fix.

A third toolbar row introduces **Prop drafts**, a first step toward actual
map editing. Select a rendered static-mesh actor in the list or viewport and
use:

- **Duplicate** to create another preview instance of that source prop.
- **X± / Y± / Z±** to move the selected original prop or new copy. The
  SpinBox controls the step size in **Godot world metres** (default 0.25).
- **Turn ±15°** to rotate the selected prop around the viewer's Y axis.
- **Reset / Delete copy** to restore an original prop to its exported pose,
  or delete the selected preview copy.
- **Save draft / Load draft** to store and restore the changes.

Draft files are JSON in the Godot user directory under
\`user://prop_drafts/<sha256-of-source-cache-path>.json\`. They store the
original mesh actor names, preview copies, and Godot-space transforms.
Saved drafts are reloaded when opening the same GLB cache and are private to
that cache. The viewer does **not** write or patch a game-compatible GMP, and
the duplicated prop has no gameplay script, physics or collision. BSP brush
modelling is a separate, future milestone.

These changes are covered by the synthetic Godot headless smoke test on CI,
including moving a prop, cloning it, rotating it, saving a draft and restoring
the clone. The Seattle Club GPU/Windows visual result still requires manual
comparison with the original game.

## 0.2.6: per-actor material skins and missing-texture diagnostics

Static mesh actors may request a named **Skin** in original Gamesys property
56 (Property_0038). Previously, DX2Ed always used the mesh resource's first
skin for every placed instance, so actors sharing one mesh could render with
the wrong material. The exporter now matches the actor's requested skin against
the IBD resource's named variants, case-insensitively, and caches separate glTF
mesh definitions **per selected skin**. Original map transforms are unchanged.

If a requested skin is not present in the supplied mesh resource, the exporter
uses the first available skin and explicitly records requested_skin_missing.
The JSON scene report includes actor_skin_selections and
actor_skin_variant_missing, with per-material statuses such as textured_diffuse,
missing_material_record, and missing_diffuse_texture. The Godot **Copy mesh info**
inspector shows the source map filename, requested and exported skin, and each
material's resolution status.

The native conversion cache version has changed, so opening the map again
regenerates the GLB. An unavailable skin variant or diffuse texture cannot be
reconstructed from missing resources, but its absence can now be diagnosed.

The screenshot of StaticMeshActor__130 (export 1526, 1Hub_city_stair1,
requested skin Tan Stones) does not match the uploaded M1_Seattle_Club.gmp,
where StaticMeshActor__130 is export 421 (M1PENT_dframe-roof). Confirm the map
filename before treating them as the same actor. No game assets are distributed.

## 0.2.7: Seattle Hub original materials verified

We examined the privately supplied shub.zip. Seattle Hub actor
StaticMeshActor__130 (export 1526) requests the **Tan Stones** variant of
1Hub_city_stair1. This mesh has four skins. Its requested Tan Stones skin uses
M1HUB_wall and M1HUB-needleconc1dark, resolving to the original wall and
m1hub-needleconc1 DXT1 diffuse images (both present in m1_hub.ibd).

Previously the exporter selected the default variant for every placed
instance, which could produce a pale/untextured-looking stair. The per-actor
skin fix corrects that selection. A new experiment with the real source files
is still needed to confirm the visual result in Godot.

The ZIP import button is now **Open DX2 map ZIP...** and automatically
recognizes a single GMP/mission IBD pair. Choose maps(1).zip as Shared ZIP,
optionally System(2).zip, then shub.zip. Ambiguous mission ZIPs are rejected
instead of silently picking the wrong map.

See Seattle_Hub_Skin_Findings.md for the original actor identifier, resource
chain and limits. All publicly committed tests use synthetic fixtures.

## Experimental 0.2.8: Unity-style 3D navigation and transform gizmos

The new viewport controls are designed to feel familiar to Unity scene users:

- **Hold right mouse button** over the 3D viewport and move the mouse to look
  around. While held, **W/A/S/D** move forward/left/back/right and **Q/E**
  move downward/upward. **Shift** speeds up movement; the mouse wheel while
  flying adjusts fly speed. This is an editor-only camera, not DX2 movement.
- **Alt + left drag** orbits around the current target. **Middle drag** pans.
  **Wheel** without RMB zooms; **F** focuses the selected actor.
- **W / E / R** outside RMB fly mode switch **Move / Rotate / Scale**.
  These are also buttons in the Prop drafts toolbar.
- Colored X/Y/Z handles appear on a selected rendered static mesh actor
  or a draft clone. Drag the axis handle to edit it in world coordinates.
  During move/rotate/scale dragging, hold **Ctrl** for coarse snapping.
- **Save draft** persists editor preview transforms only, as before.
  BSP geometry and logical actors without a rendered mesh are not
  draggable. No game GMP/IBD is modified.

The actors sidebar now has conservative **category filters**. BSP_ render
nodes are world geometry, and static meshes, brushes, lights, volume/trigger
classes, possible items and possible physics objects are classified by class
name only. **Item candidate** and **Physics candidate** labels are explicitly
heuristic: actor class hierarchy, runtime inventory behavior, collision
physics and separate IBD physics-hull associations are not yet decoded
completely. StaticMeshActor does not prove an object is static at runtime.

All of the controls are experimental and need interactive Windows/Godot
testing. The asset-free headless smoke test covers mode switching, axis
handle creation, and class-category labels but cannot simulate complete
mouse gestures or game-world physics.

## Experimental 0.2.9: enlarged move gizmo and group selection

The **Move (W)** gizmo is noticeably larger, with thicker handles for more
comfortable clicking in a busy map. Its size still adapts to camera distance.

### Multi-selection

- **Ctrl + left-click** another rendered static-mesh actor in the 3D viewport
  to add it; Ctrl-click it again to remove only that actor from the selection.
  Shift-click also toggles another mesh in the viewport.
- In the **DX2 Actors** list, use Ctrl-click for individual items and
  Shift-click for a contiguous range. Only actors with an exported mesh can
  join a transformable 3D group; logical actors remain inspectable.
- Regular left-click replaces the current selection. Each selected mesh has
  its own orange highlight.
- The gizmo appears at the **average world position** of the selected meshes.
  Move translates all selected props together. Rotate and Scale operate
  around the shared pivot. World-axis X/Y/Z buttons and Turn +/-15 degrees
  also affect the entire group.
- **Duplicate** clones every selected static mesh preview. **Reset / Delete
  copy** restores originals and removes draft copies in the selected group.
- **Save draft / Load draft** retain per-actor transforms and created copies
  through the existing JSON sidecar format. Group membership itself is
  transient; saved transforms persist, and selections do not.
- BSP render blocks cannot be multi-selected as editable props, and native
  GMP/IBD saving is still disabled. This is a preview authoring workflow.

Synthetic Godot headless regression checks cover two-object group movement,
rotation, reset, serializing/restoring the draft and Ctrl-toggle selection.
Manual Windows testing is still recommended for mouse picking and Shift
range selection in a real mission.

## Experimental 0.3.0: editor edit history

DX2Ed now has undoable **preview prop edits**. This is part of the planned
Unity-inspired workflow, not yet a full Unity-feature equivalent.

- **Ctrl+Z** / Undo toolbar button: revert the last preview edit.
- **Ctrl+Y** or **Ctrl+Shift+Z** / Redo toolbar button: redo it.
- Operations covered: X/Y/Z button moves, Turn +/-15 degrees, multi-selection
  moves and rotations, duplication, Reset/Delete copy, manually loading a
  saved draft, and moving/rotating/scaling with the axis gizmo.
- One complete **gizmo drag is one history step**, not one entry per mouse
  movement. History is capped at 100 steps and clears when a different GLB
  or GMP is opened. A new edit after Undo clears the redo stack.
- Undo/redo shortcuts are not intercepted while a text input or numeric
  editor has focus, so you can still undo typing in the search field.
- **Restore All** requests confirmation before restoring every original
  static mesh pose and deleting every draft copy. It also **overwrites the
  current map's saved sidecar with an empty draft**, so edits do not return
  on reopening the map. You may Ctrl+Z to undo Restore All during the same
  session, and must then click **Save draft** to persist that restored state.
- Save draft persists to user:// and never writes proprietary GMP/IBD files.
  Undo history itself is not persisted across app restarts.
- Camera movements, viewport selections, and gameplay object properties are
  not recorded in edit history yet. BSP geometry authoring and native map
  write-back remain future SDK work.

Headless Godot smoke tests exercise the command history on a synthetic
two-cube scene. Actual Unity-style mouse/keyboard handling should still be
tested interactively in Windows Godot.

## Experimental 0.3.1: Unity-style Hierarchy / Scene / Inspector workspace

The main editor has been reorganized into **three resizable columns**:

- **Hierarchy (left)**: searchable Tree showing original actors grouped into
  class-based editor folders (Static mesh, Brush, Light, Volume / trigger,
  gameplay classes). It also shows draft prop copies and separate unlinked
  rendered geometry / BSP. These folders are **not claims about native Unreal
  actor parent-child relationships**; the original actor metadata remains the
  authoritative representation. Browse and expand folders like Unity's
  Hierarchy; Ctrl- and Shift-select multiple actor entries.
- **Scene (center)**: the existing interactive 3D map, Unity-style camera,
  move/rotate/scale gizmos and Ctrl-click selection. This remains a preview of
  the imported original DX2 map, not an engine swap.
- **Inspector (right)**: selected object name, DX2 actor class/category/export
  ID, editable **Position X/Y/Z** for rendered static meshes and draft copies,
  plus **Rotation** (degrees) and **Scale** for an individual editable prop.
  Multi-selection Position edits move all chosen props together by their
  common pivot; group rotation and scaling remain available with the gizmos.
  Underneath, the original decoded actor properties are preserved **read-only**
  for source investigation, with source position/rotation/skin diagnostics.

All transform field changes use the same **Ctrl+Z / Ctrl+Y** history as gizmo
operations. A map reload recreates the Hierarchy from original actor records;
draft copies appear as an explicit separate folder. **Save draft** persists
the edits in a JSON sidecar, not a retail GMP/IBD. Collision, actor physics,
live component scripting, native save-back and BSP vertex editing are not
implemented in this milestone.

The asset-free Godot headless test covers Hierarchy population and selection,
editing Inspector position values, undoing those changes and the existing
multi-selection / geometry-picking workflows. Interactive Windows testing is
still needed for UI layout, tree range selection and typing/dragging in the
Inspector fields.

## Experimental 0.3.2: Rotation Lab evidence (no automatic rotation fixes)

For an original **placed static-mesh actor**, the Inspector now includes a
**Rotation Lab** that can preview the source orientation, Yaw +/-90 degrees,
Yaw 180 degrees, inverted Pitch and inverted Roll. All hypotheses are computed
from the original imported pose, not cumulatively from the last experiment.
Choose **Preview orientation** to apply a *reversible* JSON-draft transform,
with Ctrl+Z support. The original GMP and IBD are untouched.

**Copy evidence** places a diagnostic on the clipboard with original
GMP Pitch/Yaw/Roll rotator values, degrees, mesh identity and transform,
the original/current Godot bases, and for each hypothesis:

- Transformed mesh-local bounding box in Godot world space.
- Nearest BSP render-block **axis-aligned bounding-box** (AABB) gap in metres.
- Count of intersecting BSP AABBs.

This is a troubleshooting aid, **not an automatic correct-rotation detector**.
AABB overlap can be caused by enclosing walls or large BSP sections and says
nothing about whether two *surfaces* actually touch. The original map
rotation might be right while the source mesh pivot, local axis conventions,
or runtime physics transform are different. Visual comparison with the game
and reliable engine-format reconstruction remain necessary before applying
any correction globally.

The lab currently works for **one original linked static mesh** at a time.
Copies, BSP geometry, and logical-only actors do not have corresponding
native source rotations and are excluded from the lab. GitHub's headless
Godot test checks the Unreal-to-Godot 90-degree yaw convention, alternate
orientation previews and Ctrl+Z restoration; actual game-map use still needs
interactive comparison.

## 0.4.0-preview: T3Ed parity roadmap and IBD Asset Browser

See [T3ED_PARITY_PLAN.md](T3ED_PARITY_PLAN.md) and its 23-system
[t3ed_parity.json](t3ed_parity.json). They are grounded in the user's
original 2005 Thief 3 editor and newer T3SDK reference archives; no proprietary
editor binaries or game assets are included in this repository.

**First implemented step**: native DX2 mission imports now generate
`assets.json` from the supplied IBD headers, adjacent to `scene.glb` and
`actors.json`. The source index covers placed **and unplaced** static meshes,
textures, material libraries, physics hulls and TriggerScript definitions.
Each resource entry records its original name, type, bundle, index and byte
length. Duplicate resource identities across bundles are reported, with
the first selected bundle taking precedence as in the map exporter. This
index contains **no texture pixels, mesh triangles, scripts or sound payloads**.

In DX2Ed's left panel, switch from **Hierarchy** to **Assets**. You can filter
by resource type, search by name or source bundle, inspect provenance, copy a
resource name and locate the first actor referencing a placed static mesh.

This is intentionally a **browse/search milestone**. Placing a mesh that has
no existing actor instance requires a DX2-specific actor archetype, Gamesys
fields and a safe map writer. The editor does not invent those just because
a source mesh exists. Workflows from T3Ed, especially native .unr editing,
BSP/CSG, actor links and cooking .gmp/.ibt files, are not binary compatible
by assumption. Next targets are native actor class/property catalogs and
SDK-owned editable level project data.

You can also generate only the resource inventory from source-owned bundles,
without converting the map:

```powershell
python native_editor/godot_editor/backend/dx2_asset_catalog.py --bundle "C:\DX2\Maps\m1_hub.ibd" --bundle "C:\DX2\Maps\Kernel_GFXALL.ibd" --output "C:\DX2Ed-cache\hub-assets.json"
```

The catalog is read-only and has fixture-only regression tests. Original game
archives are never published or changed. Godot screenshots and in-game tests
are still required before marking new content-authoring features complete.

## 0.4.1-preview: typed DX2 actor-property drafts

In the Inspector, selecting a decoded **original actor** (including
logical-only actors with no rendered mesh) opens an Actor properties panel.
It displays **unambiguous scalar Gamesys properties** using native controls:

- Boolean values: checkbox.
- Byte, integer and floating-point values: bounded numeric field.
- Short string values: text field, committed on Enter.
- Filter by decoded property name, numeric ID or scalar type.
- Values changed from the source are marked with an asterisk. **Reset values**
  restores the selected actor's decoded source values and is undoable.

The original actor metadata remains unchanged, with original source
values still displayed in the read-only Inspector. Properties use the
**original numeric property ID**, type and actor export index. If a property
has duplicate IDs, an unknown/complex type, an out-of-range value, or it
represents an object reference, mesh reference (ID 43) or TriggerScript
(ID 92), DX2Ed keeps it **locked** instead of guessing its meaning. This
experimental editor supports `bool`, `byte`, `int`, `float` and
`string` only; source `name`, `struct`, `array`, `object` and other
types are read-only. Editable numbers are conservatively limited to +/-1e6,
bytes to 0..255 and text to 512 characters. The first 48 matching scalar
fields are shown to keep the Inspector responsive.

Typed property changes participate in **Ctrl+Z / Ctrl+Y**, **Save draft**,
**Load draft**, per-actor **Reset values**, and **Restore All**. Drafts
are backward-compatible `DX2Ed-prop-draft-v1` JSON containing an optional
`property_edits` list of actor name, source export, numeric property ID,
type and override value. Loading validates **all** entries against the
current map before applying anything. Existing transforms/copies remain
compatible. The original GMP, IBD and Gamesys package **are never written**.

These are **SDK-side metadata changes only**. Edits do not yet affect
live game logic, physics or TriggerScript execution, and native package
round-tripping remains a separate, unverified milestone. Only simple
decoded scalar types are exposed intentionally.

CI uses synthetic actors to validate editing, search, undo/redo, sidecar
round trips, rejecting restricted references, logical-actor selection and
Restore All, plus the existing Godot 4.3 scene tests.

## 0.4.2-preview: place unused IBD meshes as reversible drafts

DX2Ed's **Assets** tab now includes **Place preview mesh** for source
`staticmesh` resources, including meshes not already used by the map.

- Choose any cataloged static mesh and click **Place preview mesh**. DX2Ed
  starts a background Python worker to decode the original IBD resource and
  build **one textured GLB preview** using the existing map exporter/material
  pipeline. The output lives under the **private map cache** directory at
  `asset_previews/mesh_<SHA256 prefix>.glb`; the retail source remains
  read-only. Subsequent placements reuse the cached preview.
- The new object appears in Hierarchy as `DraftProp_N`, with source
  `AssetMesh::<resource name>`. It starts at the editor camera's target
  position and supports existing move/rotate/scale gizmos, multi-select,
  Ctrl+Z/Ctrl+Y, Duplicate, Reset, Save/Load draft and Restore All.
- The existing `DX2Ed-prop-draft-v1` sidecar schema persists asset-origin
  copies with `from_actor: "AssetMesh::<resource name>"`; this is a **virtual
  editor source**, not a Gamesys object reference or a native actor. Old
  actor-copy drafts remain compatible. On reopening, the editor reconstructs
  asset-origin drafts from locally cached previews and validates the catalog.
- New imports save user-local IBD `source_paths` in `assets.json` so
  individual resource previews can be generated on demand; older cached
  imports are upgraded **in place** without changing their map cache key or
  abandoning existing prop drafts.

**This is not yet native DX2 object creation.** No actor archetype, export
index, script, collision hull, physics or inventory behavior is invented.
Placed preview assets are not playable in retail Invisible War and cannot be
saved into a GMP/IBD package. Native actor creation requires verified Gamesys
class templates, relationships and a round-trip-safe package writer.

Asset previews inherit the map exporter's incomplete shader/lighting
approximations. Some exotic IBD meshes may be unsupported by the decoder.
The generation worker reports failures and does not modify the source file.
If an old `assets.json` has no IBD source paths, reopen the source GMP with
DX2Ed to refresh the local catalog before trying unplaced assets.

The CI tests use fixture-only meshes and a synthetic two-cube Godot scene to
check resource identity, GLB output, duplication, undo/redo, draft recovery
and Restore All. Real-map interactive placement still needs Windows testing.

## 0.4.3-preview: Gamesys class palette and observed actor templates

The left workspace now has a **Classes** tab alongside Hierarchy and Assets.
It displays two separately sourced kinds of DX2 class information:

- **Declared classes** read from the user's original System/GameSys
  `.d2u` UnrealScript `TextBuffer` declarations, when a System folder,
  System ZIP or supported class catalog JSON was supplied. Each entry keeps
  its qualified package name and declared parent class.
- **Observed classes** seen in the loaded original `.gmp`, even without
  System data. Each class shows how many source actors use it, an example
  original actor and its exported mesh when available. In duplicate-name
  cases, class-to-package attribution is *not guessed*.

The new backend cache `archetypes.json` is generated alongside
`actors.json`, `scene.glb` and `assets.json`. Old valid map caches are
upgraded **in place** to preserve JSON drafts. The palette is searchable by
class, qualified package, parent class or example mesh. **Inspect example
actor** focuses the original actor. **Place template draft** copies the
rendered visual mesh of an observed actor near the current editor camera
target, with its class, original actor name and original GMP export index
stored separately as provenance.

A template is **only a reversible 3D visual draft**. It is *not* a native
Gamesys instantiation: it has no synthesized class inheritance, default
properties, package export, AI, collision or TriggerScript logic. The
palette refuses to place a class that lacks a valid rendered example.
The existing Undo/Redo, Duplicate, Save/Load draft, and Restore All systems
preserve this template provenance, and sidecar reload validates the
class-name/original-actor/export tuple against the source catalog before
loading anything. Older prop drafts without template metadata still work.

The `dx2_archetype_catalog.py` module performs conservative class matching:
it never silently selects a GameSys package when two declared classes share
a short name. Actor property signatures come from observed instances,
not assumed constructor defaults or validated inherited schemas. This
is the foundation for later typed actor construction, not proof of working
game-engine spawn support.

Fixture-only Python tests cover declared inheritance, observed examples,
unmatched classes, ambiguous short names and synthetic catalog files.
Godot 4.3 smoke tests exercise the new tab, visual template placement,
Undo/Redo, sidecar persistence and rejection of invalid template provenance.
In-game round trips and native class creation remain future work.

## 0.4.4-preview: T3Ed-inspired primitive Brush authoring

Open the **Brushes** tab in the left workspace. Create parameterized
**Box, Wall, Floor or Stairs** from dimensions entered in **Godot metres**.
Stairs have an editable count from 1 to 64. Preview brushes are positioned
at the camera target, added to a dedicated **Brushes** folder in the
Hierarchy and selectable with the same 3D triangle picker as ordinary props.

The selected brush's Inspector exposes **size X/Y/Z** and stair count.
Changing dimensions regenerates its mesh, while ordinary transform gizmos
still move, rotate and scale the group. Create, resize, duplicate, edit,
Undo/Redo and Restore All all use the same bounded history as prop drafts.

The original `DX2Ed-prop-draft-v1` sidecar stores an optional `brush`
definition alongside each draft's transform and `Brush::<type>` source.
The loader validates brush type, dimensions, stair count and source
consistency **before changing the current scene**. Existing sidecars
without brush metadata remain supported. Individual dimension values
must be finite and between 0.05 and 256 metres. This intentionally prevents
runaway geometry or corrupted restores. Stair geometry currently combines
closed step boxes for previewing, not a manifold optimized CSG solid.

**Crucial boundary:** these are **Godot visual meshes only**, not native
Unreal brush actors, not additive/subtractive CSG operations, and not
compiled DX2 BSP, collision, portalization or navmesh resources. They
will **not appear in retail Invisible War**. Native level build requires
reconstructing the original BSP and game collision compilation pipeline.
No source GMP/IBD was changed, and this preview must not be described
as native mission geometry authoring yet.

Headless Godot 4.3 tests verify each primitive, invalid input rejection,
stair mesh regeneration, undo/redo, duplicate parameter inheritance, saved
draft recovery and Restore All. Interactive editor tests on Windows and
actual asset/render comparisons are still recommended.

## 0.5.0 experimental: native GMP Save As, location-only

The main toolbar now has **Experimental GMP Save As...**, our first limited
native binary output. Move an existing placed StaticMeshActor (position only)
and choose an isolated output folder, preserving the source GMP filename.
The output uses **the original GMP bytes**, changing only the three verified
serialized Location float coordinates. It does not rebuild packages,
install maps or change original game files.

This is **not yet game-tested**. The writer refuses changed basis/rotation,
scaling, added visual drafts, brushes, actor property edits, unknown actors,
source hash mismatches, and overwriting original or existing GMP files.
It reparses output, verifies package identity, size, byte diffs and actor
positions, and emits a JSON manifest marked **game_verified: false**.

See [GMP_SAVE_AS_EXPERIMENT.md](GMP_SAVE_AS_EXPERIMENT.md) for instructions,
CLI dry-run, backup/test-install precautions and the exact feature limits.
Both Python fixture tests and Godot UI compilation are checked in CI; actual
retail engine acceptance and physics behavior require a separate Windows
game test. New playable missions and real BSP compilation remain future work.

## 0.5.1: read-only native location audit and independent output verifier

The top toolbar now includes **Audit native GMP**. This checks the imported
original GMP's existing StaticMeshActor Location property payloads and source
actor identities. It shows how many actors are structurally eligible for the
current position-only writer and why other actor records are rejected.
No output is written by the audit.

Experimental GMP Save As now refuses drafts with **no meaningful position
changes**. The new command-line \`--verify\` mode independently reopens a
previously exported GMP and compares its full byte stream to the original,
using the Save As manifest. It rejects edits outside the original serialized
Location float fields, header/table changes, mismatched SHA-256 hashes and
manifest claims that retail gameplay has been verified.

See [GMP_SAVE_AS_EXPERIMENT.md](GMP_SAVE_AS_EXPERIMENT.md) for the audit and
verify commands, and for the critical fact that **no actual Invisible War game
load has been demonstrated yet**. The goal remains a safe test loop in a
separate backed-up game installation before enabling further native writes.

## 0.5.2-preview: Source mesh placement diagnostics and visible Inspector

After importing a GMP plus IBD bundles, DX2Ed now compares **three separate
sources of geometry evidence** for each placed mesh: the local bounds in the
GMP StaticMesh resource, the IBD mesh's declared bounds and its actual decoded
vertex bounds. It records their maximum differences, the local mesh center
and the distance between that center and its local origin/pivot.

These measurements help distinguish a possible **mesh pivot problem** from a
rotation/scale issue. They **do not prove correct world placement** and do not
change the original map transform. A large local pivot offset can be
intentional. Reversible Rotation Lab experiments remain independent.

- The actor filter now includes **Review mesh placement**, listing actors
  whose source mesh bounds disagree or whose pivot is unusually far from
  the decoded geometry. The Hierarchy marks these with **[bounds?]**.
- Selecting a linked actor shows the placement evidence in the **Inspector**
  and **Copy placement evidence** copies the original actor diagnostics,
  source position/rotation, per-mesh bounds and pivot data for comparison.
- The Scene and Inspector now use a **nested two-child splitter**, correcting
  the previous three-child HSplitContainer layout that could hide the entire
  Inspector at 1440x900.
- The source report contains `placement_audit` (counts, capped examples)
  and `placement_actor_details`. Actor records contain a corresponding
  `placement_diagnostic`. Older private scene caches are enriched in place
  without changing their cache key or discarding existing draft edits.
- If an IBD source is unavailable or cannot be decoded for the audit, the
  importer preserves the otherwise valid scene and explicitly marks the
  audit **unavailable** instead of guessing.

The audit runs solely on user-owned map/resource files and produces ordinary
metadata JSON. It does **not** export a modified GMP, correct meshes
automatically, reconstruct hidden actor attachments, or reconstruct the
retail engine's shader/physics runtime. Review issues against the actual
game before adopting any new coordinate convention.

Python fixture tests check matching and mismatching GMP/IBD/vertex bounds,
large mesh-local pivots, missing evidence and cache upgrades; the Godot 4.3
smoke test checks the nested Inspector, warning filter and evidence panel.
