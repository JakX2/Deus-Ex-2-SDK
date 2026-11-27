# Deus Ex: Invisible War — Engine Research

An unofficial reverse-engineering and decompilation project for the engine behind **Deus Ex: Invisible War (2003/2004)**, developed by Ion Storm.

## Project direction

The primary objective is to understand and reconstruct the original DX2 engine code through systematic binary analysis and decompilation.

This repository originally focused on developing a modding SDK and level editor inspired by T3Ed, the editor for Thief: Deadly Shadows. Following community feedback, SDK and editor development have been put on hold. The immediate priority is accurate, maintainable engine research rather than building tools around incompletely understood engine behavior.

Existing SDK prototypes are retained as historical research. They should not be treated as authoritative engine implementations or production-ready editing tools. A future editor may benefit from this work, but it is not the current development target.

## Research objectives

- Identify and analyze original engine functions, executable entry points and subsystem initialization.
- Recover class layouts, virtual tables, calling conventions, data structures and serialization routines.
- Reconstruct readable C/C++ implementations where supported by disassembly and decompiler evidence.
- Investigate rendering, world geometry, physics, resource loading, scripting, AI and gameplay systems.
- Compare relevant findings with Thief: Deadly Shadows and its related engine technology, without assuming the two implementations are interchangeable.
- Document unresolved functions and validate reconstructed behavior against the original binaries wherever possible.

## Research standards

Accuracy takes precedence over the amount of code produced.

- **Binary-first:** Record the target executable or library, build fingerprint, function address and relevant disassembly or cross-references.
- **Evidence over assumptions:** Clearly distinguish directly observed behavior, inferred interpretations and unresolved questions. Do not invent missing engine logic.
- **Readable reconstruction:** Treat raw decompiler output as an intermediate representation, not finished source code. Recover types, names and control flow carefully.
- **Verification:** Compilation, synthetic tests and successful file parsing are useful checks, but they do not establish equivalence to the original engine. Use original-binary comparison and runtime testing where feasible.
- **Review:** Keep changes focused and reproducible. Make assumptions and limitations visible to other researchers.

## Current status

**Early-stage reverse engineering.** This is not a complete engine decompilation, a buildable replacement engine, an SDK release or a working T3Ed port.

The current binary-analysis infrastructure targets the supplied Windows x86 images of `DX2Main.exe` and `dx2.exe`. Existing research includes package serialization, resource bundles, actor properties, TriggerScripts, world geometry and collision data. These findings are useful leads for identifying engine routines, but earlier experimental implementations require further review before they can be considered faithful reconstructions.

### Ghidra analysis

The repository includes an [opt-in GitHub-hosted Ghidra pipeline](docs/research/DX2ED_GHIDRA_HOSTED_P114.md) using Ghidra 12.2, with a [private self-hosted alternative](docs/research/DX2ED_GHIDRA_PRIVATE_HEADLESS_P113.md).

The hosted workflow fingerprints the configured original executable images and runs a bounded symbol survey. Public pull-request smoke tests use synthetic programs only. Original-image analysis requires separate owner configuration; the published output is deliberately limited to sanitized research metadata. This survey provides research leads, not recovered engine source code.

## Roadmap

1. Establish a reproducible binary inventory, function catalog and analysis workflow.
2. Identify engine initialization, core types and subsystem boundaries.
3. Recover functions and class structures incrementally, with address-linked evidence.
4. Organize reviewed C/C++ reconstructions by subsystem and document unresolved dependencies.
5. Validate reconstructed functions against the original implementation where practical.

There is no promised completion date or decompilation percentage. Progress should be measured by the quality and verification of individual findings.

## Previous SDK research

The following experimental tools remain available for reference, but are no longer the primary development focus:

| Tool | Purpose |
| --- | --- |
| [Map exporter](map_exporter/README.md) | Read-only GMP/IBD inspection and textured glTF export |
| [Actor Explorer](actor_explorer/README.md) | Offline actor and property inspection |
| [3D Actor Explorer](dx2ed_3d/README.md) | Experimental browser-based scene and actor viewer |
| [Native editor prototype](native_editor/README.md) | Godot-based experimental map viewer |
| [IBD mesh research](docs/IBD_MESH.md) | Resource and static-mesh format investigation |
| [TriggerScript research](docs/IBD_PROBE.md) | Read-only script bundle investigation |

Earlier prototypes include limited, guarded edits to existing actor properties and script parameters. They do not establish general map-writing support or native compiler compatibility. Some historical prototypes were developed outside the current checkout.

## Contributing

Technical feedback, corrections, function identifications, reproducible reverse-engineering findings and code review are welcome through GitHub issues. Please identify the binary version and addresses when reporting discoveries, and distinguish confirmed observations from hypotheses.

See [provenance](docs/PROVENANCE.md), [getting started](docs/GETTING_STARTED.md) and [safety notes](docs/SAFETY.md) for existing research documentation. These documents may reflect the earlier SDK-oriented phase.

## Source and copyright

This is an independent fan research project and is not affiliated with Ion Storm, Eidos, Square Enix, Epic Games or the Thief community.

We do not distribute retail game binaries, maps, textures, models, TriggerScript definitions or prepatched game bundles. Researchers should supply original files from their own installation. Keep proprietary input files and private analysis artifacts out of public commits and workflow artifacts.

Code licensing and third-party provenance audits remain pending. No open-source license is currently granted by this repository. Source contributions should wait until the applicable licensing and provenance requirements have been settled.

**The goal is to understand the original engine first.**
