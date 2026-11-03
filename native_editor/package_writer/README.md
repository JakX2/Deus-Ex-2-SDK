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

## Fourth milestone: original GameSys property inventory and declaration schema

This phase connects **DX2-specific source declarations** to original cooked
GameSys blocks, **without enabling native GameSys writes**.

- dx2_gamesys_schema.py loads the user's original System folder or System
  ZIP containing *.d2u script packages, extracts TextBuffer declarations,
  and uses the MIT-licensed T3SDK parser **against DX2 sources**, not
  against the Thief 3 property table. It records source property IDs,
  declared names, types, categories, editor descriptions, owner classes,
  original package SHA-256 and ambiguous declarations. The original
  UnrealScript source bodies are not published.
- dx2_gamesys_audit.py independently scans every source actor's serialized
  GameSys block IDs, version numbers, original offsets and exact byte
  lengths using DX2SDK's tagged actor parser. It then **checks each
  block** against the T3SDK GamesysBlock reader, including the raw
  payload bytes. It can validate an existing DX2Ed actors.json against
  the source map's exact SHA-256 and actor export indices.
- The original DX2Ed decoder labels raw encoding code **0x0040** as
  "unknown", whereas T3SDK labels the same opaque value "type0x40".
  That single raw encoding is admitted as a **label alias only**.
  No interpretation or editing of this unknown encoding is attempted.
- Source names and declared types are **editor metadata only**. They do
  not prove runtime actor inheritance, event graph edges, correct array
  element references, or playable GameSys edits.

### CLI

With original game data supplied locally:

    python native_editor/package_writer/dx2_gamesys_schema.py "C:\DX2\System" --output "C:\DX2EdResearch\dx2-gamesys-declarations.json"

    python native_editor/package_writer/dx2_gamesys_audit.py "C:\DX2\Content\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --system "C:\DX2\System" --actors "C:\DX2EdCache\WTO\actors.json" --output "C:\DX2EdResearch\WTO-gamesys-audit.json"

The schema CLI also accepts the original System ZIP. The audit CLI accepts
that same folder/ZIP, the resulting rich schema JSON, or the existing
DX2Ed dx2-catalog-0.1 JSON as --system.

Both default to fail-closed source verification. The audit's optional
--allow-partial is **for diagnostics only**: it explicitly records
unverified actors without fabricating source values. Both tools create
new JSON files and refuse overwrites.

### Direct original-file research results

Original System(3).zip source TextBuffers declare **1,126 distinct
GameSys property IDs**, with zero name/type ID conflicts in the
current original archive. For example, Engine.Actor declares **ID 92
TriggerScripts** with source type **array<name>**, under the Scripts
editor category; this **does not** establish the runtime mapping of
cooked numeric array elements to TS_*.tsd filenames.

| Original GMP | State-frame exports | Original blocks | Source-labeled blocks |
|---|---:|---:|---:|
| WTO Terminal | 1,058 | 5,177 | 5,177 |
| Seattle Club | 1,640 | 7,637 | 7,636 |

The old WTO actor cache contains 1,033 map actors with 5,075 blocks;
their source IDs, version and encodings match the original data once
the **11 opaque 0x0040** labels are normalized. The additional
state-frame exports are not necessarily actors placed in the scene.

The 2005 original Thief 3 editor binaries and retail game data are
not committed. The upstream MIT T3SDK source and license are included,
and synthetic automated regression tests cover GameSys boundaries,
corrupted sizes, source declarations, source-hash-pinned cache identity
and unknown native block types.

**Not yet available**: GameSys property editing, array or struct
reserialization, native actor creation, native IBD rebuild, game
install or playable mission compilation. These require native
round-trip tests and isolated game runtime verification.

## Fifth milestone: original DX2Gamesys archetype class hierarchy

The upstream MIT T3SDK archetype parser (t3gamesys.py, now vendored
unchanged with pinned SHA) can read most of the original DX2 class
defaults from System/DX2Gamesys.d2u, not just map-placed actor instances.

    python native_editor/package_writer/dx2_gamesys_archetype_audit.py "C:\DX2\System" --declarations "C:\DX2EdResearch\dx2-gamesys-declarations.json" --output "C:\DX2EdResearch\dx2-gamesys-archetypes.json"

The same source argument accepts the user's own System ZIP or the
standalone original DX2Gamesys.d2u. Output includes original archetype
name and display label, immediate parent, conservative source
inheritance chain, local GameSys default identifiers/types/byte sizes
and source hashes. No original GameSys binary data is included.

Local original-file result:
- **2,476** DX2 archetype class records detected.
- **2,419** parsed by upstream T3SDK unchanged.
- **57** class layouts require additional DX2-specific reverse engineering.
- **2,418** ancestry chains have no unparsed or missing source ancestor.
- **58** ancestry chains incomplete (57 unparsed, one descendant).
- **9,259** locally parsed default property blocks across parsed classes.

This is partial decoding, **not proof that these archetypes can be
instantiated correctly**. Some source classes have layout discrepancies
from T3SDK's expected Thief 3 format. Their ancestors/descendants are
flagged until verified. Inherited defaults are NOT treated as complete
where any source parent failed.

The original source-derived metadata was also used to generate an
offline read-only local archetype browser for testing, showing examples
such as the original GenericHuman class and its immediate source
defaults. This does not enable actors to be added to a native GMP or
spawned in the game.

## Sixth milestone: original DX2 vulnerability and biomod grouped defaults

The original T3SDK archetype parser had previously reported 57 incomplete
source classes. **None were missing**: T3SDK read their names, display
labels, inheritance parents and normal source prefix before encountering
repeated GameSys values it interpreted as separate blocks.

DX2Ed now includes a **separate, strictly read-only DX2-specific decoder**
at `native_editor/package_writer/dx2_gamesys_archetype_arrays.py`.
It validates the complete original UClass preamble, tagged defaults,
all Group ID / element count / per-element byte length fields, and the
original export's exact ending offset. It does **not** modify upstream
MIT T3SDK code or create/serialize native actors.

Local inspection of the supplied original DX2Gamesys.d2u established
these observed multi-element encodings:

| Encoded property ID | Original item count | Classes containing it | Contents |
|---|---:|---:|---|
| `0x000803bf` | 29 | 42 | Tagged vulnerability struct entries |
| `0x00040725` | 3 | 15 | Biomod level descriptions |
| `0x000804f0` | 3 | 1 | Biomod tagged modifier structs |
| `0x000804be` | 3 | 1 | Biomod tagged modifier structs |

For example, `D_1179` is the original **BotBasicVuln** class,
with parent `D_1198` (**PawnVulnerabilities**). One of its
29 tagged element records contains the source fields
`Vulnerability=1.0`, `MinHealthDamage=5.0`, and
`StimToHealthDamageFactor=0.5`.

The previous error claiming to read 21,708,672 bytes was **not a
missing asset**. It happened because the unmodified T3SDK parser
interpreted an element length as the beginning of a fresh GameSys
block and thereby lost synchronization.

**Original research result:** all **57** failing classes are recovered:
42 vulnerability classes and 15 biomod classes. The package contains
**2,476** archetype classes total, now **2,476 structurally decoded**,
with all **2,476 original parent chains verified** and zero remaining
original class-layout parse errors. Original T3SDK errors remain in the
JSON under `original_t3sdk_parse_error` for provenance.

Synthetic test cases cover 29-element vulnerability struct records,
3-element biomod strings and modifier structs, exact original lengths,
invalid item sizes, unknown multi-item encodings, truncated records
and inherited source-class completeness.

**Critical limit:** the recovery establishes source-level framing and
tagged value serialization only. It does **not** establish gameplay
semantics, native write support, inherited runtime resolution or
game-tested actor spawning. No `GameSys` Save As or BSP code is changed.

## Seventh milestone: original GameSys data in the Godot editor (read-only)

DX2Ed now creates an **optional, source-verified GameSys sidecar** in the
private map cache when importing a GMP **with the user's original System
folder/ZIP**:

    <cache folder>/gamesys_inspector.json

The source generator lives in
native_editor/godot_editor/backend/dx2_gamesys_inspector_sidecar.py.

It requires:
- a **matching source GMP and cached actors.json SHA-256**, map filename,
  original export index, actor name, block ID, version and sequence;
- a successful independent source GameSys block audit, including exact
  original payload byte extents and source declaration labels;
- a fully source-validated original DX2Gamesys archetype audit, including
  the 57 DX2-specific vulnerability/biomod records recovered by the
  supplementary grouped-element parser.

Existing cached GLBs are **not invalidated**. Old caches receive this
optional sidecar on the next normal import. If original System data was
not supplied or a new research decoder cannot verify a map, import still
works as before and the read-only panels simply remain unavailable.
No retail GMP, IBD, TSD or System source file is changed or written.

### Godot user interface

- **Inspector → Original GameSys | Verified read-only data**:
  select exactly one original actor from Scene/Hierarchy. Browse original
  GameSys blocks by ID/name/type and inspect the original cached value,
  source-declared type/class, encoded property ID, original binary offset,
  byte count and payload SHA-256. Search/filter is independent of draft
  actor-property controls, which remain unchanged.
- **GameSys sidebar tab**: browse original D_* archetype hierarchy,
  display labels, source parent chains and local property defaults,
  including recovered 29-element vulnerability structs and three-level
  biomod descriptions. This list is **not** a list of newly spawnable
  DX2 actors; the pre-existing Classes tab and visual-only template
  draft behavior remain untouched.

**Important:** The sidecar explicitly refuses to bind a placed map actor
to a D_* archetype based on matching display names or numeric suffixes.
That class/object mapping still needs research. Actor fields and source
defaults are separate evidence, not a computed runtime inheritance
resolution.

The native GMP writer, BSP construction, Auto Roll controls, draft
serialization and GameSys Save As are **not modified** by this work.

### Regression checks

- native_editor/tests/test_dx2_gamesys_inspector_sidecar.py:
  source SHA/actor export/property-order strict join, incomplete class
  refusal, unresolved script arrays preserved as source values and
  no game-source writes.
- native_editor/tests/test_dx2_gamesys_cache_integration.py:
  opt-in System behavior, cache re-use, stale-source sidecar refusal
  and nonfatal fallback when research decoders encounter unknown
  original records.

The Python and fixture checks run in GitHub Actions. **Godot GUI
interaction and in-game loading have not yet been tested on a local
Windows client**; these are separate release gates.

## Eighth milestone: exact native GameSys scalar serialization

The read-only property Inspector can now be complemented by a separate
**opt-in, strictly limited experimental native GMP writer** for a single
**existing** GameSys float32/int32 block on an **existing** actor:

    native_editor/package_writer/dx2_gamesys_scalar_probe.py

The first gate is still **memory-only**. It requires the exact original
GMP SHA-256, the original one-based actor export number AND name, one
unambiguous existing GameSys numeric ID, the original source numeric
value, and the proposed new value.

    python native_editor/package_writer/dx2_gamesys_scalar_probe.py "C:\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --source-sha256 ORIGINAL_HASH --actor-export 23 --actor-name D_464__1 --property-id 1586 --kind float --expect 0.49803924560546875 --replace 0.6

The tool verifies a **byte-identical no-op** baseline, then uses both:

- DX2SDK's independent native GameSys reader and original byte-offset
  replacement, limited to an existing 4-byte scalar payload.
- The unchanged, MIT-licensed T3SDK \`ActorEdit.set_block\` +
  \`PackageWriter.write\` path.

Both outputs must match **for every byte of the entire GMP**, and
**the only differences from the original are within the exact four
original payload bytes**. The source file is checked again for drift.
Any unknown type, duplicate property, unsupported runtime bit, wrong
original value or unexpected byte change aborts the operation.

### Experimental isolated Save As (optional)

**This does not enable or modify Godot's native Save As button.**
Users explicitly choosing \`--output\` can create a separate
*experimental* copy, never an in-place retail replacement:

    python native_editor/package_writer/dx2_gamesys_scalar_probe.py "C:\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --source-sha256 ORIGINAL_HASH --actor-export 23 --actor-name D_464__1 --property-id 1586 --kind float --expect 0.49803924560546875 --replace 0.6 --output "C:\DX2EdIsolatedTest\M1_Seattle_Hub_WTOterminal.gmp"

- Output filename must match the original and its directory must be
  outside the source map folder and its descendants.
- An existing output or manifest is **never overwritten**.
- Writes only after full in-memory serializer parity, then independently
  re-parses the binary GMP from disk and writes an adjacent
  \`*.dx2ed-gamesys-scalar.json\` report.
- Both report and tool explicitly say \`runtime_verified=false\`.
  **Do not copy this over retail files until a separate disposable
  game-installation test verifies it.**

Original file compatibility sampled **40 individual edits** across
two original user-owned GMPs: 20 WTO Terminal existing float32
GameSys fields and 20 Seattle Club existing int32 GameSys fields,
with exact complete-file parity between T3SDK and direct byte-patch
serializers, and no writes to source assets.

Original-source inventories contain 173 eligible 4-byte GameSys float
blocks and 19 int blocks in WTO Terminal, and 316 float plus 34 int
in Seattle Club. **The 40 sampled parity passes are not a claim that
all these candidate fields have been gameplay-tested**.

Native strings/names, object references, byte and bool flags, arrays,
structs, script references, class creation, GameSys inheritance and
IBD/TriggerScript write support remain disabled. Their encoding and
runtime meaning require separate evidence.

## Ninth milestone: independent binary preflight before an in-game test

Once the standalone experimental GameSys scalar Save As has created
a **separate** modified GMP and its adjacent research manifest,
\`dx2_gamesys_runtime_preflight.py\` can independently reopen
BOTH GMPs and prove they differ only in exactly the original four-byte
int32/float32 GameSys field.

    python native_editor/package_writer/dx2_gamesys_runtime_preflight.py --original "C:\DX2\Maps\M1_Seattle_Hub_WTOterminal.gmp" --candidate "C:\DX2EdIsolatedTest\M1_Seattle_Hub_WTOterminal.gmp" --report "C:\DX2EdIsolatedTest\preflight.json"

The tool does not edit, install or run the game. It requires the
exact manifest adjacent to the candidate, and independently confirms:
- the manifest's source/output SHA-256 values match **actual** files;
- each GMP's header, GUID, name/import/export metadata parses using
  both the DX2SDK reader and the MIT T3SDK package reader;
- original and modified actors have identical original export index,
  name, header, size and GameSys property ID/version/type;
- **all** changed bytes are within the same original four-byte numeric
  payload, with no other byte changed anywhere in the GMP;
- the original and modified float values are finite when relevant;
- an untouched original source file still matches the initial hash.

The checker refuses forged hash updates trying to conceal unrelated
GMP bytes, missing/reordered actor data, stale sources, changed
manifests and non-scalar or malformed GameSys blocks. It does not
trust a writer's previous success flag as evidence.

Success is reported only as
\`binary-preflight-passed-runtime-not-tested\`.
The output always includes \`game_runtime_tested: false\` and
\`gameplay_effect_confirmed: false\`. These booleans are not set to
true by this tool.

The separately documented manual Windows field test is in
[GAMESYS_RUNTIME_TEST.md](GAMESYS_RUNTIME_TEST.md).

### Original source confirmation

Rechecking the supplied original WTO Terminal GMP confirmed the
existing actor \`D_464__1\` (export 23), native GameSys property
\`1586\` (\`EmissiveScale\`), original float32 value
\`0.49803924560546875\`. The candidate value \`0.6\` differs at
four bytes starting at absolute offset **708948**. Both T3SDK's
actor serializer and the independently constructed four-byte patch
produced the same complete modified GMP in memory. No edited original
GMP was written or run in-game. The report is available locally to
the user, not checked into the public GitHub repository.

Automated tests use synthetic GMP fixtures for both float32 and
int32 preflight, overwritten/stale/forged manifests, altered data
outside the intended scalar and non-overwrite JSON report behavior.
No retail map binary is added to the SDK.

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
