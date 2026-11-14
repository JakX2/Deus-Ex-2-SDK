# DX2Ed v0.96: strict private JSON parsing

This source-private hardening rejects duplicate JSON object keys at every
nesting level in both the independent convex Box preflight CLI and the
Wavefront OBJ export CLI. Python's default JSON decoder otherwise silently
accepts the last duplicate value, making ambiguous authored input appear
well-defined. The shared `load_private_json_text` helper also refuses
nonfinite JSON constants (NaN and Infinity).

## Reproduction

```sh
python -m unittest native_editor.tests.test_dx2sdk_private_json_strict -v
python -m dx2sdk.private_brush_preflight private.json
python -m dx2sdk.private_brush_obj private.json NEW.obj
```

Synthetic regression cases cover top-level and nested duplicate keys,
nonfinite constants, both CLI refusal paths, absent OBJ output on failure,
and a byte-unchanged mock original GMP sentinel.

This change only affects input validation for Godot-private Box brush
specifications and draft sidecars. It does not read or write original DX2
GMP/IBD files, generate native BSP surfaces, rebuild collision, or establish
retail-runtime compatibility. No licensed game assets are included.
