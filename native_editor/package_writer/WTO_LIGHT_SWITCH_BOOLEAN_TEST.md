# WTO Terminal: original bLightOn authored-Boolean runtime test

**Status (2026-11-02): USER-REPORTED IN-GAME VISUAL EFFECT.**
The user installed the separate LIGHTS OFF GUI candidate, reported that
it worked and that the WTO Terminal is darker, and supplied before/after
screenshots. This is a visible runtime observation, not an independently
measured lighting delta or an on-disk checksum attestation.

## Why another test?

The earlier user-tested ceiling-fixture EmissiveScale A/B experiment
showed no convincing visible difference. Original DX2 UnrealScript
described EmissiveScale as affecting **Flesh objects without a light**,
so testing it on ceiling fixtures was a poor property choice.

Original DX2 Engine.Actor declares GameSys property **1487 / bLightOn**,
type **bool**, Lighting category, with this source description:

> Whether a light is in the on state or not.

The user-supplied original WTO Terminal map has four existing
non-runtime authored GameSys bLightOn blocks on ceiling-light fixtures.
The code is 0x008005cf (T3SDK GamesysBlock type word 0x0080 for a single
Boolean byte). Every original data byte is **0x01 (true)**:

| Original export (one-based) | Actor | Absolute original 1-byte offset |
|---:|---|---:|
| 426 | \`D_298__4\` | 772889 |
| 1989 | \`D_298__12\` | 1055306 |
| 2027 | \`D_298__2\` | 1062475 |
| 2046 | \`D_298__14\` | 1067038 |

## Binary research

- Original source file \`M1_Seattle_Hub_WTOterminal.gmp\` SHA-256:
  \`a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa\`
- Derived LIGHTS OFF GMP SHA-256:
  \`868e7ae356d02c2c00165e74bffce9004fef3ce115ded5235f977c9da26c91a4\`
- Both files are **1,112,716 bytes**.
- Exactly **four bytes** differ: one \`01 -> 00\` at each of the four
  original byte offsets listed above.
- Every one of these four original blocks was decoded and independently
  cross-checked against the MIT T3SDK reader and the DX2 source audit.
- A **single** T3SDK PackageWriter updated all four original GameSys
  Boolean blocks in the original GMP; an independent writer replaced
  the four original source offsets directly. These two complete GMP
  byte streams agreed **exactly**, then T3SDK parsed the result and
  reconfirmed all four false values.
- No GUID, package table, export offset/size/flag, mesh or geometry data
  was modified.

## Changes to public SDK

\`native_editor/package_writer/dx2_gamesys_bool_probe.py\` is a separate
fail-closed original GameSys **one-byte authored Boolean** serializer
probe. It requires the source map SHA-256, original actor export/name,
unique original existing property ID, exact True/False byte, and a
non-runtime 0x0080 property with a one-byte value. It then requires
the entire edited GMP to match T3SDK's re-encoded object **and** an
independent source-offset edit. Source originals remain untouched.

An optional isolated copy writer creates a new same-name GMP outside
the source Maps folder and an adjacent research JSON; both are checked
after writing. These functions **do not** modify the existing four-byte
float/int probe, normal Godot Save As, or Inspector property editing.

Synthetic \`native_editor/tests/test_dx2_gamesys_bool_probe.py\`
covers byte-exact parity, original source immutability, output
isolation, stale SHA, wrong actor and property, encoding rejection,
runtime flags, bool \`0x02\`, non-boolean caller input, deliberately
faulty writer and no-overwrite guarantees.

## No-command Windows test bundle (not committed)

A user-specific ZIP of derived copyrighted game data was delivered
privately in the conversation:
\`DX2Ed_WTO_Real_Light_Switch_GUI.zip\`

The ZIP contains a generated LIGHTS OFF GMP (no original game map),
a verification report and a Windows PowerShell Forms GUI with
\`START_HERE.cmd\`. It requires choosing a **separate copied installation**
and confirming that fact. It recognizes the original WTO GMP, the
first single-emissive GMP, both earlier DIM/BRIGHT GMPs, and the new
LIGHTS OFF GMP by exact SHA-256.

- **INSTALL LIGHTS OFF** works only when the selected test copy
  contains the original verified source map. It creates or reuses
  the verified original backup before changing one selected map.
- **RESTORE ORIGINAL** uses the exact original validated backup,
  including one created by the preceding Windows GUI tests.
- Unknown map hashes, invalid backups and altered bundled files
  are refused. The GUI never guesses a compatible game build.
- No retail game content, source texture, edited proprietary GMP
  or in-game screenshot is checked into GitHub.

## User-reported in-game A/B result (2026-11-02)

After trying the delivered LIGHTS OFF Windows GUI candidate, the user wrote:

> "I checked the file you sent and it worked, it's darker now"

The user attached screenshots marked **before** and **after**, both showing
the WTO Terminal PEQUOD'S counter and seating area. The after view visibly
shows darker room surfaces, including the floor and furniture; the
PEQUOD'S sign and some bright fixture artwork remain luminous.

**Interpretation:** this is user-attested evidence that changing the four
original authored `bLightOn` Boolean flags can affect in-game scene
illumination. It is the first reported visible property effect of our
DX2 GameSys GMP edits, unlike the earlier inconclusive EmissiveScale A/B
test. Do not infer that every light actor responds identically or that
fixture emissive artwork is controlled by the same property.

**Evidence limits:** screenshots differ in viewpoint and NPC state; this
was not a same-camera pixel-calibrated comparison. The user's installed
GMP hash, game executable build, second launch, restored-original
retest, individual-fixture causality, save/load and mission transitions
were not independently verified. Images and proprietary game files remain
in the private conversation, not this repository.

## Runtime evidence boundary and next gate

The visually observed result is sufficient to advance the experimental
`bLightOn` path from *binary-only* to *user-reported visible runtime effect*.
It is **not** a green light for unrestricted Godot GameSys editing or
package rewriting.

Before exposing even a limited lighting control in the normal editor:
1. Confirm **RESTORE ORIGINAL** returns the same area to original brightness.
2. If practical, re-enter the map from a fresh load using the changed copy.
3. Isolate one original authored `bLightOn` field at a time to map which
   fixture affects which nearby surfaces; preserve exact SHA / byte gates.
4. Keep the change on an isolated test installation, never on the retail
   original. Do not enable runtime-owned fields, array/struct writes,
   new properties or actor spawning.


## Experimental Godot single-fixture Save As (follow-up)

The original GameSys Inspector in `native_editor/godot_editor/main.gd` now offers
an **experimental Save As: light OFF/ON** button only after selecting a map
actor with a verified **existing authored** `Engine.Actor.bLightOn` field
(GameSys ID 1487, `bool` encoding 0x0080, one byte, unflagged).
The sidecar remains read-only: this control does not create draft properties,
enable general GameSys writes, or modify the normal translation-only GMP
Save As pathway.

### How to use it

1. Launch the **Godot editor from a complete DX2SDK repository checkout**.
   The action uses the existing
   `native_editor/package_writer/dx2_gamesys_bool_probe.py` and its pinned
   MIT T3SDK dependency, which must remain alongside the editor.
2. Import the **unmodified** WTO Terminal GMP with its original DX2
   System folder so the source-backed GameSys audit is populated. The
   standard map editor import and visual preview must finish first.
3. In the **Hierarchy**, select a fixture actor carrying an authored
   `bLightOn` record, then select that record in the Inspector's
   **Original GameSys** panel. The experimental Save As button appears
   only for the supported Boolean. Other GameSys values remain view-only.
4. Click the button, choose a **separate isolated folder** for an output
   GMP with the **same original filename**, and review the explicit
   confirmation showing actor, one-based export and old/new state.
5. After accepting, the standalone Boolean probe pins source GMP SHA,
   original export/name, property ID, exact prior Boolean and original
   payload offset. It requires **whole-package byte parity** between
   the T3SDK serializer and an independent one-byte source edit.
   Output is new-only and is reparsed after writing; an adjacent
   `*.dx2ed-gamesys-bool.json` report is retained. The source GMP is
   never modified.
6. Only after inspecting the output and its manifest, manually test it in
   a **disposable copied game installation**. Restore the original GMP
   before the next experiment.

### Deliberate restrictions and release status

- No overwrite, batch changes, actor creation, property insertion,
  runtime-owned Boolean edits or wrong-name output.
- Selection, original source SHA and visible actor/field identity are
  checked again at confirmation, not just when the button appears.
- Only **one existing authored bLightOn** record changes per output map.
  Testing the four fixtures requires four distinct outputs and restoring
  the original baseline between tests; do not concatenate edits through
  the single-field tool.
- The generated map is **not automatically installed** into the game.
- `native_edit_supported` in the source audit stays **false** because
  native GameSys writing is not generally supported.
- The earlier four-light `bLightOn` in-game observation remains user
  reported. **This new per-light Godot workflow has not yet been tested
  in-game or on the user's Windows setup.**
- The repo's existing asset-free Godot smoke test now covers visibility for
  a verified `bLightOn` record and rejection of runtime bits, non-Boolean
  encodings and numeric lookalike values. The original standalone
  Python Boolean parity suite remains unchanged.

**Next gate:** run Godot headless smoke and Python tests for this commit,
then verify a one-fixture isolated map loads and returns to normal after
restoring the source GMP. Do not merge the draft PR on UI tests alone.


## Source-verified retail map and four one-light candidates (2026-11-02)

The user authorized reading the **DX2 project folder on Google Drive**.
The downloaded `maps.zip` includes the original WTO Terminal GMP and its
matching `m1_hub_wtoterminal.ibd`. The GMP is **1,112,716 bytes** and hashes
exactly to the original baseline already pinned in this document:
`a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa`.

All four earlier-proven authored `bLightOn=true` payload offsets contain
`01`, immediately following the identical original 12-byte prefix
`cf 05 80 00 01 00 00 00 01 00 00 00`
(GameSys ID 1487, type word 0x0080, version 1, data length 1).

A **private** no-Python Windows Forms A/B package was prepared from the user's
identical original GMP. Every map is independently derived from the same
baseline by setting only **one** original authored Boolean byte to zero;
all other bytes, package tables, actors, meshes and GUID stay unchanged.

| Original actor | Export | One changed offset | Candidate SHA-256 |
|---|---:|---:|---|
| `D_298__4` | 426 | 772889 | `65b94ce9f30683db823ae2a99e70eb855112813af6f37a32da49458c7499ac0d` |
| `D_298__12` | 1989 | 1055306 | `0abe7993cbc83bbe47ebb235df5d2e68457da9fd3620228292cab2998ed2356f` |
| `D_298__2` | 2027 | 1062475 | `4589145311cf09903491b1de9160234316592787d0fe6edf93c46e9cdb37e3a7` |
| `D_298__14` | 2046 | 1067038 | `44f599046cd63208134b810b376343d391ff5de0d2f90a62d57691d09c745e74` |

The private GUI verifies baseline/candidate whole-file hashes **and** checks
that the selected GMP differs by exactly the pinned Boolean byte before
installation. It requires an explicitly confirmed separate test game's
`Content/DX2/Maps` directory, retains a hash-verified original backup,
supports restoring that backup and refuses unknown map hashes or overwriting
unknown backups. The user can compare fixtures one at a time and return to
the original lighting.

**Status:** structural/byte integrity verified against the original user's
map; **new Windows GUI and individually altered GMPs have NOT been tested
in game**. Do not publish proprietary derived GMPs in GitHub; keep the PR
draft. The earlier four-light screenshot remains the only in-game light
switch result reported so far.

### Direct GMP import correction

The Godot viewer's direct `.gmp` import previously cleared the System path.
It can now use the recognized `<install>/System` sibling of
`<install>/Content/DX2/Maps`, or a manually selected original DX2 System
directory, when `Engine.d2u` and `DX2Gamesys.d2u` are both present.
It still refuses to reuse unrelated ZIP-staged paths. This allows the
source-verified GameSys panel to appear during ordinary full-installation
imports and does not grant any new serializer permissions.


## User A/B feedback: individual OFF did not visibly reproduce four-light effect

On 2026-11-02, after receiving the isolated single-light GUI bundle,
the user reported:

> "I don't see any difference. Previous test was more effective"

**Interpretation boundary:** one or more single-fixture trials were visually
inconclusive. The user did not identify precisely which of the four isolated
variants they tested, supply a current on-disk test GMP checksum, or confirm
same-viewpoint original restore for this trial. It is incorrect to mark every
single-light variant as runtime tested or visually effective.

The prior four-light simultaneous `bLightOn` OFF experiment remains the
strongest positive evidence, with user-reported screenshots showing visible
room darkening. Possible reasons for the discrepancy include overlapping light
contributions, actor position relative to the camera, baked illumination,
adaptation or the game using separate fixture/emissive components. None is
established by the available evidence.

### Next controlled isolation step (private experimental binaries only)

A separate, restore-safe Windows Forms GUI test bundle was prepared against
the identical verified original WTO Terminal map, with **two pair tests**,
**four leave-one-ON triple tests**, and the **verified four-light OFF control**.
Every candidate changes only its two, three or four originally authored
`bLightOn` Boolean bytes, with exact byte offsets and full-package SHA-256
recorded in a private `verification.json`.

The all-four control reproduces exactly the earlier independently verified
four-light candidate SHA:
`868e7ae356d02c2c00165e74bffce9004fef3ce115ded5235f977c9da26c91a4`.

If PAIR A and PAIR B show no effect but ALL FOUR still darkens the scene,
test the leave-one-ON TRIPLE cases. Compare the same PEQUOD'S viewpoint after
fresh map entry, restoring original between trials. New grouped candidates
are **binary-verified but not yet game-runtime tested**. The public SDK retains
no proprietary modified map content. Godot's individual-field writer remains
separate and strictly one field per isolated Save As.
