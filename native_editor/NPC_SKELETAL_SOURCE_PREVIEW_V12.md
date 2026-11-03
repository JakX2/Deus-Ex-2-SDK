# DX2Ed v12: original AI origins & skeletal metadata (NOT full NPC rendering)

Status: **source-only research / editor preview**. This does not create,
rig, pose, animate or natively spawn a character. It makes missing bodies
and source dependency relationships discoverable before any unsafe writer.

## Source observations

The user's original private `maps.zip` includes `m1_hub.ibd`.
Its validated IBD resource table (0x130-byte records) contains:

- **151** type-4 static meshes, including accessory resources such as
  `generic_glasses_M`, `generic_felt_hat_M`, `generic_beanie_M`,
  `trooper_wto_hat_M`;
- **9** type-16 skeletal meshes, including `generic_male`,
  `trooper_male`, `order_soldierF_def`, `chad_def`;
- **7** type-17 skeletal animation resources, including `wto` and
  `billie`.

Current `dx2level.py` exports type-4 placed static meshes, not the
skinned geometry in type-16 resources. This explains floating headwear
in a preview as a credible pipeline issue; it does **not** establish
whether every specific hat belongs to a missing in-map NPC or how the
retail game renders that person.

The user's original `SkeletalMeshes.zip` contains **114** `.pro`
models, **114** `.ski` descriptors (and 25 `.RGD` files).
The 114 `.ski` files are all parsed by the checked v2-v5
descriptor structure: 17 v2, 10 v3, 27 v4 and 60 v5.

Original descriptor references:
- `generic_male.ski` names animation set `wto`;
- `trooper_male.ski` names `wto`;
- `chad_def.ski` names `wto`;
- `order_soldierF_def.ski` names `billie`.

The `.ski` animation-set reference is **not** a verified relationship
between a map actor class and this mesh. It does not decode `.pro`,
bone positions, weights, skin materials or animation frames.

The screenshots provided show floating hat/headwear meshes within
Seattle Hub. A specific source actor identity for the accessories
was not determined from those screenshots alone.

## Editor usage (Godot 4.3+)

1. Load original `M1_Seattle_hub.gmp` and matching IBD bundles.
2. Enable **AI origins (capsule proxies)** in the top toolbar.
   Cyan translucent editor-only capsules appear at source-verified
   actors on original GameSys editor property 82 = `AI`.
   Click a capsule to select the source actor. Press F to focus.
   These are *unverified AI-layer candidates*, not literal NPC bodies.
3. In **Assets**, filter **Skeletal meshes** or **Skeletal animations**
   to see original IBD names and sizes.
4. Select **Open original SkeletalMeshes.zip (read-only)** and choose
   the original archive. This invokes the standalone Python 3
   `dx2_skeletal_ski_inventory.py` metadata reader. It returns
   structured metadata in memory only. The Inspector displays
   `.ski` version, availability of corresponding `.pro`,
   source transform and declared animation set for selected
   skeletal mesh assets. It does **not** make them placeable.
5. Disable the capsule toggle to avoid clutter. A new map clears
   actor origins. Nothing gets added to GMP or editable prop drafts.

CLI audit without Godot:

```powershell
python native_editor/godot_editor/backend/dx2_skeletal_ski_inventory.py "C:\DX2\SkeletalMeshes.zip"
```

Optional `--output C:\DX2EdResearch\skeletal-metadata.json`
writes a **new** JSON report (no overwrites).

## Native NPC placement requirements

Before a playable NPC can be spawned safely, we must resolve:
1. Original `D_*` actor class / GameSys archetype to **SkeletalTag**
   or equivalent actual geometry and material selection.
2. Skeletal `.pro` geometry/bones/weights + `.ski` configuration
   + `.pan` animations, with original skin/material variants.
3. Headwear and accessories attached to named bones and sockets,
   not simply parented at actor XYZ.
4. Actor native state frame, Level list, physics/ragdoll, nav,
   AI sensory state, inventory, dialogue and script links.
5. Guarded native Save As on a disposable source-bound map,
   independent reparse, then retail runtime test.

Never silently re-label an AI candidate as a verified NPC or offer
`StaticMeshActor` duplication as a character spawner.

## Validation

Synthetic Godot headless checks cover exact source coordinates,
click/visibility behavior and source/draft immutability. Python
unit tests cover v2-v5 original descriptor grammars and unsafe
ZIP members. Windows interactive visualization and actual skeletal
bodies remain pending.
