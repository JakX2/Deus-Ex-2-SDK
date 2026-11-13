# DX2Ed v0.96: read-only exact private Box OBJ round-trip audit

This adds an independently parsed **read-only** audit for v0.93/v0.95 editor-private clipped Box OBJ exports. An authored private Box specification or a single named `DX2Ed-prop-draft-v1` copy is paired with its exported local OBJ. The audit verifies bounded ASCII OBJ syntax, positive per-face winding, reciprocal oriented triangle edges, finite enclosed volume, bounded vertex/normal/face/triangle census and an exact byte-for-byte match against the independently preflighted canonical private export.

## Commands

```bash
python -m dx2sdk.private_brush_obj_audit private_box.json exported.obj
python -m dx2sdk.private_brush_obj_audit private_draft.json exported.obj --copy DraftProp_7
python -m unittest native_editor.tests.test_dx2sdk_private_brush_obj_audit -v
```

Success emits a JSON report with `exact_export_match=true`, canonical geometry/spec fingerprints and SHA-256 of the OBJ. Invalid files return exit 2, write nothing and report refusal on stderr.

## Explicit limitations and input boundaries

- This is a provenance **audit**, not a general OBJ import. A mesh edited in Blender is deliberately refused because vertex order, triangle layout, surface groups or decimal precision no longer match the source-private canonical exporter.
- Only regular `.json` (max 128 KiB) and `.obj` (max 128 KiB) are accepted. Symlinked OBJ paths, native `.gmp`/`.ibd` inputs, nonfinite coordinates, material references, arbitrary OBJ directives, out-of-range vertex indices, degenerate triangles and non-manifold meshes are refused.
- The audit does not load original game geometry, source actor files or game archives, does not write output, and does not modify original game assets.
- Native World BSP/CSG, UV/material binding, Havok/MOPP collision rebuilding, gameplay compilation, and retail runtime compatibility remain **unsupported and unverified**.

The regression uses synthetic half-Box and eight-corner cut geometry, deliberate invalid/tampered OBJ cases, a private draft selection, CLI success/failure and a byte-hashed synthetic GMP sentinel. The Windows prototype packager, offline doctor and bundle tests now require the audit module. T3Ed import/export capability is still **partial**.
