## A/B runtime result and root-cause finding (2026-11-02)

The user ran both versions in *Invisible War* and supplied two
screenshots inside the PEQUOD'S area of WTO Terminal:

> "idk, I don't see any difference"

**Observed result:** both modified maps render and allow the test,
but **no convincing lighting change is visible** between the provided
screenshots. The camera positions, HUD and moving NPCs differ slightly,
so a quantitative same-pixel comparison is not justified. No crash
was reported for either A/B screenshot.

**Root cause of the unsuitable test property identified in original
DX2 source:** `Engine.d2u` (the source-declared `Engine.Actor`
property, ID 1586, `EmissiveScale`) carries this description:

> "0.0 = not emissive, 1.0 = fully emissive. This only applies to
> Flesh objects which don't have a light."

We changed `EmissiveScale` on *ceiling-light fixture* archetypes,
not on the documented *Flesh objects without a light*. That is a
source-backed explanation for why the lighting A/B experiment was
not expected to have a visible effect. It is a **test-target selection
error**, not an observed serializer failure. The choice of an out-of-range
`4.0` "bright" value was also outside the declaration's stated
0.0-to-1.0 full-emissive interpretation. Do not present this A/B
experiment as proof of GameSys visual effect.

**Better original-property candidate, not yet tested:**
`Engine.Actor.bLightOn` (property ID **1487**), declared as
`bool` in the `Lighting` category, with source description:

> "Whether a light is in the on state or not."

Original WTO Terminal GMP contains four non-runtime, one-byte,
existing `bLightOn = true` records for these `D_298` ceiling
fixture exports:

| Export | Actor | Raw payload offset | Original |
|---:|---|---:|---|
| 426 | `D_298__4` | 772889 | `01` |
| 1989 | `D_298__12` | 1055306 | `01` |
| 2027 | `D_298__2` | 1062475 | `01` |
| 2046 | `D_298__14` | 1067038 | `01` |

These are original `0x008005cf` one-byte bool blocks,
runtime flag off. **The existing experimental numeric scalar writer
supports only existing four-byte float32/int32 values** and must
not be bypassed. An independent one-byte bool editing/parity gate
and synthetic tests are prerequisites for any next GUI test. Even
`bLightOn` does not guarantee a visible dynamic-light difference
without game test because authored lighting may be precomputed.

### Interpretation

- The 11 A/B `EmissiveScale` fields were **serialized correctly**.
- The screenshots do **not** establish the editor can control
  in-game lamp brightness, which was the intended hypothesis.
- The earlier one-field GMP load/stable exploration evidence remains.
- Next candidate should be a semantically relevant source-defined
  lighting property, with guarded binary tests before user-facing GUI.

---

# WTO Terminal: ceiling-light EmissiveScale A/B test (GUI only)

**Status:** experimental test files prepared from the user's original
`M1_Seattle_Hub_WTOterminal.gmp`; NOT yet tested in the game's renderer.

## Purpose

Our earlier single-property GameSys edit was user-reported to load and
remain stable during normal exploration. The edited property, however,
was not visually identified. This follow-up tries a more noticeable
controlled comparison with the user's own original WTO Terminal map.

The original serialized `DrawScale` field on the sky dome was initially
considered, but **its encoded ID carries the runtime flag**. The strict
existing native scalar writer explicitly refuses runtime-flagged blocks,
so that option was rejected without weakening the safety gate.

Instead, the original source GameSys audit identified **11 existing
`D_298__*` ceiling-light fixture exports**, with
`1Hub_wto_term-detail6-b` meshes, each carrying authored non-runtime
GameSys ID **1586 = EmissiveScale**, source type `float32`, original
value **0.3764706254005432**, encoded block ID **0x00100632**.

Two separate source-derived test variants were prepared:

| Variant | Source values | Proposed values | Edited GMP SHA-256 |
|---|---:|---:|---|
| Dim | 0.3764706254 | 0.0 | `e4d76ea6fab1f70ab9770b271741ad3d15225e825fd08618602bb086126f14d1` |
| Bright | 0.3764706254 | 4.0 | `0a412b7fdf221316013c599435d708aef6a5123eeec8a4800090e4593397a112` |

Original map SHA-256:
`a6c68dd8b7b8ea0b1ee27dac4b5d18a57251297feb2f8ccb9f1bc40e317e17aa`

Original actor exports and original property payload offsets:

| Export (one-based) | Actor | GMP payload offset |
|---:|---|---:|
| 372 | `D_298__11` | 765257 |
| 426 | `D_298__4` | 772775 |
| 1904 | `D_298__0` | 1045267 |
| 1989 | `D_298__12` | 1055189 |
| 1992 | `D_298__8` | 1056014 |
| 2007 | `D_298__17` | 1058594 |
| 2009 | `D_298__5` | 1059133 |
| 2016 | `D_298__13` | 1060293 |
| 2027 | `D_298__2` | 1062358 |
| 2045 | `D_298__1` | 1066607 |
| 2046 | `D_298__14` | 1066917 |

## Verification performed locally

For **each** derived GMP, the unmodified MIT-licensed T3SDK
`ActorEdit.set_block`/`PackageWriter` rebuilt the package. A second
independent process applied precisely the original 11 four-byte field
replacements by original source offset. The complete GMP byte streams
matched **byte for byte**. Re-parsing the edited GMPs with T3SDK
confirmed exact value bytes, original export layout, package GUID and
unchanged name table. In each candidate, precisely **44 bytes changed**;
GMP length remained **1,112,716 bytes**.

No original retail GMP, IBD or other proprietary game asset is
committed to GitHub. The two source-derived experimental GMP copies
and the Windows PowerShell/Forms no-command install/restore helper
were delivered in the conversation as a private user-specific ZIP.

## Human-facing test

1. Extract the test ZIP and double-click `START_HERE.cmd`.
2. Choose only a **separate game installation copy**. The helper
   requires explicit confirmation and recognizes the original GMP,
   the previous single EmissiveScale test GMP, and both new variants.
   Switching from any edited map requires a verified original backup
   from the earlier GUI workflow; unknown maps are refused.
3. With the game closed, install **DIM**, launch the test game,
   enter WTO Terminal freshly and note the ceiling fixtures.
4. Close the game, install **BRIGHT**, enter the level again
   from roughly the same camera position, and compare visuals.
5. Close the game and use the new GUI's **RESTORE ORIGINAL** button.

**Do not use the prior one-edit test helper to restore these new
variants**: it does not recognize their hashes. The new helper
recognizes both and reuses the existing verified backup. The
Windows GUI is not runtime-tested in the Linux build environment.

## Evidence boundary

The expected visible lighting difference is **a hypothesis**.
The render engine may use baked lighting, another light property,
or only some of the selected fixtures. If both variants look
identical, that is an **inconclusive visual-effect test**, not proof
that native serialization failed. A crash is also a valuable result.

This is separate from the existing single-field writer and from
Godot's default native Save As. No runtime-flagged `DrawScale`
property, GameSys array/struct, actor creation or geometry edit is
enabled by this test. Normal retail game files remain untouched.
