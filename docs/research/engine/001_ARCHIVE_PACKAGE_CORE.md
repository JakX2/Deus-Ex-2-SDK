# DX2 engine decompilation: archive and package core, pass 001

Status: static disassembly evidence, not original-runtime validation. This
pass starts the engine-first research branch, independent of the historical
SDK and editor work. Function names below are research labels unless an
embedded diagnostic explicitly supports the name.

## Binary identity

Source: owner-supplied DX2 System archive, locally inspected. Both original
PE images match the existing hash-only manifest. Main analysis target:
DX2Main.exe (6,111,232 bytes), SHA-256
f31db8c8d5c6ce33a4d8f4e0025e246dd3823026518f01f8bfa731a38f446692.
PE32 i386, preferred image base 0x00400000, entry VA 0x00833C5A.
The smaller dx2.exe is a separate image, not the target for these addresses.
No proprietary executable or full disassembly is committed.

## Function evidence ledger

All ranges are preferred virtual addresses, end exclusive. Direct CALL
counts are from GNU objdump linear disassembly of .text; these are leads,
not a complete control-flow-aware xref count. No indirect calls included.

| VA start | VA end | Direct call sites | Research identification | Status |
| --- | --- | ---: | --- | --- |
| 0x00409920 | 0x00409937 | 10 | Archive transfer, 1 byte | Static body verified |
| 0x00409940 | 0x00409957 | 7 | Archive transfer, 2 bytes | Static body verified |
| 0x00409960 | 0x00409977 | 15 | Archive transfer, 4 bytes | Static body verified |
| 0x005B7390 | 0x005B753F | 157 | Compact signed index serialization | Static behavior reconstructed privately |
| 0x005EA200 | 0x005EA240 | 10 | Four sequential 4-byte transfers | Static body verified; type provisional |
| 0x005F0CC0 | 0x005F0CC6 | 26 | Constant 69 getter; licensee-version candidate | Static body verified |
| 0x005F3610 | 0x005F3649 | 2 | FPackageFileSummary constructor candidate | Strong diagnostic-name evidence |
| 0x005F4650 | 0x005F4897 | 4 | FPackageFileSummary archive serialization candidate | Partial static analysis |

The original spans are fingerprinted in the accompanying JSON. The
first three wrappers take two stack arguments (archive, destination), call
virtual slot +0x04 with the fixed byte length, and return the archive in EAX.
Caller cleanup is consistent with cdecl. No native class ABI is implemented.

## Compact index routine (0x005B7390)

The function takes an archive pointer and a pointer to a 32-bit value,
returning the archive pointer. Both archive fields +0x14 and +0x18 are
tested: when both are zero it transfers four bytes directly through
virtual slot +0x04. Otherwise it transfers between one and five bytes.

Evidence checkpoints:

- 0x005B7396–0x005B73B6: mode checks and raw-width fallback.
- 0x005B73BE–0x005B73FB: signed magnitude, first byte and transfer.
- 0x005B7402–0x005B74B9: continuation-controlled individual byte transfers.
- 0x005B74BC–0x005B7513: 32-bit reconstruction and sign restoration.
- 0x005B7515–0x005B7534: archive +0x18 enables comparison with the
  original input; mismatch diagnostic call at 0x005B752F.

The first byte has six magnitude bits, continuation bit 0x40 and sign bit
0x80. Intermediate bytes have seven payload bits and continuation bit
0x80. If the fourth byte continues, the fifth byte is transferred and the
accumulation proceeds with ordinary 32-bit arithmetic; there is no
sixth-byte loop or explicit canonicality/overflow check in this body.
Transfer failures and archive diagnostics remain dependent on the actual
virtual implementation. The probable loading/saving interpretation of
the flags remains provisional until concrete archive implementations are
identified. This is not a proposed hardened file parser.

A private, independent C++ behavioral reconstruction compiled with
G++ C++17 and strict warning flags. Ten known-answer canonical values,
10,000 synthetic encode/decode round trips, four noncanonical decode
cases and raw-mode read/write passed. This checks the model, not the
original function. An isolated i386 ELF original-function harness was
assembled and linked, but execution returned Exec format error in the
current environment. No original-function differential test passed or
is claimed. Keep reconstructed source private pending the project's
licensing/provenance decision; public evidence is address/hash metadata
and independently authored observations only.

## Package summary and linker evidence

The diagnostic referenced at 0x005F3616 identifies FPackageFileSummary's
constructor, supporting the candidate at 0x005F3610. It initializes a
member at +0x44 via 0x005D9910 then clears 0x50 bytes of object storage.
The related constructor sequence at 0x005F367B embeds that summary at
linker +0x30. Diagnostics at 0x005F36B8, 0x005F36CF and 0x005F36E6
identify ULinker NameMap, ImportMap and ExportMap, respectively. Their
observed member offsets are +0x80, +0x8C, +0x98. These are native
observations, not recovered complete C++ definitions.

The serializer at 0x005F4650 transfers nine successive 4-byte fields
at summary +0x00 through +0x20. It branches on the upper 16 bits of
the version word at +0x04 (threshold 29), and later on the lower
16 bits (threshold 68). The generation-related diagnostic referenced
at 0x005F474E supports the association with the array at +0x44.
Its four direct call sites are 0x005C688E, 0x005C75C4, 0x005F5D50 and
0x00606462. At 0x005F5DF0 the caller checks the UE package tag
0x9E2A83C1. At 0x005F5E96 it compares the low version against 60.
At 0x005F682C the complementary path writes the tag; the version
construction at 0x005F6833–0x005F6871 uses low 16-bit value 95 and
a helper returning 69 when the observed branch selects it.
The helper at 0x005F0CC0 always returns integer 69; its exact
original source name has not been recovered.

An independent header-only audit of all 19 user-owned Seattle maps
found the expected package tag and version 95 in every map; upper
version counts are 65:3, 67:3, 68:12, 69:1. This corroborates the
binary observations without establishing all summary field meanings.

The routine at 0x005EA200 transfers four consecutive 4-byte fields.
It is called within the summary serializer at 0x005F4728 and
0x005F4805, supporting (but not proving) a GUID-like helper type.
Do not declare a native class or field type based solely on width.

## Next evidence targets

- Recover concrete archive vtables and transfer implementations.
- Confirm archive mode flags and calling conventions from constructor
  and reader/writer call paths.
- Recover NameMap, ImportMap and ExportMap element serialization from
  the load/save paths around the package-summary callers.
- Run the compact-index original-function differential test on a
  compatible isolated x86 environment before claiming equivalence.

Reproduction: verify the original PE hash, use GNU objdump -h to confirm
.text VA/file mapping, then objdump -d -Mintel with the recorded
--start-address and --stop-address. Do not upload the output containing
original instructions. The JSON ledger uses hashes of source spans
rather than the original bytes. No SDK code or game assets changed.
