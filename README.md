# Deus Ex: Invisible War SDK (DX2Ed)

**Experimental community tooling for Deus Ex: Invisible War (2003/2004).** Not affiliated with Ion Storm, Eidos, Square Enix, Epic Games, or the Thief community.

Our goal is a practical, UnrealEd-style modding SDK inspired by the original Deus Ex SDK and informed by research into Thief: Deadly Shadows' editor (T3Ed). The engine branches are related, but T3Ed has **not** been successfully ported to DX2.

## Available now: DX2 Map Exporter 0.1

**[Open the standalone map exporter](map_exporter/)** or double-click [START_MAP_EXPORTER.bat](START_MAP_EXPORTER.bat) after cloning the repository and installing Python 3.9+ with Tkinter. This read-only GUI lists your installed `.gmp` maps, detects associated mission and graphics `.ibd` resources, and exports textured `.glb` scenes with JSON reports for Blender. A command-line mode is also included.

Tested with the retail Penthouse Upper and Lower levels: respectively 471 and 1,000 placed static meshes exported, zero missing mesh actors, 88 and 113 embedded diffuse textures. **Not a full map editor or a game-compatible import/rebuild tool.** See [exporter setup and limitations](map_exporter/README.md).

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
