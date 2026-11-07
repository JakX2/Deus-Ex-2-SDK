# DX2Ed Windows prototype 0.6.0-alpha

**Target review: November 7, 2026.** This archive is a portable research **prototype**: it contains the original-source DX2Ed Godot project and official Godot 4.3 Standard Windows x64 engine, launched in project-run mode. It is **not** a Godot exported/published standalone game, a production UnrealEd replacement, or a complete engine-native map writer.

## DX2SDK v0.27 unified build: original Actor Workbench + archive audit

This integrated artifact contains the tested v0.19 Godot viewport-to-original
Actor Workbench source-identity handoff, guarded original `LightColor` and
`IntProperty`/`FloatProperty` Save As controls, **and** the read-only
v0.26 three-reader original map ZIP audit on one installable branch.
Inspect a private owner-original map ZIP without extracting game assets:

```bat
DX2SDK_CONSOLE.cmd audit-map-zip --archive "D:\\PrivateDX2\\maps.zip" --max-files 512
```

The command emits aggregate counts to the console and never creates or edits a
GMP/D2U. Optional `--sha256` pins the ZIP to an independently calculated
lowercase SHA-256. It does not prove native BSP/zone ownership or retail runtime
compatibility. Never copy retail maps into the distributed ZIP. The Godot
editor still uses its existing source-verified per-map import flow.

## T3Ed-style viewport controls (v0.28 preview-only)

The embedded Godot 3D viewport now offers **Perspective**, **Top (XZ)**,
**Front (XY)**, and **Side (ZY)** from its view dropdown. With the pointer
inside the viewport, press **1–4** to switch views, mouse wheel to zoom,
**middle drag** (or Alt+left drag in planar mode) to pan, and **F** to frame
the selected actor. The **Ortho grid** checkbox toggles a source-independent
planar reference grid. **Grid m** controls spacing (0.25–64 Godot metres) and
the existing Ctrl-drag move snapping/preview nudge increment.

These are editor-only visual guides and draft preview controls. No native
DX2 BSP leaf/zone geometry, collision, GameSys or authored map is modified;
perspective orbit/fly mode remains available. Imported GLB geometry and
source-original actor identities remain unchanged by switching views.

## Get running in Windows 10/11, 64-bit

1. **Extract the entire ZIP** to a normal user-writable directory, e.g. `D:\DX2Ed_Prototype\`. Do not run files directly from inside the ZIP. Do not extract it into your game install or `Content\DX2\Maps`.
2. Install **Python 3.11 or newer** if necessary, with `python` or `py -3` available on the Windows command line. No Node.js, pip package download, Visual Studio or separate Godot installation is needed for the bundled prototype.
3. Double-click **START_DX2ED.cmd**, or **drag your own original .gmp onto START_DX2ED.cmd** to launch directly into that map. The offline preflight now checks Python 3.11+, loads five real map/collision/native-worker modules, verifies the Godot binaries, and passes the **absolute interpreter it actually tested** to the Godot workers. This avoids accidentally invoking a different Python or Windows Store alias after launch.
4. Click **Load demo cubes** first to confirm the renderer, mouse input, camera and inspector without original game files. The included two-cube GLB and actor JSON were **generated from scratch** by our synthetic test generator.
5. Click **Open DX2 map (.gmp)** and choose a map in your **own original DX2 Content/DX2/Maps folder**. Give the importer the corresponding mission `.ibd` and shared resource bundles, either through automatic discovery or **IBD override...**. Optional original System resources can be supplied via **DX2 System folder...**.
6. The editor builds an isolated cache in the Windows per-user Godot directory, not inside the retail game. Use actor search, viewport picking and **Frame scene**. **Inspect source collision** is opt-in and needs an authentic GMP/MOPP cache. Select an original triangle and a valid source-exact linked edge to try **Profile capsule heights**, then **Inspect selected height** in the capsule panel.

**Precheck an original map before importing:** Drag the owner-original `.gmp` onto **DIAGNOSE_GMP.cmd**. This performs **local filename/companion IBD discovery only**, through the same Python resource resolver used by DX2Ed. It reports fixed codes such as `bundle_paths_found`, `mission_ibd_missing` or `resource_discovery_failed`, without embedding your original file paths or hashes. A `ready` outcome means the candidate resource paths were located, **not** that the GMP/IBD contents have decoded successfully or that the map can render. No cache or modified game output is generated. When manual IBD overrides are necessary, select them in the editor UI.

**Troubleshooting:** Double-click `CHECK_DX2ED.cmd` for offline preflight, or run `START_DX2ED.cmd --self-test` in a Windows Command Prompt to run **fifteen** completely synthetic Godot 4.3 headless fixture scripts and a project-startup check. Real game maps are not required for these checks. Windows Defender and SmartScreen may warn about a downloaded unsigned experimental executable; the two engine binaries are taken from the **official Godot 4.3 stable Standard Windows release** with upstream release checksum verification during packaging. Check `GODOT_LICENSE.txt` for Godot's separate redistribution notice.

## New: DX2SDK v0.5 public Python API and console

This Windows source-only prototype now contains **DX2SDK v0.5.0**, a
public Python package (`dx2sdk/`) and `DX2SDK_CONSOLE.cmd` launcher.
You can use the source-backed SDK without launching Godot:

```bat
DX2SDK_CONSOLE.cmd --help
DX2SDK_CONSOLE.cmd info --map "C:\\MyDX2\\Content\\DX2\\Maps\\OriginalMap.gmp"
DX2SDK_CONSOLE.cmd actors --map "C:\\MyDX2\\Content\\DX2\\Maps\\OriginalMap.gmp" --class StaticMeshActor --limit 20
DX2SDK_CONSOLE.cmd scan-map --map "C:\\MyDX2\\Content\\DX2\\Maps\\OriginalMap.gmp" --output "D:\\MyDX2SDK\\OriginalMap\\actors.json"
DX2SDK_CONSOLE.cmd inspect-actor --map "C:\\MyDX2\\Content\\DX2\\Maps\\OriginalMap.gmp" --export 15
```

The SDK also offers original-script/IBD source reads and a **real but
experimental native edit**: translate existing `StaticMeshActor` locations
using exact original GMP + private matching `actors.json`, first through
an automatic **dry run**, then (only with `--write`) a new copy in a
separate, non-game folder.
**The source-only `scan-map` command can now create the exact
original-map-matched private `actors.json` directly from your GMP,
without the GUI.** It scans native actor identity and property blocks
and marks unresolved mesh references as non-writable. Original source
files are read-only, and the new cache must live outside game folders.
`inspect-actor` shows existing tagged/GameSys property values with
opaque formats explicitly labeled; it is not a property writer.

**Experimental v0.3 native scalar edit:** `DX2SDK_CONSOLE.cmd
scalar-fields --map ORIGINAL.gmp --actors PRIVATE/actors.json --actor
EXACT_STATIC_MESH_ACTOR` lists the existing authored four-byte int32/
float32 tagged fields eligible for binary patching. After selecting a
real source field, run `set-scalar --map ... --actors ... --actor ...
--property ... --value ... --output NEW_ISOLATED_ORIGINAL_NAME.gmp`
for a **dry run**. Only append `--write` to explicitly create a fresh
isolated GMP with an independent per-byte verification and a private
`.dx2sdk-scalar.json` manifest; `verify-scalar` checks that copy again.
The original GMP must pass a byte-identical T3SDK no-op reconstruction
first. This is **not game-runtime tested**, not native GameSys editing,
and it does not modify original game files, TriggerScripts, brushes or
Havok collision. Full examples are in `dx2sdk/README.md`.

**Experimental v0.5 source-locked batch prop cloning:** after checking
original source actors with `clone-candidates`, you can build a
reusable private plan using `DX2SDK_CONSOLE.cmd make-multi-clone-plan
--map ORIGINAL.gmp --copy EXPORT DX DY DZ --copy EXPORT DX DY DZ
--plan PRIVATE/clone_plan.json`. There must be 2–8 copies, each
referencing an original eligible `StaticMeshActor`. The CLI
`apply-multi-clone-plan --map ORIGINAL.gmp --plan PRIVATE/clone_plan.json
--output ISOLATED/ORIGINAL.gmp` is a complete in-memory dry run
unless explicitly given `--write`. It creates new native exports/Level
actor references in a separate GMP, never altering the source.
`verify-multi-clone` recomputes the original-source package changes
and compares the entire result, byte-for-byte. This is source-only
binary testing, **not retail gameplay, actor physics or collision
verification**.

**Experimental v0.4 original static prop duplicate:** use
`DX2SDK_CONSOLE.cmd clone-candidates --map ORIGINAL.gmp` to list
native source actors with the required idle state, no links and no
unknown native tails. Only a returned **source actor name/export**
can be passed to `clone-prop --map ORIGINAL.gmp --actor NAME
--export NUMBER --dx 100 --dy 0 --dz 0 --output NEW_ISOLATED_GMP`.
A dry-run is the default. Explicit `--write` creates one new
`StaticMeshActor` export and appends a Level actor-list reference
in a fresh GMP copy, with existing actor bytes otherwise preserved.
`verify-clone --map ORIGINAL.gmp --output COPY.gmp` independently
replays the exact clone from the original GMP and compares the
entire output byte-for-byte. This is **not arbitrary NPC spawning,
brush placement, collision rebuild or validated retail gameplay**;
never install the experiment into your original game.

For reusable projects, **`make-plan`** writes a new source-hash-locked
editable JSON actor position plan, and **`apply-plan`** validates the
original GMP and private actor-cache hashes plus every actor export
identity before dry-running or explicitly writing several moves. These
plans are not native game resources and must not be placed in your
retail game folders. The isolated copy is re-opened and **every
changed original byte** checked against allowed serialized Location fields.
This is **binary verification, not proof that the retail game loads the
edited map**. No original source GMP or IBD is modified. Arbitrary
actor placement, BSP compilation, collision regeneration, native script
writing and dialogue compilation remain unsupported.

See **`dx2sdk/README.md`** in the extracted package for a complete
Windows command guide, Python API examples, authoring limits and safety
requirements. The SDK is available from repository checkout as
`python -B -m dx2sdk` as well. It requires Python 3.11+ and reuses
the included T3SDK-derived native package reader/writer.

## What this version can do

- Launch DX2Ed on Windows without opening Godot Project Manager.
- Load synthetic demo cubes, inspect a 3D scene, view actors and imported DX2 static meshes.
- Read original `.gmp`/`.ibd` using existing Python loaders and private visual cache; inspect source-linked collision where original Level/MOPP provenance is available.
- Inspect model/asset properties, work with **reversible preview drafts**, and run opt-in research-only capsule/contact/height profiles from source-exact edges.
- Use the **Scripts** tab to browse source-authenticated original TriggerScript definitions, select an original map actor, click **Plan script on selected actor**, add a 400-character design note, and **Save design / Load design**. These plans are versioned private Godot-user-data JSON scoped to the exact original GMP SHA-256 and original TriggerScript archive SHA-256. They **do not** assign executable scripts or enter native GMP Save As.
- **Original IBD script resources:** after opening your unchanged GMP and original `TriggerScript.zip`, click **Verify script resources in original IBD...** in Scripts, then select the mission or `Kernel_TSDALL.ibd` file from your own game. DX2Ed verifies standalone `Defs/*.tsd` payload bytes against named original IBD **kind 21** resource entries, shows `[IBD exact]` or `[IBD differs]`, and keeps the report in private user data. A script missing from one IBD may appear in another. **Matching payload bytes establish resource identity, NOT the actor-to-script runtime binding, native script editing, or game compatibility.**
- **Actor script-reference research:** after the same IBD resource check completes, select an original actor and click **Inspect selected actor script fields** in Scripts. DX2Ed independently re-decodes original native GameSys property **92 (TriggerScripts)**, verifies it against the source-hashed actor cache, and displays each raw compact integer alongside the name at that numeric position in the original GMP name table (if present). It also marks matches in original TSD definitions and the selected IBD. These are **name-slot candidates only**: the actual array element interpretation and runtime actor-to-script bindings are still unverified. A triple name/TSD/IBD match must **not** be treated as a successfully bound or executable script. No native writer is enabled.
- **Map-wide script-index hypothesis audit:** once original IBD verification completes, click **Show map-wide script index audit** in Scripts. DX2Ed aggregates only independently re-decoded original GameSys 92 compact arrays and compares name-table positions at raw index shifts **-2, -1, 0, +1 and +2**. The results show how many actor indices land on nonempty GMP name-table slots, original TSD script names and exact/different original IBD script payloads. Unverified or opaque actors are excluded and counted. **These are exploratory offset controls**, not a proof of script-array encoding or a statistically certified winner. No shift is automatically selected and no native script writer is enabled. Use **Copy sanitized index audit summary** to share only source-independent aggregate counts and warnings. The clipboard summary excludes original map paths, source hashes, actor names, script names and all original game bytes.
- **Compare original mission vs Kernel TriggerScripts:** With your original **Club GMP**, original `TriggerScript.zip` and the **Club mission IBD** selected via **Verify script resources in original IBD...**, click **Compare mission IBD against Kernel_TSDALL...**. Select `Content/DX2/Maps/Kernel_TSDALL.ibd` from your original game. This compares each original script resource against the standalone `Defs/*.tsd` payload and, when the script is in both bundles, the mission and Kernel payloads against each other. The summary distinguishes **script-resource counts** from repeated **actor name-slot candidate occurrences** (the earlier 71 "IBD differs" could reflect repeated references, not 71 unique scripts). It summarizes same-length/different-length payloads and the five most common **first different byte offsets**, and now separates **changes confined to payload bytes 4–7** from cases where the same four-byte region changes *alongside other payload bytes or length*. The four-byte region's meaning is **not known**; it is not automatically labeled a checksum, size or version field. The actor candidate summary now normalizes missing IBD references consistently when the mission and Kernel script ID sets are **disjoint**, as observed on the Club map. Use **Inspect selected script's mission / Kernel differences** for a chosen script's first mismatch, byte-run and prefix/suffix metadata. **Copy sanitized mission / Kernel summary** copies counts/offsets only, not source names, files, hashes or bytes. All source bundles are read-only, reports are private local JSON, and these comparisons **do not** prove which script an actor actually executes or permit any native script writer.
- Use the new **Dialogue** tab to author a small dialogue tree: choose a **source actor** as a speaker in Hierarchy, type a line, click **Add line**, create player-choice branches using an existing **Target #** line ID, and edit/delete lines or branches. **Save dialogue design** stores an original-GMP-SHA-bound private JSON in Godot user data, not DX2 dialogue binaries. Deleting a line prunes broken incoming choices. These designs are useful for later conversion once native DX2 conversation structures are researched.
- Access existing **experimental** actor-location-only native GMP Save As tools with independent verification; **never overwrite originals**. Their output is **not** confirmed gameplay compatible and should only be attempted against backed-up/copy data.

## What this version cannot do

- Compile modified BSP geometry, regenerate Havok MOPP, or guarantee valid game-engine collisions.
- Spawn arbitrary new retail DX2 actors or produce completed working missions.
- Write planned TriggerScript/actor links to the game, compile authored dialogue trees, resolve raw mission script indices, or claim runtime script behavior has been verified. The Scripts/Dialogue tabs produce **design artifacts**, not native game conversation/script resources. The original IBD resource matching tool is **read-only provenance**, not an editor or compiler.
- Claim that source geometry "contact" means blocking or that a no-contact path is playable.
- Guarantee texture-perfect import, shader parity, original in-game placement or reliable Windows GPU behavior across every map. Some materials remain approximate and advanced features need owner-side real-map validation.
- Include **any** original game files. Source-derived private JSON reports must not be submitted to GitHub.

## Minimum two-day acceptance checklist

For a **working prototype** rather than a paper research PR, verify this sequence on the target Windows PC:

- [ ] `CHECK_DX2ED.cmd` passes.
- [ ] `START_DX2ED.cmd --self-test` passes 15/15 Godot fixtures and project startup.
- [ ] `DX2SDK_CONSOLE.cmd --help` and `DX2SDK_CONSOLE.cmd info --map <own-original-map.gmp>` work without launching Godot; note the original actor count.
- [ ] Optional native SDK write: use a SHA-matched DX2Ed actors.json and try `DX2SDK_CONSOLE.cmd move` **without** `--write` first. With a copied installation ready, write a fresh isolated GMP and verify it with `verify-move`. The original game and saves must remain untouched.
- [ ] `START_DX2ED.cmd` opens a visible DX2Ed window.
- [ ] **Load demo cubes** displays two colored synthetic cubes; scene selection and camera work.
- [ ] Open one **owned original GMP** plus IBD resources, observe nonempty rendered geometry and actor list; reopen same map and confirm cache reuse.
- [ ] Optional scripting milestone: open your original **TriggerScript.zip** in the Scripts tab; choose an original script and a source actor; plan a link, add a note, save it, then reload. Verify the original game files remain unchanged.
- [ ] Optional native-resource milestone: click **Verify script resources in original IBD...** and select an owner-original mission/kernel IBD. Check at least one exact/different payload classification, and confirm no game file timestamps or hashes changed.
- [ ] Optional native GameSys research: choose an actor with serialized TriggerScripts; in **Inspect selected actor script fields**, note whether the independently re-decoded compact integers happen to match GMP name-table slots and active scripts. Report *candidate names* separately from *verified runtime bindings*. Do not overwrite or publish source GMP/IBD/ZIP files.
- [ ] Optional map-wide hypothesis audit: choose **Show map-wide script index audit** and compare the five offsets. Confirm that opaque actors remain excluded and the editor **does not select a presumed runtime FName offset**. This is research evidence only; native actor-script execution is still unverified.
- [ ] Optional Club/Kernel research: after verifying your Club mission IBD, select **Compare mission IBD against Kernel_TSDALL...** and choose your original `Kernel_TSDALL.ibd`. Inspect the size/first-byte-difference clusters, choose a source script and inspect its per-resource diff. Copy only the sanitized summary if sharing results. **Do not upload either IBD, the GMP, private report or TriggerScript.zip to GitHub.**
- [ ] Optional dialogue milestone: select two original actors in Hierarchy, add two dialogue lines in **Dialogue**, connect one line to the other via a choice, save/reload, and confirm there are no native game edits.
- [ ] Try **Inspect source collision** on an original MOPP triangle. Note whether the source cache initializes. Valid linked-edge capsule profile is optional if no floorlike unique neighbor is available.
- [ ] Confirm original GMP and IBD hashes/modified timestamps are unchanged. Do not overwrite or commit game content.

If only the first four items pass, this is a functioning **viewer/synthetic prototype**, not yet a verified retail DX2-map prototype. If the first five pass, it is a **map-inspection prototype**. Editing and in-game physics are later milestones.

## Folder layout

```text
DX2Ed_Windows_Prototype/
    START_DX2ED.cmd            # primary Godot GUI launch
    DX2SDK_CONSOLE.cmd          # public Python SDK CLI launcher (read by default)
    CHECK_DX2ED.cmd            # verified Python interpreter, real worker imports, package doctor
    DIAGNOSE_GMP.cmd           # drag/drop source resource discovery precheck
    map_import_preflight.py    # sanitized local GMP/IBD resource resolver
    python_runtime.gd          # inside Godot project, uses verified Python
    startup_route.gd           # inside Godot project, direct --gmp routing
    prototype_doctor.py        # safe source-only preflight
    dx2sdk/                    # SDK v0.1 public Python package + examples
    runtime/                   # official Godot 4.3 Standard Windows executables
    native_editor/godot_editor # source Godot project, 15 fixtures, IBD/Kernel script comparisons, index audit and authoring drafts
    native_editor/package_writer/
    map_exporter/
    actor_explorer/
    research/dx2/
    third_party/t3sdk_assets/  # upstream license and sources
    docs/research/             # research cautions and experiment docs
    prototype-manifest.json
    GODOT_LICENSE.txt
```

The prototype does not bundle an original DX2 binary or any source-assets-derived collision profile. It is distributed as a short-lived GitHub Actions artifact for testing, not a signed installer.

**Reporting a blocker:** share a screenshot or the **fixed-code** result from `CHECK_DX2ED.cmd` / `--self-test`, plus whether the demo and direct GMP loaded. Do not post source GMPs, IBDs, private profile JSONs or original map paths.
