# DX2Ed T3SDK-based GMP writer (no-op compatibility phase)

**Status:** research adapter. This proves binary **no-change reconstruction
only**, not gameplay-tested editing or level compilation.

## Rationale

Thief 3 and DX2 use related Ion Storm Unreal v95 packages. The MIT-licensed
T3SDK PackageWriter reconstructs the summary, names, imports, exports,
objects and padding while preserving unknown fields. DX2Ed's independent
dx2inspect.Package cross-checks the original.

The adapter requires both readers to agree on v95 version, DX2 licensee,
package GUID, names, table counts and each export's name, payload size and
offset. It refuses to write unless the reconstructed output is
**byte-identical** to the original.

Only DX2 v95 licensee 68 and 69 are allowed. Thief 3's v95 licensee 133
maps serve as a direct upstream control but are not accepted by the DX2
adapter.

## Commands

From the repository root (Python 3.11+):

    python native_editor/package_writer/dx2_package_roundtrip.py audit "C:\DX2\Content\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp"

Audit reads only and prints package identity, hashes and no-op parity.

To write an **identical copy only** into a separate test folder:

    python native_editor/package_writer/dx2_package_roundtrip.py copy "C:\DX2\Content\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --output "C:\DX2EdTestMaps\M1_Seattle_Hub_WTOterminal.gmp"

The adapter refuses source folders and their descendants, different output
filenames, existing GMP files and existing manifests. It writes an adjacent
dx2ed-roundtrip.json research report with runtime_game_verified=false.
The original input package is never modified.

This is **not evidence** that changed actor data, BSP, physics, scripts
or IBD resources will load in-game.

## Second milestone: cross-check edited Location bytes (in memory only)

DX2Ed now independently compares the upstream T3SDK PackageWriter's
same-sized set_object replacement against the existing DX2Ed
apply_location_plan byte-range writer for **existing StaticMeshActor
Location.X/Y/Z** changes. Both must produce exactly the same complete
GMP byte stream. The original draft constraints are reused, including
source SHA, actor export index, original transform basis (no Roll/rotation
changes), and absence of cloned objects or unsupported property edits.

    python native_editor/package_writer/dx2_package_roundtrip.py compare-translation "C:\DX2\Content\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --actors "C:\DX2EdCache\WTO\actors.json" --draft "C:\DX2EdCache\WTO\editor_draft.json"

The comparison reports the edited actor names, changed byte count, and
result hash, without saving a modified GMP. It refuses the result if the
two independently implemented serializers disagree by even one byte.
Synthetic CI verifies a real nested tagged FVector Location change and
rejection of edited rotation bases and new actor drafts.

**This is not an in-game test.** The unchanged DX2Ed experimental
Location-only Save As remains the separate way to create an edited GMP
for isolated retail testing, with its own manifest and binary verifier.
No new editor button or silently enabled native-save capability is added.


## Third milestone: existing tagged int32/float32 properties (read-only)

The new source-only inspector:
- native_editor/package_writer/dx2_native_scalar_catalog.py
- native_editor/package_writer/dx2_scalar_property_probe.py

uses T3SDK's strict actor layout together with **an independent DX2
tagged-property offset parser**. It only admits one **existing** four-byte
top-level tagged Int or Float in an original actor. It refuses duplicate
tags, array indices, missing properties, wrong source values, changed
original hashes, unrecognized actor names or export indices, and unknown
types. It leaves all other actor bytes, including GameSys and native
tails, entirely unchanged.

List verified original 32-bit scalar source fields:

    python native_editor/package_writer/dx2_native_scalar_catalog.py "C:\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --output "C:\DX2EdResearch\wto-scalars.json"

The output is source metadata only, **not** a claim that those properties
are safe to edit in-game. The catalog includes the SHA-256 needed for
strict source pinning. It refuses to overwrite existing research JSON.

Compare a single proposed value in memory, without writing a GMP:

    python native_editor/package_writer/dx2_scalar_property_probe.py "C:\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --source-sha256 ORIGINAL_GMP_SHA256 --actor-export EXPORT_NUMBER --actor-name SkyZoneInfo__0 --property DistanceFogEnd --kind float --expect 300.0 --replace 310.0

The process makes the same exact one-field change twice: once via
T3SDK's structured ActorEdit and once via DX2Ed's independent
field-level offsets. It refuses any full-package byte discrepancy,
unexpected change outside four bytes, or accidental table growth.
**The modified bytes exist in memory only**.

Direct original-file research (no modified files written):
- WTO Terminal SkyZoneInfo__0.DistanceFogEnd float32 300 -> 310:
  T3SDK serializer and independent four-byte replacement match exactly.
- Seattle Club LevelInfo__0.DistanceFogStart float32 500 -> 600:
  the two implementations match exactly.
- The original WTO actor corpus contains 1,058 state-frame exports and
  86 eligible unique top-level 32-bit scalar fields; Seattle Club has
  1,640 state-frame exports and 258 such fields. In both cases there were
  zero actor layout parse failures. These are not all the properties or
  GameSys values present in the map.
- Synthetic v95 native tests cover both int32 and float32 modification,
  stale hashes, wrong actor/value, absent tags, wrong type, no-op edits
  and rejection of exports without an actor state frame.

**Still unsupported:** gameplay semantics and any in-game runtime proof,
actual edited-GMP output from this new path, raw GameSys property edits,
nested typed structures, arrays, string/object references, new objects,
BSP or collision rebuilding, and native IBD resource editing.

## Original-file compatibility evidence

Tested locally using the unchanged T3SDK 0.3.1 reader and writer:

| Original package | UE version | Licensee | Source bytes | No-op rewrite |
|---|---:|---:|---:|---|
| M1_Seattle_Hub_WTOterminal.gmp | 95 | 68 | 1,112,716 | byte-exact |
| M1_Seattle_Club.gmp | 95 | 68 | 2,296,630 | byte-exact |
| T3 Tutorial3.gmp (upstream-only control) | 95 | 133 | 49,507 | byte-exact |

No game files are committed. CI uses independently assembled synthetic
packages, not proprietary maps.

## Next steps

1. Compare T3SDK same-size set_object edits against the SDK's established
   location-only GMP patch, requiring **identical modified bytes**.
2. Add typed property support only when unknown fields, state frames,
   actor links and native tails can be preserved.
3. Validate Level references before introducing new actors.
4. Develop a separate DX2 IBD writer. The DX2 resource-table entry is
   different from Thief 3's IBT entry and is NOT drop-in compatible.
5. Validate changes in a disposable original-game installation before
   making runtime claims.

## Third-party provenance

The files in third_party/t3sdk_assets were taken unchanged from the
MIT-licensed T3SDK contributor code at Veradictus/Thief3-Decomp,
tools/assets/, matching the user's T3SDK 0.3.1 release. The full original
MIT notice is retained in third_party/t3sdk_assets/LICENSE.

Retain that license and attribution with future adaptations.
