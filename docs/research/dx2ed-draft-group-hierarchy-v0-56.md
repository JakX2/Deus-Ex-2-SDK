# DX2Ed v0.56: private group hierarchy and parent transforms

**Checkpoint:** 2026-11-09  
**Scope:** editor-only Godot preview hierarchy, private JSON drafts, and reversible group transforms.

## User-facing workflow

The Hierarchy tab now exposes a group-name field plus **Group selected** and **Ungroup** actions. Select two or more editable preview meshes, enter a short ASCII name (letters, digits and underscores), and create a group. DX2Ed creates a real Node3D parent beneath the editor-only DX2Ed_DraftGroups_EDITOR_ONLY root, then reparents the selected preview meshes with Godot's keep-global-transform operation. The initial group pivot is the median of the selected mesh origins, so grouping does not visibly move or rotate the members.

Selecting a group row selects all of its member meshes while the transform system targets the single parent node. Move, rotate, scale, Inspector transforms, orthographic gizmos and local-orientation axes therefore operate on the parent; child local transforms remain intact. Selecting a member row instead targets that mesh individually. Multiple group rows can be selected together. Ungroup reparents members to their remembered original preview parents while preserving their world transforms.

Duplicating a selected group duplicates its members and reconstructs a separate parent group. Resetting a selected group ungroups it first, restores original actor preview transforms and deletes only the selected private copies. Group creation, deletion, duplication and parent transforms are included in Undo/Redo snapshots.

## Private draft persistence and preflight

The existing DX2Ed-prop-draft-v1 JSON schema remains backward compatible. New documents add optional groups and selected_groups arrays. Each group stores a bounded name, a 12-number Godot parent transform, and a unique list of original actor mesh / private draft-copy identities. Child world transforms continue to use the existing moved and copies records. On reopen, the group parent is reconstructed first and members are reparented while preserving their saved world transforms, restoring the same local offsets and future parent-transform behavior.

Before the current editor state is changed, group preflight rejects unknown members, duplicate group names, duplicate membership across groups, malformed or non-finite transforms, singular parent bases, out-of-bounds basis magnitudes, invalid names, and invalid selected-group references. Legacy drafts without group metadata still load as ungrouped scenes. Scene unload explicitly ungroups members back to their remembered source-preview parents before freeing private copies or the imported preview root.

## Evidence and limits

The Godot 4.3 regression creates synthetic Polygon previews plus a synthetic actor mesh. It checks world-transform preservation during grouping, parent-driven child transforms, Hierarchy-tree selection, Undo/Redo, private save/reopen, rejection of duplicate-member and singular-matrix documents before mutation, group duplication, and reset. The Windows prototype self-test includes the same smoke.

This is a useful T3Ed-style hierarchy milestone, not proof of Thief 3's exact group implementation or native DX2 object ownership. The T3SDK inventory in the parity plan identifies separate editor/viewer concerns but does not establish that the two games share scene or BSP formats. No direct Google Drive connector was exposed during this run, and the Library search did not return a relevant T3Ed grouping source; no proprietary T3SDK code was copied.

All group nodes and membership remain private Godot editor state. They are not serialized into GMP/IBD/BSP/CSG/leaf/zone/collision/lightmap/TriggerScript/GameSys data. Original retail files remain read-only. No native playable custom-level claim is made.
