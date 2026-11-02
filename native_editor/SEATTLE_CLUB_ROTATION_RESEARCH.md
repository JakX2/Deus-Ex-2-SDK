# Seattle Club rotation reference audit (DX2Ed 0.5.6 research)

This report was generated locally from the user's **retail**
`M1_Seattle_Club.gmp` in `club(2).zip`. The analysis used the supplied
T3SDK 0.3.1 `upkg.py` v95 package reader and the DX2Ed read-only
`dx2_rotation_audit.py`. **No proprietary GMP/IBD bytes or asset arrays
are committed here.**

## Observations

| Measurement | Count |
| --- | ---: |
| Actors in the level actor list | 1,641 |
| `StaticMeshActor` instances | 845 |
| Static mesh actors with successfully resolved names | 833 |
| Static mesh actors with unresolved names | 12 |
| Resolved actors with nontrivial Roll inversion | 329 |
| Resolved actors with half-turn Roll (sign inversion is a no-op) | 49 |
| Resolved actors with zero/full-turn Roll | 455 |
| Static mesh actors with no explicit Rotation property | 91 |
| Actor-read parse errors in this pass | 0 |

Unresolved static mesh names are excluded from the read-only audit but
are **not evidence of invalid rotation**. Counting all static mesh actors,
the raw source Roll histogram is 461 with Roll 0, 55 with Roll 32768,
and 329 with other nonzero Roll values. The 12-name difference explains
why the mesh-linked classification sums to 833 instead of 845.

For the 329 nontrivial cases, the preliminary mesh-family counts include
`GEN_TRIM1-16ft` (64), `GEN_TRIM2-6ft` (40), `GEN_TRIM1-8ft` (34),
`GEN_TRIM2-16ft` (32), `GEN_TRIM2-8ft` (30), `GLO_LightPill_L` (24),
and 18 stair instances across the two previously investigated meshes.

The inverted-Roll preview matrices exactly match the numerical UE2
reference matrices computed directly by the supplied T3SDK `t3common.py`
over 2,500 randomized combinations of Pitch/Yaw/Roll (after converting
its column-vector Godot Basis into row-major form). This is an independent
source check of the transform algebra, **not** validation against a running
Invisible War renderer.

## Implications

1. Seattle Club's most useful test objects are stairs and repeating
   ceiling trims with nontrivial Roll. A global convention affects hundreds
   of placements, so the current Auto Roll option remains reversible.
2. A source Roll of 180 degrees is invariant under sign inversion;
   visually misplaced pipes with this Roll need investigation of a
   different axis, a mesh-local pivot, or another transform convention.
3. Spatially matching bounding boxes alone cannot establish orientation
   accuracy. Compare textured faces and endpoints with actual retail-game
   screenshots.

## Next validation

Use both **Auto Roll ON** and **OFF** in DX2Ed 0.5.5 with the original
Seattle Club and WTO Terminal maps, then capture exact Export IDs from
**Copy mesh info** for every misaligned object. Record the game reference,
original rotator and corrected/uncorrected appearance. Do not modify game
files or promote the hypothesis to a permanent GMP rewrite.
