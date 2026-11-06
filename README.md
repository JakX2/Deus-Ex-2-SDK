# Deus Ex: Invisible War SDK (DX2Ed)

**Experimental community tooling for Deus Ex: Invisible War (2003/2004).** Not affiliated with Ion Storm, Eidos, Square Enix, Epic Games, or the Thief community.

Our goal is a practical, UnrealEd-style modding SDK inspired by the original Deus Ex SDK and informed by research into Thief: Deadly Shadows' editor (T3Ed). The engine branches are related, but T3Ed has **not** been successfully ported to DX2.

## New: DX2SDK v0.1 public Python API and Windows console

DX2SDK v0.12 now has a [standalone Python API](dx2sdk/README.md) with source-verified native property inspection, direct original GMP-to-private-actors.json scanning without Godot, experimental isolated existing UE95 tagged int32/float32 scalar editing, and conservative single or **2–8 source-locked original StaticMeshActor duplicates**, native Light dependency audits, guarded existing GameSys `bLightOn` Boolean edits, and experimental original-layout LightColor brightness/hue/saturation byte editing. The clones create new exports and Level references, replay original-source serialization to verify every byte, and are NOT retail gameplay tested. The Python 3.11+ package (`from dx2sdk import DX2Map`) and a command-line
interface (`python -B -m dx2sdk`). The native-editor Windows prototype
also packages `DX2SDK_CONSOLE.cmd` next to `START_DX2ED.cmd`.
A smaller **Python-only portable DX2SDK ZIP** (with `RUN_DX2SDK.cmd`,
no Godot runtime and no retail data) is built by the separate
[SDK source release workflow](.github/workflows/dx2sdk-source-release.yml).

You can open original Ion Storm v95 `.gmp` maps, inspect source-positioned
actors and original TriggerScript/IBD resources, run byte-identical
T3SDK package audits, and prepare **dry-run or isolated output copies of
native StaticMeshActor Location translations**. Source-hash-bound
`actors.json` and the original GMP are required for native writes;
existing static-mesh Location edits remain restricted to position X/Y/Z.
The v0.3 **experimental tagged-scalar** writer separately permits exact
source-serialized top-level int32/float32 values on original placed
StaticMeshActors; both writers reparse and byte-audit their isolated GMP
copies. No source game file is overwritten.

**This is an experimental SDK foundation**, not a finished native level
compiler. In-game acceptance of the edited copy is not guaranteed;
collision/BSP rebuilding, arbitrary actors, native TriggerScript writing
and dialogue resource serialization are not supported by the new public
API. See [SDK usage, supported operations, and safety limits](dx2sdk/README.md).

The new `audit-lights`, `light-switches`, `set-light-switch` and
`verify-light-switch` commands are source-locked. No native Light actor
creation or relocation is supported, and game-visible lighting effects are
not proven by binary parity alone. The switch writer is opt-in and limited
to a pre-existing non-runtime one-byte Boolean field.

DX2SDK v0.7 also supports the **existing, exact 10-byte LightColor** GameSys struct on original positioned actors. The CLI provides `light-colors`, `set-light-color` (dry-run default; `--write` for an isolated copy), and `verify-light-color`. Only originally serialized byte fields are supported, not general GameSys structs, new light actors, light baking or BSP leaf placement. See `dx2sdk/README.md` for precise constraints and original-runtime evidence limits.

DX2SDK v0.8 further adds source-locked, reusable **2–8 existing LightColor actor plans** using `make-lightcolor-plan`, `apply-lightcolor-plan` (dry run by default), and `verify-multi-lightcolor`. These remain strict, source-authored byte-only GMP edits, not new Lights or a BSP/collision baker. Full details in `dx2sdk/README.md`.

DX2SDK v0.9 introduces **read-only original World Model BSP plane-side diagnostics** through `bsp-trace-point` and `bsp-light-regions`. The latter compares source-original native `Light` Region fields with hypotheses from the decoded candidate BSP link graph. **No reliable point-to-leaf/zone resolver or new Light actor construction is claimed.** Reports remain private source-hash-bound JSON; no BSP or retail map is written. See `dx2sdk/README.md`.

DX2SDK v0.10 adds a **read-only native Light/BSP source-evidence atlas**, using `bsp-light-atlas` and `bsp-compare-point`. It compares authored Light Regions across hypothetical BSP terminal paths at several plane tolerances and flags contradictory source pairs. This is not a verified native BSP leaf/zone solver or Light spawner; only private, SHA-replayed JSON reports can be written. See [DX2SDK documentation](dx2sdk/README.md).

DX2SDK v0.11 adds **read-only source-original Actor Region evidence across multiple native classes**, through `bsp-actor-regions` and `bsp-compare-actor-regions`. The independent package readers validate original Level membership and explicit Location/Region/LevelInfo tags; matching or contradictory source pairs are retained without inventing a point-to-leaf or zone assignment. It only writes fresh private JSON reports. Details: [DX2SDK documentation](dx2sdk/README.md).

DX2SDK v0.12 adds a dedicated **LightColor editing panel to the Godot-based DX2Ed editor**. Load an original GMP, scan exact existing original GameSys #116 `LightColor` structs, select an actor, edit only its three authored byte fields, and run independent in-memory full-GMP parity before an explicitly confirmed isolated **Save As** with a fresh private verifier manifest. It never writes retail files or enables native Light construction, Region placement or BSP rebuilding. [Details and limitations](dx2sdk/README.md).

## Available now: DX2 Map Exporter 0.1

**[Open the standalone map exporter](map_exporter/)** or double-click [START_MAP_EXPORTER.bat](START_MAP_EXPORTER.bat) after cloning the repository and installing Python 3.9+ with Tkinter. This read-only GUI lists your installed `.gmp` maps, detects associated mission and graphics `.ibd` resources, and exports textured `.glb` scenes with JSON reports for Blender. A command-line mode is also included.

Tested with the retail Penthouse Upper and Lower levels: respectively 471 and 1,000 placed static meshes exported, zero missing mesh actors, 88 and 113 embedded diffuse textures. **Not a full map editor or a game-compatible import/rebuild tool.** See [exporter setup and limitations](map_exporter/README.md).

## New: DX2Ed Native Editor 0.2

The [Godot-based native editor](native_editor/README.md) can now **open a retail `.gmp` map directly** and automatically build a private textured GLB cache plus searchable actor data. Requires Godot 4.3+ and Python 3.9+. The original game files remain untouched. This is still an experimental read-only editor, not a full level writer.

## Project status

This is an **early research repository**, not a downloadable full level editor.

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/de511541-593d-471e-b042-dc1883511ce0" />


Work to date (validated in individual research prototypes):

- Read DX2 `.gmp` maps and `.ibd` resource bundles; export textured geometry to Blender/glTF.
- Inspect actor properties and make guarded, size-preserving position/rotation edits.
- Modify existing scalar parameters in packaged TriggerScripts; two independent delay changes were confirmed executing in a retail Penthouse Upper level.
- Research skeletal model UV/position layouts, mission flags, conversations, and compatibility with T3Ed.

**Not yet supported:** creating arbitrary new actors or maps; authoring/recompiling scripts; editing arbitrary `.ibd` bundles; a general NPC mesh/animation importer; a finished GUI editor.

## Source checked into this repository

- [IBD resource and static-mesh inspector](tools/maps/dx2bundles.py), including individual-mesh GLB export, with [documentation](docs/IBD_MESH.md).
- [Read-only TriggerScript bundle probe](tools/scripts/dx2_script_bundle_probe.py), with [documentation](docs/IBD_PROBE.md).
- [Fixture-free tests](tests/) and [GitHub Actions syntax and test checks](.github/workflows/verify.yml).

Both parsers were imported from the research source archive and verified against its original Git blob hashes. The map exporter is now integrated above. The v0.28 TriggerScript writer and the other research prototypes have **not yet** been integrated into this checkout.

## Source archive

A **54-file source-only starter package** has been prepared separately as `DX2Ed_GitHub_Starter_Source_0.1.zip`. This repository is being populated from that package in stages; do not mistake the current checkout for the full historical research toolkit. Existing tools may require original game files and specific runtime hashes.

## Source and copyright

We do **not** distribute retail binaries, game maps, textures, models, TriggerScript definitions, or prepatched game bundles. Supply files from your own installation when using a tool.

Code licensing and third-party provenance audit are pending. Until these are resolved, there is no open-source license granted by this repository.

## Safety

Back up your game. Only test modified files on a separate installation or verified copy. Fixed-size modifications that succeeded in one game build do **not** imply general write support, and the format of some per-resource metadata fields remains unknown.

## Roadmap

1. Publish and audit the source-only research modules.
2. Build a reusable read-only map/resource browser.
3. Integrate actor selection, property editing and tested script editing.
4. Develop a Windows DX2Ed desktop interface.
5. Research new-actor serialization and mission creation.
6. Evaluate T3Ed interoperability in a controlled environment.

See [Getting Started](docs/GETTING_STARTED.md), [Safety](docs/SAFETY.md), and [Provenance](docs/PROVENANCE.md).

**Research-stage project: contributions welcome after source licensing is settled.**

## Actor Explorer (research prototype)

The [Actor Explorer](actor_explorer/README.md) provides a read-only, offline, interactive actor view generated from your installed DX2 `.gmp` map. Search actor names, filter by class, inspect tagged/gameplay properties, and optionally join a locally generated TriggerScript logic index. Python 3.9+ is required.

From the repository checkout on Windows:

```powershell
python .\actor_explorer\dx2_actor_explorer.py --gui
```

This does **not** save changes back to the game. Future work will connect it to an editable 3D viewport.

## DX2Ed 3D Actor Explorer 0.2 (experimental alpha)

The [3D Actor Explorer](dx2ed_3d/README.md) combines textured GLB scenes from the map exporter with Actor Explorer's engine and gameplay property inspector.

- Builds a textured DX2 map scene from a user-supplied `.gmp` plus the required `.ibd` bundles, or reuses a previously exported GLB with matching source-map SHA-256.
- Displays an orbitable WebGL2 3D viewport alongside searchable actor lists and per-actor engine property panels. Mesh selection uses original `DX2ExportIndex` glTF metadata.
- Requires Python 3.9+ and an accelerated WebGL2 browser. No Node/npm/CDN dependency. Starts a read-only HTTP server bound to `127.0.0.1`.
- No gameplay writes, proprietary retail content, or new actor creation.

Windows users can run `START_DX2ED_3D.bat` from the repository root. The research ZIP is distributed separately. The viewport rendering is still awaiting a Windows user GPU test; headless Chromium here lacks WebGL2.

## Native 3D editor prototype

The browser-based DX2Ed viewport remains experimental. The new [Godot-based native viewer](native_editor/README.md) uses Godot 4's GLB importer and built-in 3D renderer to display DX2Ed-exported scenes alongside `actors.json` entity metadata. It is read-only, not yet a standalone EXE, and Windows GPU rendering still requires hands-on validation. The ZIP release includes a wholly original two-cube fixture to help isolate renderer issues from game asset conversion.
