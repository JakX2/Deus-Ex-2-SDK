# DX2Ed v0.63: combined GMP reference and TriggerScript IBD evidence

**Checkpoint:** 2026-11-10. **Status:** source-only, read-only research.
**Does not establish gameplay behavior or a complete actor-to-script graph.**

## Why this matters to a T3Ed-style Invisible War SDK

Deleting a placed actor involves more than deleting a rendered preview mesh.
DX2Ed v0.62 could already detect several explicit serialized links **inside
the GMP**. However, the retail game also loads original script-resource
bundles and binary TriggerScript definitions. Cross-source evidence matters
for understanding what an "unplace" might affect, while we have not yet
reverse-engineered the actor-to-script runtime binding.

Existing research independently verifies:
- Original GMP source actor identity and typed native reference links,
  via v0.62's incoming reference audit.
- Original TriggerScript ZIP source definitions versus byte-identical
  original IBD entries, via dx2_script_ibd_provenance.py.
- Raw GameSys property 92 numeric array values and original GMP name
  table, **without treating numeric matches as script identities**, via
  dx2_actor_script_name_candidates.py.

The v0.63 dx2_crosssource_ref_review.py tool combines these **existing
independent evidence pipelines** into one source-pinned report for a
selected original static actor. It does not guess links or edit game files.

## Inputs

1. The unchanged owner-original DX2 .gmp and exact SHA-256
2. The exact original actor name and one-based export ID
3. Source-pinned editor actors.json generated from that same GMP
4. Owner-original TriggerScript.zip
5. Original map or kernel .ibd containing TriggerScript resources

The tool verifies each source using existing parsers. If the map/cache
SHA, target identity, ZIP contents or IBD structure is inconsistent,
the operation is refused.

## Read-only terminal usage

Without an output path, only a brief JSON summary appears on stdout:

    python native_editor/package_writer/dx2_crosssource_ref_review.py --map "C:\RetailDX2\Content\DX2\Maps\M1_Example.gmp" --source-sha256 ORIGINAL_SHA256 --actor-export 123 --actor-name ORIGINAL_STATIC_PROP --actors "C:\DX2EdCache\actors.json" --scripts "C:\RetailDX2\Content\DX2\TriggerScript.zip" --ibd "C:\RetailDX2\Content\DX2\Maps\Kernel_TSDALL.ibd"

Add an optional private JSON report in a **different, non-game
directory**:

    --output "C:\DX2EdResearch\OriginalStaticPropReview.json"

The output cannot overwrite existing files or be written into the
original map, IBD, ZIP or parent game resource directory. The original
GMP, IBD and ZIP remain byte-identical.

## What is proven

- Exactly which **decoded GMP fields** in other exports explicitly
  point to the original actor: tagged UE2 Object/Class properties,
  GameSys object/class properties, actor links and export metadata.
- Independent source GMP SHA and target export name/Location.
- Whether each original IBD script resource has an **identical source
  payload** in the original TriggerScript ZIP, a differing payload,
  or lacks a source definition. Aggregate counts, not binary payloads,
  are included in the report.
- Whether the target appears among source actor rows containing
  original serialized TriggerScript property 92 and whether the native
  property could be independently re-decoded. This does not imply a
  verified binding.

Explicitly decoded GMP references block the v0.62 native unplace
exporter. An exactly matching IBD resource is **resource identity
evidence only**, not a reference to this actor.

## What remains UNPROVEN

These fields are always false:
- target_actor_to_script_binding_verified
- incoming_script_links_verified
- full_incoming_reference_graph_verified
- native_script_writer_enabled
- gameplay_runtime_verified
- safe_to_unplace_claimed

The GameSys 92 integer array has not been proven to encode TSD names or
IBD indices. Unresolved script logic, cross-map links, opaque native
tails, untyped arrays, AI, object lifetime, collision and game save/
reload behavior remain outside the audit.

No safety certificate is issued, even with zero confirmed GMP links.

## Automated evidence

Asset-free synthetic fixtures combine:
- A valid UE95 Level with two static actors, with and without one
  deliberately injected incoming tagged ObjectProperty.
- Original-style synthetic TriggerScript ZIP and one .tsd.
- Separately serialized synthetic IBD with exact matching and
  deliberately different script resources.
- Source-hashed actor cache for that original GMP.

Tests verify SHA locking, source preservation, typed GMP link counts,
TSD/IBD provenance without invented actor links, read-only CLI mode,
private JSON export, refusal of game-root or overwrite destinations,
and rejection of stale source/cache hashes.

The Windows prototype ZIP and doctor include the reader. For now it is
a research CLI using original files available to source browsing, not a
native script authoring UI or an in-game runtime test.

## Next gates

1. Collect actual original-source reports for a few nonessential static
   props and script-heavy actors.
2. Identify GameSys 92 dispatch semantics through real source evidence.
3. Reconstruct missing incoming references and engine ownership.
4. Conduct controlled backed-up retail A/B tests for unplace,
   collision, level re-entry and save/reload.
5. Develop typed actors, scripts, geometry/BSP/collision and mod
   packaging toward T3Ed-level DX2 mission authoring.
