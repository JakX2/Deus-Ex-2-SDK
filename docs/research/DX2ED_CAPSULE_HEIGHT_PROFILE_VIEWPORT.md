# DX2Ed: authenticated capsule-height profile viewport lines

Research extension stacked on the multi-height source-exact capsule PR #52 (itself stacked on PR #51). **No original GMP/IBD modification, no Havok player collision, no native MOPP writer.** This is a *contact-visualization aid*.

## Interactive use

1. Inspect an original owner-provided GMP with **Inspect source collision** and its v3 SHA-authenticated source exact-welded cache.
2. Select a verified *unique* source-edge neighboring pair and choose **Profile capsule heights**, as documented in `DX2ED_SOURCE_EDGE_CAPSULE_HEIGHT_PROFILE.md`.
3. Once the existing read-only Python worker completes and its private output passes schema, source SHA, requested trajectory, shape and sample checks, DX2Ed draws an editor-only bundle of the finite tested crossing paths at their sampled original Level +Z offsets:
   - **Cyan line:** no original source triangle contact along that sampled finite capsule sweep in the offline oracle.
   - **Amber line:** at least one source-triangle geometric contact. **This can include normal floor support.**
   - **Pink X:** earliest *path parameter* where the independent numerical first-contact result reported an original source triangle. It is a centerline time marker, **not** the actual triangle contact point.
4. Use **Clear height paths** to remove the editor-only drawing. It also clears on **Clear points**, a new pick, a new generated edge-crossing probe, source-inspection reset, or a map change. Markers are attached only to DX2Ed's `world_root`, not to loaded GLB, actor draft contents or game collision meshes.

The text profile and the private JSON remain the primary source for counts, original triangle IDs and near-tangency/initial-overlap flags. Single-height **Probe capsule across edge** continues to use the separately verified PR #47 detailed first-contact capsule wireframe.

## Trust boundary

The viewport refuses a worker-supplied height profile unless all of the following agree with the *current* read-only editor's original GMP and pending worker request: source map filename, 64-character original SHA, schema, coordinate system, read-only/non-Havok flags, original Godot preview baseline start/end, capsule radius and axis half-length, sample count, ordered relative offsets, original triangle ID domain, first-contact time bounds, nullability of no-contact rows, and worker's contact-count/first-hit consistency.

A document can only be rendered in the editor when **Inspect source collision** is still active and hash-matched. The Python exporter has independently checked each sample's full-source triangle hits, separate first-contact oracle, and conservative MOPP candidate inclusion before writing the private JSON. The overlay does **not** reinterpret a contacting floor as impassable or a no-hit as traversable. Source geometry/physics materials, player controller shape, Havok filters and dynamic actors remain outside the proof.

To prevent accidental original-content distribution, never commit or upload private profile JSON generated from retail GMPs. Synthetic CI fixture JSON is entirely invented and contains no licensed map geometry.

## Automated evidence and limitations

- `native_editor/godot_editor/source_edge_capsule_height_overlay.gd`: strict result validator, cyan/amber paths, contact-path markers.
- `native_editor/godot_editor/capsule_sweep_panel.gd`: fresh-result handoff, overlay lifecycle, explicit **Clear height paths** control.
- `native_editor/godot_editor/tests/smoke_source_edge_capsule_height_overlay.gd`: eighth independent Godot 4.3 headless smoke fixture, testing valid synthetic profile, invalid hashes/source IDs/numbers/offsets, generated line geometry and cleanup.
- `.github/workflows/native-dx2ed.yml`: eighth headless fixture.

**Still required:** manual Windows DX2Ed test on original authorized GMPs, comparison to actual gameplay/Havok traces, and larger map performance tests. This feature remains a **draft research experiment** until those checks occur.
