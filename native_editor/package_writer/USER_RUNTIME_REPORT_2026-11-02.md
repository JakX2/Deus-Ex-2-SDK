# First user-reported DX2 GameSys GMP in-game load

Date reported: **2026-11-02**

## Original experimental modification

- Map: `M1_Seattle_Hub_WTOterminal.gmp` (WTO Terminal)
- Source actor export: `23`, original name `D_464__1`
- Existing GameSys property: `1586`, source-declared `EmissiveScale` (`float32`)
- Original scalar: `0.49803924560546875`
- Experimental scalar: `0.6`
- Edit: exactly the four original payload bytes, with unchanged overall GMP size
- Prior checks: upstream MIT T3SDK and independent DX2 raw-byte edit agree, original source preserved. The provided Windows test package included a generated edited GMP and a GUI installer/restorer for a separate game copy.

## User's field report

The user installed and tested the previously supplied no-command
WTO Terminal experimental test package, then wrote:

> "it worked"

They attached a screenshot depicting a running Invisible War scene
in WTO Terminal, with the expected interior, city backdrop, NPCs and
in-game HUD visible.

**Reported outcome:** WTO Terminal reached a rendered in-game scene
without an immediately reported crash following the experimental
map-install workflow.

**Evidence status:** *user-reported runtime smoke success; asset identity
and edited scalar not independently attested by the screenshot.*
The screenshot is available in the conversation and intentionally **not**
committed to this repository.

## What this does and does not prove

This is valuable first field evidence consistent with DX2 accepting
a native GMP whose existing GameSys float32 payload was edited using
DX2SDK's independently checked serialization path.

It is **not yet** conclusive proof that:

- the screenshot itself shows the exact edited GMP rather than a restored
  or cached unmodified version;
- the game consumed the **new** `EmissiveScale` value;
- the changed scalar produces an observable visual or gameplay effect;
- loading a save, re-entering the map, or saving with the edited package
  will succeed;
- other GameSys types, actors, maps, arrays, structs, name references,
  BSP changes, IBD bundles or native class spawning are supported.

No logs, target game executable version, on-disk test copy hash,
A/B comparison or second clean load were supplied.

## Suggested next GUI-only checks

1. In the **separate** test installation, while the edited map is active,
   walk around and interact with a nearby NPC to rule out an immediate
   post-load crash or frozen state.
2. If practical, enter a different area, return to WTO Terminal and
   confirm it reloads.
3. Use the provided GUI's **Restore original test map** button. Do not
   replace any files in the retail installation.
4. For a controlled experiment on the original property's actual effect,
   compare a fixed viewpoint before and after the edit, or select a
   deliberately visible, harmless numeric property for a new test.

Do not enable the Godot Inspector's general GameSys Save As yet. The
standalone experimental single-scalar writer and independent binary
preflight stay fenced off pending stronger game-runtime evidence.

**Current release gate:** reported first successful map load; gameplay
property semantics remain unverified.
