# Original material patch primary UV basis

The expanded 92-byte vertex includes four equal primary UV pairs.
A largest-distance vertex pair and maximum-area third corner produce
a stable affine mapping for a source patch. Evaluate every original
corner, record maximum UV residual and plane residual, and allow
interpolated preview UV only at residual <=1e-4 and plane error <=.15.
Original surviving vertex UV values are preserved verbatim in preview.
Texture mapping is surface-locked during a supporting-plane translation.

The packed 32-byte vertex's final 8 bytes are not secondary float UVs.
Exploratory private source evidence across 19 maps:
* All 76,732 final u32 words are 0xffffffff.
* All 76,732 preceding words have upper byte FF and three vector bytes.
* The vector, decoded BGR with (byte-127.5)/127.5, is orthogonal to the
  expanded normal within .02 for all vertices. 76,525 have length within
  .02 of one.
* The geometric tangent derived from the source UV Jacobian is available
  at 76,728 vertices; its dot product with the decoded vector is above
  .98 at 76,475 vertices. This strongly supports a tangent-like meaning,
  but does not authenticate the exact engine quantization/averaging rule
  or final all-FF word semantics.
* 16,713 of 16,789 primary UV fits are within 1e-4, 16,788 within 1e-3.
  All have residual below .01; 16,785 basis planes have residual <=.15.

The original UV translation writer preserves both trailing words and
does not need to regenerate them for a constant texture shift. Future
geometry and UV rotation writers must handle tangent encoding explicitly.

    python research/dx2/inspect_level_polygon_uv_basis.py MAP.gmp

Use root, map_exporter and research/dx2 on PYTHONPATH. Source-only
aggregate audit; no map modification. Packaged corpus validation pending.
