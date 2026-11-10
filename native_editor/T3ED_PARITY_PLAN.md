# T3Ed-to-DX2Ed capability port: source-grounded roadmap

**Direction:** recreate as much of the original Ion Storm T3Ed mission-authoring workflow as can be supported **for Deus Ex: Invisible War**, while retaining the Unity-like interface. The result should be an editor for DX2 missions, not a Thief 3 map opener or an unverified T3 binary transplant.
**Player-facing success criterion:** A player can import an original DX2 mission,
make a meaningful change to geometry, objects, properties, scripts or gameplay,
export a game-compatible mod, and load/play that modification in the original
Invisible War executable. Private Godot previews and byte-valid GMP candidates
are intermediate research milestones, not a completed SDK. T3Ed is the
capability reference; DX2-specific engine data and serialization remain the
source of truth. Experimental original StaticMeshActor Level-list removal is
tracked in docs/research/dx2ed-native-static-unplace-v0-59.md, but its
retail runtime effect is not yet verified.


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

## Current v0.60: first atomic native static-prop changes

The isolated DX2 v95 writer now supports an exact, source-pinned combined
edit plan in one GMP: existing `StaticMeshActor` Location translations,
new neutral-state duplicates and original Level-list unplacements. Godot
provides temporary unplace staging plus an explicit experimental combined
Save As, while retaining the existing single-operation writers. Each
operation reuses the conservative original export/name/neutral-frame
gate; the final GMP is independently regenerated byte-for-byte from the
original source.

**This is not yet a general T3Ed-style Save Map.** BSP, collision baking,
IBD resource authoring, typed class spawning, scripts/links and game
runtime acceptance are separate milestones. The next evidence gate is
controlled retail Windows gameplay: combine a moved prop with a new prop,
then combine a new prop with Level-list unplacement, verifying changed
visuals, collision, level re-entry, save/reload and original-map restoration.
See docs/research/dx2ed-native-prop-plan-v0-60.md.

## DX2Ed v0.61: portable JSON recipe export and rebuild

The Godot editor can now export a content-free source-SHA-locked JSON
recipe of combined v0.60 StaticMeshActor changes, and another player
with a byte-identical original GMP can read-only validate that recipe,
recompile the exact expected candidate and Save As to a separate
isolated GMP. The recipe contains only actor identities, coordinates,
edit instructions and GMP hash/size receipts, never any retail
GMP/IBD/mesh payload. Both authoring and receiving are accessible
through the Godot interface and standalone Python. A complete GMP
is regenerated byte-for-byte from each player's own original game.

This is not yet a final mod package or an installation workflow.
Combined native edits still need disposable-install retail tests before
we call them playable. See
docs/research/dx2ed-portable-mod-recipes-v0-61.md.

## DX2Ed v0.62: conservative source-only incoming actor references

The first native object-unplace prototypes could not detect when another
source actor already pointed to the targeted static prop. v0.62 adds a
read-only decoder audit across explicitly typed UE2 object/class
properties, GameSys object/class blocks, scripted object-link lists,
native script-frame node pointers and export table references. A confirmed
external reference blocks unplace in both the single and combined
source-SHA-pinned writers, including shared mod recipe reconstruction.
Godot refuses staging and Save As for known referenced originals.

This improves source evidence but **does not** provide a complete
reference graph. Unknown native arrays/tails, IBD/TriggerScript and
runtime collision/AI/save behavior are not decoded. "No known incoming
refs" must not be marketed as "safe native actor deletion." Original
exports remain serialized and retail gameplay needs separate A/B tests.
See docs/research/dx2ed-explicit-incoming-reference-audit-v0-62.md.

## DX2Ed v0.63 original GMP / IBD / TriggerScript evidence overlay

Building on the v0.62 explicit GMP incoming-object reference audit,
v0.63 cross-checks a selected original StaticMeshActor with independently
validated original TriggerScript ZIP and IBD resource identities.
The Scripts tab shows confirmed typed GMP links and TSD/IBD exact-
payload counts in a read-only dialog, recording a full private JSON
report outside game directories. The CLI verifies original GMP, actor
cache, ZIP and IBD hashes and refuses stale sources.

**Strict distinction:** exact source TSD/IBD bytes demonstrate resource
identity, NOT verified actor-to-script binding. Raw GameSys 92 integers
and package name-table offsets have not been proven to identify
runtime scripts. This tool does not modify native game packages or
turn absent known links into an actor-deletion safety claim.
See docs/research/dx2ed-crosssource-script-ref-review-v0-63.md.

## Immediate workflow

Use the parity tracker in code review and keep its `missing`, `partial`, `verified` labels conservative. Do not equate a working preview with a working mod. Next engineering step is the DX2 IBD **Asset Browser**, followed by typed actor properties. Each cross-over feature requires its own DX2 format tests, then Windows/Godot UI tests and in-game validation.

External corroboration: T3Ed is a derivative of UnrealEd used to make Thief 3 fan missions, but its edited source and cooked outputs differ. See https://worthplaying.com/article/2005/2/23/news/22704-thief-deadly-shadows-game-editor-available-now/ and https://github.com/Veradictus/Thief3-Decomp.


## v0.47: source render-section → MatLib name cross-reference

The original source collision picker already preserves a source MOPP-linked
Level triangle ID and its validated Flesh render block/section tuple, along
with the section's observed render-material name. DX2Ed v0.47 carries that
evidence into the Inspector and correlates the name with a user-imported
read-only MatLib catalog.

The panel distinguishes exact case-sensitive matches, case-insensitive-only
candidates, multiple candidates, and no match in the imported catalog. A
candidate exposes its source bundle, raw category/flags/stage mask, nine
ordered stage references and a hash-checked slot-0 texture thumbnail. The
source GMP basename/SHA and Level triangle/block/section IDs remain visible.

This is deliberately **not** called a native material binding. The join key is
the render-section name, not an independently decoded native material index.
The MatLib inventory deduplicates case-folded names and reports only a
catalog-wide duplicate count, so source-level uniqueness cannot be inferred.
Texture-stage semantics and Havok physical materials remain unverified, and
the panel has no writer. This adds a useful T3Ed-like surface inspection step
without crossing the DX2 native-format evidence boundary.


## v0.48: original source render-section topology subset Inspector

DX2Ed v0.48 adds a bounded read-only analysis of the MOPP terminal-leaf
triangles belonging to the selected original Flesh render-section tuple. It
reports exact source-weld connectivity, section-subset components, summed Level-unit
triangle area/bounds/centroid, MOPP-leaf edge-class counts, perimeter and cross-section
MOPP-shared edges, and adjacent MOPP-linked render sections. The report can be
copied as derived JSON without source bytes or paths.

The analysis cap is 8,192 section triangles and 1,024 incidences per touched
edge; either limit skips atomically without partial statistics. It is not a complete render section or BSP surface, and it does not
prove Havok runtime adjacency, physics materials, shader behavior or native
material identity. MOPP leaf connectivity and neighbor discovery remain
limited to the authenticated collision sidecar subset.


## v0.49: topology-guided section navigation and filled MOPP subset preview

DX2Ed adds a selectable adjacent-section list to the read-only source topology
Inspector. Neighbor links are derived from exact source-weld edge incidence
among authenticated MOPP terminal-leaf triangles. Each neighbor exposes the
lowest observed original triangle ID as a deterministic navigation target;
selecting it updates the main source-triangle Inspector and its provenance.

A separate **Fill MOPP subset** toggle draws the selected section's MOPP leaf
triangles as a translucent viewport overlay. It uses a bounded 8,192-triangle
payload and a display-only 0.0015 Godot-unit normal offset. Neither operation
writes source or private draft geometry.

This advances T3Ed-like section navigation and visual inspection, but does not
establish complete Flesh/BSP surface topology, native surface IDs, Havok
adjacency, physical materials, shader semantics or playable native level
authoring. The source remains a MOPP terminal-leaf subset only.


## v0.51: interactive exact-weld MOPP-subset edge selection

DX2Ed v0.51 turns the v0.50 edge overlay into a viewport interaction. A
camera-signature-cached 64-pixel screen-space index limits hover queries to
nearby edge candidates. The index is rebuilt when the camera transform,
projection settings or viewport size changes. Hover draws a transient
screen-width highlight; clicking selects an edge without changing the source
triangle selection.

The selected-edge Inspector exposes the exact original float32 weld-ID pair,
the selected MOPP-subset incident Level triangle IDs, local incidence, raw
source edge-class code (still uninterpreted), and any observed external
MOPP-linked section representative. It can navigate to a local incident
triangle or to the adjacent section's representative original triangle, and
copy a source-pinned read-only JSON record.

This is still **MOPP terminal-leaf subset interaction**, not complete Flesh
BSP edge/vertex picking, a native BSP surface identity, Havok adjacency,
walkability, physics material, or a writable map. Screen-space selection and
its highlights are transient editor overlays. No original GMP/IBD, imported
mesh or private draft geometry is changed.

## v0.52: exact-weld source vertex handles

DX2Ed v0.52 adds a **Show exact-weld vertex handles** toggle to the original
source-section topology Inspector. It derives a bounded vertex report from
the already validated v0.50 edge report, preserving exact original Level
float32 weld IDs, preview XYZ, incident edge keys, incident original Level
triangle IDs and observed adjacent-section representative triangles.

The 3D viewport displays transient editor-only MultiMesh handles. A
camera-aware screen-space index supports hover and click selection with a
12-pixel radius; camera movement, projection changes, near/far clipping,
aspect/offset changes and viewport resizing invalidate the index. The
selected-vertex Inspector can select an incident source triangle, navigate
to an adjacent MOPP-linked section representative and copy source-pinned
JSON.

This is a useful T3Ed-style vertex-inspection interaction, but its source
authority remains the authenticated MOPP terminal-leaf subset. It does not
establish native BSP vertex identity, complete render-section vertices,
Havok adjacency, physical materials, or a writable map. Native map writers
remain disabled.

## v0.53: independent quad viewport cameras and saved workspace

DX2Ed v0.53 adds a Single / Quad (2x2) viewport layout. The quad shows
Perspective, Top (XZ), Front (XY) and Side (ZY) simultaneously. Each pane owns
a separate Godot SubViewport and Camera3D, while all four viewports share the
same editor-only World3D scene. Camera target, zoom distance, yaw and pitch are
independent per view; hovering a pane routes selection, gizmos, polygon vertex
dragging and source-topology picking through that pane's camera and viewport
dimensions. Keys 1-4 jump to a canonical view and key 5 toggles Single / Quad.

The planar authoring grid is also isolated per viewport using separate
visibility layers and matching camera cull masks. This prevents the Top grid
from appearing in Front or Side, even though all panes share one preview
world. Hidden panes stop their render-target updates in Single mode to avoid
wasting four render passes.

Private prop-draft workspace metadata now records the layout, active view and
all four bounded camera states. Legacy v0.52 three-field workspace records
remain readable and migrate to a safe default camera set. Quad records require
exactly four view states with finite, bounded targets, distance, yaw and pitch;
malformed or non-finite camera state is rejected before current editor changes
are cleared. The state is still UI-only JSON metadata and never enters GMP,
IBD, BSP, MOPP, collision, lighting or gameplay serialization.

The T3SDK archive inventory includes separate viewer-state, map-viewer and
picking scripts, which supports treating viewport state and picking as
distinct editor concerns. DX2Ed's implementation is original Godot code;
no T3SDK source or binary was copied. The archive inventory is not evidence
that Thief 3 and DX2 share native geometry formats.

The four cameras render the same preview scene and read-only source overlays.
They do not establish native BSP topology, a playable native level, or
independent scene/world contents per pane.


## v0.54: active-pane orthographic transform gizmos

DX2Ed v0.54 assigns a private interaction cull layer to the currently hovered
viewport. Custom Polygon corner handles, the footprint wire and transform
gizmos render only in that active pane; imported geometry, material previews
and read-only source diagnostics continue to share the preview world. This
avoids the previous quad-view ambiguity where a gizmo shaped for one camera
was visible in all four panes.

Move and scale gizmos expose only the two axes visible in Top (X/Z), Front
(X/Y) or Side (Y/Z). Rotate exposes only the view-normal ring. Move adds a
small plane handle between the visible axes, allowing direct two-dimensional
translation in the orthographic plane. Ctrl snapping aligns the resulting
world pivot to the existing Grid m increment. Perspective retains all three
world axes.

The real Godot smoke creates an invented private Polygon, switches all four
views and all three tools, checks camera cull masks and handle identities,
drags the Top plane handle through the viewport ray, commits one Undo item,
performs Undo/Redo, then saves and reopens the transformed private draft.
The portable Windows doctor and self-test require the new smoke. No native
GMP/IBD/BSP/CSG/collision writer is enabled.

The reference T3SDK archive inventory lists separate viewer picking,
map-editor editing and edit-dock scripts. This supports keeping viewport
interaction and edit transactions distinct; the inventory is not source-level
proof of T3Ed's exact gizmo implementation, and no T3SDK code is copied.


## v0.55: transform pivots and local/world orientation

DX2Ed v0.55 adds Median / Active / 3D Cursor transform pivots, a visible editor-only 3D cursor and World / Local gizmo orientation. Perspective local axes follow the active selected object's orthonormal basis; orthographic views retain world-plane constraints. Cursor placement is one Undo/Redo transaction. The private workspace validates and persists the three preferences while continuing to migrate the earlier three-field and six-field workspace schemas. This advances the transform workflow but remains editor-private preview state, not native DX2 transform serialization.


## v0.56: private group hierarchy and parent transforms

DX2Ed v0.56 adds a Hierarchy-tab group-name field with Group selected / Ungroup actions. Selected editable preview meshes are reparented under an editor-only Node3D parent while preserving their world transforms. Selecting the group row expands selection to its member meshes but routes Move, Rotate, Scale, Inspector edits and viewport gizmos to the parent node; selecting a child row remains an individual transform. Multiple groups can be selected. Duplicating a selected group reconstructs a separate group, and Reset removes the selected group's private copies without touching original source files.

Group identity, parent transform and member names are optional additions to the existing private prop-draft JSON. The loader validates group names, unique member ownership, source/copy identities, finite bounded transforms, invertible parent bases and selected-group references before clearing the current editor state. Older drafts without groups remain readable. Scene unload ungroups original preview meshes back to their original parents before freeing the private copies and imported preview root. Group state is part of Undo/Redo.

The Godot 4.3 synthetic smoke exercises parent transforms, Hierarchy selection, group creation/ungroup, Undo/Redo, group duplication, reset, private Save/reopen and rejection of duplicate-member and singular-transform documents before mutation. The Windows prototype includes this same test. This is editor-private scene organization only: it does not prove T3Ed's exact implementation, native DX2 group ownership, native rotator conversion, BSP/CSG/leaf/zone/collision/lightmap behavior or a playable cooked map. No proprietary game assets or T3SDK source are bundled, and native writers remain disabled.
