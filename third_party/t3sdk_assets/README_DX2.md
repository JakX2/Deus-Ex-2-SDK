# T3SDK source reuse and original editor reference policy

## Vendored T3SDK contributor code

Upstream: https://github.com/Veradictus/Thief3-Decomp
Pinned upstream snapshot: `6b5789f9d4645e384064d9f0a532962b20af498f` (main, 2026-10-24).
License: **MIT**, see [LICENSE](LICENSE).

These files are copied verbatim from upstream `tools/assets/`:

| Vendored file | Upstream Git blob SHA-1 | Purpose |
|---|---|---|
| `t3common.py` | `315bff659b91c924940086f9de108eaa522ae380` | Binary reader and shared utilities |
| `upkg.py` | `3036e2b0864ff94f65a2182541e20c65ce26874c` | Unreal package reader |
| `upkgwrite.py` | `d0f5e0612e91e5f5817d5b1984a80f120ac9f3ab` | Unreal package writer |
| `formats.json` | `493d0a1cb6ed068bbc9976d936b5376842a4002f` | Tool format metadata |
| `t3props.py` | `6036ac4dc52e202bce6fd62b6eb919813f3b2025` | T3-specific typed game property metadata reference |
| `t3pack.py` | `5c2f9e5429914298e457334df6c57523790ba5c8` | T3-specific actor edit/installation reference |
| `t3gamesys.py` | `b7b34a74143552b220e86b7f3c189fe21c4773db` | T3 class archetype reader; experimental DX2Gamesys read-only compatibility |
| `LICENSE` | `76e2b4bc5fc14b9098a556d5dec0b5e60d772693` | Required MIT attribution and license grant |

The accompanying SDK tests check Git-blob hashes to flag accidental edits
to upstream snapshots. **Keep adapted DX2-specific code outside this
directory**, retaining origin and license notices in derived files.

### Compatibility boundaries

- `upkg` and `upkgwrite` are exercised through the **fail-closed**
  DX2 adapter in `native_editor/package_writer/`. Currently supported:
  original file byte-identical no-op reconstruction and an in-memory
  cross-check against the independently implemented Location-only DX2
  serializer. They have **not** been approved for arbitrary native
  object edits or full BSP builds.
- `t3props` and `t3pack` are included **as reference implementations
  only**. Their original T3 class tables, editor defaults, installation
  logic, saved game conventions and Thief package paths are not DX2 data.
  **Do not run T3 package install/restore functions against Invisible War**.
- T3 IBT and DX2 IBD resource table layouts differ, so upstream IBT code
  cannot be used as a drop-in IBD writer.
- No original retail GMP, IBD, TSD or game art files are shipped here.

## Original 2005 Ion Storm T3Ed files

The public T3Ed archive (`thief3editorrelease_jan2005.zip`) is valuable
for researching authoring workflows, UI controls, file formats and developer
tool behavior. **Public availability is not evidence of an MIT or other
general redistribution license for its executable, textures or original
game assets**. The complete archive was inspected for license/readme
filenames without finding a blanket reuse grant.

For the DX2SDK public repository, document observations and use
T3Ed on developers' own machines without checking original binaries
or art into Git. If specific additional redistribution terms emerge,
evaluate those separately. This restriction doesn't apply to the
above explicitly MIT-licensed contributor-authored T3SDK source files.
