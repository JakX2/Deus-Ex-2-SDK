# DX2Ed v0.44: MatLib stage-resource diagnostics

## User-facing workflow

Open **Materials**, import a user-owned IBD or Maps ZIP, and select a MatLib
record. The browser now shows a compact nine-slot audit:

- raw ordered slot references, including explicit empty and unresolved entries;
- the uninterpreted raw MatLib stage-mask integer;
- named, resolved, unresolved and empty slot counts;
- the referenced texture's raw numeric usage code, decoded format, dimensions,
  source bundle and the existing parser label;
- filters for texture usage codes 0 through 6.

The usage filters are based on the texture resource's parsed usage field. They
do not claim that a MatLib slot has a particular shader role. The parser's
labels (diffuse, normal, specular, mask, detail, emissive, environment) remain
labels, not proof of the material's runtime shader graph.

## Evidence and interpretation boundary

The checked-in `map_exporter/dx2textures.py` parser reads an observed
40-part MatLib record with nine ordered texture-name strings. It separately
reads texture resources and maps their numeric usage field through the
existing `USAGE` table. v0.44 preserves that numeric usage value as
`usage_code` in the private catalog so unknown values are not lost or guessed.

The UI intentionally reports `stage_mask` as raw hexadecimal and computes
only counts from the nine reference entries. It does not assume that the mask
bits correspond directly to slot positions, and it does not infer blending,
UV generation, animation, environment mapping, normal-map handling or
shader-stage execution order.

The existing slot-0 surface preview action is now labelled as a legacy
preview candidate. Its diffuse shader meaning has not been independently
verified. This correction is descriptive only; the preview-only data path
remains source-hash/thumbnail-hash checked and private.

## Compatibility and safety

- Existing v0.41/v0.42 catalogs without the additive `usage_code` field
  remain readable; those entries display an unknown raw usage code and do not
  match numeric usage filters.
- Unknown nonnegative 32-bit usage values are preserved as numbers and retain
  the parser's numeric fallback label.
- Negative or out-of-range synthetic values are rejected before catalog
  creation.
- IBD/Maps ZIP source files remain read-only. Only bounded preview PNGs and
  metadata are written under the private user cache.
- No original MatLib, shader, BSP surface index or GMP data is written.
- Native MatLib/BSP material writers, CSG/collision/lightmap cooking and
  retail runtime compatibility remain disabled or unverified.

## Regression coverage

The Python suite checks known, unknown and out-of-range texture usage codes.
The Godot 4.3 browser smoke creates synthetic slot-0 and slot-2 resources,
checks raw stage-mask presentation and exact slot counts, exercises a numeric
usage filter and a negative-control filter, and verifies that the slot-0 UI
does not claim verified diffuse shader semantics. All source data and preview
pixels are invented test fixtures.
