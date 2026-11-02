# WTO Terminal: original bLightOn authored-Boolean runtime test

**Status (2026-11-02):** source-backed binary experiment prepared,
Windows no-command GUI package delivered to the user. **No game test
of this specific Boolean modification has yet been reported.**

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

## Runtime evidence boundary

The original game scripts strongly suggest bLightOn is more relevant
to a visible light switch than EmissiveScale. Nevertheless, an existing
light fixture can have baked lightmaps, a scripted state override or
a separate dynamic-light component. **A visible lighting change is a
hypothesis, not a demonstrated result.**

The prior user-reported load and stable exploration of a different
GameSys edit do **not** automatically establish bLightOn behavior.
Before extending general native GameSys writes, the next step is an
isolated game test with an on/off comparison and a successful restore.
