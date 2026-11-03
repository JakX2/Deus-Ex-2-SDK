# Third-party T3 file tools: reference inventory (not vendored)

The user supplied `T3_Tools.1(1).zip` on 2026-11-02 as a
research reference for DX2Ed's T3Ed-like materials, sounds and
textures. This file is also **already listed** in the user's
DX2SDK Google Drive project folder as `T3_Tools.1.zip`.
We did **not** upload or publish the executables to GitHub.

## Provenance and preservation

Published upstream:
[Thief 3 File Tools by snobel on ModDB](https://www.moddb.com/mods/thief-3-sneaky-upgrade/downloads/thief-3-file-tools).
Its displayed archive size is 4,289,238 bytes and published MD5 is
`d04dd1fac267cbea7fad668a50de7b30`. Both **match the user's
uploaded archive locally**. The upstream page describes CLI utilities
for Thief 3 and sometimes Deus Ex 2, and links the creator's
documentation at
[TTLG: Some tools for working with Thief 3 (and Deus Ex 2) files](https://www.ttlg.com/forums/showthread.php?t=151472).

Local uploaded ZIP:
- Size: **4,289,238 bytes**
- SHA-256: `1d13c1a3227b5d3d96c20a55dfb6ebe2cf2704f350837214be0ad511502354b3`
- MD5: `d04dd1fac267cbea7fad668a50de7b30`
- Members: **six Windows PE executables; no included license text or source code**

| Member | Original size (bytes) | SHA-256 |
|---|---:|---|
| `cel_upscale.exe` | 268800 | `727e5706f5baa8a6c34f783c571837931a51c66806779f8cc52c0a9dde867cce` |
| `csc-tool.exe` | 1612288 | `049030d191517f360fcbc437b08514d25bd22dcc38afc9f0a2f078751ebec224` |
| `cubemap-tool.exe` | 246272 | `4a8b12e13786edaeba1a2494127569ed68e6e2c6c1e51aecab81479cc3c87d23` |
| `ibt_tool.exe` | 2597888 | `7dbd1eea1a3e68f9403753c4e3d0d210c9c2ed50e14f4b278857bcf127ebcc95` |
| `ibt_xbt_ibd_texture_extract.exe` | 294912 | `ad50880827c0c14cd30542158c77be455421b674d9bab558592f9da7125b7c50` |
| `mlb-tool.exe` | 416768 | `b1d246f9d5ff5ef514ac2cd5caf054871aba6a0344f835b4d49c91316e8ac93e` |

## Storage and security

The user's existing Drive project entry is preserved as-is.
A direct download of that **existing Drive file** returned an upstream
403 `cannotDownloadAbusiveFile` warning from Google Drive, so the
Drive copy's bytes could **not** be independently hashed. Its displayed
size matches the local upload. No bypass was attempted. The binaries
were not executed or redistributed.

Because no license explicitly authorizes vendoring or redistribution
in this archive, **do not commit EXEs or ZIPs to the public repo**.
Record names/hashes, use user-owned copies locally after appropriate
security verification, and independently implement the needed format
decoders in DX2SDK. A malware/spam warning does not establish whether
the archive is actually malicious, but it warrants caution.

## Relevant formats for DX2Ed

- `mlb-tool.exe`: static inspection suggests MatLib/MLB material
  work, a reference for native material library parsing.
- `csc-tool.exe`: static printable strings expose commands
  `--compile/-c`, `--decompile/-d`, `--modify/-m` and
  `--in/-i`, `--out/-o`. It handles compiled `.csc`
  sound-schema blocks, discrete `.sch` sound definitions, and
  LAD payloads. **No executable testing was performed.**
- `ibt_xbt_ibd_texture_extract.exe`: independent DDS
  texture extraction/verification reference.
- `cubemap-tool.exe`: DDS cubemap inspection and conversion reference.
- `ibt_tool.exe`: T3 IBT/CBT compression reference, not an
  established native DX2 geometry writer.
- `cel_upscale.exe`: T3 font metadata; creator notes DX2's
  Visible Upgrade lacks the needed T3-specific font patch.

## First-party format evidence

The user's own `DX2/System/Default.ini` enumerates:
`SoundSchemas=sch|Sounds*`,
`SoundSchemaMetafiles=csc|Sounds`, and
`WaveSound=ogg;wav|Sounds*`. These are **actual DX2 mappings**,
rather than assumed from T3. Sound entities still require
GameSys source archetypes, map actor state and native
links to be examined before writer support is enabled.

Next: add a source-backed read-only sound schema/browser, then
a tightly controlled native sound-emitter or light-actor experiment
with independently verified map bytes and an explicit runtime gate.
