# T3Ed-to-DX2Ed capability port: source-grounded roadmap

**Direction:** recreate as much of the original Ion Storm T3Ed mission-authoring workflow as can be supported **for Deus Ex: Invisible War**, while retaining the Unity-like interface. The result should be an editor for DX2 missions, not a Thief 3 map opener or an unverified T3 binary transplant.

See [t3ed_parity.json](t3ed_parity.json) for the machine-readable 23-area tracker. Status describes **DX2Ed**, not T3Ed.

## Evidence inspected: supplied original archives

The user provided `thief3editorrelease_jan2005(1).zip` and `T3SDK-Launcher_0.3.1_portable(1).zip`. The original 2005 editor archive contains:

- `System/T3Ed.exe`, original editor resources under `System/EditorRes/`, and `content/T3/Maps/` with **37 .unr source maps** and **4 .gmp game maps**.
- `System/EditorRes/ModeAdd.bmp`, `ModeSubtract.bmp`, `ModeIntersect.bmp`, `ModeDeintersect.bmp`, `ModeVertex.bmp`, `ModeFaceDrag.bmp`, `ModePolygon.bmp`, `ModeBrushClip.bmp`, `ModeTerrainEdit.bmp`, `ModeAddStaticMesh.bmp`, `ModeAddVolume.bmp`, `ModeAddLinks.bmp`, `ModeConnectPaths.bmp`, `ModeEditAttachedLight.bmp` and `ModeMatinee.bmp`.
- Brush/shape icons for **cubes, cones, cylinders, spheres, linear/curved/spiral stairs, sheets, terrain**; UV manipulation buttons `TexturePan.bmp` and `TextureRotate.bmp`.
- Asset and scripting infrastructure: **3,473 .tsd**, **15,411 .sch**, **4,125 .dds** entries (including user-owned original data). The archive also includes 3ds Max plug-ins and scripts such as `StaticMeshExp4.DLE`, `CollisionMaker.ms` and `BatchExportStaticMeshTimFiles.ms`.
- `System/DEFAULT.INI` points to separate static/skeletal mesh publishing paths, sound schema paths, dynamically loaded textures and Books resources.

The modern T3SDK launcher archive is **a separate, third-party codebase**, not Ion Storm's 2005 T3Ed source. It contains `tools/assets/t3map.py`, `t3gamesys.py`, `t3mesh.py`, `t3save.py`, `ibtwrite.py`, `upkgwrite.py`, and Godot scripts `t3_edits.gd`, `t3_pick.gd` and `edit_dock.gd`. Its placement changes, diff tracking and package writer are useful **technical references**, not drop-in DX2 parsers. Check each upstream file's license before adapting code.

**Evidence limits:** an icon, file extension or DLL name establishes that the archive includes that tool/resource, not that we have verified its runtime behavior or binary interoperability. Unpacking is not running the original editor. Do not publish source retail files.

## Crucial format boundary

- Original **T3Ed .unr** retains authoring information. T3's .gmp is a game map. Our supplied DX2 maps are **retail .gmp**, with paired IBD bundles, so missing editor-native metadata might be unrecoverable.
- T3Ed tools are not guaranteed to understand DX2 actor classes, physics, scripts, lighting, collision, shader properties, IBD structures or cooked resources.
- We should maintain a **DX2Ed source project**, with non-destructive CSG brushes, actor placement and links. Build validated DX2-specific binary writers separately. A GLB preview or JSON prop draft is **not** yet a playable DX2 mission.

## Priority 1: core authoring shell (next)

1. **Asset Browser**: enumerate all DX2 IBD static meshes, textures and material definitions, including unplaced resources, provenance and collision warnings. Preview decoded assets; place original meshes as draft actors using source mesh name and temporary editor ID.
2. **Typed actor/component Inspector**: derive classes, inheritance and properties from DX2Gamesys/Editor and actor records. Distinguish decoded native properties from unknown data. Edit supported scalar/enum/string fields with undo; do not silently drop unknown fields.
3. **Source IDs, provenance and selections**: stable native export indices, mesh resource references, clone lineage, read-only raw value panel. Selection/isolation and actor links.
4. **Transform truth tests**: compare DX2 rotator matrices, mesh-local pivots, scale components, and runtime placement on several maps. No global flipping based on one staircase.
5. **Editable project file**: explicit versioned DX2Ed scene project containing authored edits; preserve source map hashes and record unresolved round-trip constraints.

## Priority 2: level geometry and visual authoring

- Primitive brushes; additive/subtractive CSG; clipping and vertex/polygon/face editing.
- Surface texture selection, UV scale/pan/rotate, material variants and light/volume placement.
- Dedicated viewport overlays, orthographic modes, grid snapping, hidden/locked items, prefab/group reuse.
- For **native output**, decode/rebuild DX2 BSP, collision, portal data and game-linked placement. Do not write broken-looking render meshes into GMP.

## Priority 3: gameplay systems

- Type-safe link/trigger graph and TriggerScript editing; preserve binary event and object references.
- DX2-specific AI/patrol/navigation links, NPCs, conversations, sound schemas, inventory/loot and mission objective logic.
- Edit and validate collision, rigid-body/Havok-style data and separate render/physics resources without assuming a `StaticMeshActor` is physical.

## Priority 4: DX2 compiler, package builder and mod distribution

- Reversible **Save As** to a fresh GMP/IBD only once serialization, checksums, links and runtime load are validated. Keep backups and refuse in-place retail writes.
- New mission creation, cooking/compilation, mission entry points, travel, localization and reproducible packaging.
- Test both clean installs and modded installs; automated import/export/round-trip checks.

## Milestone acceptance tests

- A scene with 0 modified objects exports no changes; a move/rotate/skin change round-trips without unexpected actors or source mutations.
- A mesh added from the asset browser can be reloaded with a stable source ID and correct resource/material reference.
- A primitive BSP brush survives saving, reload, collision rebuild and actual game playtest before being marked **verified**.
- A linked trigger/objective chain remains functional after Save As and reload; unknown native fields survive unchanged.
- A new mission launches in original DX2 **without replacing or corrupting retail packages**.

## Immediate workflow

Use the parity tracker in code review and keep its `missing`, `partial`, `verified` labels conservative. Do not equate a working preview with a working mod. Next engineering step is the DX2 IBD **Asset Browser**, followed by typed actor properties. Each cross-over feature requires its own DX2 format tests, then Windows/Godot UI tests and in-game validation.

External corroboration: T3Ed is a derivative of UnrealEd used to make Thief 3 fan missions, but its edited source and cooked outputs differ. See https://worthplaying.com/article/2005/2/23/news/22704-thief-deadly-shadows-game-editor-available-now/ and https://github.com/Veradictus/Thief3-Decomp.
