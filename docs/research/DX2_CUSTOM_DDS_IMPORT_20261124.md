# Coordinated custom DDS import and resource iteration evidence (2026-11-24)

## Purpose

This change builds on #204-206. The previous writer could insert a clone
of an existing texture and change one bundled material's diffuse reference.
This adds compatible caller-supplied legacy DDS pixels, coordinated across
all matching material instances in the supplied IBD ZIP, plus the matching
standalone material library. It is a local, isolated candidate generator,
not a game installer, general texture constructor, or runtime-verified SDK.

## Verified source format and corpus observations

The owner's Maps code.zip and MatLib.zip were checked privately:

- 12 IBD bundles, 2,169 resource records; 1,084 distinct case-folded names,
  of which 959 occur more than once.
- 138 standalone libraries, 2,694 records, 24,246 nine-stage texture
  reference slots. Every examined slot has a NUL terminator and ASCII
  prefix. Nonzero bytes after the terminator exist in some fields.
- 286 bundled material records have unique full-path/name standalone
  correspondence. Of these, 208 have active diffuse references, all
  with zero-filled tails in the standalone diffuse slot.
- Stage 0, material flags and stage mask match for all 286 corresponding
  records. Other stages are not universally identical (two stage-1
  and twelve stage-2 differences), so they are not synchronized.
- The 208 active corresponding instances comprise 154 material
  identities. Fifty occur in multiple bundles, up to three instances.

The identity is the full MatLib-relative source path plus case-folded
material name, not a basename or texture name alone. The new reference
is limited to 63 ASCII characters to fit the proven standalone slot.

## Independent executable observations

Static decoding of the SHA-256-pinned owner DX2Main.exe corroborates
the IBD resource descriptor interpretation. An accessor/iteration
path reads the type at record offset 0x28, forms a name pointer at
offset 0x29 and copies the index, size, part count, type and name pointer
into a five-dword descriptor. Nearby routines multiply the resource
index by 0x130 and compare it to the header resource count (0x18).
The writer has a path that advances by 0x130, copies a bounded name
into the record at 0x29, and writes the type byte at 0x28. The descriptor
path has callers that use both a specific type argument and an
all-types sentinel.

This supports a table-count-driven resource iteration mechanism.
It does not prove that the downstream texture registry accepts new
names, that an inserted texture is loaded, or how duplicate names,
resource order, cache state and standalone sources are resolved.
The exact runtime call chain remains to be established. No original
disassembly, binaries or private source paths are published.

## New implementation

tools/maps/dx2_custom_texture_import.py

- Require independent SHA-256 pins for both source ZIPs.
- Validate all IBD digests and standalone library structures.
- Reject the proposed new name if it matches an existing resource,
  bundled stage reference, standalone material or standalone stage
  reference anywhere in the supplied corpus.
- Select all matching bundled instances. Refuse ambiguous instances,
  destination collisions, or disagreement on proven standalone fields.
- Use the existing clone/rebind operation, replace only the appended
  texture's mip bytes with the supplied compatible DDS, and reparse.
- Undo the custom pixels and reverse the append/rebind; require exact
  original bytes. The new DDS is recovered exactly by the existing reader.
- Synchronize only the selected standalone 64-byte diffuse name slot
  at record offset 148; require exact old reference, zero tail, flags
  and stage-mask agreement. Preserve every other byte and verify reversal.
- Create a new isolated output tree and JSON receipt, never overwrite
  input ZIPs or install anything into a game.
- Bound selected instances and combined candidate bytes and reject
  ambiguous Windows paths, device names and NTFS stream names.

The name-collision scope is the supplied archives only, not every
archive installed in the game. The importer does not invent a new
texture format, resize textures, generate mips or compress source images.

## Validation

The exact final CI source bundle from run 45332977898 was executed
locally against the owner's original ZIPs. All 35 source-only tests
passed. Seven independent coordinated import cases used newly generated
DXT pixel data (not original pixel copies), with matching original
DDS metadata:

| Material group | Format | Bundled instances |
| --- | --- | ---: |
| Menu logo | DXT1 | 2 |
| Male body | DXT1 | 3 |
| Male teeth | DXT1 | 3 |
| Female body | DXT1 | 3 |
| Female teeth | DXT1 | 3 |
| Glass material 1 | DXT3 | 2 |
| Glass material 2 | DXT3 | 2 |
| Total | | 18 |

All 18 modified IBDs passed integrity, exact custom DDS extraction,
and byte-identical inverse reconstruction. All seven standalone MLB
candidates preserved every byte outside the intended diffuse slot and
passed reversal. Both ZIP SHA-256 values were unchanged. No retail
runtime was launched. No original or modified asset was committed.

Eight additional synthetic test methods check multiple instances,
precise library updates, wrong input pins and mip shapes, collisions,
dirty slot tails, mismatched fields, unsafe paths and isolated output.
The intermediate unsafe-name regression failed only because an earlier
ZIP preflight returned a different refusal message; the final test
accepts either correct refusal path.

## Usage

Extract the source-only package and run Python 3.11 or newer. The DDS
must have the same legacy format, dimensions and full mip chain as the
existing diffuse texture in every selected archive.

For the specific owner-provided ZIP versions, the command is:

    python tools/maps/dx2_custom_texture_import.py --ibd-zip "C:\Owned\Maps code.zip" --mlb-zip "C:\Owned\MatLib.zip" --ibd-sha256 0e97c15a30a85b7b01a256b403237e3a9216ff2b8945e1ecb126283ecc54c8ff --mlb-sha256 d47980d50047db398fa306b601b3196c2e193e6d67d7b1dc1014bdf6d8461490 --library "MatLib/UI_METAGAME.mlb" --material meta_IWLOGO --new-name DX2SDK_CustomLogo --dds "C:\Work\replacement.dds" --output "C:\DX2CustomTrial"

For this logo example use a 512x128 DXT1 DDS with ten mip levels.
The output contains Maps/MainMenu_GFXALL.ibd, Maps/Kernel_GFXALL.ibd,
MatLib/UI_METAGAME.mlb and trial.json, generated from the user's inputs.

Use the receipt to verify a complete disposable game copy's original
files. Test the existing-resource marker from #205 first. Restore the
originals, then test the two new IBD candidates together with the
standalone library unchanged. Restore again, and test the two IBD
candidates plus the updated standalone library. Close the game between
trials and restore all original files at the end. Do not treat a
negative observation as proof of a particular loading order.

## Next priorities

Trace downstream resource registration and duplicate-resolution behavior
from the descriptor path. Establish an actual retail test of imported
assets. Continue resource format construction and native GMP actor
registration/BSP research separately. All runtime flags remain false.
