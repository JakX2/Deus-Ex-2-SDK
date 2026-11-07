# DX2SDK v0.27: unified Godot editor and private package audit

**Status:** source-only DRAFT integration; no retail assets or game-runtime
compatibility tests. The existing Godot editor is a usable experimental UI,
not an UnrealEd/T3Ed-equivalent native BSP/CSG compiler.

## Architectural milestone: formerly diverged branches now coexist

This branch is the **two-parent merge** of:

- the v0.26 private DX2 package ZIP research stack, formerly PR #93,
  including the strict DX2 export-table audit, DX2 legacy reader and
  T3SDK/Thief3 third-reader name/import/export concordance; and
- the v0.19 Godot v4.3 Actor Workbench editor stack, formerly PR #86,
  including single-original-mesh viewport selection handoff, original
  actor navigation, property categories/search/staged comparisons, and
  guarded existing native scalar/LightColor Save As controls.

The two tips descended from v0.17 and had **zero overlapping changed file
paths**. The integration copied the 16 editor tree entries (original blob
identities) into the latest research tree, then created a merge commit with
**both parents**. No original PR was merged into main or discarded.

## Practical end-to-end workflows

1. On Windows, download the source-only DX2Ed Godot 4.3 prototype artifact
   from this branch's successful Windows CI, extract to a user-writable
   directory outside the retail game, then run **START_DX2ED.cmd**.
   The package includes the versioned \`dx2sdk\` source-only CLI as well.
2. Run \`START_DX2ED.cmd --self-test\` to perform the source-only Godot
   fixtures. The CI launch smoke also uses the bundled official Godot
   runtime. Open the generated demo before importing an original map.
3. Import a locally owned original GMP. After the existing source SHA/cache
   gates pass, select a single original positioned StaticMeshActor mesh.
   Use **Inspect original actor in Workbench**, then browse the actor's
   source-original categories and existing tags. Eligible existing
   numeric/LightColor controls support staged preview and explicitly gated,
   isolated Save As with byte-replay verification. Some original classes
   and layouts remain read-only; the source game is never overwritten.
4. The **new public SDK command** can audit a locally stored ZIP of
   original map packages entirely in memory, without extracting them:
   ~~~bat
   DX2SDK_CONSOLE.cmd audit-map-zip --archive "D:\PrivateDX2\maps.zip" --max-files 512
   ~~~
   In the standalone Python source ZIP, use \`RUN_DX2SDK.cmd\` in place of
   \`DX2SDK_CONSOLE.cmd\`. Optional \`--sha256\` takes an independently
   computed lowercase SHA-256 of the entire ZIP; the command refuses
   mismatched hashes before parsing any member.

   The return contains only aggregate validated/rejected counts and
   explicit non-authority flags. It prints **no actor/map names, payloads
   or offsets**, writes no files, and never extracts the archive.

## Bundling and CI evidence gates

- Both Windows Godot and portable Python builds declare SDK **0.27.0** and
  include the research auditor dependencies, existing Actor Workbench
  modules, and the full source-only SDK code. Packaging refuses omissions.
- The source manifest signals that actor Workbench handoff and archive
  auditing exist, while independently verified DX2 native BSP/zone ownership,
  retail gameplay runtime and arbitrary native writes **do not**.
- A synthetic extracted-portable-ZIP regression test invokes the new
  \`python -B -m dx2sdk audit-map-zip\` on a wholly invented DX2 package ZIP,
  verifies one accepted member and one malformed member, confirms
  SHA mismatch rejection and unchanged ZIP bytes, and checks for absence
  of private name/path leakage.
- The Windows CLI workflow runs the public archive-auditor help command
  using the actual extracted \`RUN_DX2SDK.cmd\`. The prototype doctor
  also validates this subcommand in the extracted Godot distribution.
- Exact tests, original game evidence and release artifacts must be
  verified from the draft PR's CI, not inferred from source availability.

## Explicitly not delivered

This does **not** decode or reconstruct authenticated native DX2 BSP
leaves/zone-portals, perform level-lightmap/collision rebuilds, cook original
Ion Storm resources, spawn arbitrary new native actors, implement complete
GameSys / TriggerScript writers, or establish in-game acceptance of edited
GMP files. Original DX2 retail packages are excluded from GitHub and CI.
The current strict/legacy/Thief readers share package-format assumptions,
so concordance alone is insufficient for writer authorization.

**Next major milestones:** privately verify real package identity and
primitive BSP/zone byte layouts against owner originals, then implement a
genuinely useful **read-only native geometry/leaf visualization** in the
unified Godot viewport before attempting bounded geometry authoring.
