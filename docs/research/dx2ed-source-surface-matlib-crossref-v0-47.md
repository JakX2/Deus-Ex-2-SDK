# DX2Ed v0.47: original source-surface to MatLib name cross-reference

## Purpose

T3Ed's original 2005 editor resources include face-drag and polygon editing
modes plus texture pan/rotate controls. The checked-in T3Ed parity plan records
those source archive observations and keeps them separate from DX2 format
claims. DX2Ed v0.47 adds a practical read-only bridge between its original
MOPP-linked source triangle inspector and the v0.41+ MatLib browser.

## Authenticated source side

The source collision picker consumes the validated original Level/MOPP
selection sidecar. For a selected terminal-leaf triangle it preserves the
original Level triangle ID, source block ID, packed Flesh render block ordinal,
render-section ordinal, observed render-material name, and source GMP basename
and SHA-256. The source section is identified by the original
block/render-block/section tuple, not by a material name alone.

## MatLib correlation

The panel joins the selected source render-material name to catalog material
names using exact case-sensitive equality first, then case-insensitive
equality only when there is no exact match. Multiple candidates are marked
ambiguous; no match means absent from the currently imported catalog. A
catalog-wide duplicate material-name count is shown because the current
inventory retains the first case-folded record rather than per-name variants.

A candidate shows its source bundle/label, raw category ID, flags and
stage-mask, all nine stage references and a SHA-256-verified slot-0 preview
when available. The preview is a decoded source texture thumbnail, not the
native DX2 shader result.

## Evidence boundary

A string match is a useful cross-reference, **not proof of a native surface
material index or binding**. The source collision triangle is a MOPP-linked
subset of the original Level geometry, not a complete editable BSP surface
database. No native material index is decoded, no shader-stage semantics are
inferred, and no physics material is assigned. The feature writes no GMP,
IBD, BSP, material, collision or lightmap data.

The T3SDK launcher archive is a separate third-party codebase from Ion Storm's
2005 T3Ed release. Its editor-dock and edit/pick scripts remain reference
material only; no T3SDK code is copied by this milestone.

## Regression coverage

The synthetic Godot 4.3 smoke checks exact, case-insensitive, ambiguous and
missing name matches; candidate selection; catalog-wide duplicate caveats;
hash-verified thumbnail display; path-traversal rejection; and refusal of
malformed source evidence. The existing source collision picker smoke checks
that a source triangle selection reaches this panel with its original IDs.
Fixtures are invented and contain no retail assets.
