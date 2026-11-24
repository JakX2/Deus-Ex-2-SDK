# Native texture import and isolated logo trial (2026-11-24)

## Scope and status

Experimental source-only writer, layered on the verified IBD integrity/repack
work (#204). This supports existing ordinary 2D texture resources; it does
not add textures, compress PNGs, resize textures, implement cubemaps, or
establish game runtime acceptance. No original or modified game assets are
included in this change.

The writer independently checks the 12-part texture prefix and six parts
per mip level, version, original format, dimensions, mip lengths, total size,
and agreement with the existing texture reader. Only the pixel parts may be
changed. The IBD writer recomputes the padded resource SHA-1 and header
SHA-1; all other bytes must remain identical. A source SHA-256 pin, isolated
output directory, original filename, and no-overwrite checks are required.

Legacy DDS input must match the exact original format, width, height, mip
count and tightly packed mip lengths. DXT1, DXT3, DXT5, BGRA8 and BGRX8 are
supported. DX10, cube maps, volumes, arrays and incompatible DDS flags,
pixel masks or pitch are refused. No compression or conversion is attempted.

The diagnostic marker recolors all existing mips magenta or cyan. It
preserves BC1 block mode and selectors, BC2/BC3 alpha blocks and selectors,
and the fourth byte in uncompressed 32-bit textures.

## Actual verification on private originals

Using the exact source-only GitHub Actions bundle, all 12 members of the
owner-provided Maps code ZIP passed IBD digest validation. The 367 texture
records comprise 365 accepted ordinary 2D textures and two rejected
environment cube maps.

| Format | DDS payload round trips | Alpha/mip diagnostic checks |
| --- | ---: | ---: |
| DXT1 | 312 | 312 |
| DXT3 | 47 | 47 |
| DXT5 | 2 | 2 |
| BGRA8 | 4 | 4 |
| Total | 365 | 365 |

BGRX8 is covered by synthetic tests, not the observed original samples.
Twenty-two complete IBD edit/reimport experiments across available
bundle/format combinations and both logo resources restored the exact
source archive bytes. The two logo trial files were actually generated
locally using the new CLI, and combined candidates matched. No game
installation was modified. No game runtime was launched.

Source-only CI and local source-bundle tests passed: 19 test methods in
the IBD integrity, canonical repack, texture writer and logo trial modules.

## Diagnostic runtime experiment

The same meta_iwlogo texture is present in MainMenu_GFXALL.ibd (resource
index 213) and Kernel_GFXALL.ibd (resource index 229). Both are DXT1,
512x128, ten mips, with matching material references. The largest mip is
identical, but two lower mips differ. The original files were individually
pinned; these pins represent the supplied archive version and may differ
from another installation.

From the extracted source-only tool bundle, using Python 3.11:

    python tools/maps/dx2_logo_trial.py --maps-dir "C:\Game\Content\DX2\Maps" --output "C:\DX2_Logo_Trial"

Adjust the source path for your installation, or use a directory containing
the two original IBDs from the supplied archive. The output must be a new
directory outside the source Maps tree. The script fails on missing or
mismatched source pins. It creates A_MainMenu_Magenta, B_Kernel_Cyan,
C_Both and trial.json. It does not install anything.

Use a complete disposable game copy. Close the game and preserve both
original IBDs. For each test restore both originals first, then copy the
appropriate candidate(s) into the disposable game's Maps folder, and launch
that copy's executable. Record whether the logo becomes magenta, cyan,
unchanged, or the game fails to load. Restore both originals after testing.
A positive observation will establish whether the targeted archive and
resource affect the display in that configuration. A negative observation
is not conclusive: another asset, loading order or cache may be involved.

## Generic DDS editing

Inspect an existing original:

    python tools/maps/dx2_texture_writer.py inspect "C:\source\Example.ibd" --name TextureName

Use the original SHA-256 reported by inspect to pin an import:

    python tools/maps/dx2_texture_writer.py import-dds "C:\source\Example.ibd" --name TextureName --source-sha256 ORIGINAL_HASH --dds "C:\work\replacement.dds" --output "C:\candidate\Example.ibd"

The DDS must already have the matching original mip layout and format.
Use the diagnostic marker command with --palette magenta or --palette cyan
instead of --dds to generate an isolated recolor. Review the receipt and
test with a disposable installation. The runtime_verified field remains
false until separately established by an actual game test.

## Next step

Establish runtime acceptance and asset selection before integrating this
writer into the editor. Subsequent work should cover material field
serialization, texture resizing/new resource insertion, and GMP/BSP
compilation. This milestone does not establish native geometry editing.
