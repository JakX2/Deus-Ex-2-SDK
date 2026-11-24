# Native material binding and append-only texture insertion (2026-11-24)

## Evidence and scope

This experimental writer builds on the IBD integrity/repack and texture
replacement research (#204 and #205). It does not implement native BSP,
unrestricted resource creation, PNG conversion, or game-verified asset
loading. No game assets are committed.

Private original-data inspection of the owner's Maps code.zip:

- 12 IBDs, 2,169 resource-name fields, each NUL-terminated with a zero tail.
- 292 version-0 material records, all using the same 40-part layout.
- Nine stage-name strings are stored as little-endian length fields plus
  NUL-terminated ASCII byte parts. In all 292 materials the nine-bit stage
  mask matches the nonempty strings exactly.
- 214 active diffuse references, all uniquely resolved to an existing
  ordinary 2D texture in the same bundle; 78 inactive diffuse references.
- Eligible original texture formats: 202 DXT1, 12 DXT3.

The numeric color and parameter slots remain untouched. The new code
does not infer their shader semantics from the field sizes.

## Implemented tools

dx2_material_writer.py:

- Inspect an existing material with strict part layout and independent
  reader agreement.
- Retarget an active diffuse binding to an existing same-bundle texture
  with the same format, dimensions, usage, detail and mip count.
- Clone the existing diffuse texture and append one new type-8 resource
  under a unique ASCII name. The original texture remains present.
  Optionally recolor every mip using the alpha-preserving diagnostic marker.
- Change only the material's diffuse-string length and bytes, preserving
  its other parts, stage mask, all original resource identities and order.
- Rebuild header/table sizes, resource offsets, part indices, alignment,
  maxima and digests using the canonical IBD reconstruction. Unknown
  original layouts, unknown name-tail metadata, duplicate names and
  unsupported textures are refused.
- Reparse every existing and appended resource and compare its parts to
  the plan. Require the final archive itself to be canonically reconstructable.
- In-memory inverse trial removes only the appended texture and restores
  the old reference. The independently known original SHA-256 and complete
  forward reproducibility must match. This is not a general deletion API.
- Disk writes require a pinned source SHA-256, isolated new output with
  the same filename, and no overwrite. Original files are not modified.

## Verification

The exact committed source-only artifact from run 45330956477 was
downloaded and tested locally on the owner's original archives. All 292
material layouts passed. All 214 eligible diffuse bindings across eight
archives independently passed clone-and-bind, candidate integrity and
exact inverse reconstruction of the original archive. The original
format inventory and all original resource identity checks were retained.

A representative 16-case subset also explicitly measured data-header
growth: nine trials crossed a 2 KiB boundary and successfully relocated
the following data. Synthetic tests independently exercise that boundary.
The clone remains unverified in a retail game session.

## Standalone MatLib corroboration

Private inspection of the owner's MatLib.zip found 138 version-3 libraries
with magic 0xFACE and 2,694 fixed 788-byte records after a 12-byte header.
All record name fields are NUL-terminated with zero tails.

Matching by full MatLib path and case-folded material name (rather than
only the library basename) gives 286 uniquely corresponding bundled
materials. All 286 match the standalone diffuse name (offset 148, 64-byte
slot), material flags (offset 144) and stage mask (offset 64). Six bundled
materials have no standalone source path. Other fields can differ and
are not claimed interchangeable. This is read-only correspondence,
not a standalone MLB writer.

dx2_material_audit.py automates these private aggregate checks and offers
optional full clone and reverse verification. It never extracts input
archives to disk or emits original names or payloads.

## Usage

Extract the source-only tools and run with Python 3.11 or newer.

    python tools/maps/dx2_material_audit.py "C:\Owned\Maps code.zip" --mlb-zip "C:\Owned\MatLib.zip" --verify-clones

    python tools/maps/dx2_material_writer.py inspect "C:\Owned\MainMenu_GFXALL.ibd" --material meta_IWLOGO

Use the reported SHA-256 for a trial:

    python tools/maps/dx2_material_writer.py clone-and-bind "C:\Owned\MainMenu_GFXALL.ibd" --material meta_IWLOGO --new-name DX2SDK_LogoTrial --palette magenta --source-sha256 ORIGINAL_HASH --output "C:\DX2Trial\MainMenu_GFXALL.ibd"

An existing compatible target can be selected with retarget-diffuse and
--target instead of --new-name/--palette.

The source-only trial candidate has an extra texture and a changed
material binding. Compare it to the previous texture-only marker trial:
if the texture-only candidate works but the clone candidate does not,
that helps distinguish archive loading from runtime resource registration
or material lookup. Test only in a complete disposable game installation,
restore originals between runs, and do not change the standalone MLB
simultaneously. The new resource may require a separate runtime
registration step; no successful in-game observation is claimed.

## Next work

- Confirm runtime behavior of the existing texture marker and the
  appended texture/material binding in a disposable game copy.
- Investigate resource registration and lookup in DX2Main.exe.
- Add user-supplied compatible DDS data to newly cloned texture resources.
- Study standalone material serialization and synchronization separately.
- Return to GMP actor registration and native BSP/collision compilation.

