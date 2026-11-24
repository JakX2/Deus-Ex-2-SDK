# DX2 IBD native integrity and same-size resource replacement (2026-11-24)

## Evidence from two independent sources

The owner's SHA-256-pinned 32-bit DX2Main.exe was inspected privately.
Independent x86 decoding revealed both a resource-bundle reader and a
writer using the same constants as tools/maps/dx2bundles.py:

* Reader compares the initial dword to 0xC0000001 and tests
  header[0x08] + header[0x0C] against a file-size value.
* Reader obtains the resource-table address by adding 0x34 to the
  header base, then advances by header[0x18] multiplied by 0x130 to
  find the part-size table.
* Writer initializes the magic, adjusts resource offsets by the
  aligned data start, and serializes fixed header, resource records
  and part-size table using 0x34, 0x130 and 4-byte units respectively.
* The reader copies the 20-byte header digest at offset 0x20, zeros
  those five dwords, conditionally initializes the SHA-1 state
  (the five standard SHA-1 IV constants), hashes data_start bytes
  starting at the header base, finalizes and compares the digest.
  This check is conditional; its runtime enable condition is not
  established.
* The writer clears the five digest dwords and passes header, resource
  table, part table and alignment padding through the same hash path.

These are bounded static observations, not a recovered callable engine
API. No proprietary instructions, original assets or code are included.

The archive named Maps code.zip in the owner's DX2 project was fetched
through the connected Drive and inspected privately. All 12 IBD members
were checked independently using Python hashlib and struct. The exact
rules confirmed by original stored digests:

1. Header digest = SHA1(bytes [0, data_start), replacing bytes
   [32,52) with twenty zero bytes). Includes table/alignment padding.
2. Per-resource digest = SHA1(bytes [offset, offset + size + padding)).
   The digest lives at resource-table record offset + 20, 20 bytes long.
3. Payload-only hashing does not match the stored resource digests in
   these 12 original bundles.

| Check | Verified |
| --- | ---: |
| IBD bundles | 12/12 |
| Header SHA-1 | 12/12 |
| Padded-resource SHA-1 | 2169/2169 |
| Part table records counted | 42953 |
| In-memory one-byte change, rehash, full digest recheck, reverse and exact original-byte comparison | 12/12 |

The private in-memory experiment flipped the first resource's first byte,
recomputed its padded digest and the enclosing header digest, checked
all resource digests, then reversed the modification. It proves the
integrity calculation and allowed byte ranges, not that arbitrary
payload changes are semantically valid. No modified retail archive
was installed or retained.

## New tool

`tools/maps/dx2_ibd_integrity.py` uses the existing structural Bundle
parser, with additional mandatory whole-archive digest validation.
The same-size replacement path leaves offsets, names, types, table
records other than the affected digest, part lengths and all padding
unchanged. Revalidates the complete candidate and compares every byte
outside three allowed ranges. Requires a pinned full-file SHA-256
and a new isolated output retaining the original filename. Does not
overwrite the source or an existing destination.

    python tools/maps/dx2_ibd_integrity.py audit "/owned/map.ibd"
    python tools/maps/dx2_ibd_integrity.py audit-zip "/owned/Maps code.zip"
    python tools/maps/dx2_ibd_integrity.py replace-same-size "/owned/map.ibd" --index 0 --payload "/private/replacement.bin" --source-sha256 <64-hex-original-sha256> --output "/isolated/map.ibd"

Replacement indices are zero-based source resource-table indices.
The supplied payload must have the exact original size and preserve the
meaning of every resource part; the tool verifies byte geometry and
digests, **not payload semantics**. This is deliberately opt-in and not
wired into the Godot editor. The legacy read-only parser is unchanged.

Six synthetic test cases cover nonzero alignment bytes, corrupt source
headers/resources, same-size replacement and reversal, rejected
unsupported sizes/indexes, ZIP audit/duplicate names, original pins
and isolated no-overwrite output.

## Related GMP observations

The original PE contains a package magic comparison and a separate
magic initialization using 0x9E2A83C1, matching the existing Unreal
package reader. The success branch checks a low-word package version
against 60; this is not proof of support for all later versions.

The previous GMP keyword candidate has an x86 frame prologue, reads
five stack argument slots and is followed by caller stack cleanup of
20 bytes (or 24 bytes when a following one-argument call shares
cleanup). The package-failure keyword candidate is inside another
routine, after an earlier unconditional jump, in an apparent error
path. Do not identify either routine's exact C++ signature or purpose
solely on this basis.

## Remaining work

- Validate resource payload semantics for one deliberately selected
  edit (e.g. an existing known texture or TriggerScript scalar).
- Retail runtime A/B test in a disposable game copy.
- Recover size-changing IBD table rebuilding, alignment handling,
  resource-specific serialization, and map/resource linkage.
- GMP native actor and BSP/collision writing remain separate tasks.

No new gameplay or native geometry functionality is claimed.
