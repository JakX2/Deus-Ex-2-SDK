# DX2Ed v0.89: direct private Box cap rotation from the viewport

**Source-only editor feature.** This affects only Godot-authored private `Brush::Box` cutting planes, not game-native DX2 World BSP, Unreal CSG, Havok/MOPP collision or original GMP/IBD files.

## Interaction

On a selected, editor-authored Box with one to eight valid convex cutting planes, hold **Alt+Ctrl+Shift**, press the left mouse button on a **visible** cutting cap and drag:

- Moving horizontally rotates the selected face normal about the Box's **local Y** axis.
- Moving vertically rotates it about the Box's **local X** axis.
- Once the cursor has moved 12 screen pixels, the dominant initial direction locks the axis for that gesture. The chosen local axis remains fixed until mouse release, even if the pointer subsequently changes direction.
- Every 24 screen pixels corresponds to one **5°** snapped step; the total tilt is limited to **±30°** per gesture. This is an editing convenience, not physics or camera-space orientation.
- The plane rotates about the **area-weighted centroid of the original visible cap at mouse-down**. The cap's signed offset changes alongside its normal to preserve this pivot.
- Preview geometry is recomputed from the original mouse-down plane metadata on each movement. It cannot accumulate repeated incremental rotations or snapping drift.
- Only a fully validated, nonempty, closed, strictly shrinking convex preview may replace the prior mesh. A declined step leaves the last valid preview in place. Returning to the original angle restores the initial brush metadata.
- Releasing the left mouse button finishes with **exactly one Undo/Redo transaction** for a changed brush. Zero movement and a drag brought back to the original angle create **no history entry**.

The new gesture does not replace **Alt+Ctrl+drag** (normal offset), **Alt+Shift+click** (visible cap selection), ordinary **Alt+left** orbit, or Inspector **Y±5° / X±5°** rotation. A triple-modifier click that misses a private cap is consumed without falling through to imported actor selection or orbit manipulation.

## Safety and implementation

The existing `private_box_cap_picker.gd` rejects hidden caps, non-cap Box sides, ambiguous boundary hits, invalid transforms, and nonexistent cutters. A valid mouse-down captures the full private draft and Undo checkpoint. The existing `private_box_cap_rotate.gd` calculates the visible triangle-area centroid and validates each candidate through the full native-Godot private convex mesh pipeline. No rendering overlay is added to original game actor lists or serialized source data. The private project JSON format is unchanged.

The integration in `native_editor/godot_editor/main.gd` finishes a tilt on mouse release or when switching editor transform tools. Keyboard Undo/Redo finishes an active tilt before operating on history. This is intentionally separate from the offset-drag gesture, including separate input and state, to prevent accidental mixing.

## Regression coverage

The real Godot 4.3 `tests/smoke_private_box_cap_rotate.gd` now exercises the full viewport path on a synthetic two-plane Box:

1. Start on a visible x-cut, verify the selected clip index and no initial history entry.
2. Confirm subthreshold pointer movement is ignored; horizontal movement totaling 24px produces a 5° local Y pivoted turn while leaving the other plane untouched.
3. Mouse release adds exactly one Undo operation. Undo and Redo recover the complete respective cutter stacks.
4. Another gesture tilted forward and returned to zero restores the mouse-down source state without an Undo step.
5. A ray that first hits an uncut original Box side cannot enter the tilt.
6. Starting on the second cap, vertical movement tilts about local X independently, with Undo/Redo; imported original actors cannot access private clipping controls.

The existing real Godot native fixture workflow runs that test, with no proprietary game data and no retail game executable. The Windows source-only ZIP includes the same main/editor scripts as the previous version. The T3Ed `vertex_face` capability remains **partial**.

## Remaining milestones

This is not native DX2 polygon/BSP editing. Direct arbitrary 3D vertex/edge operations, real game CSG compilation, and game-authenticated collision regeneration are still required before player-created maps can load and behave correctly in Invisible War.
