# DX2Ed research: combining Invisible War maps without loading screens

**Status: design and feasibility plan, not an implemented writer.**

The core request is to let modders combine adjacent small retail DX2 maps
into a larger traversable area, inspired by the larger spaces available in
Deus Ex (2000). More modern PC hardware may provide additional performance,
but that alone cannot establish whether DX2's engine/runtime can load a
combined scene safely. It is necessary to distinguish the editor preview
from actual in-game behavior.

## Proposed milestones

1. **Read-only multi-map workspace.** Import two source GMPs into separate
   namespaced containers; render their BSP and static mesh previews together
   using explicit user-selected offsets. Display a boundary and transform
   overlays. Do not edit or overwrite either GMP.
2. **Dependency graph and provenance.** Record per-source GMP and companion
   IBD hashes; export/import/class object indices and names; LevelInfo,
   GameSys/archetype references, static mesh/texture/material dependencies,
   TriggerScript references, AI/pathing, ambient ZoneProperties and sounds.
   Flag dangling or ambiguous cross-map references rather than guessing.
3. **Runtime constraints audit.** Measure per-map actors, serialized object
   counts, BSP nodes/leaves/zones, lights, triangles and material usage.
   Reverse-engineer whether runtime imposes object, zone, streaming, memory,
   pathing or state limits independent of modern graphics hardware.
4. **Spatial assembly in preview.** Align adjacent maps with adjustable
   transforms and visualize overlapping/inaccessible boundary surfaces.
   Confirm coordinate and orientation transforms against known landmarks.
   Keep collisions and portals/zone visibility as separate, unsolved layers.
5. **Native merge research in an isolated output.** Only after reconstructing
   object-reference remapping, BSP/zone topology, collision, per-zone light
   metadata and lighting/precomputation, investigate a new combined GMP and
   corresponding resource package. Any test writer must independently parse
   and verify all untouched data and use exclusive Save As outside game dirs.
6. **Gameplay migration.** Resolve travel triggers/loading portals, quest and
   cutscene transitions, AI navigation, mission flags, conversation location
   dependencies, zone sound, save/load and persistent world-state rules.
   Run rollback-safe retail runtime tests on a pair of simple maps before
   attempting mission-scale merges.

## Explicit blockers

- A valid DX2 Level actor list is **not** a complete merged map.
- Current guarded StaticMeshActor duplication work does not rebuild BSP,
  zones, baked lighting or runtime actor initialization.
- Source Light actors use serialized `Region.iLeaf`,
  `Region.ZoneNumberLow` and a native state frame distinct from props.
  Copying them with old coordinates or zone fields is unsafe.
- Map resources may rely on mission-specific IBD packages, object indices,
  class names and script references that cannot simply be concatenated.
- The full in-game load/lighting/AI consequences of a larger combined level
  have not been established.

## First defensible deliverable

A **non-destructive two-map Godot viewport composer** with explicit map
transforms, namespace-safe actor identifiers, alignment markers and source
hash/provenance reports. This would immediately help modders design seamless
areas while giving the project hard evidence for the native writer research.
