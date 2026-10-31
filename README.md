# Deus Ex: Invisible War SDK (DX2Ed)

**Experimental community tooling for Deus Ex: Invisible War (2003/2004).** Not affiliated with Ion Storm, Eidos, Square Enix, Epic Games, or the Thief community.

Our goal is a practical, UnrealEd-style modding SDK inspired by the original Deus Ex SDK and informed by research into Thief: Deadly Shadows' editor (T3Ed). The engine branches are related, but T3Ed has **not** been successfully ported to DX2.

## Project status

This is an **early research repository**, not a downloadable full level editor.

Work to date (validated in individual research prototypes):

- Read DX2 `.gmp` maps and `.ibd` resource bundles; export textured geometry to Blender/glTF.
- Inspect actor properties and make guarded, size-preserving position/rotation edits.
- Modify existing scalar parameters in packaged TriggerScripts; two independent delay changes were confirmed executing in a retail Penthouse Upper level.
- Research skeletal model UV/position layouts, mission flags, conversations, and compatibility with T3Ed.

**Not yet supported:** creating arbitrary new actors or maps; authoring/recompiling scripts; editing arbitrary `.ibd` bundles; a general NPC mesh/animation importer; a finished GUI editor.

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
