# DX2Ed v0.36: integrated T3Ed-style face editing + private selection restoration

## Integration provenance

Draft PR #102 introduced strict preview selection persistence and preflight
during private scene reopening. Draft PR #103 introduced six-sided
box/wall/floor editor-only face In/Out editing with anchored opposing plane,
Undo/Redo, and real Godot project save/reopen smoke.

This branch integrates **both** using a genuine **two-parent merge** (one
parent is the #103 plus selection-resolved editor tree; the other is the
full #102 head). The main Godot editor now contains both features without
silently discarding either, and both original smoke suites remain packaged.

## Usable editor workflow

1. Open the Godot DX2Ed prototype (owner original map or synthetic demo).
2. From the Brush tool, create an editor-only Box/Wall/Floor.
3. In Inspector select any local face, press In or Out; changes are snapped
   to Grid m, preserve the other face, and support Ctrl+Z/Ctrl+Y.
4. Select the original rendered actor preview and the authored draft brush
   together. Save the **private editor draft** in the map cache.
5. Change the scene, then Load draft. It restores the moved original actor
   **preview**, rotated/dimensioned brush, selected original+draft objects,
   and the orthographic view/grid controls. Strict selection identity and
   brush/source preflight run before live edits are cleared.
6. The source-only real-Godot smoke checks this full sequence using wholly
   invented bytes and original-preview identities. The existing strict
   synthetic selection smoke from PR #102 also runs in the bundled Windows
   self-test.

## Boundaries

All geometry and selection changes are **preview-only**. The source-original
GMP/IBD, raw BSP/collision, Light, AI or authored TriggerScript data is not
written. No retail DX2 maps are bundled or tested in public CI. A private
Godot draft project is not a playable or game-cooked mission.

The next step is genuinely usable face **picking** inside the viewport,
surface materials/UV draft operations, and independently validated original
BSP/zone format evidence before any native level writer can be considered.
