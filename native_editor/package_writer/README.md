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
