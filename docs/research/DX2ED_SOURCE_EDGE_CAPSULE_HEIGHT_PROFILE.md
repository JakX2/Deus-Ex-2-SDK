# DX2Ed: source-exact edge capsule height profile (research)

**Stacked research milestone after PR #51** (and its #50 exact original-Level welded-neighbor cache). This is a *multi-height static-geometry contact profile*, **not** a Havok player walkability, clearance threshold, or step/slope classifier.

## Usage

1. Open an owner-supplied original `.gmp` using DX2Ed. Enable **Inspect source collision**.
2. Pick an original source collision triangle, and choose an authentic **Exact Source Edge Link** having one unique neighbor that meets the existing chosen floor-like slope/hinge and opposite-side horizontal conditions.
3. Choose **Interior fraction**, **Up offset**, **Capsule radius**, and **Half-axis** as for PR #51. The values are illustrative; no original DX2 player-capsule dimensions are known.
4. Under the same edge inspector, set **Height samples** (2 to 9, default 5) and **Height step** (0.1 to 10 original Level units, default 0.5). Choose **Profile capsule heights**.
5. DX2Ed rebuilds the baseline crossing chord from the *current authenticated original source v3 cache* rather than trusting supplied vector coordinates. It rejects invalid, ambiguous, stale, or forged original source edges. All profile heights are translated **up original Level +Z** relative to the starting chord (which already has its chosen **Up offset**). Total baseline Up offset plus sample rise must remain within 100 original Level units.
6. The already-vetted Python exporter loads and SHA-authenticates the owner GMP **once**, then evaluates the same finite edge-crossing chord independently for each height. Every sample runs the existing **whole-map fixed-axis capsule first-contact numerical oracle**, the separate **complete sweep geometry oracle**, and **conservative MOPP candidate inclusion** check. A mismatch refuses the entire export.
7. Results are written to one **new private JSON sidecar outside original Maps**, with the `DX2Ed-source-edge-capsule-height-profile-v1` schema. The capsule sweep panel lists relative heights, counts of original source triangles with *any geometric contact*, and first-contact original triangle IDs when present.

## Read the profile cautiously

- A sample with **no geometric contact** means only that this particular finite, fixed-axis, translated capsule chord had no static source-triangle contact under the offline oracle. It does **not** certify player traversal in DX2.
- A sample with **contacts** does **not** necessarily mean blocked movement. Original floor surfaces can supply supporting contacts; the profile does not classify support versus obstruction or solve a contact manifold.
- The currently validated height profile is a **text comparison and private JSON report**, not a new multi-color viewport overlay or a native collision export. The existing single-height **Probe capsule across edge** remains the way to render the PR #47 validated first-contact wireframe for one height.
- A raised straight chord is **not a floor-following walk path**. On hinged/sloped faces, height above the underlying surface may vary along the chord.
- Shape size, axis orientation, step/hinge thresholds, dynamic obstacles, gameplay collision filters, native Havok controller, and actual gameplay outcomes are **unverified**. Original game GMP/IBD are never modified or committed.

## Schema

Each `profile_samples` entry contains `relative_height_level_units`, `geometric_source_triangle_hits`, `first_hit_original_triangle_id`, `first_contact_path_t`, `first_contact_initial_overlap`, and `first_contact_near_tangency`. Absence of a first hit is represented by `null`, not an invented original triangle ID.

The sidecar also records the authenticated source map filename/SHA-256, original Level +Z direction, baseline Godot preview chord and shape parameters, and explicit **no walkability / no native Havok** flags. Per-triangle original retail vertices and raw MOPP bytes are not included. Outputs generated from original assets must remain private.

## Validation

- Python synthetic test `native_editor/tests/test_dx2_capsule_height_profile.py` checks low floor contact versus high empty geometry, original triangle identity and immutable source inputs, coordinate transform and relative offsets, bound refusals, source provenance failures, and the rule that wrong hashes may not create sidecars.
- Existing Godot 4.3 exact-edge headless fixture `smoke_source_edge_capsule_probe.gd` now also checks bounded profile height generation and enabled/disabled edge Inspector controls.
- The previous single-height exporter path remains backward compatible when `--height-offsets` is not supplied.

CLI for developer research, with original Level coordinates and an independently known SHA-256:

```bash
python research/dx2/export_capsule_first_contact_preview.py \
  --map /private/original/Maps/Example.gmp \
  --output /private/research/profile.json \
  --expected-sha256 <verified-original-gmp-sha256> \
  --start 8 8 1 --end 12 12 1 \
  --radius 0.2 --axis 0 0 1 --axis-half-length 0.5 \
  --height-offsets 0 0.5 1 1.5 2
```

**Pending owner verification:** actual Windows DX2Ed click-through on source-authenticated retail GMPs, performance on larger maps, and any real Havok runtime parity. CI synthetic fixtures do not replace those checks.
