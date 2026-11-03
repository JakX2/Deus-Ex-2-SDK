# Additional DX2/T3 reference archive inventory (2026-11-03)

This is a **read-only provenance and capability survey** of additional
original archives privately supplied in the user's shared Google Drive.
No executables were launched, no game resources were modified, and no
proprietary binaries/source files from these uploads are vendored in this PR.

## New root-folder archives

| Source archive | Verified on-disk contents | DX2SDK relevance / limits |
|---|---|---|
| `Thief3-Decomp-main.zip` | 8,576 ZIP entries, including extensive C++ headers/implementation and T3SDK Python asset tooling. Root MIT license. `src/Game/cBuildFleshBSP.cpp` contains only `cBuildFleshBSP::Init()` in the reviewed snapshot. `tools/assets/t3bsp.py` scans packed render blocks from a retail `Level` export. | **High for comparative formats and engine research**; neither file is an implemented or verified native BSP construction pipeline. T3SDK Map Studio currently reuses original map actors and does **not** support constructing new geometry; its own documentation says retail in-game edit results still need confirmation. Reuse any MIT-licensed portion with license and notices. |
| `deus-ex-invisible-war-native-main.zip` | 56 entries, Rust crates `iw-core`, `iw-assets`, `iw-app`; package, actor, TriangleGroup and collision source/tests. Public checkpoint dated 2026-10-23. | **High as independent DX2 research evidence**. README explicitly reports incomplete world/BSP ground geometry, a triangle-strip winding bug, missing material/class-default/runtime fidelity, and no playable port. `LICENSE-STATUS.md` says no project-wide license granted: **do not copy its code into DX2SDK without permission**. |
| `dxtoolinstall_1.42.7z` | Legacy `DXTool.exe`, `dxdll.dll`, `DXTool.ini` and 11,812-byte readme. | DX2 and T3 texture viewer/exporter/importer, alpha layers and batch-import XML. Readme states importing larger textures than originals is not supported by that release. Useful **independent reference** for a controlled native IBD texture writer, not for BSP building. |
| `CSC_Export.2.7z` | One Java 8 JAR (165 embedded entries), with `ReadCSC`, `WriteCSC`, `WriteXML`, and `con_parser` classes. | Potentially useful for DX2 conversation, sound schema and `.csc` tooling. Existence of writer classes is **not** validation of safe round-trip behavior or licensing. |
| `DXIW Sound Drone.zip` | Nine entries; legacy `DXIW Sound Drone.exe`, codec DLLs and detailed 2004 beta readme. | Readme explicitly supports **browsing, playing and extracting DX2 sounds**, but **not** inserting/replacing sound or editing subtitles/parameters. Explains Meta Sound / Tagged Sound / Mission Sound relationships; useful read-only audio schema research. |
| `TagEdit.zip` | `CscTagEdit.exe`, `Vorbis.dll`. | Legacy standalone tagged-sound GUI candidate; behavior, writable schema and license not independently verified. No execution performed. |

## Additional Thief 3 sound folder

The folder `T3/sounds` contains the user's original
`Sounds.zip`, `SchemaMetafile_DVD1.zip`,
`SchemaMetafile_DVD2.zip`, `SchemaMetafile_DVD3.zip`.
`Sounds.zip` was checked via its ZIP central directory and CRC:
two files, `SchemaMetafile_Memory.csc` (zero bytes) and
`SchemaMetafile_HardDrive.csc` (38,102,343 bytes).
The three very large DVD archives have been discovered by metadata only,
not downloaded or decoded. These **retail data** must never be committed.

## Suggested research order

1. Keep the separate T3Ed original-compiler experiment as the **primary**
   new-geometry milestone. The T3SDK's `cBuildFleshBSP::Init` recovery
   is not the missing full constructor/build operation.
2. Study T3SDK's MIT-licensed `t3bsp.py` and `t3pack.py` for format
   documentation/round-trip invariants, independently test new writer
   ideas on synthetic and private original files.
3. Treat the Rust native checkpoint as external, **unlicensed**
   comparative research; prioritize its stated TriangleGroup/winding
   and BSP-ground problems when forming independent DX2 test cases.
4. Once native geometry issues are isolated, build a **separate** sound
   schema/CSC audit from the legacy README and controlled user-owned
   CSC files. Do not run historic Windows programs or deploy any
   audio replacements directly against retail installation paths.

All conclusions above are based on archive entries, source/readme text,
and static metadata, not on verified runtime behavior.
