# DX2Ed Windows prototype 0.6.0-alpha

**Target review: November 7, 2026.** This archive is a portable research **prototype**: it contains the original-source DX2Ed Godot project and official Godot 4.3 Standard Windows x64 engine, launched in project-run mode. It is **not** a Godot exported/published standalone game, a production UnrealEd replacement, or a complete engine-native map writer.

## Get running in Windows 10/11, 64-bit

1. **Extract the entire ZIP** to a normal user-writable directory, e.g. `D:\DX2Ed_Prototype\`. Do not run files directly from inside the ZIP. Do not extract it into your game install or `Content\DX2\Maps`.
2. Install **Python 3.11 or newer** if necessary, with `python` or `py -3` available on the Windows command line. No Node.js, pip package download, Visual Studio or separate Godot installation is needed for the bundled prototype.
3. Double-click **START_DX2ED.cmd**, or **drag your own original .gmp onto START_DX2ED.cmd** to launch directly into that map. The offline preflight now checks Python 3.11+, loads five real map/collision/native-worker modules, verifies the Godot binaries, and passes the **absolute interpreter it actually tested** to the Godot workers. This avoids accidentally invoking a different Python or Windows Store alias after launch.
4. Click **Load demo cubes** first to confirm the renderer, mouse input, camera and inspector without original game files. The included two-cube GLB and actor JSON were **generated from scratch** by our synthetic test generator.
5. Click **Open DX2 map (.gmp)** and choose a map in your **own original DX2 Content/DX2/Maps folder**. Give the importer the corresponding mission `.ibd` and shared resource bundles, either through automatic discovery or **IBD override...**. Optional original System resources can be supplied via **DX2 System folder...**.
6. The editor builds an isolated cache in the Windows per-user Godot directory, not inside the retail game. Use actor search, viewport picking and **Frame scene**. **Inspect source collision** is opt-in and needs an authentic GMP/MOPP cache. Select an original triangle and a valid source-exact linked edge to try **Profile capsule heights**, then **Inspect selected height** in the capsule panel.

**Precheck an original map before importing:** Drag the owner-original `.gmp` onto **DIAGNOSE_GMP.cmd**. This performs **local filename/companion IBD discovery only**, through the same Python resource resolver used by DX2Ed. It reports fixed codes such as `bundle_paths_found`, `mission_ibd_missing` or `resource_discovery_failed`, without embedding your original file paths or hashes. A `ready` outcome means the candidate resource paths were located, **not** that the GMP/IBD contents have decoded successfully or that the map can render. No cache or modified game output is generated. When manual IBD overrides are necessary, select them in the editor UI.

**Troubleshooting:** Double-click `CHECK_DX2ED.cmd` for offline preflight, or run `START_DX2ED.cmd --self-test` in a Windows Command Prompt to run **eleven** completely synthetic Godot 4.3 headless fixture scripts and a project-startup check. Real game maps are not required for these checks. Windows Defender and SmartScreen may warn about a downloaded unsigned experimental executable; the two engine binaries are taken from the **official Godot 4.3 stable Standard Windows release** with upstream release checksum verification during packaging. Check `GODOT_LICENSE.txt` for Godot's separate redistribution notice.

## What this version can do

- Launch DX2Ed on Windows without opening Godot Project Manager.
- Load synthetic demo cubes, inspect a 3D scene, view actors and imported DX2 static meshes.
- Read original `.gmp`/`.ibd` using existing Python loaders and private visual cache; inspect source-linked collision where original Level/MOPP provenance is available.
- Inspect model/asset properties, work with **reversible preview drafts**, and run opt-in research-only capsule/contact/height profiles from source-exact edges.
- Use the **Scripts** tab to browse source-authenticated original TriggerScript definitions, select an original map actor, click **Plan script on selected actor**, add a 400-character design note, and **Save design / Load design**. These plans are versioned private Godot-user-data JSON scoped to the exact original GMP SHA-256 and original TriggerScript archive SHA-256. They **do not** assign executable scripts or enter native GMP Save As.
- Access existing **experimental** actor-location-only native GMP Save As tools with independent verification; **never overwrite originals**. Their output is **not** confirmed gameplay compatible and should only be attempted against backed-up/copy data.

## What this version cannot do

- Compile modified BSP geometry, regenerate Havok MOPP, or guarantee valid game-engine collisions.
- Spawn arbitrary new retail DX2 actors or produce completed working missions.
- Write planned TriggerScript/actor links to the game, compile dialogue, resolve raw mission script indices, or claim runtime script behavior has been verified. The Scripts tab's new plan is a **design artifact**, not a native editor compiler.
- Claim that source geometry "contact" means blocking or that a no-contact path is playable.
- Guarantee texture-perfect import, shader parity, original in-game placement or reliable Windows GPU behavior across every map. Some materials remain approximate and advanced features need owner-side real-map validation.
- Include **any** original game files. Source-derived private JSON reports must not be submitted to GitHub.

## Minimum two-day acceptance checklist

For a **working prototype** rather than a paper research PR, verify this sequence on the target Windows PC:

- [ ] `CHECK_DX2ED.cmd` passes.
- [ ] `START_DX2ED.cmd --self-test` passes 11/11 Godot fixtures and project startup.
- [ ] `START_DX2ED.cmd` opens a visible DX2Ed window.
- [ ] **Load demo cubes** displays two colored synthetic cubes; scene selection and camera work.
- [ ] Open one **owned original GMP** plus IBD resources, observe nonempty rendered geometry and actor list; reopen same map and confirm cache reuse.
- [ ] Optional scripting milestone: open your original **TriggerScript.zip** in the Scripts tab; choose an original script and a source actor; plan a link, add a note, save it, then reload. Verify the original game files remain unchanged.
- [ ] Try **Inspect source collision** on an original MOPP triangle. Note whether the source cache initializes. Valid linked-edge capsule profile is optional if no floorlike unique neighbor is available.
- [ ] Confirm original GMP and IBD hashes/modified timestamps are unchanged. Do not overwrite or commit game content.

If only the first four items pass, this is a functioning **viewer/synthetic prototype**, not yet a verified retail DX2-map prototype. If the first five pass, it is a **map-inspection prototype**. Editing and in-game physics are later milestones.

## Folder layout

```text
DX2Ed_Windows_Prototype/
    START_DX2ED.cmd            # primary launch
    CHECK_DX2ED.cmd            # verified Python interpreter, real worker imports, package doctor
    DIAGNOSE_GMP.cmd           # drag/drop source resource discovery precheck
    map_import_preflight.py    # sanitized local GMP/IBD resource resolver
    python_runtime.gd          # inside Godot project, uses verified Python
    startup_route.gd           # inside Godot project, direct --gmp routing
    prototype_doctor.py        # safe source-only preflight
    runtime/                   # official Godot 4.3 Standard Windows executables
    native_editor/godot_editor # source Godot project, 11 synthetic fixtures, mission_logic_draft.gd
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
