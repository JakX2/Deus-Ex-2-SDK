# Engine core pass 002: archive, linker and package tables

Binary-first continuation of [pass 001](001_ARCHIVE_PACKAGE_CORE.md).
Same SHA-256-pinned DX2Main.exe image. All eight previous function
span hashes were reproduced. The accompanying ledger adds 29 static
function observations, not 29 claims of complete decompilation.
The original runtime has not been executed. Labels are provisional.

## Archive mode and virtual dispatch

ULinkerLoad constructor at 0x005F57B0 installs the primary table
0x00932238 and secondary archive table 0x009321E0 at object +0xB8
(0x005F5857/0x005F585D). ULinkerSave at 0x005F6580 installs
0x00932328 and 0x009322D0. Both initialize archive version +0x04
to 95, +0x08 to 600 (meaning unknown), +0x0C to 69.
The loading flag +0x14 is set by 0x005F5D34; saving flag +0x18
by 0x005F68EF. This resolves the provisional mode flag identification
in pass 001. The loader replaces +0x04/+0x0C with the package
version halves after summary transfer (0x005F5D70/76).

Observed slots relative to each archive virtual table:

| Slot | Operation | Load target | Save target |
| --- | --- | --- | --- |
| +04 | byte transfer | 005F29D0 | 006065D0 |
| +08 | bit transfer | 005B6B80 | 005B6B80 |
| +0C | indirect four-byte transfer | 005B6BD0 | 005B6BD0 |
| +18 | object reference | 005C1BA0 | 005C1E90 |
| +1C | name reference | 005C1C10 | 005C1E50 |
| +28 | tell | 005F29B0 | 005EFCA0 |
| +2C | size | 005F29C0 | 005B5DE0 (not a forwarder) |
| +34 | seek | 005F29A0 | 005EFCB0 |

The load forwarders use the underlying archive at secondary object
+0x448 (full linker +0x500). Save byte/tell/seek forward to secondary
+0x34 (full linker +0xEC). These are observed offsets, not a complete
native C++ ABI. The bit transfer routine and +0x0C helper require
separate caller analysis before reconstruction.

Memory reader constructor 0x005F7FF0 installs vtable 0x009390E0.
Loading and +0x1C mode fields are set. Data pointer +0x44,
current position +0x48, length +0x4C, array member +0x34 and
pointer to that member +0x40. Slots +04/+28/+2C/+30/+34 target
0x005F80F0/0x005F80A0/0x005F80B0/0x005F80D0/0x005F80C0.
Observed operations transfer bytes and advance cursor, return cursor,
return length, compare cursor against length, and assign cursor.
The private host test buffer is intentionally not a native memory
archive or a faithful implementation of the original allocation policy.

## Linker arrays and reference transfer

Base constructor 0x005F3650 and loader loops establish:

| Full linker offset | Member | In-memory element size |
| --- | --- | --- |
| +30 | FPackageFileSummary | 80 bytes |
| +80 | NameMap | 4 bytes |
| +8C | ImportMap | 28 bytes |
| +98 | ExportMap | 36 bytes |
| +B8 | archive subobject | incomplete layout |

The loader reads a compact name index through the underlying archive,
checks it via 0x005D8910 and copies a NameMap element (0x005C1C10).
Save 0x005C1E50 and lookup 0x005F2B50 use two 16-bit components of
the native name handle to address the nested name remapping table.
Handle construction at 0x005C68E5..0x005C68FC independently supports
the two-component interpretation. NameIndices and ObjectIndices are
identified by constructor diagnostics; full-object offsets +0xFC and
+0xF0 respectively. Save-side object lookup 0x005F2B70 and reference
transfer 0x005C1E90 select a mapped object index or zero for null.
Load 0x005C1BA0 transfers the compact reference and calls 0x005F53B0:
zero means null, positive values select export index minus one,
negative values select import index by magnitude minus one.
Lazy resolution and object construction are not yet reconstructed.

## String and name-entry transfer

0x005DD180 uses compact signed length. Positive length reads bytes;
negative length reads two-byte units and maps values above 255 to
0x7F. A loaded length of one is cleared to an empty string. The
saving selector 0x005E1D40 returns one unconditionally in this
binary, selecting the narrow path. This is not a general Unicode
codec. Name entry function 0x005DE1F0 selects older raw NUL-terminated
byte transfer for archive engine versions below 64, otherwise the
string serializer, followed by a four-byte flags field. Legacy
name entry handling remains outside the private model's scope.

## Summary and table field evidence

The summary serializer 0x005F4650 and loader at 0x005F57B0 establish
the nine leading words: tag, packed version, flags (provisional
label), name count/offset, export count/offset, import count/offset.
For upper header version >=29, the summary +0x2C word is transferred;
saving records the current stream position at +0x30 beforehand.
For engine version >=68, a four-word GUID candidate and an array of
two-word generation records follow. The final two words, summary
+0x24 and +0x28, are controlled by the archive licensee field +0x0C
>=22, not directly by the header upper word. Loader diagnostics and
the code at 0x005F6123, 0x005F6150, 0x005F616C and 0x005F635A
identify these as forceLoadExports count/offset. Entries are raw
four-byte zero-based export indices.

In all 19 Seattle maps, the +0x2C offset is strictly inside the
first MyLevel export, 1,236 to 4,072 bytes into its payload.
It is neither the name-table boundary nor an export boundary.
The eight modern System packages have zero there. Meaning unresolved;
do not assign a field name based on location alone.

The load loops at 0x005F60C0..0x005F6121 and
0x005F61C0..0x005F6259 establish field transfer order. Import record:
compact name, compact name, raw word, compact name. Export record:
compact reference, compact reference, raw word, compact name, raw
flags word, compact serialized size and conditional compact offset
when size is nonzero. These are variable-width wire records, distinct
from the native 28/36-byte strides. Full semantic reconstruction of
object and class relationships is still pending.

## Independent original-package validation

Two independent approaches were used: a Python table boundary audit
and a private compiled C++17 behavioral transfer model.

| Corpus | Packages | Names | Imports | Exports | Force-load indices |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seattle original GMPs | 19 | 57662 | 3019 | 47613 | 0 |
| System original packages | 10 | 12039 | 334 | 12307 | 611 |
| Total | 29 | 69701 | 3353 | 59920 | 611 |

All 29 have engine version 95. Two System Entry packages have
licensee 27 and 72-byte summaries, the other 27 packages have
76-byte summaries. All observed names are narrow and nonempty.
All generation tail counts match the export/name counts.
Every export table ends at the original file boundary; every last
nonempty payload ends at the import table. Five System packages
exercise the force-load branch, and all 611 indices are valid and
unique within their own tables. The nonempty force tables occupy
the exact span between imports and exports. All 19 Seattle maps
have no force entries and contiguous import/export tables.

The private C++ model compiled with C++17 and -Wall -Wextra
-Wpedantic -Werror. Ten synthetic cases and 29 original summary,
name, import and export byte-exact reserialization checks passed.
No original engine execution, object instantiation, native ABI
validation, or legacy engine-version <68 summary reconstruction.
The model is not a new parser or production SDK; its test buffer
uses checked host-side operations, and only valid observed data
is claimed. It remains private pending licensing/provenance
review. No original executable, data, disassembly or reconstructed
function source is committed.

## Next targets

Trace export creation and preload into UObject serialization; recover
the exact source of summary +0x2C; identify the native name table
implementation and concrete file-backed archive. Validate original
functions by isolated execution where supported. No editor work
performed in this pass.
